"""Re-derive every table that depends on EM / containment under the single scoring rule of scripts/scoring.py
(gold answer or any MRQA alternative). No model calls. Output: results/paper_checks/unified_scoring.json
ROUGE-L, MiniLM cosine, BERTScore and the LLM-judge equivalence are not rescored (single gold answer; paper Sec. 6.1).
"""
import json, random, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import ROOT, ALIASES, em, cont, mcn, holm, boot, paired  # noqa: E402

res = {}
# ---------------------------------------------------------------- NQ 200-sample benchmark (Sec. 6.7, Table 11)
VERS = {"v1": "nq_benchmark", "v1.5": "nq_benchmark_svoa_enhanced", "v2": "nq_benchmark_svoa_enhanced_v2",
        "v3": "nq_benchmark_svoa_enhanced_v3"}
nq = {}
for v, d in VERS.items():
    nq[v] = collections.defaultdict(dict)
    for l in (ROOT / "results" / d / "per_question_results.jsonl").open():
        r = json.loads(l); nq[v][r["condition"]][r["sample_id"]] = r
EMf = lambda i, r: em(i, r["predicted_answer"]); CTf = lambda i, r: cont(i, r["predicted_answer"])
q = {i: r["question"] for i, r in nq["v3"]["precis_full"].items()}
res["nq200"] = {"distinct_questions": len(set(q.values())), "conditions": sorted(nq["v3"])}
for v in VERS:
    for c, recs in nq[v].items():
        res["nq200"][f"{v}|{c}"] = {"EM": sum(EMf(i, r) for i, r in recs.items()), "containment": sum(CTf(i, r) for i, r in recs.items()),
                                    "EM_stored_single_gold": sum(str(r["exact_match"]) == "True" for r in recs.values())}
N3, P3 = nq["v3"]["naive_rag"], nq["v3"]["precis_full"]
res["nq200"]["naive_vs_precis_v3"] = {"EM": paired(N3, P3, EMf, q), "containment": paired(N3, P3, CTf, q)}
res["nq200"]["v1_to_v15_EM"] = paired(nq["v1.5"]["precis_full"], nq["v1"]["precis_full"], EMf, q)
res["nq200"]["v2_to_v3_EM"] = paired(nq["v3"]["precis_full"], nq["v2"]["precis_full"], EMf, q)
res["nq200"]["v15_to_v2_EM"] = paired(nq["v2"]["precis_full"], nq["v1.5"]["precis_full"], EMf, q)
for c in nq["v3"]:
    if c not in ("naive_rag", "precis_full"):
        res["nq200"][f"{c}_vs_precis_full_v3_EM"] = paired(nq["v3"][c], P3, EMf, q)

# ---------------------------------------------------------------- confirmatory 2x2x2 (Sec. 6.6, Tables 8-10)
D = ROOT / "experiments/prompt_validation"
R = [json.loads(l) for l in (D / "raw_outputs/eval_records.jsonl").open()]
idx = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]): r for r in R}
ids = sorted({r["sample_id"] for r in R})
models = ["qwen2.5-coder:7b", "qwen3.5:4b"]; conds = ["naive_rag", "precis_full"]
cells = {}; EMc = lambda k: em(k[0], idx[k]["predicted_answer"]); CTc = lambda k: cont(k[0], idx[k]["predicted_answer"])
for m in models:
    for c in conds:
        row = {}
        for p in ("standard", "concise"):
            row[f"EM_{p}"] = sum(EMc((i, m, c, p)) for i in ids); row[f"containment_{p}"] = sum(CTc((i, m, c, p)) for i in ids)
            row[f"EM_{p}_stored"] = sum(str(idx[(i, m, c, p)]["exact_match"]) == "True" for i in ids)
            row[f"containment_{p}_stored"] = sum(str(idx[(i, m, c, p)]["containment_correct"]) == "True" for i in ids)
        up = sum(1 for i in ids if (not EMc((i, m, c, "standard"))) and EMc((i, m, c, "concise")))
        dn = sum(1 for i in ids if EMc((i, m, c, "standard")) and not EMc((i, m, c, "concise")))
        row.update({"concise_only_EM": up, "standard_only_EM": dn, "p_one_sided": mcn(up, dn, "one")}); cells[f"{m}|{c}"] = row
res["confirmatory_cells"] = cells
# Holm over the three secondary prompt effects (one-sided)
sec = [k for k in cells if k != "qwen3.5:4b|precis_full"]
hp = holm([cells[k]["p_one_sided"] for k in sec]); res["confirmatory_secondary_holm"] = {k: [cells[k]["p_one_sided"], h] for k, h in zip(sec, hp)}
# interaction: (gain under precis) - (gain under naive), 10,000 paired bootstrap over questions (seed 42)
def gain(m, c, i): return int(EMc((i, m, c, "concise"))) - int(EMc((i, m, c, "standard")))
import numpy as np
inter = {}
for m in models:   # same procedure as experiments/prompt_validation/analyze_results.py (numpy, seed 42, 10,000 resamples)
    d = np.array([gain(m, "precis_full", i) - gain(m, "naive_rag", i) for i in ids], float)
    bm = d[np.random.default_rng(42).integers(0, len(d), size=(10000, len(d)))].mean(1)
    inter[m] = {"point": float(d.mean()), "ci95": [float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))]}
res["confirmatory_interaction_EM"] = inter
ret = {}
for m in models:
    for p in ("standard", "concise"):
        for name, f in (("EM", EMc), ("containment", CTc)):
            nv = sum(1 for i in ids if f((i, m, "naive_rag", p)) and not f((i, m, "precis_full", p)))
            pv = sum(1 for i in ids if (not f((i, m, "naive_rag", p))) and f((i, m, "precis_full", p)))
            ret[f"{m}|{p}|{name}"] = {"naive_only": nv, "precis_only": pv, "p": mcn(nv, pv)}
res["confirmatory_retrieval_effect"] = ret
hp = holm([v["p"] for v in ret.values()]); 
for (k, v), h in zip(ret.items(), hp): v["holm8"] = h
# cross-model comparisons (4): qwen3.5 vs coder under concise/standard x retrieval, EM two-sided
cm = {}
for c in conds:
    for p in ("standard", "concise"):
        x = sum(1 for i in ids if EMc((i, "qwen3.5:4b", c, p)) and not EMc((i, "qwen2.5-coder:7b", c, p)))
        y = sum(1 for i in ids if (not EMc((i, "qwen3.5:4b", c, p))) and EMc((i, "qwen2.5-coder:7b", c, p)))
        cm[f"{c}|{p}"] = {"q35_only": x, "coder_only": y, "p": mcn(x, y)}
hp = holm([v["p"] for v in cm.values()])
for (k, v), h in zip(cm.items(), hp): v["holm4"] = h
res["confirmatory_cross_model_EM"] = cm
# audit-sheet exact-match definition: how many of the 60 audited generations change status
sheet = [json.loads(l) for l in (D / "human_review_sheet.jsonl").open()]
res["confirmatory_n_changed_vs_stored_EM"] = sum(1 for k in idx if EMc(k) != (str(idx[k]["exact_match"]) == "True"))
res["confirmatory_n_changed_vs_stored_containment"] = sum(1 for k in idx if CTc(k) != (str(idx[k]["containment_correct"]) == "True"))

# ---------------------------------------------------------------- 2x2 follow-up (Table 9)
F = [json.loads(l) for l in (D / "followup/followup_records.jsonl").open()]
fi = {(r["sample_id"], r["model"], r["condition"], r["prompt_mode"]): r for r in F}
tab = collections.defaultdict(dict)
for (i, m, c, p), r in fi.items():
    tab[f"{m}|{c}"].setdefault(p, [0, 0]); tab[f"{m}|{c}"][p][0] += em(i, r["predicted_answer"]); tab[f"{m}|{c}"][p][1] += str(r["exact_match"]) == "True"
for m in models:
    for c in conds:
        for p in ("standard", "concise"):
            tab[f"{m}|{c}"][p] = [sum(EMc((i, m, c, p)) for i in ids), sum(str(idx[(i, m, c, p)]["exact_match"]) == "True" for i in ids)]
res["followup_EM_alias_vs_stored"] = tab
(ROOT / "results/paper_checks/unified_scoring.json").write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: res[k] for k in ("confirmatory_n_changed_vs_stored_EM", "confirmatory_n_changed_vs_stored_containment")}))

# ---------------------------------------------------------------- consistency: table cohorts already used this rule
cons = {}
rows = [json.loads(l) for l in (ROOT / "results/diagnostic_experiment_4_v1/experiment_4_8_0_final_confirmatory_20261011/eval_records.jsonl").open()][1:]
for c in "abcdefg":
    k = f"cond_{c}"; n_st = sum(bool(r[k]["exact_match"]) for r in rows); n_re = sum(em(r["case_id"], r[k]["predicted_answer"]) for r in rows)
    cs_st = sum(bool(r[k]["containment"]) for r in rows); cs_re = sum(cont(r["case_id"], r[k]["predicted_answer"]) for r in rows)
    cons[f"table_cohort_{c.upper()}"] = {"EM_stored": n_st, "EM_rescored": n_re, "cont_stored": cs_st, "cont_rescored": cs_re}
fr = [json.loads(l) for l in (ROOT / "experiments/fresh_table_cohort/records.jsonl").open()]
for arm in ("N_raw", "N_clean", "D", "F2", "G"):
    cons[f"fresh_{arm}"] = {"EM_stored": sum(bool(r[arm]["em"]) for r in fr), "EM_rescored": sum(em(r["sample_id"], r[arm]["pred"]) for r in fr),
                            "cont_stored": sum(bool(r[arm]["cont"]) for r in fr), "cont_rescored": sum(cont(r["sample_id"], r[arm]["pred"]) for r in fr)}
res["consistency_table_cohorts"] = cons
(ROOT / "results/paper_checks/unified_scoring.json").write_text(json.dumps(res, indent=1, default=str))
for k, v in cons.items(): print(k, v)
