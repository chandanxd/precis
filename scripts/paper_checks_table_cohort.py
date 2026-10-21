"""Verification analyses for the table-bearing cohort (paper Sec. 6.2).

Reads only stored experiment records; writes results/paper_checks/table_cohort_checks.json.
No model calls. Run: python3 scripts/paper_checks_table_cohort.py
"""
import json, re, random, collections, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "results/diagnostic_experiment_4_v1/experiment_4_8_0_final_confirmatory_20261011/eval_records.jsonl"
THR = ROOT / "results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl"
OUT = ROOT / "results/paper_checks/table_cohort_checks.json"
CONDS = "abcdefg"

rows = [json.loads(l) for l in REC.open()][1:]
assert len(rows) == 200


def exact_mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n * 2
    return min(1.0, p)


def paired(x, y, metric):
    """x vs y; b = x correct & y wrong, c = x wrong & y correct."""
    b = sum(1 for r in rows if r[f"cond_{x}"][metric] and not r[f"cond_{y}"][metric])
    c = sum(1 for r in rows if (not r[f"cond_{x}"][metric]) and r[f"cond_{y}"][metric])
    return b, c


def cluster_boot(x, y, metric, B=10000, seed=42):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["question"]].append(int(r[f"cond_{x}"][metric]) - int(r[f"cond_{y}"][metric]))
    keys = list(groups)
    rnd = random.Random(seed)
    stats = []
    for _ in range(B):
        tot = n = 0
        for _ in keys:
            g = groups[keys[rnd.randrange(len(keys))]]
            tot += sum(g); n += len(g)
        stats.append(tot / n)
    stats.sort()
    return stats[int(0.025 * B)], stats[int(0.975 * B)]


res = {"n_cases": len(rows), "distinct_questions": len({r["question"] for r in rows}), "pairs": {}}
pairs = [("b", "d"), ("a", "b"), ("a", "d"), ("d", "f"), ("g", "a"), ("g", "b"), ("g", "c"),
         ("g", "d"), ("g", "e"), ("g", "f"), ("e", "d"), ("f", "d"), ("d", "b"), ("c", "b")]
for x, y in pairs:
    for m in ("exact_match", "containment"):
        b, c = paired(x, y, m)
        lo, hi = cluster_boot(x, y, m)
        res["pairs"][f"{x}-{y}:{m}"] = {"x_only": b, "y_only": c, "net_pp_x_minus_y": 100 * (b - c) / 200,
                                        "p_exact_mcnemar": exact_mcnemar(b, c),
                                        "cluster_boot95_pp": [100 * lo, 100 * hi]}

# --- repeated-question structure
cnt = collections.Counter(r["question"] for r in rows)
res["repeated_questions"] = {q: n for q, n in cnt.items() if n > 1}

# --- negation rendering in stored contexts (only F and G have stored contexts)
neg_cue = re.compile(r"\b(?:not|never|n't)\b", re.I)
double = re.compile(r"(?<=\s)NOT (?=(?:\S+ ){0,2}(?:[Nn]ot|NOT|[Nn]ever|n't|N'T)(?=\s|$))")
neg = {}
for c in "fg":
    withNOT = dbl = 0
    dbl_cases = []
    nfacts = 0
    for r in rows:
        ctx = r[f"cond_{c}"]["context"]
        hit = False; dhit = False
        for line in ctx.split("\n"):
            if line.startswith("Fact "):
                nfacts += 1
            if re.search(r"\bNOT\b", line):
                hit = True
                if double.search(line):
                    dhit = True
        withNOT += hit; dbl += dhit
        if dhit: dbl_cases.append((r["case_id"][:8], r[f"cond_{c}"]["exact_match"]))
    neg[c] = {"contexts_with_NOT": withNOT, "contexts_with_doubled_negation": dbl,
              "facts_rendered_total": nfacts, "doubled_cases_(id,EM)": dbl_cases}
res["negation_in_stored_contexts"] = neg

# --- proxy vs native token counts (full prompt includes template overhead)
tok = {}
for c in "fg":
    xs = [(r[f"cond_{c}"]["context_estimated_tokens"], r[f"cond_{c}"]["full_prompt_model_tokens"]) for r in rows
          if r[f"cond_{c}"].get("full_prompt_model_tokens")]
    n = len(xs)
    mx = sum(a for a, _ in xs) / n; my = sum(b for _, b in xs) / n
    sxx = sum((a - mx) ** 2 for a, _ in xs); sxy = sum((a - mx) * (b - my) for a, b in xs)
    slope = sxy / sxx; icpt = my - slope * mx
    ss_tot = sum((b - my) ** 2 for _, b in xs); ss_res = sum((b - (icpt + slope * a)) ** 2 for a, b in xs)
    tok[c] = {"n": n, "mean_est_ctx_tokens": mx, "mean_full_prompt_model_tokens": my,
              "slope_native_per_est": slope, "intercept_template_overhead": icpt, "r2": 1 - ss_res / ss_tot}
# implied native context tokens = full_prompt - intercept of the pooled fit
a_all = [(r[f"cond_{c}"]["context_estimated_tokens"], r[f"cond_{c}"]["full_prompt_model_tokens"], c) for r in rows for c in "fg"]
n = len(a_all); mx = sum(a for a, _, _ in a_all) / n; my = sum(b for _, b, _ in a_all) / n
slope = sum((a - mx) * (b - my) for a, b, _ in a_all) / sum((a - mx) ** 2 for a, _, _ in a_all)
icpt = my - slope * mx
res["token_proxy"] = {"per_variant": tok, "pooled_slope": slope, "pooled_intercept": icpt}
mean_f = sum(r["cond_f"]["full_prompt_model_tokens"] for r in rows) / 200
mean_g = sum(r["cond_g"]["full_prompt_model_tokens"] for r in rows) / 200
res["token_proxy"]["mean_full_prompt_model_tokens"] = {"F": mean_f, "G": mean_g, "relative_reduction_pct": 100 * (1 - mean_g / mean_f)}
ef = sum(r["cond_f"]["context_estimated_tokens"] for r in rows) / 200
eg = sum(r["cond_g"]["context_estimated_tokens"] for r in rows) / 200
res["token_proxy"]["mean_estimated"] = {"F": ef, "G": eg, "relative_reduction_pct": 100 * (1 - eg / ef)}
# paired bootstrap-free: per-case native reduction
red = [(r["cond_f"]["full_prompt_model_tokens"] - r["cond_g"]["full_prompt_model_tokens"]) for r in rows]
res["token_proxy"]["native_paired_reduction_mean"] = sum(red) / 200
res["token_proxy"]["native_G_lt_F_cases"] = sum(1 for d in red if d > 0)
res["token_proxy"]["native_G_gt_F_cases"] = sum(1 for d in red if d < 0)
res["token_proxy"]["max_full_prompt_tokens"] = {"F": max(r["cond_f"]["full_prompt_model_tokens"] for r in rows),
                                                 "G": max(r["cond_g"]["full_prompt_model_tokens"] for r in rows)}

res["token_proxy"]["native_prompt_gt_2048"] = {c.upper(): sum(1 for r in rows if r[f"cond_{c}"]["full_prompt_model_tokens"] > 2048) for c in "fg"}
dbl_f = [r for r in rows if re.search(r"\bNOT\b", r["cond_f"]["context"]) and any(double.search(l) for l in r["cond_f"]["context"].split("\n"))]
res["F_vs_G_sensitivity"] = {"F_contexts_with_doubled_negation": len(dbl_f),
    "of_which_F_EM_wrong": sum(1 for r in dbl_f if not r["cond_f"]["exact_match"]),
    "of_which_G_EM_right": sum(1 for r in dbl_f if r["cond_g"]["exact_match"])}
# --- where does the gold answer sit? (evidence flags stored by the 4.2 threshold run)
thr = [json.loads(l) for l in THR.open()][1:]
flags = collections.Counter()
for r in thr:
    flags[(bool(r.get("evidence_in_source")), bool(r.get("evidence_in_all_tables")))] += 1
res["answer_location_(in_source,in_any_table)"] = {str(k): v for k, v in flags.items()}
res["answer_location_n"] = len(thr)
OUT.write_text(json.dumps(res, indent=1, default=str))
print("written", OUT)
