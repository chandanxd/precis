"""Re-run the frozen extractor (no coreference stage) on dev and held-out NQ documents and report
answer-bearing coverage. Coverage = any single extracted fact (canonical or rendered text) contains any
MRQA answer alias (rule of backend/scripts/analyze_benchmark_failures.py).

Held-out = records of nq_dev.jsonl whose doc_id is not one of the 200 development doc_ids and whose
question is not one of the development questions; one random record per distinct question (seed 42).
Writes results/paper_checks/heldout_coverage.json. Run with the backend venv:
  PYTHONPATH=backend/src backend/venv/bin/python scripts/paper_checks_heldout_coverage.py
"""
import json, random, re, sys, collections, math, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "backend"))
from precis.api.security import sanitize_document
from precis.pipeline.svoa import extract_facts
from precis.pipeline.sdh import canonical_fact_text
from precis.pipeline.packer import _render_fact_parts
from precis.evaluation.metrics import normalize_answer

DATA = ROOT / "backend/data/nq_subset/nq_dev.jsonl"
dev_ids = set(json.load(open(ROOT / "backend/data/nq_subset/reconstructed_facts_cache_v3.json")))
recs = [json.loads(l) for l in DATA.open()]
dev = [r for r in recs if r["doc_id"] in dev_ids]
dev_q = {r["question"] for r in dev}
pool = [r for r in recs if r["doc_id"] not in dev_ids and r["question"] not in dev_q]
byq = collections.defaultdict(list)
for r in pool: byq[r["question"]].append(r)
rnd = random.Random(42)
qs = sorted(byq); rnd.shuffle(qs)
held = [rnd.choice(byq[q]) for q in qs[:1000]]


def has(text, ans):
    na, nt = normalize_answer(ans), normalize_answer(text)
    return bool(na and nt and re.search(r"(?:\b|^)" + re.escape(na) + r"(?:\b|$)", nt))


def covered(r):
    refs = [r["gold_answer"]] + [a for a in (r.get("answers") or []) if a]
    facts = extract_facts(sanitize_document(r["document"]), source_doc=r["doc_id"])
    for f in facts:
        c, t = canonical_fact_text(f), " ".join(_render_fact_parts(f))
        if any(has(c, a) or has(t, a) for a in refs): return True, len(facts)
    return False, len(facts)


def boot(flags, qlist, B=10000):
    g = collections.defaultdict(list)
    for f, q in zip(flags, qlist): g[q].append(f)
    k = list(g); rr = random.Random(42); s = []
    for _ in range(B):
        t = n = 0
        for _ in k:
            x = g[k[rr.randrange(len(k))]]; t += sum(x); n += len(x)
        s.append(t / n)
    s.sort(); return [round(100 * s[int(.025 * B)], 1), round(100 * s[int(.975 * B)], 1)]


out = {"n_records": len(recs), "n_dev": len(dev), "pool_after_exclusions": len(pool), "pool_distinct_questions": len(byq)}
t0 = time.time()
fl_dev = []; nf = []
for r in dev:
    c, n = covered(r); fl_dev.append(c); nf.append(n)
out["dev200_no_coref"] = {"covered": sum(fl_dev), "n": len(dev), "pct": round(100 * sum(fl_dev) / len(dev), 1),
                          "cluster_boot95": boot(fl_dev, [r["question"] for r in dev]), "mean_facts": sum(nf) / len(nf)}
print("dev", out["dev200_no_coref"], round(time.time() - t0), "s", flush=True)
fl = []
for i, r in enumerate(held):
    c, _ = covered(r); fl.append(c)
    if i % 200 == 199: print(i + 1, sum(fl), flush=True)
for n in (200, 1000):
    out[f"heldout_{n}"] = {"covered": sum(fl[:n]), "n": n, "pct": round(100 * sum(fl[:n]) / n, 1),
                          "cluster_boot95": boot(fl[:n], [r["question"] for r in held[:n]])}
out["heldout_has_table_or_list_markup_share"] = round(sum(1 for r in held if re.search(r"<(?:table|ul|ol|li)\b", r["document"], re.I)) / len(held), 3)
(ROOT / "results/paper_checks/heldout_coverage.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
