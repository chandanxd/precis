"""Analysis of experiments/baseline_budget (protocol: PROTOCOL.md). No model calls.
  backend/venv/bin/python scripts/analyze_baseline_budget.py
"""
import json, math, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from precis.evaluation.metrics import normalize_answer
B = ROOT / "experiments/baseline_budget"
F = ROOT / "experiments/fresh_table_cohort"
fresh = {r["sample_id"]: r for r in map(json.loads, (F / "records.jsonl").open())}
man = {m["sample_id"]: m for m in map(json.loads, (F / "manifest.jsonl").open()) if "sample_id" in m}
single = {r["sample_id"]: r for r in map(json.loads, (B / "single_records.jsonl").open())} if (B / "single_records.jsonl").exists() else {}
multi = {r["sample_id"]: r for r in map(json.loads, (B / "multi_records.jsonl").open())} if (B / "multi_records.jsonl").exists() else {}
MARGIN = 5.0


def mc(b, c):
    m = b + c
    if m == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)


def boot(d, level, B_=10000, seed=42):
    rnd = np.random.default_rng(seed); d = np.asarray(d, float)
    s = np.sort([d[rnd.integers(0, len(d), len(d))].mean() for _ in range(B_)])
    a = (1 - level) / 2
    return [100 * s[int(a * B_)], 100 * s[int((1 - a) * B_) - 1]]


def paired(X, Y, key, level=0.95):
    x = np.array([int(v) for v in X[key]]); y = np.array([int(v) for v in Y[key]])
    b = int(((x == 1) & (y == 0)).sum()); c = int(((x == 0) & (y == 1)).sum())
    return {"diff_pp": 100 * (x - y).mean(), "x_only": b, "y_only": c, "p_mcnemar": mc(b, c), f"ci{int(level * 100)}_pp": boot(x - y, level)}


def present(ctx, answers):
    t = normalize_answer(ctx or "")
    return any(normalize_answer(a) and normalize_answer(a) in t for a in answers)


def col(rows):
    return {"em": [r["em"] for r in rows], "cont": [r["cont"] for r in rows], "tok": [r["est_tokens"] for r in rows]}


def summarize(X, answers):
    n = len(X["em"])
    return {"n": n, "em": int(sum(X["em"])), "cont": int(sum(X["cont"])), "mean_tokens": float(np.mean(X["tok"])),
            "em_pp_per_100tok": 1e4 * float(np.mean(X["em"])) / max(1e-9, float(np.mean(X["tok"]))),
            "cont_pp_per_100tok": 1e4 * float(np.mean(X["cont"])) / max(1e-9, float(np.mean(X["tok"]))),
            "answer_in_context": int(sum(present(c, a) for c, a in zip(X["ctx"], answers)))}


res = {}
# ------------------------------------------------------------------ E1
ids = [i for i in fresh if i in single]
res["n_single"] = len(ids)
if ids:
    arms = {a: {"rows": [fresh[i][a] for i in ids]} for a in ("N_raw", "N_clean", "D", "F2", "G")}
    for a in ("TC", "H", "W"): arms[a] = {"rows": [single[i]["e1"][a] for i in ids]}
    ans = [man[i]["answers"] for i in ids]
    X = {}
    for a, v in arms.items():
        X[a] = col(v["rows"]); X[a]["ctx"] = [r["context"] for r in v["rows"]]
    e1 = {"summary": {a: summarize(X[a], ans) for a in X}, "G_vs": {}}
    for a in ("N_raw", "N_clean", "W", "TC", "H", "D", "F2"):
        row = {}
        for key in ("em", "cont"):
            p99 = paired(X["G"], X[a], key, 0.99); p95 = paired(X["G"], X[a], key, 0.95)
            row[key] = {**p95, "ci99_pp": p99["ci99_pp"], "non_inferior_at_5pp_99ci": bool(p99["ci99_pp"][0] > -MARGIN)}
        gt = np.array(X["G"]["tok"], float); at = np.array(X[a]["tok"], float)
        row["tokens"] = {"G_mean": gt.mean(), "arm_mean": at.mean(), "G_reduction_pct": 100 * (1 - gt.mean() / at.mean()),
                         "G_shorter": int((gt < at).sum()), "G_longer": int((gt > at).sum())}
        e1["G_vs"][a] = row
    res["E1"] = e1
    # ---- E2 ceiling sweep
    e2 = {}
    for c in ("256", "512", "1024"):
        ar = {a: [single[i]["e2"][c][a] for i in ids] for a in ("G", "N", "H", "W")}
        XX = {a: col(v) for a, v in ar.items()}
        for a, v in ar.items(): XX[a]["ctx"] = [r["context"] for r in v]
        e2[c] = {"summary": {a: summarize(XX[a], ans) for a in XX},
                 "G_vs": {a: {k: paired(XX["G"], XX[a], k) for k in ("em", "cont")} for a in ("N", "H", "W")}}
    res["E2"] = e2
    # ---- E4 sensitivity
    e4 = {}
    GR = {"em": [single[i]["e1"]["G"]["em"] for i in ids], "cont": [single[i]["e1"]["G"]["cont"] for i in ids]}
    res["G_rerun_vs_original"] = {"em_original": int(sum(X["G"]["em"])), "em_rerun": int(sum(GR["em"])),
        "outcomes_changed": int(sum(a != b for a, b in zip(X["G"]["em"], GR["em"]))),
        "contexts_identical": int(sum(single[i]["e1"]["G"]["context"] == fresh[i]["G"]["context"] for i in ids))}
    for name in single[ids[0]]["e4"]:
        rows = [single[i]["e4"][name] for i in ids]
        Y = {"em": [r["em"] for r in rows], "cont": [r["cont"] for r in rows], "tok": [r["est_tokens"] for r in rows]}
        e4[name] = {"contexts_changed": int(sum(not r["same_as_G"] for r in rows)), "em": int(sum(Y["em"])), "cont": int(sum(Y["cont"])),
                    "mean_tokens": float(np.mean(Y["tok"])), "vs_G_em": paired(Y, GR, "em"), "vs_G_cont": paired(Y, GR, "cont")}
    res["E4"] = e4
# ------------------------------------------------------------------ E3
mids = [i for i in fresh if i in multi]
res["n_multi"] = len(mids)
if mids:
    ans = [man[i]["answers"] for i in mids]; e3 = {"corpus_mean_est_tokens": float(np.mean([multi[i]["corpus_est_tokens"] for i in mids]))}
    for c in ("1024", "2048"):
        ar = {a: [multi[i]["e3"][c][a] for i in mids] for a in ("G", "N", "H", "W")}
        XX = {a: col(v) for a, v in ar.items()}
        for a, v in ar.items(): XX[a]["ctx"] = [r["context"] for r in v]
        e3[c] = {"summary": {a: summarize(XX[a], ans) for a in XX},
                 "G_vs": {a: {k: paired(XX["G"], XX[a], k) for k in ("em", "cont")} for a in ("N", "H", "W")}}
    res["E3"] = e3
# ------------------------------------------------------------------ E6 replay
for p in B.glob("replay_*.jsonl"):
    rr = [json.loads(l) for l in p.open()]
    by = {}
    for r in rr: by.setdefault(r["arm"], {})[r["sample_id"]] = r
    common = sorted(set.intersection(*[set(v) for v in by.values()])) if by else []
    if len(common) < 20: continue
    Z = {a: {"em": [by[a][i]["em"] for i in common], "cont": [by[a][i]["cont"] for i in common]} for a in by}
    out = {"n": len(common), "model": rr[0]["model"], "summary": {a: {"em": int(sum(Z[a]["em"])), "cont": int(sum(Z[a]["cont"]))} for a in Z},
           "G_vs": {a: {k: paired(Z["G"], Z[a], k) for k in ("em", "cont")} for a in Z if a != "G"}}
    res[f"E6_{p.stem}"] = out
(B / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float)[:6000])
