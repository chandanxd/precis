"""Analysis of experiments/long_doc_cohort (protocol: PROTOCOL.md). No model calls; written before the results were known.
  backend/venv/bin/python scripts/analyze_long_doc_cohort.py
Writes experiments/long_doc_cohort/analysis.json.
"""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))

MARGIN = 5.0


def mc(b, c):
    """Two-sided exact McNemar (as in analyze_baseline_budget.py)."""
    m = b + c
    if m == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)


def boot(d, level, B_=10000, seed=42):
    """Question-level bootstrap interval in percentage points (as in analyze_baseline_budget.py)."""
    rnd = np.random.default_rng(seed); d = np.asarray(d, float)
    s = np.sort([d[rnd.integers(0, len(d), len(d))].mean() for _ in range(B_)])
    a = (1 - level) / 2
    return [100 * s[int(a * B_)], 100 * s[int((1 - a) * B_) - 1]]


L = ROOT / "experiments/long_doc_cohort"
man = {m["sample_id"]: m for m in map(json.loads, (L / "manifest.jsonl").open()) if "sample_id" in m}
recs = [json.loads(l) for l in (L / "records.jsonl").open()]
ARMS = ("G", "N", "N_raw", "W", "TC", "H")
COMPARATORS = ("N", "N_raw", "W", "TC", "H")


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); out = [0.0] * len(ps); run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i])); out[i] = run
    return out


def vec(rows, ceil, arm, key):
    return np.array([int(bool(r["ceil"][ceil][arm][key])) for r in rows])


def block(rows, ceil):
    out = {"n": len(rows), "arms": {}, "G_vs": {}}
    for a in ARMS:
        em, ct = vec(rows, ceil, a, "em"), vec(rows, ceil, a, "cont")
        tok = np.array([r["ceil"][ceil][a]["est_tokens"] for r in rows], float)
        out["arms"][a] = {"em": int(em.sum()), "cont": int(ct.sum()), "answer_in_context": int(vec(rows, ceil, a, "answer_in_context").sum()),
                          "mean_tokens": float(tok.mean()), "em_pp_per_100tok": float(1e4 * em.mean() / max(tok.mean(), 1e-9))}
    g = vec(rows, ceil, "G", "em")
    ps = []
    for c in COMPARATORS:
        y = vec(rows, ceil, c, "em"); b = int(((g == 1) & (y == 0)).sum()); k = int(((g == 0) & (y == 1)).sum())
        d = g - y; ci99 = boot(d, 0.99)
        out["G_vs"][c] = {"diff_pp": float(100 * d.mean()), "G_only": b, "comp_only": k, "p_mcnemar": mc(b, k),
                          "ci95_pp": [float(x) for x in boot(d, 0.95)], "ci99_pp": [float(x) for x in ci99], "non_inferior_at_5pp": bool(ci99[0] > -MARGIN)}
        ps.append(mc(b, k))
    for c, p in zip(COMPARATORS, holm(ps)):
        out["G_vs"][c]["p_holm5"] = p
    return out


res = {"n": len(recs), "margin_pp": MARGIN,
       "doc_words_median": float(np.median([man[r["sample_id"]]["doc_words"] for r in recs])),
       "doc_est_tokens_median": float(np.median([r["doc_est_tokens"] for r in recs]))}
for ceil in ("2048", "1024"):
    res[ceil] = block(recs, ceil)
    res[ceil]["strata"] = {}
    for name, keep in (("answer_in_table", True), ("answer_outside_table", False)):
        sub = [r for r in recs if man[r["sample_id"]]["answer_in_table"] == keep]
        if sub:
            res[ceil]["strata"][name] = {"n": len(sub), "em": {a: int(vec(sub, ceil, a, "em").sum()) for a in ARMS},
                                         "answer_in_context": {a: int(vec(sub, ceil, a, "answer_in_context").sum()) for a in ARMS}}
(L / "analysis.json").write_text(json.dumps(res, indent=1))
print(json.dumps({c: {a: (v["em"], v["answer_in_context"], round(v["mean_tokens"])) for a, v in res[c]["arms"].items()} for c in ("2048", "1024")}))
print(json.dumps({c: {k: (round(v["diff_pp"], 1), [round(x, 1) for x in v["ci99_pp"]], round(v["p_holm5"], 3), v["non_inferior_at_5pp"])
                      for k, v in res[c]["G_vs"].items()} for c in ("2048", "1024")}))

# ------------------------------------------------------------------ post hoc, descriptive (added after the results were known)
# What G's contexts consist of: tables, lists only, prose facts, and reference/category/media-link boilerplate (a heuristic
# pattern). Not part of the protocol's analysis; reported in the paper as a post hoc description of the mechanism.
import re
diag = {}
for c in ("2048", "1024"):
    G = [r["ceil"][c]["G"] for r in recs]
    is_tab = [bool(re.search(r"^\|.*\|", g["context"], re.M)) for g in G]
    diag[c] = {"with_table": sum(is_tab), "lists_only": len(G) - sum(is_tab),
               "with_fact": sum(1 for g in G if re.search(r"^Fact \d+:", g["context"], re.M)),
               "with_reference_or_navigation_boilerplate": sum(1 for g in G if re.search(
                   r"Jump up|Retrieved \w+ \d|Wikimedia Commons|^\* .* (?:births|deaths|people|treaties|relations)\b",
                   g["context"], re.M | re.I)),
               "answer_in_ctx_table": sum(g["answer_in_context"] for g, t in zip(G, is_tab) if t),
               "answer_in_ctx_lists_only": sum(g["answer_in_context"] for g, t in zip(G, is_tab) if not t)}
with open(L / "g_context_diagnostic.json", "w") as f:
    json.dump(diag, f, indent=1)
