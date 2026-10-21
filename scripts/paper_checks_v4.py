"""Re-analyses requested by the simulated review of v3 (no model calls). Writes results/paper_checks/v4_reanalysis.json.
  backend/venv/bin/python scripts/paper_checks_v4.py

1. Non-inferiority of G (fresh cohort, Table 6) at margins of 3-7 points: 99% and Bonferroni-7 (99.29%) bootstrap intervals and
   Newcombe hybrid-score paired intervals; paired per-case token differences.
2. Table-document and list-only strata of the fresh cohort for all eight arms.
3. Ceiling sweeps (Table 7): exact McNemar of G against N, H and W in all five settings with Holm over the 15 contrasts.
4. 2x2 format-by-abstention follow-up: main effects and interaction per model and retrieval condition, EM and judged.
5. Judge validation: Wilson intervals, agreement by answer format of the audited output.
6. Extractor audit: Wilson intervals per Table 13 row and PABAK.
7. Confirmatory primary test under the single-gold and the alias rule.
8. Table 11: whether v1.5 and v2 differ although their mean facts packed and EM coincide.
"""
import collections, csv, json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/src")); sys.path.insert(0, str(ROOT / "scripts"))
from scoring import em as _em
OUT = ROOT / "results/paper_checks/v4_reanalysis.json"
Z = {0.95: 1.959964, 0.99: 2.575829, 0.99286: 2.690110}


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


def boot(d, level, B_=10000, seed=42):
    rnd = np.random.default_rng(seed); d = np.asarray(d, float)
    s = np.sort([d[rnd.integers(0, len(d), len(d))].mean() for _ in range(B_)])
    a = (1 - level) / 2
    return [100 * s[int(a * B_)], 100 * s[int((1 - a) * B_) - 1]]


def wilson(k, n, level=0.95):
    if n == 0: return [None, None]
    z = Z[level]; p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [c - h, c + h]


def newcombe(x, y, level):
    """Newcombe (1998) method 10: hybrid-score interval for a paired difference of proportions, in points."""
    x = np.asarray(x, int); y = np.asarray(y, int); n = len(x)
    a = int(((x == 1) & (y == 1)).sum()); b = int(((x == 1) & (y == 0)).sum())
    c = int(((x == 0) & (y == 1)).sum()); d = n - a - b - c
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n, level); l2, u2 = wilson(a + c, n, level)
    num = a * d - b * c
    num = max(num - n / 2, 0) if num > 0 else (min(num + n / 2, 0) if num < 0 else 0)
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    phi = num / den if den else 0.0
    dl = math.sqrt(max(0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return [100 * (p1 - p2 - dl), 100 * (p1 - p2 + du)]


def paired(x, y):
    x = np.asarray(x, int); y = np.asarray(y, int)
    b = int(((x == 1) & (y == 0)).sum()); c = int(((x == 0) & (y == 1)).sum())
    return {"diff_pp": 100 * float((x - y).mean()), "x_only": b, "y_only": c, "p": mc(b, c), "ci95_boot": boot(x - y, 0.95)}


res = {}
# ------------------------------------------------------------------ 1-2 fresh cohort and baseline arms
F = ROOT / "experiments/fresh_table_cohort"; B = ROOT / "experiments/baseline_budget"
fresh = {r["sample_id"]: r for r in map(json.loads, (F / "records.jsonl").open())}
single = {r["sample_id"]: r for r in map(json.loads, (B / "single_records.jsonl").open())}
multi = {r["sample_id"]: r for r in map(json.loads, (B / "multi_records.jsonl").open())}
ids = [i for i in fresh if i in single]
row = lambda i, a: fresh[i][a] if a in ("N_raw", "N_clean", "D", "F2", "G") else single[i]["e1"][a]
ARMS = ["N_raw", "N_clean", "W", "TC", "H", "D", "F2", "G"]
EM = {a: [int(row(i, a)["em"]) for i in ids] for a in ARMS}
TOK = {a: [row(i, a)["est_tokens"] for i in ids] for a in ARMS}
ni = {}
for a in ARMS[:-1]:
    r = {"diff_pp": 100 * float(np.mean(np.array(EM["G"]) - np.array(EM[a])))}
    d = np.array(EM["G"]) - np.array(EM[a])
    r["discordant"] = [int((d == 1).sum()), int((d == -1).sum())]
    for lev in (0.99, 0.99286):
        r["boot_%g" % lev] = boot(d, lev); r["newcombe_%g" % lev] = newcombe(EM["G"], EM[a], lev)
    r["verdict_by_margin"] = {str(m): {k: bool(r[k][0] > -m) for k in ("boot_0.99", "newcombe_0.99", "boot_0.99286", "newcombe_0.99286")}
                              for m in (3, 4, 5, 6, 7)}
    t = np.array(TOK["G"], float) - np.array(TOK[a], float)
    r["tokens_G_minus_arm"] = {"mean": float(t.mean()), "ci95_boot": [v / 100 for v in boot(t, 0.95)],
                               "relative_pct": 100 * float(t.mean() / np.mean(TOK[a]))}
    ni[a] = r
res["noninferiority"] = ni
strata = {}
for name, sel in (("table", lambda i: fresh[i]["has_table"]), ("list_only", lambda i: not fresh[i]["has_table"])):
    S = [k for k, i in enumerate(ids) if sel(i)]
    s = {"n": len(S), "em": {a: int(sum(EM[a][k] for k in S)) for a in ARMS}, "G_vs": {}}
    for a in ARMS[:-1]:
        s["G_vs"][a] = paired([EM["G"][k] for k in S], [EM[a][k] for k in S])
    for a in ("N_clean", "N_raw", "W", "TC", "H"):
        s["D_vs_" + a] = paired([EM["D"][k] for k in S], [EM[a][k] for k in S])
    strata[name] = s
res["fresh_strata"] = strata

# ------------------------------------------------------------------ 3 ceiling sweeps, Holm over 15 contrasts
sweep = []
for setting, getter in [("single_256", lambda i, a: single[i]["e2"]["256"][a]), ("single_512", lambda i, a: single[i]["e2"]["512"][a]),
                        ("single_1024", lambda i, a: single[i]["e2"]["1024"][a]),
                        ("multi_1024", lambda i, a: multi[i]["e3"]["1024"][a]), ("multi_2048", lambda i, a: multi[i]["e3"]["2048"][a])]:
    mids = [i for i in ids if i in multi] if setting.startswith("multi") else ids
    g = [int(getter(i, "G")["em"]) for i in mids]
    for a in ("N", "H", "W"):
        p = paired(g, [int(getter(i, a)["em"]) for i in mids]); p.update(setting=setting, arm=a); sweep.append(p)
for p, h in zip(sweep, holm([p["p"] for p in sweep])): p["holm"] = h
res["ceiling_sweep"] = sweep

# ------------------------------------------------------------------ 4 2x2 follow-up decomposition
PV = ROOT / "experiments/prompt_validation"; FU = PV / "followup"
recs = [json.loads(l) for l in (PV / "raw_outputs/eval_records.jsonl").open()] + [json.loads(l) for l in (FU / "followup_records.jsonl").open()]
jud = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]): int(r["judge"]) for r in map(json.loads, (FU / "judge_records.jsonl").open())}
T = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]): r for r in recs}
sids = sorted({k[0] for k in T})
# prompts: standard = sentence+explicit, sent_token = sentence+token, short_explicit, concise = short+token
fu = {}
for m in ("qwen2.5-coder:7b", "qwen3.5:4b"):
    for c in ("naive_rag", "precis_full"):
        cell = {}
        for metric in ("em", "judge"):
            val = lambda s, p: int(_em(s, T[(s, m, c, p)]["predicted_answer"])) if metric == "em" else jud[(s, m, c, p)]
            se, st, he, ht = ([val(s, p) for s in sids] for p in ("standard", "sent_token", "short_explicit", "concise"))
            se, st, he, ht = map(np.array, (se, st, he, ht))
            fmt = ((he + ht) - (se + st)) / 2; ab = ((st + ht) - (se + he)) / 2; inter = (ht - he) - (st - se)
            cell[metric] = {"format_main_pp": 100 * fmt.mean(), "format_ci95": boot(fmt, 0.95),
                            "abstention_main_pp": 100 * ab.mean(), "abstention_ci95": boot(ab, 0.95),
                            "interaction_pp": 100 * inter.mean(), "interaction_ci95": boot(inter, 0.95),
                            "abst_effect_sentence": paired(st, se), "abst_effect_short": paired(ht, he)}
        fu["%s|%s" % (m, c)] = cell
res["followup_2x2"] = fu

# ------------------------------------------------------------------ 5 judge validation
key = json.load(open(FU / "judge_validation_key.json"))
sheet = {r["item"]: r for r in csv.DictReader(open(FU / "judge_validation_sheet.csv"))}
by = collections.defaultdict(lambda: [0, 0, 0])  # agree, scored, hard
for it, k in key.items():
    lab = (sheet[it]["human_label(CORRECT/INCORRECT)"] or "").strip().upper()
    fmt = "sentence" if k["key"][3] in ("standard", "sent_token") else "short"
    if lab not in ("CORRECT", "INCORRECT"): by[fmt][2] += 1; continue
    by[fmt][1] += 1; by[fmt][0] += int((lab == "CORRECT") == bool(k["judge"]))
res["judge_validation"] = {"overall_wilson95": wilson(83, 90), "judge_correct_wilson95": wilson(41, 44), "judge_incorrect_wilson95": wilson(42, 46),
                           "by_format": {f: {"agree": v[0], "scored": v[1], "hard_to_tell": v[2], "wilson95": wilson(v[0], v[1])} for f, v in by.items()}}

# ------------------------------------------------------------------ 6 extractor audit intervals and PABAK
E = json.load(open(ROOT / "experiments/extractor_eval/extractor_scores.json"))
fa = E["facts"]; se_ = E["sentences"]
ci = {}
for who in ("A", "B", "agreed"):
    pp = fa["%s_polarity_precision" % who] if who != "agreed" else fa["agreed_polarity_precision"]
    mp = fa["%s_modality_precision" % who] if who != "agreed" else fa["agreed_modality_precision"]
    for k, v in list(pp.items()) + list(mp.items()):
        ci["%s|%s" % (who, k)] = {"k": v["correct"], "n": v["n"], "wilson95": wilson(v["correct"], v["n"])}
    for s in ("negation", "nonasserted"):
        v = se_["%s_vs_%s" % (s, who)]
        ci["%s|%s_recall" % (who, s)] = {"k": v["tp"], "n": v["tp"] + v["fn"], "wilson95": wilson(v["tp"], v["tp"] + v["fn"])}
        ci["%s|%s_precision" % (who, s)] = {"k": v["tp"], "n": v["tp"] + v["fp"], "wilson95": wilson(v["tp"], v["tp"] + v["fp"])}
res["audit_intervals"] = ci
res["audit_pabak"] = {"polarity": 2 * fa["raw_agreement_polarity"] - 1, "modality_correct": 2 * fa["raw_agreement_modality"] - 1,
                      "sentence_negation": 2 * se_["raw_agreement_negation"] - 1,
                      "sentence_modality_4class": (4 * se_["raw_agreement_modality"] - 1) / 3}
res["audit_modality_errors_A"] = fa["A_modality_errors_stored_to_true"]

# ------------------------------------------------------------------ 7 confirmatory primary test under both rules
cm = [r for r in recs if r["model"] == "qwen3.5:4b" and r["condition"] == "precis_full"]
by_s = collections.defaultdict(dict)
for r in cm: by_s[r["sample_id"]][r["prompt_mode"]] = r
prim = {}
for rule, f in (("single_gold", lambda r: bool(r["exact_match"])), ("alias", lambda r: bool(_em(r["sample_id"], r["predicted_answer"])))):
    b = sum(1 for s, v in by_s.items() if "standard" in v and "concise" in v and f(v["concise"]) and not f(v["standard"]))
    c = sum(1 for s, v in by_s.items() if "standard" in v and "concise" in v and f(v["standard"]) and not f(v["concise"]))
    prim[rule] = {"std": sum(f(v["standard"]) for v in by_s.values() if "standard" in v), "conc": sum(f(v["concise"]) for v in by_s.values() if "concise" in v),
                  "concise_only": b, "standard_only": c, "p_one_sided": sum(math.comb(b + c, i) for i in range(b, b + c + 1)) / 2 ** (b + c) if b + c else 1.0}
res["confirmatory_primary"] = prim

# ------------------------------------------------------------------ 8 Table 11 v1.5 versus v2
load = lambda d: {r["sample_id"]: r for r in map(json.loads, open(ROOT / "results" / d / "per_question_results.jsonl")) if r["condition"] == "precis_full"}
v15, v2 = load("nq_benchmark_svoa_enhanced"), load("nq_benchmark_svoa_enhanced_v2")
res["table11_v15_v2"] = {"mean_packed": [float(np.mean([r["facts_packed"] for r in v15.values()])), float(np.mean([r["facts_packed"] for r in v2.values()]))],
                         "cases_with_different_facts_packed": sum(v15[s]["facts_packed"] != v2[s]["facts_packed"] for s in v15),
                         "cases_with_different_answer": sum(v15[s]["predicted_answer"] != v2[s]["predicted_answer"] for s in v15),
                         "em": [sum(bool(r["exact_match"]) for r in v15.values()), sum(bool(r["exact_match"]) for r in v2.values())]}

OUT.write_text(json.dumps(res, indent=1, default=float)); print("wrote", OUT)
