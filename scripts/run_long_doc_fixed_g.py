"""Repaired guarded packing (G2) on a fresh long-document draw (protocol: experiments/long_doc_fixed_g/PROTOCOL.md).

  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_long_doc_fixed_g.py build
  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_long_doc_fixed_g.py run      # resumable
Data construction and eligibility are those of scripts/run_long_doc_cohort.py; the questions of that cohort are excluded.
"""
import hashlib, inspect, json, random, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.api.security import sanitize_document, sanitize_document_layout
from precis.evaluation.naive_rag import naive_rag_retrieve
from precis.graph.store import FactStore
from precis.pipeline import structural
from eval_table_selection_v2 import check_containment
from run_baseline_budget import G_FN, est, g_context, gen, html_blocks, md_doc, retrieval_arms, trim
from run_long_doc_cohort import MIN_WORDS, earlier_questions, examples, ingest_with_retry, table_regions

D = ROOT / "experiments/long_doc_fixed_g"
MANI, REC = D / "manifest.jsonl", D / "records.jsonl"
DOCS = ROOT / "backend/data/nq_full/long_docs_fixed_g.jsonl"
FIRST = ROOT / "experiments/long_doc_cohort/manifest.jsonl"
CEIL = 2048

# ---- G2: the two changes of the protocol, applied to the source of G
REF_PAT = re.compile(r"Jump up|Retrieved|Archived from|ISBN|doi\s*:|Wikimedia Commons|Official website|External links", re.I)


def is_reference_boilerplate(content):
    lines = [l for l in content.split("\n") if l.strip() and not l.startswith("###") and not l.startswith("| ---")]
    if not lines:
        return True
    return sum(1 for l in lines if REF_PAT.search(l)) / len(lines) >= 0.30


_src = inspect.getsource(structural.assemble_structural_query_context)
for old, new in (
    ("        if f.source_doc and f.source_doc in packed_struct_docs:\n", "        if False:\n"),
    ("    for item, sim in struct_candidates:\n        searchable_lower",
     "    for item, sim in struct_candidates:\n        if is_reference_boilerplate(item.content):\n            continue\n        searchable_lower"),
):
    assert _src.count(old) == 1, old
    _src = _src.replace(old, new)
_ns = dict(structural.__dict__); _ns["is_reference_boilerplate"] = is_reference_boilerplate
exec(_src, _ns)
G2_FN = _ns["assemble_structural_query_context"]


def build():
    proto = (D / "PROTOCOL.sha256").read_text().split()[0]
    used = earlier_questions()
    used |= {" ".join(json.loads(l)["question"].lower().split()) for l in FIRST.open() if '"question"' in l}
    counts = {"examples": 0, "no_short_answer": 0, "no_table": 0, "too_short": 0, "input_limit": 0, "used_earlier": 0}
    pool = {}
    for r in examples():
        counts["examples"] += 1
        q = r["question"]["text"]; ann = r["annotations"]
        sas = [sa for sa, yn in zip(ann["short_answers"], ann["yes_no_answer"]) if sa["text"] and yn == -1]
        if not sas: counts["no_short_answer"] += 1; continue
        tok, is_html = r["document"]["tokens"]["token"], r["document"]["tokens"]["is_html"]
        h1 = tok.index("<H1>") if "<H1>" in tok else 0
        if "<Table>" not in tok[h1:]: counts["no_table"] += 1; continue
        words = sum(1 for t, h in zip(tok[h1:], is_html[h1:]) if not h)
        if words < MIN_WORDS: counts["too_short"] += 1; continue
        doc = " ".join(tok[h1:])
        try:
            sanitize_document(doc); sanitize_document_layout(doc)
        except ValueError:
            counts["input_limit"] += 1; continue
        if " ".join(q.lower().split()) in used: counts["used_earlier"] += 1; continue
        answers = []
        for sa in sas:
            for t in sa["text"]:
                if t not in answers: answers.append(t)
        st = sas[0]["start_token"][0]
        pool.setdefault(q, {"sample_id": r["id"], "question": q, "gold_answer": sas[0]["text"][0], "answers": answers,
                            "answer_in_table": any(a <= st < b for a, b in table_regions(tok)),
                            "answer_word_offset": sum(1 for t, h in zip(tok[h1:st], is_html[h1:st]) if not h),
                            "doc_words": words, "document": doc})
    qs = sorted(pool); rnd = random.Random(43); rnd.shuffle(qs)
    sel = [pool[q] for q in qs[:200]]
    with DOCS.open("w") as fd, MANI.open("w") as fm:
        fm.write(json.dumps({"type": "header", "protocol_sha256": proto, "seed": 43, "n": len(sel), "pool": len(pool),
                             "counts": counts, "manifest_hash": hashlib.sha256(",".join(s["sample_id"] for s in sel).encode()).hexdigest()}) + "\n")
        for s in sel:
            doc = s.pop("document")
            fd.write(json.dumps({"sample_id": s["sample_id"], "document": doc}) + "\n")
            s["doc_sha256"] = hashlib.sha256(doc.encode()).hexdigest()
            fm.write(json.dumps(s) + "\n")
    print(json.dumps({"pool": len(pool), "selected": len(sel), **counts}))


def gen_with_retry(q, ctx, gold, answers):
    """Ollama can fail (HTTP 500) when the coreference model still holds GPU memory; free it and retry the same call once."""
    from precis.pipeline.inference import OllamaInferenceError
    import torch
    try:
        return gen(q, ctx, gold, answers)
    except OllamaInferenceError:
        torch.cuda.empty_cache(); time.sleep(10)
        print("Ollama error, cache freed, retrying", flush=True)
        return gen(q, ctx, gold, answers)


def run():
    rows = [json.loads(l) for l in MANI.open()][1:]
    docs = {r["sample_id"]: r["document"] for r in map(json.loads, DOCS.open())}
    done = {json.loads(l)["sample_id"] for l in REC.open()} if REC.exists() else set()
    with REC.open("a") as fo:
        for i, m in enumerate(rows, 1):
            sid = m["sample_id"]
            if sid in done: continue
            raw = docs[sid]
            assert hashlib.sha256(raw.encode()).hexdigest() == m["doc_sha256"], sid
            t0 = time.time(); q, gold, answers = m["question"], m["gold_answer"], m["answers"]
            clean = sanitize_document(raw)
            blocks = html_blocks(raw); full = md_doc(blocks)
            store = FactStore(in_memory=True, collection_name=f"lf_{i}_{sid[:10]}")
            ingest_with_retry(clean, sid, store, raw)
            ra = retrieval_arms(blocks, q, [CEIL])
            ch, _ = naive_rag_retrieve(document=clean, query=q, top_k=5, chunk_size=512, overlap=128)
            ctxs = {"G": g_context(G_FN, q, store, CEIL), "G2": g_context(G2_FN, q, store, CEIL), "TC": ra[CEIL]["TC"],
                    "W": trim(full, CEIL), "N": trim("\n\n".join(ch) if ch else "", CEIL)}
            row = {"sample_id": sid, "doc_est_tokens": est(full), "arms": {}}
            for a, ctx in ctxs.items():
                r = gen_with_retry(q, ctx, gold, answers)
                r["answer_in_context"] = check_containment(ctx, gold, answers) if ctx else False
                row["arms"][a] = r
            fo.write(json.dumps(row) + "\n"); fo.flush()
            print(i, sid[:8], {a: v["em"] for a, v in row["arms"].items()}, round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
