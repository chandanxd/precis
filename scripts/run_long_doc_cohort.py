"""Long-document cohort (protocol: experiments/long_doc_cohort/PROTOCOL.md).

  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_long_doc_cohort.py build   # draw the cohort, write the manifest
  PYTHONPATH=backend/src backend/venv/bin/python scripts/run_long_doc_cohort.py run     # generate (resumable)
Reads the NQ v1.0 dev shards from backend/data/nq_full/ (git-ignored); the cohort documents are cached in
backend/data/nq_full/long_docs.jsonl and their SHA-256 is recorded in the manifest. Arms reuse the implementations of
scripts/run_baseline_budget.py unchanged.
"""
import hashlib, json, random, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.api.security import sanitize_document, sanitize_document_layout
from precis.evaluation.naive_rag import naive_rag_retrieve
from precis.graph.store import FactStore
from precis.pipeline.orchestrator import ingest_document
from eval_table_selection_v2 import check_containment
from run_baseline_budget import G_FN, est, g_context, gen, html_blocks, md_doc, retrieval_arms, trim
from run_fresh_table_cohort import used_ids_and_questions

D = ROOT / "experiments/long_doc_cohort"
MANI, REC = D / "manifest.jsonl", D / "records.jsonl"
NQF = ROOT / "backend/data/nq_full"
SHARDS = [NQF / f"validation-0000{i}-of-00007.parquet" for i in (0, 1, 2)]
DOCS = NQF / "long_docs.jsonl"
CEILINGS = (2048, 1024)
MIN_WORDS = 3000


def earlier_questions():
    ids, qs = used_ids_and_questions()
    for l in (ROOT / "backend/data/nq_subset/nq_dev.jsonl").open():       # MRQA records whose ids were used earlier
        r = json.loads(l)
        if r["doc_id"] in ids: qs.add(r["question"])
    for p in (ROOT / "experiments/fresh_table_cohort/manifest.jsonl", ROOT / "experiments/prompt_validation/sample_manifest.jsonl"):
        for l in p.open():
            r = json.loads(l)
            if r.get("question"): qs.add(r["question"])
    return {" ".join(q.lower().split()) for q in qs}


def table_regions(tokens):
    regs, depth, start = [], 0, None
    for i, t in enumerate(tokens):
        if t == "<Table>":
            if depth == 0: start = i
            depth += 1
        elif t == "</Table>" and depth:
            depth -= 1
            if depth == 0: regs.append((start, i))
    return regs


def examples():
    import pyarrow.parquet as pq
    for shard in SHARDS:
        for batch in pq.ParquetFile(shard).iter_batches(batch_size=32, columns=["id", "document", "question", "annotations"]):
            for r in batch.to_pylist():
                yield r


def build():
    proto = (D / "PROTOCOL.sha256").read_text().split()[0]
    used = earlier_questions()
    counts = {"examples": 0, "no_short_answer": 0, "no_table": 0, "too_short": 0, "input_limit": 0, "used_earlier": 0}
    pool = {}
    for r in examples():
        counts["examples"] += 1
        q = r["question"]["text"]
        ann = r["annotations"]
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
        first = sas[0]
        st = first["start_token"][0]
        regs = table_regions(tok)
        pool.setdefault(q, {"sample_id": r["id"], "question": q, "gold_answer": first["text"][0], "answers": answers,
                            "answer_in_table": any(a <= st < b for a, b in regs),
                            "answer_word_offset": sum(1 for t, h in zip(tok[h1:st], is_html[h1:st]) if not h),
                            "doc_words": words, "document": doc})
    qs = sorted(pool); rnd = random.Random(42); rnd.shuffle(qs)
    sel = [pool[q] for q in qs[:200]]
    with DOCS.open("w") as fd, MANI.open("w") as fm:
        fm.write(json.dumps({"type": "header", "protocol_sha256": proto, "seed": 42, "n": len(sel), "pool": len(pool),
                             "counts": counts, "manifest_hash": hashlib.sha256(",".join(s["sample_id"] for s in sel).encode()).hexdigest()}) + "\n")
        for s in sel:
            doc = s.pop("document")
            fd.write(json.dumps({"sample_id": s["sample_id"], "document": doc}) + "\n")
            s["doc_sha256"] = hashlib.sha256(doc.encode()).hexdigest()
            fm.write(json.dumps(s) + "\n")
    print(json.dumps({"pool": len(pool), "selected": len(sel), **counts}))


def ingest_with_retry(clean, sid, store, raw):
    """Coreference on a very long page can exhaust the 8 GB GPU while Ollama holds the generator. On CUDA OOM, free the
    cache, ask Ollama to unload its model (it reloads on the next call) and retry the same ingestion once."""
    import requests, torch
    try:
        ingest_document(text=clean, source_doc=sid, store=store, enable_list_extraction=True, raw_document=raw)
    except torch.OutOfMemoryError:
        torch.cuda.empty_cache()
        requests.post("http://127.0.0.1:11434/api/generate", json={"model": "qwen2.5-coder:7b", "keep_alive": 0}, timeout=60)
        print("OOM during ingestion of", sid[:8], "- generator unloaded, retrying", flush=True)
        ingest_document(text=clean, source_doc=sid, store=store, enable_list_extraction=True, raw_document=raw)


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
            store = FactStore(in_memory=True, collection_name=f"ld_{i}_{sid[:10]}")
            ingest_with_retry(clean, sid, store, raw)
            ra = retrieval_arms(blocks, q, list(CEILINGS))
            ch, _ = naive_rag_retrieve(document=clean, query=q, top_k=5, chunk_size=512, overlap=128)
            ncl = "\n\n".join(ch) if ch else ""
            ch, _ = naive_rag_retrieve(document=raw, query=q, top_k=5, chunk_size=512, overlap=128)
            nraw = "\n\n".join(ch) if ch else ""
            row = {"sample_id": sid, "doc_est_tokens": est(full), "ceil": {}}
            for c in CEILINGS:
                ctxs = {"G": g_context(G_FN, q, store, c), "N": trim(ncl, c), "N_raw": trim(nraw, c), "W": trim(full, c),
                        "TC": ra[c]["TC"], "H": ra[c]["H"]}
                out = {}
                for a, ctx in ctxs.items():
                    r = gen(q, ctx, gold, answers)
                    r["answer_in_context"] = check_containment(ctx, gold, answers) if ctx else False
                    out[a] = r
                row["ceil"][str(c)] = out
            fo.write(json.dumps(row) + "\n"); fo.flush()
            print(i, sid[:8], {a: v["em"] for a, v in row["ceil"]["2048"].items()}, round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
