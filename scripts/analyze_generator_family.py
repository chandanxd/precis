"""Analysis of experiments/generator_family (protocol: PROTOCOL.md). No model calls; written before the results were known.
  backend/venv/bin/python scripts/analyze_generator_family.py
Compares, per generator, G with every other arm on the fixed fresh-cohort contexts: qwen2.5-coder:7b (stored records),
qwen3.5:9b (experiments/baseline_budget replay) and gemma4:e4b (this experiment). Writes experiments/generator_family/analysis.json.
"""
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

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


ARMS = ("N_raw", "N_clean", "W", "TC", "H", "D", "F2", "G")
fresh = {r["sample_id"]: r for r in map(json.loads, (ROOT / "experiments/fresh_table_cohort/records.jsonl").open())}
single = {r["sample_id"]: r for r in map(json.loads, (ROOT / "experiments/baseline_budget/single_records.jsonl").open())}


def coder():
    out = {}
    for sid, fr in fresh.items():
        out[sid] = {a: fr[a] for a in ("N_raw", "N_clean", "D", "F2", "G")}
        out[sid].update({a: single[sid]["e1"][a] for a in ("TC", "H", "W")})
    return out


def replay(path):
    out = {}
    for r in map(json.loads, path.open()):
        out.setdefault(r["sample_id"], {})[r["arm"]] = r
    return out


GENS = {"qwen2.5-coder:7b": coder(),
        "qwen3.5:9b": replay(ROOT / "experiments/baseline_budget/replay_qwen3_5_9b.jsonl"),
        "gemma4:e4b": replay(ROOT / "experiments/generator_family/replay_gemma4_e4b.jsonl")}
res = {}
for gname, recs in GENS.items():
    ids = sorted(s for s in fresh if s in recs and all(a in recs[s] for a in ARMS))
    v = {a: np.array([int(bool(recs[s][a]["em"])) for s in ids]) for a in ARMS}
    c = {a: int(sum(bool(recs[s][a]["cont"]) for s in ids)) for a in ARMS}
    g = v["G"]; cmp_ = {}
    for a in ARMS:
        if a == "G": continue
        b = int(((g == 1) & (v[a] == 0)).sum()); k = int(((g == 0) & (v[a] == 1)).sum())
        cmp_[a] = {"diff_pp": 100 * (g - v[a]).mean(), "G_only": b, "arm_only": k, "p_mcnemar": mc(b, k), "ci95_pp": boot(g - v[a], 0.95)}
    res[gname] = {"n": len(ids), "em": {a: int(v[a].sum()) for a in ARMS}, "cont": c, "G_vs": cmp_}
(ROOT / "experiments/generator_family/analysis.json").write_text(json.dumps(res, indent=1))
for gname, r in res.items():
    print(gname, r["n"], r["em"])
    print("   ", {a: (round(x["diff_pp"], 1), round(x["p_mcnemar"], 3)) for a, x in r["G_vs"].items()})
