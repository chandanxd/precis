"""Analysis of experiments/long_doc_fixed_g (protocol: PROTOCOL.md). No model calls; written before the results were known.
  backend/venv/bin/python scripts/analyze_long_doc_fixed_g.py
Writes experiments/long_doc_fixed_g/analysis.json.
"""
import json, math, re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
L = ROOT / "experiments/long_doc_fixed_g"
recs = [json.loads(l) for l in (L / "records.jsonl").open()]
ARMS = ("G", "G2", "TC", "W", "N")
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
    return [float(100 * s[int(a * B_)]), float(100 * s[int((1 - a) * B_) - 1])]


def vec(arm, key):
    return np.array([int(bool(r["arms"][arm][key])) for r in recs])


def pair(x_arm, y_arm, level):
    x, y = vec(x_arm, "em"), vec(y_arm, "em")
    b = int(((x == 1) & (y == 0)).sum()); c = int(((x == 0) & (y == 1)).sum())
    return {"diff_pp": float(100 * (x - y).mean()), "x_only": b, "y_only": c, "p_mcnemar": mc(b, c),
            "ci_pp": boot(x - y, level), "level": level}


res = {"n": len(recs), "arms": {}}
for a in ARMS:
    tok = np.array([r["arms"][a]["est_tokens"] for r in recs], float)
    res["arms"][a] = {"em": int(vec(a, "em").sum()), "cont": int(vec(a, "cont").sum()),
                      "answer_in_context": int(vec(a, "answer_in_context").sum()), "mean_tokens": float(tok.mean())}
h1 = pair("G2", "G", 0.95)
h2 = pair("G2", "TC", 0.975); h2["non_inferior_at_5pp"] = bool(h2["ci_pp"][0] > -MARGIN)
first, second = sorted((h1, h2), key=lambda h: h["p_mcnemar"])       # Holm over the two primary p-values
first["p_holm2"] = min(1.0, 2 * first["p_mcnemar"])
second["p_holm2"] = max(first["p_holm2"], min(1.0, second["p_mcnemar"]))
res["H1_G2_vs_G"], res["H2_G2_vs_TC"] = h1, h2
res["secondary"] = {a: pair("G2", a, 0.95) for a in ("W", "N")}
res["g2_contexts_with_fact"] = sum(1 for r in recs if re.search(r"^Fact \d+:", r["arms"]["G2"]["context"], re.M))
res["g_contexts_with_fact"] = sum(1 for r in recs if re.search(r"^Fact \d+:", r["arms"]["G"]["context"], re.M))
(L / "analysis.json").write_text(json.dumps(res, indent=1))
print(json.dumps({a: (v["em"], v["answer_in_context"], round(v["mean_tokens"])) for a, v in res["arms"].items()}))
print("H1", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in h1.items() if k != "ci_pp"}, [round(x, 1) for x in h1["ci_pp"]])
print("H2", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in h2.items() if k != "ci_pp"}, [round(x, 1) for x in h2["ci_pp"]])
print("facts in G2 / G contexts:", res["g2_contexts_with_fact"], res["g_contexts_with_fact"])
