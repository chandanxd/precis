"""Re-derive Table 6 / Sec. 6.3 numbers and the context-negation scan from raw confirmatory records.

Reads experiments/prompt_validation/{raw_outputs/eval_records.jsonl,cached_contexts.jsonl,
human_review_sheet.jsonl}; writes results/paper_checks/confirmatory_checks.json. No model calls.
"""
import json, re, math, collections, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "experiments/prompt_validation"
OUT = ROOT / "results/paper_checks/confirmatory_checks.json"
R = [json.loads(l) for l in (D / "raw_outputs/eval_records.jsonl").open()]
b = lambda v: str(v) == "True"


def mcn(x, y, alt="two"):
    n = x + y
    if n == 0: return 1.0
    k = min(x, y)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p) if alt == "two" else (sum(math.comb(n, i) for i in range(y + 1)) / 2 ** n)


idx = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]): r for r in R}
ids = sorted({r["sample_id"] for r in R})
models = ["qwen2.5-coder:7b", "qwen3.5:4b"]; conds = ["naive_rag", "precis_full"]
res = {"n_questions": len(ids), "n_records": len(R)}
cells = {}
for m in models:
    for c in conds:
        row = {}
        for metric, key in (("EM", "exact_match"), ("containment", "containment_correct")):
            for p in ("standard", "concise"):
                row[f"{metric}_{p}"] = sum(b(idx[(i, m, c, p)][key]) for i in ids)
        # paired standard->concise
        up = sum(1 for i in ids if (not b(idx[(i, m, c, "standard")]["exact_match"])) and b(idx[(i, m, c, "concise")]["exact_match"]))
        dn = sum(1 for i in ids if b(idx[(i, m, c, "standard")]["exact_match"]) and not b(idx[(i, m, c, "concise")]["exact_match"]))
        row.update({"concise_only_EM": up, "standard_only_EM": dn, "p_one_sided": mcn(up, dn, "one")})
        cells[f"{m}|{c}"] = row
res["cells"] = cells

# retrieval main effect (not run in the paper): Naive vs Precis, per model x prompt, EM and containment
ret = {}
for m in models:
    for p in ("standard", "concise"):
        for metric, key in (("EM", "exact_match"), ("containment", "containment_correct")):
            nv = sum(1 for i in ids if b(idx[(i, m, "naive_rag", p)][key]) and not b(idx[(i, m, "precis_full", p)][key]))
            pv = sum(1 for i in ids if (not b(idx[(i, m, "naive_rag", p)][key])) and b(idx[(i, m, "precis_full", p)][key]))
            ret[f"{m}|{p}|{metric}"] = {"naive_only": nv, "precis_only": pv, "p_two_sided": mcn(nv, pv)}
# pooled across the 4 model x prompt strata (not independent: same questions) -> report per-stratum only
res["retrieval_main_effect"] = ret

# 30-case audit: re-derive the correction mechanism from raw outputs
sheet = [json.loads(l) for l in (D / "human_review_sheet.jsonl").open()]
ref = re.compile(r"insufficient|do(?:es)? not (?:contain|provide|have|include)|not enough information|cannot (?:be )?(?:answer|determin)|no information", re.I)
corr = []
for s in sheet:
    sid = s["sample_id"]
    st = idx[(sid, "qwen3.5:4b", "precis_full", "standard")]; cn = idx[(sid, "qwen3.5:4b", "precis_full", "concise")]
    # the review sheet pairs which model/condition? use the sheet's own outputs to classify
    if s["transition_status"] == "Prompt-Correction":
        mp = s["_blinded_mapping"]
        std_out = s["output_a"] if mp["output_a_prompt"] == "standard" else s["output_b"]
        corr.append({"id": sid[:8], "standard_output": std_out[:110], "refusal_like": bool(ref.search(std_out))})
res["audit_prompt_corrections"] = {"n": len(corr), "refusal_like_standard_output": sum(c["refusal_like"] for c in corr),
                                   "cases": corr}
res["audit_transition_counts"] = dict(collections.Counter(s["transition_status"] for s in sheet))
res["audit_sheet_has_label_fields"] = sorted(set(sheet[0].keys()))

# which model/condition did the sheet audit? check hash of outputs against raw records
m = collections.Counter()
for s in sheet:
    outs = {s["output_a"].strip(), s["output_b"].strip()}
    for r in R:
        if r["sample_id"] == s["sample_id"] and r["predicted_answer"].strip() in outs:
            m[(r["model"], r["condition"], r["prompt_mode"])] += 1
res["audit_sheet_output_source_counts_top"] = [(list(k), v) for k, v in m.most_common(6)]

# negation markers in cached Precis contexts
cc = [json.loads(l) for l in (D / "cached_contexts.jsonl").open()]
double = re.compile(r"(?<=\s)NOT (?=(?:\S+ ){0,2}(?:[Nn]ot|NOT|[Nn]ever|n't|N'T)(?=\s|$))")
nNOT = nDbl = nfacts = 0; ex = []
for r in cc:
    ctx = r["precis_v3"]["context_text"]
    hit = dh = False
    for line in ctx.split("\n"):
        if line.startswith("Fact "): nfacts += 1
        if re.search(r"\bNOT\b", line):
            hit = True
            if double.search(line): dh = True; ex.append(line[:110])
    nNOT += hit; nDbl += dh
affected = set()
for r in cc:
    for line in r["precis_v3"]["context_text"].split("\n"):
        if re.search(r"\bNOT\b", line) and double.search(line): affected.add(r["sample_id"])
bound = {}
for m in models:
    for pm in ("standard", "concise"):
        for metric, key in (("EM", "exact_match"), ("containment", "containment_correct")):
            wrong = sum(1 for i in affected if not b(idx[(i, m, "precis_full", pm)][key]))
            bound[f"{m}|{pm}|{metric}"] = {"affected_contexts": len(affected), "precis_wrong_in_affected": wrong}
res["doubled_negation_sensitivity_bound"] = bound
res["negation_in_cached_precis_contexts"] = {"contexts": len(cc), "with_NOT": nNOT, "with_doubled": nDbl, "facts": nfacts, "examples": ex[:4]}
# does the context rendering used for those experiments match the current packer? record pattern shown
OUT.write_text(json.dumps(res, indent=1, default=str))
print("written", OUT)
