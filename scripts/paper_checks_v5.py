"""Re-analyses requested by the simulated review of v4 (no model calls). Writes results/paper_checks/v5_reanalysis.json.
  backend/venv/bin/python scripts/paper_checks_v5.py

1. Abstention against answerability: in the 2x2 prompt follow-up, how many abstaining outputs had an answer string
   (gold or MRQA alternative) in the cached context, per model, retrieval condition and prompt.
2. Fresh-cohort abstentions of every arm split the same way.
3. Table-rendering defect: G contexts on the fresh cohort whose Markdown table has a placeholder header (Col_n) or a
   first column that is empty in most rows (row headers lost), with exact match on and off those cases.
4. Generation latency stored with the main prompt experiment (wall-clock per call, local Ollama, GPU host).
"""
import collections, json, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from scoring import ALIASES, contains, mcn
OUT = ROOT / "results/paper_checks/v5_reanalysis.json"
PV = ROOT / "experiments/prompt_validation"
ABST = re.compile(r"(insufficient information|not (?:enough|sufficient)|does not (?:contain|provide|specify|mention|state)|do not (?:contain|provide)|no information|cannot be (?:determined|answered)|not (?:specified|mentioned|provided|stated))", re.I)
res = {}


def in_ctx(sid, ctx):
    return any(contains(ctx, a) for a in ALIASES[sid])


# ------------------------------------------------------------------ 1. 2x2 abstention vs answerability
ctx = {}
for l in (PV / "cached_contexts.jsonl").open():
    if not l.strip(): continue
    r = json.loads(l)
    ctx[(r["sample_id"], "naive_rag")] = r["naive_rag"]["context_text"]
    ctx[(r["sample_id"], "precis_full")] = r["precis_v3"]["context_text"]
recs = [json.loads(l) for l in (PV / "raw_outputs/eval_records.jsonl").open() if l.strip()]
recs += [json.loads(l) for l in (PV / "followup/followup_records.jsonl").open() if l.strip()]
ab = collections.defaultdict(lambda: {"n": 0, "abst": 0, "abst_answer_in_ctx": 0, "answer_in_ctx": 0})
for r in recs:
    k = f'{r["model"]}|{r["condition"]}|{r["prompt_mode"]}'
    present = in_ctx(r["sample_id"], ctx[(r["sample_id"], r["condition"])])
    a = bool(ABST.search(r["predicted_answer"] or ""))
    c = ab[k]; c["n"] += 1; c["answer_in_ctx"] += present; c["abst"] += a; c["abst_answer_in_ctx"] += a and present
res["abstention_vs_answerability_2x2"] = dict(ab)

# ------------------------------------------------------------------ 2-3. fresh cohort
fresh = [json.loads(l) for l in (ROOT / "experiments/fresh_table_cohort/records.jsonl").open() if l.strip()]
fa = {}
for arm in ["N_raw", "N_clean", "D", "F2", "G"]:
    n_ab = n_ab_in = 0
    for r in fresh:
        o = r[arm]
        if ABST.search(o["pred"] or ""):
            n_ab += 1; n_ab_in += in_ctx(r["sample_id"], o.get("context") or "")
    fa[arm] = {"abstained": n_ab, "abstained_answer_in_ctx": n_ab_in}
res["fresh_abstention_vs_answerability"] = fa


def defective(md):
    """Placeholder header or a first column empty in at least half of the body rows of some table."""
    for block in re.split(r"\n\s*\n", md):
        rows = [l for l in block.splitlines() if l.strip().startswith("|")]
        if len(rows) < 3: continue
        header, body = rows[0], [x for x in rows[2:]]
        if re.search(r"\|\s*Col_\d+\s*\|", header): return "placeholder_header"
        first = [x.strip().strip("|").split("|")[0].strip() for x in body]
        if body and sum(1 for f in first if not f) >= max(2, len(body) / 2): return "empty_first_column"
    return None


kinds = collections.Counter(); em_def = []; em_ok = []; d_vs = {"G_ok_on_def": 0, "N_raw_ok_on_def": 0}
for r in fresh:
    g = r["G"]; kind = defective(g.get("context") or "")
    if kind:
        kinds[kind] += 1; em_def.append(g["em"]); d_vs["G_ok_on_def"] += g["em"]; d_vs["N_raw_ok_on_def"] += r["N_raw"]["em"]
    elif "|" in (g.get("context") or ""):
        em_ok.append(g["em"])
b = sum(1 for r in fresh if defective(r["G"].get("context") or "") and r["G"]["em"] and not r["N_raw"]["em"])
c = sum(1 for r in fresh if defective(r["G"].get("context") or "") and r["N_raw"]["em"] and not r["G"]["em"])
res["g_table_rendering_defect"] = {"cases": sum(kinds.values()), "by_kind": dict(kinds), "g_em_defective": int(sum(em_def)),
                                   "g_em_rate_defective": float(np.mean(em_def)) if em_def else None,
                                   "g_em_rate_other_table_contexts": float(np.mean(em_ok)) if em_ok else None,
                                   "n_other_table_contexts": len(em_ok), **d_vs, "G_vs_N_raw_discordant": [b, c], "p": mcn(b, c)}

# ------------------------------------------------------------------ 4. latency (main prompt experiment only)
lat = collections.defaultdict(list)
for r in recs:
    if "latency_ms" in r and r.get("latency_ms") is not None:
        lat[f'{r["model"]}|{r["condition"]}|{r["prompt_mode"]}'].append(r["latency_ms"])
res["generation_latency_ms"] = {k: {"n": len(v), "median": float(np.median(v)), "p90": float(np.percentile(v, 90)),
                                    "max": float(max(v))} for k, v in sorted(lat.items())}

OUT.write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
