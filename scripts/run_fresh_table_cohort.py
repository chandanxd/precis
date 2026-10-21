"""Fresh table-bearing cohort run (protocol: experiments/fresh_table_cohort/PROTOCOL.md).

  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_fresh_table_cohort.py
Resumable; writes experiments/fresh_table_cohort/{manifest.jsonl,records.jsonl}.
"""
import hashlib, inspect, json, random, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.api.security import sanitize_document
from precis.evaluation.naive_rag import naive_rag_retrieve
from precis.graph.store import FactStore
from precis.pipeline import orchestrator, structural
from precis.pipeline.inference import generate_answer
from precis.pipeline.orchestrator import assemble_query_context, ingest_document
from eval_experiment_4_2_threshold import build_table_retention_context
from eval_table_selection_v2 import check_containment, check_exact_match

D = ROOT / "experiments/fresh_table_cohort"
MANI, REC = D / "manifest.jsonl", D / "records.jsonl"
NQ = ROOT / "backend/data/nq_subset/nq_dev.jsonl"
BASE, MODEL = "http://127.0.0.1:11434", "qwen2.5-coder:7b"

# ---- variant F2: current assembly without the same-document suppression ----
_src = inspect.getsource(structural.assemble_structural_query_context)
_src = _src.replace("if f.source_doc and f.source_doc in packed_struct_docs:", "if False:")
_src = _src.replace("if subj and obj and (subj in struct_combined_content) and (obj in struct_combined_content):", "if False:")
assert _src.count("if False:") == 2
_ns = dict(structural.__dict__); exec(_src, _ns)
F2_FN, G_FN = _ns["assemble_structural_query_context"], orchestrator.assemble_structural_query_context


def used_ids_and_questions():
    ids, qs = set(), set()
    for p in ROOT.glob("results/**/sample_manifest*.jsonl"):
        for l in p.open():
            r = json.loads(l)
            for k in ("sample_id", "doc_id", "id"):
                if r.get(k): ids.add(r[k])
            if r.get("question"): qs.add(r["question"])
    for p in (ROOT / "experiments").glob("*/sample_manifest.jsonl"):
        for l in p.open():
            r = json.loads(l)
            for k in ("sample_id", "doc_id", "id"):
                if r.get(k): ids.add(r[k])
            if r.get("question"): qs.add(r["question"])
    ids |= set(json.load(open(ROOT / "results/diagnostic_structural_decompilation_v3/historical_exclusions.json"))["ids"])
    ids |= set(json.load(open(ROOT / "backend/data/nq_subset/reconstructed_facts_cache_v3.json")))
    return ids, qs


def build_manifest():
    ids, qs = used_ids_and_questions()
    recs = [json.loads(l) for l in NQ.open()]
    qs |= {r["question"] for r in recs if r["doc_id"] in ids}
    cand = []
    for r in recs:
        low = r["document"].lower()
        if r["doc_id"] in ids or r["question"] in qs: continue
        if not ("<table" in low or "<ul" in low or "<ol" in low): continue
        try: sanitize_document(r["document"])
        except ValueError: continue
        cand.append(r)
    byq = {}
    for r in cand: byq.setdefault(r["question"], []).append(r)
    rnd = random.Random(42)
    questions = sorted(byq); rnd.shuffle(questions)
    sel = [rnd.choice(byq[q]) for q in questions[:200]]
    h = hashlib.sha256(",".join(r["doc_id"] for r in sel).encode()).hexdigest()
    with MANI.open("w") as f:
        f.write(json.dumps({"type": "header", "seed": 42, "n": len(sel), "manifest_hash": h, "excluded_ids": len(ids),
                            "excluded_questions": len(qs), "candidates": len(cand), "distinct_candidate_questions": len(byq),
                            "protocol_sha256": (D / "PROTOCOL.sha256").read_text().split()[0]}) + "\n")
        for r in sel:
            low = r["document"].lower()
            f.write(json.dumps({"sample_id": r["doc_id"], "question": r["question"], "gold_answer": r["gold_answer"],
                                "answers": r.get("answers") or [r["gold_answer"]],
                                "has_table": "<table" in low, "has_list": "<ul" in low or "<ol" in low}) + "\n")
    return sel


def gen(q, ctx, gold, answers):
    if not ctx.strip():
        return {"pred": "", "em": False, "cont": False, "status": "empty_context", "prompt_tokens": None}
    res = generate_answer(query=q, context=ctx, model=MODEL, temperature=0.0, top_p=0.9, max_tokens=512,
                          prompt_style="concise", base_url=BASE)
    p = (res.answer or "").strip()
    return {"pred": p, "em": check_exact_match(p, gold, answers) if p else False,
            "cont": check_containment(p, gold, answers) if p else False,
            "status": "ok" if p else "empty_answer", "prompt_tokens": res.prompt_tokens}


def est(ctx):
    return structural.estimate_text_tokens(ctx) if ctx else 0


def main():
    if not MANI.exists(): build_manifest()
    rows = [json.loads(l) for l in MANI.open()][1:]
    docs = {}
    for l in NQ.open():
        r = json.loads(l)
        docs[r["doc_id"]] = r["document"]
    done = {json.loads(l)["sample_id"] for l in REC.open()} if REC.exists() else set()
    with REC.open("a") as fo:
        for i, m in enumerate(rows, 1):
            sid = m["sample_id"]
            if sid in done: continue
            raw, q, gold, answers = docs[sid], m["question"], m["gold_answer"], m["answers"]
            t0 = time.time(); clean = sanitize_document(raw); ctxs = {}
            ch, _ = naive_rag_retrieve(document=raw, query=q, top_k=5, chunk_size=512, overlap=128)
            ctxs["N_raw"] = "\n\n".join(ch) if ch else ""
            ch, _ = naive_rag_retrieve(document=clean, query=q, top_k=5, chunk_size=512, overlap=128)
            ctxs["N_clean"] = "\n\n".join(ch) if ch else ""
            ctxs["D"], _ = build_table_retention_context(raw_doc=raw, query=q, table_threshold=0.0)
            store = FactStore(in_memory=True, collection_name=f"fresh_{i}_{sid[:10]}")
            ingest_document(text=clean, source_doc=sid, store=store, enable_list_extraction=True, raw_document=raw)
            orchestrator.assemble_structural_query_context = F2_FN
            f2 = assemble_query_context(query=q, store=store, token_ceiling=2048, enable_list_extraction=True, raw_document=None)
            orchestrator.assemble_structural_query_context = G_FN
            g = assemble_query_context(query=q, store=store, token_ceiling=2048, enable_list_extraction=True, raw_document=None)
            ctxs["F2"], ctxs["G"] = f2.context, g.context
            row = {"sample_id": sid, "question": q, "has_table": m["has_table"], "has_list": m["has_list"],
                   "f2_use_structural": f2.use_structural, "g_use_structural": g.use_structural,
                   "f2_tokens": f2.tokens_used, "g_tokens": g.tokens_used, "g_facts_packed": g.facts_packed,
                   "gold_in_any_table": None}
            for c, ctx in ctxs.items():
                r = gen(q, ctx, gold, answers)
                r["context"] = ctx; r["est_tokens"] = est(ctx)
                row[c] = r
            fo.write(json.dumps(row) + "\n"); fo.flush()
            print(i, sid[:8], {c: row[c]["em"] for c in ctxs}, round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
