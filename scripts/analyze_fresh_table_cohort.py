"""Analysis of the fresh table-bearing cohort exactly as pre-specified in PROTOCOL.md.
Run with the backend venv (needs scipy): backend/venv/bin/python scripts/analyze_fresh_table_cohort.py
"""
import json, math, random, re, sys
from pathlib import Path
import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "experiments/fresh_table_cohort"
rows = [json.loads(l) for l in (D / "records.jsonl").open()]
mani = [json.loads(l) for l in (D / "manifest.jsonl").open()]
n = len(rows)
C = ["N_raw", "N_clean", "D", "F2", "G"]


def mc(b, c):
    m = b + c
    if m == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)


def pair(x, y, key, idx=None):
    R = rows if idx is None else [rows[i] for i in idx]
    b = sum(1 for r in R if r[x][key] and not r[y][key]); c = sum(1 for r in R if r[y][key] and not r[x][key])
    d = np.array([int(r[x][key]) - int(r[y][key]) for r in R]); rnd = np.random.default_rng(42)
    bs = np.sort([d[rnd.integers(0, len(d), len(d))].mean() for _ in range(10000)])
    return {"x_only": b, "y_only": c, "net_pp": 100 * (b - c) / len(R), "p": mc(b, c),
            "ci95_pp": [100 * bs[250], 100 * bs[9750]]}


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); out = [None] * len(ps); run = 0
    for rank, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i])); out[i] = run
    return out


res = {"n": n, "manifest_header": mani[0],
       "rates": {c: {"em": sum(r[c]["em"] for r in rows), "cont": sum(r[c]["cont"] for r in rows),
                     "empty_context": sum(r[c]["status"] == "empty_context" for r in rows)} for c in C}}
prim = {}
for key, name in (("em", "primary_em"), ("cont", "secondary_containment")):
    ps = [pair("G", x, key) for x in ("D", "F2", "N_raw", "N_clean")]
    adj = holm([p["p"] for p in ps])
    prim[name] = {x: {**p, "p_holm_m4": a} for x, p, a in zip(("D", "F2", "N_raw", "N_clean"), ps, adj)}
res["contrasts_G_vs"] = prim
res["exploratory_unadjusted"] = {f"{a}-{b}:{k}": pair(a, b, k) for a, b in (("D", "N_raw"), ("D", "N_clean"), ("F2", "D")) for k in ("em", "cont")}
# context size
for tag, f in (("est_tokens", lambda r, c: r[c]["est_tokens"]), ("prompt_tokens", lambda r, c: r[c]["prompt_tokens"] or 0)):
    a = np.array([f(r, "F2") for r in rows], float); g = np.array([f(r, "G") for r in rows], float)
    res[f"G_vs_F2_{tag}"] = {"mean_F2": a.mean(), "mean_G": g.mean(), "reduction_pct": 100 * (1 - g.mean() / a.mean()),
                             "G_shorter": int((g < a).sum()), "G_longer": int((g > a).sum()),
                             "wilcoxon_p": float(wilcoxon(a, g).pvalue) if (a != g).any() else 1.0}
res["mean_est_tokens"] = {c: float(np.mean([r[c]["est_tokens"] for r in rows])) for c in C}
res["mean_prompt_tokens"] = {c: float(np.mean([r[c]["prompt_tokens"] or 0 for r in rows])) for c in C}
# markup strata
strata = {"table_present": [i for i, r in enumerate(rows) if r["has_table"]], "list_only": [i for i, r in enumerate(rows) if not r["has_table"]]}
res["strata_sizes"] = {k: len(v) for k, v in strata.items()}
res["by_stratum_em"] = {k: {c: sum(rows[i][c]["em"] for i in v) for c in C} for k, v in strata.items()}
res["by_stratum_G_vs_D_em"] = {k: pair("G", "D", "em", v) for k, v in strata.items() if v}
# answer location: gold answer present in D context (tables) / in any context
def has(ctx, answers):
    cl = ctx.lower()
    return any(a and a.lower() in cl for a in answers)
res["answer_in_D_context_share"] = sum(has(r["D"]["context"], m["answers"]) for r, m in zip(rows, mani[1:])) / n
# doubled negation in contexts
dbl = re.compile(r"(?<=\s)NOT (?=(?:\S+ ){0,2}(?:[Nn]ot|NOT|[Nn]ever|n't|N'T)(?=\s|$))")
res["doubled_negation_contexts"] = {c: sum(1 for r in rows if dbl.search(r[c]["context"])) for c in C}
res["contexts_with_NOT"] = {c: sum(1 for r in rows if re.search(r"\bNOT\b", r[c]["context"])) for c in C}
res["g_use_structural_share"] = sum(r["g_use_structural"] for r in rows) / n
res["g_facts_packed_total"] = sum(r["g_facts_packed"] for r in rows)
(D / "analysis.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float))
