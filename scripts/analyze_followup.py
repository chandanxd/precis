"""RQ2 follow-up analysis (protocol: experiments/prompt_validation/followup/PROTOCOL.md). No model calls.
  backend/venv/bin/python scripts/analyze_followup.py
"""
import collections, json, math, re, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src"))
from precis.evaluation.metrics import normalize_answer
sys.path.insert(0, str(ROOT / "scripts"))
from scoring import em as _em, cont as _cont  # gold answer or any MRQA alternative
PV = ROOT / "experiments/prompt_validation"; FU = PV / "followup"
ABST = re.compile(r"(insufficient information|not (?:enough|sufficient)|does not (?:contain|provide|specify|mention|state)|do not (?:contain|provide)|no information|cannot be (?:determined|answered)|not (?:specified|mentioned|provided|stated))", re.I)
recs = [json.loads(l) for l in (PV / "raw_outputs/eval_records.jsonl").open()] + ([json.loads(l) for l in (FU / "followup_records.jsonl").open()] if (FU / "followup_records.jsonl").exists() else [])
jud = {}
if (FU / "judge_records.jsonl").exists():
    for l in (FU / "judge_records.jsonl").open():
        r = json.loads(l); jud[(r["sample_id"], r["model"], r["condition"], r["prompt_mode"])] = r["judge"]


def f1(p, g):
    a, b = normalize_answer(p).split(), normalize_answer(g).split()
    if not a or not b: return float(a == b)
    c = sum((collections.Counter(a) & collections.Counter(b)).values())
    if c == 0: return 0.0
    pr, rc = c / len(a), c / len(b)
    return 2 * pr * rc / (pr + rc)


T = {}
for r in recs:
    k = (r["sample_id"], r["model"], r["condition"], r["prompt_mode"])
    T[k] = {"em": _em(r["sample_id"], r["predicted_answer"]), "cont": _cont(r["sample_id"], r["predicted_answer"]), "f1": f1(r["predicted_answer"], r["gold_answer"]),
            "abst": bool(ABST.search(r["predicted_answer"] or "")), "judge": jud.get(k), "len": len(r["predicted_answer"].split())}
sids = sorted({k[0] for k in T}); models = ["qwen2.5-coder:7b", "qwen3.5:4b"]; conds = ["naive_rag", "precis_full"]
P = ["standard", "sent_token", "short_explicit", "concise"]


def mc(b, c):
    m = b + c
    if m == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); out = [None] * len(ps); run = 0
    for rank, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i])); out[i] = run
    return out


res = {"cells": {}, "contrasts": []}
for m in models:
    for c in conds:
        cell = {}
        for p in P:
            rows = [T[(s, m, c, p)] for s in sids if (s, m, c, p) in T]
            if len(rows) < len(sids): continue
            cell[p] = {"em": sum(r["em"] for r in rows), "cont": sum(r["cont"] for r in rows), "f1": float(np.mean([r["f1"] for r in rows])),
                       "abstained": sum(r["abst"] for r in rows), "mean_words": float(np.mean([r["len"] for r in rows])),
                       "judge": sum(bool(r["judge"]) for r in rows) if all(r["judge"] is not None for r in rows) else None}
        res["cells"][f"{m}|{c}"] = cell
CON = [("format|abst=explicit", "short_explicit", "standard"), ("format|abst=token", "concise", "sent_token"),
       ("abstention|format=sentence", "sent_token", "standard"), ("abstention|format=short", "concise", "short_explicit")]
rows = []
for name, x, y in CON:
    for m in models:
        for c in conds:
            if not all((s, m, c, p) in T for s in sids for p in (x, y)): continue
            b = sum(1 for s in sids if T[(s, m, c, x)]["em"] and not T[(s, m, c, y)]["em"]); cc = sum(1 for s in sids if T[(s, m, c, y)]["em"] and not T[(s, m, c, x)]["em"])
            rows.append({"contrast": name, "x": x, "y": y, "model": m, "retrieval": c, "x_only": b, "y_only": cc, "diff_pp": 100 * (b - cc) / len(sids), "p": mc(b, cc)})
adj = holm([r["p"] for r in rows]) if rows else []
for r, a in zip(rows, adj): r["p_holm16"] = a
res["contrasts"] = rows
# retrieval ranking under each metric
rk = {}
for m in models:
    for p in P:
        if not all((s, m, c, p) in T for s in sids for c in conds): continue
        d = {}
        for key in ("em", "cont", "f1", "judge"):
            vals = {c: [T[(s, m, c, p)][key] for s in sids] for c in conds}
            if any(v is None for c in conds for v in vals[c]): continue
            d[key] = {c: float(np.mean([float(v) for v in vals[c]])) for c in conds}
        rk[f"{m}|{p}"] = d
res["retrieval_ranking"] = rk
(FU / "analysis.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1)[:3000])
