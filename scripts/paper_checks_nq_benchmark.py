"""Clustered re-analysis of the 200-sample NQ benchmark (paper Tables 3/4/8, Sec. 6.4).

Uses stored per_question_results.jsonl from the four extraction versions; 200 samples hold 74 distinct
questions, so inference is also done with question-level clustering. Single-reference gold scoring
(gold_answer only), as in the benchmark harness. No model calls.
"""
import json, math, random, re, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src"))
from precis.evaluation.metrics import normalize_answer  # noqa: E402

VERS = {"v1": "nq_benchmark", "v1.5": "nq_benchmark_svoa_enhanced",
        "v2": "nq_benchmark_svoa_enhanced_v2", "v3": "nq_benchmark_svoa_enhanced_v3"}


def contains(text, ans):
    na, nt = normalize_answer(ans), normalize_answer(text)
    return bool(na and nt and re.search(r"(?:\b|^)" + re.escape(na) + r"(?:\b|$)", nt))


def load(v, cond):
    d = {}
    for l in (ROOT / "results" / VERS[v] / "per_question_results.jsonl").open():
        r = json.loads(l)
        if r["condition"] == cond:
            d[r["sample_id"]] = r
    return d


def mcn(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def cmp(X, Y, f, B=10000, seed=42):
    ids = sorted(X)
    q = {i: X[i]["question"] for i in ids}
    b = sum(1 for i in ids if f(X[i]) and not f(Y[i])); c = sum(1 for i in ids if (not f(X[i])) and f(Y[i]))
    g = collections.defaultdict(list)
    for i in ids: g[q[i]].append(int(f(X[i])) - int(f(Y[i])))
    keys = list(g); rnd = random.Random(seed); s = []
    for _ in range(B):
        t = n = 0
        for _ in keys:
            gg = g[keys[rnd.randrange(len(keys))]]; t += sum(gg); n += len(gg)
        s.append(t / n)
    s.sort()
    return {"x_only": b, "y_only": c, "net_pp": 100 * (b - c) / len(ids), "p_exact_mcnemar_unclustered": mcn(b, c),
            "cluster_boot95_pp": [100 * s[int(.025 * B)], 100 * s[int(.975 * B)]]}


EM = lambda r: bool(r["exact_match"])
CT = lambda r: contains(r["predicted_answer"], r["gold_answer"])
out = {"distinct_questions": len({r["question"] for r in load("v3", "precis_full").values()})}
n3, p3 = load("v3", "naive_rag"), load("v3", "precis_full")
out["naive_vs_precis_v3"] = {"EM": cmp(n3, p3, EM), "containment": cmp(n3, p3, CT),
                            "EM_counts": [sum(map(EM, n3.values())), sum(map(EM, p3.values()))],
                            "containment_counts": [sum(map(CT, n3.values())), sum(map(CT, p3.values()))]}
out["version_steps_precis_full"] = {}
for a, b in (("v1", "v1.5"), ("v1.5", "v2"), ("v2", "v3"), ("v1", "v3")):
    A, Bv = load(a, "precis_full"), load(b, "precis_full")
    out["version_steps_precis_full"][f"{b}-vs-{a}"] = {"EM": cmp(Bv, A, EM), "EM_counts": [sum(map(EM, A.values())), sum(map(EM, Bv.values()))]}
# per-question duplicates: is the naive/precis result identical across repeated questions? (repeats share document?)
q = collections.defaultdict(list)
for i, r in p3.items(): q[r["question"]].append(i)
out["repeated_question_groups"] = sum(1 for v in q.values() if len(v) > 1)
out["max_group_size"] = max(len(v) for v in q.values())
Path(ROOT / "results/paper_checks/nq_benchmark_checks.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
