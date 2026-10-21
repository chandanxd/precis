"""
Independent Audit Script for Experiment 4.4 Full-Cohort Evaluation.

Verifies input/output hashes, checks prediction provenance, re-evaluates all scores
independently, recomputes paired McNemar comparisons and confidence intervals,
analyzes context length distributions, breaks down performance by strata,
and performs sensitivity analysis.
"""

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import scipy.stats

# Path setup
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
import sys
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
SRC_DIR = REPO_ROOT / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from eval_table_selection_v2 import check_exact_match, check_containment, check_rouge_l
from eval_experiment_4_2_threshold import compute_mcnemar_exact, estimate_text_tokens


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_independent_audit():
    exp4_4_dir = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "full_cohort_evaluation_20261010"
    audit_out_dir = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "independent_audit_20261010"
    audit_out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Input / Output Hashes
    files_to_hash = {
        "sample_manifest.jsonl": REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest.jsonl",
        "eval_records_stage_c.jsonl": REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "eval_records_stage_c.jsonl",
        "nq_dev.jsonl": REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl",
        "eval_records_exp4_2.jsonl": REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "full_cohort_threshold_20261010" / "eval_records.jsonl",
        "failure_inventory_gate1.jsonl": REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "failure_attribution_20261010" / "failure_inventory.jsonl",
        "gate2_stage_2b_eval_records.jsonl": REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "gate_2_list_extraction_20261010" / "stage_2b_eval_records.jsonl",
        "eval_records_exp4_4.jsonl": exp4_4_dir / "eval_records.jsonl",
        "aggregate_summary.json": exp4_4_dir / "aggregate_summary.json",
        "paired_comparisons.json": exp4_4_dir / "paired_comparisons.json",
        "regression_audit.jsonl": exp4_4_dir / "regression_audit.jsonl",
        "evaluation_report.md": exp4_4_dir / "evaluation_report.md",
        "integrity_report.json": exp4_4_dir / "integrity_report.json",
        "walkthrough.md": exp4_4_dir / "walkthrough.md",
    }

    hashes = {}
    for name, p in files_to_hash.items():
        if p.exists():
            hashes[name] = {"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p), "exists": True}
        else:
            hashes[name] = {"path": str(p.relative_to(REPO_ROOT)), "sha256": None, "exists": False}

    # 2. Load Evaluation Records
    records_exp4_4 = []
    run_header_exp4_4 = None
    with open(files_to_hash["eval_records_exp4_4.jsonl"], "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("type") == "run_header":
                run_header_exp4_4 = r
            else:
                records_exp4_4.append(r)

    assert len(records_exp4_4) == 200, f"Expected 200 records, got {len(records_exp4_4)}"

    # Load Exp 4.2 records for provenance checking
    records_exp4_2 = {}
    with open(files_to_hash["eval_records_exp4_2.jsonl"], "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("type") == "run_header":
                continue
            cid = r.get("case_id") or r.get("sample_id")
            records_exp4_2[cid] = r

    assert len(records_exp4_2) == 200, f"Expected 200 Exp 4.2 records, got {len(records_exp4_2)}"

    # Load Gate 2 records for provenance checking
    records_gate2 = {}
    with open(files_to_hash["gate2_stage_2b_eval_records.jsonl"], "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            cid = r.get("case_id") or r.get("sample_id")
            records_gate2[cid] = r

    assert len(records_gate2) == 31, f"Expected 31 Gate 2 records, got {len(records_gate2)}"

    # 3. Provenance and Score Recomputation
    provenance_audit = {
        "total_records": len(records_exp4_4),
        "gate2_reused_count": 0,
        "newly_generated_count": 0,
        "condition_d_matches_exp4_2_count": 0,
        "gate2_prediction_exact_matches_count": 0,
        "score_recomputation_mismatches": [],
        "provenance_anomalies": [],
    }

    recomputed_case_scores = []
    cond_keys = ["cond_a", "cond_b", "cond_c", "cond_d", "cond_e"]

    for r in records_exp4_4:
        cid = r.get("case_id") or r.get("sample_id")
        q = r["question"]
        gold = r["gold_answer"]
        alts = r.get("answers", [])
        prov = r.get("cond_e", {}).get("provenance", {})
        reused_flag = prov.get("reused", False)

        # Provenance check
        is_gate2 = cid in records_gate2
        if is_gate2:
            provenance_audit["gate2_reused_count"] += 1
            if not reused_flag:
                provenance_audit["provenance_anomalies"].append(f"Case {cid} in Gate 2 but reused_flag is False")
            g2_pred = records_gate2[cid].get("condition_b_candidate", {}).get("predicted_answer", "")
            e_pred = r.get("cond_e", {}).get("predicted_answer", "")
            if g2_pred == e_pred:
                provenance_audit["gate2_prediction_exact_matches_count"] += 1
            else:
                provenance_audit["provenance_anomalies"].append(f"Case {cid} Gate 2 prediction mismatch: '{g2_pred}' vs '{e_pred}'")
        else:
            provenance_audit["newly_generated_count"] += 1
            if reused_flag:
                provenance_audit["provenance_anomalies"].append(f"Case {cid} not in Gate 2 but reused_flag is True")

        # Exp 4.2 Condition D match check
        exp4_2_d_pred = records_exp4_2[cid].get("cond_d", {}).get("predicted_answer", "")
        e4_d_pred = r.get("cond_d", {}).get("predicted_answer", "")
        if exp4_2_d_pred == e4_d_pred:
            provenance_audit["condition_d_matches_exp4_2_count"] += 1
        else:
            provenance_audit["provenance_anomalies"].append(f"Case {cid} Exp 4.2 Condition D prediction mismatch: '{exp4_2_d_pred}' vs '{e4_d_pred}'")

        # Independent Score Verification across all 5 conditions
        case_scores = {"case_id": cid, "stratum": r.get("stratum", "")}
        for ck in cond_keys:
            c_data = r.get(ck, {})
            pred = c_data.get("predicted_answer", "")
            stored_em = c_data.get("exact_match", False)
            stored_cont = c_data.get("containment", False)

            calc_em = check_exact_match(pred, gold, alts)
            calc_cont = check_containment(pred, gold, alts)

            if calc_em != stored_em:
                provenance_audit["score_recomputation_mismatches"].append({
                    "case_id": cid, "condition": ck, "metric": "exact_match",
                    "stored": stored_em, "calculated": calc_em, "pred": pred, "gold": gold
                })
            if calc_cont != stored_cont:
                provenance_audit["score_recomputation_mismatches"].append({
                    "case_id": cid, "condition": ck, "metric": "containment",
                    "stored": stored_cont, "calculated": calc_cont, "pred": pred, "gold": gold
                })

            case_scores[f"{ck}_em"] = calc_em
            case_scores[f"{ck}_cont"] = calc_cont
            case_scores[f"{ck}_tokens"] = c_data.get("context_estimated_tokens", 0)
            case_scores[f"{ck}_latency_ms"] = c_data.get("latency_ms", 0.0)

        recomputed_case_scores.append(case_scores)

    # 4. Independent Aggregate Summary Computation
    n_total = len(recomputed_case_scores)
    independent_summary = {}

    for ck in cond_keys:
        ems = [s[f"{ck}_em"] for s in recomputed_case_scores]
        conts = [s[f"{ck}_cont"] for s in recomputed_case_scores]
        toks = [s[f"{ck}_tokens"] for s in recomputed_case_scores]
        lats = [s[f"{ck}_latency_ms"] / 1000.0 for s in recomputed_case_scores]

        em_count = sum(1 for x in ems if x)
        cont_count = sum(1 for x in conts if x)

        independent_summary[ck] = {
            "n_total": n_total,
            "exact_match_count": em_count,
            "exact_match_pct": round(em_count / n_total * 100.0, 2),
            "containment_count": cont_count,
            "containment_pct": round(cont_count / n_total * 100.0, 2),
            "context_tokens": {
                "mean": round(float(np.mean(toks)), 2),
                "std": round(float(np.std(toks)), 2),
                "median": round(float(np.median(toks)), 2),
                "min": int(np.min(toks)),
                "max": int(np.max(toks)),
                "p25": round(float(np.percentile(toks, 25)), 2),
                "p75": round(float(np.percentile(toks, 75)), 2),
                "p90": round(float(np.percentile(toks, 90)), 2),
                "ceiling_violations": sum(1 for t in toks if t > 2048),
            },
            "latency_seconds": {
                "mean": round(float(np.mean(lats)), 3),
                "median": round(float(np.median(lats)), 3),
            }
        }

    # 5. Paired Comparisons and McNemar Tests
    pairs = [
        ("cond_e", "cond_d", "Condition E vs Condition D"),
        ("cond_e", "cond_a", "Condition E vs Condition A"),
        ("cond_e", "cond_c", "Condition E vs Condition C"),
        ("cond_e", "cond_b", "Condition E vs Condition B"),
        ("cond_d", "cond_a", "Condition D vs Condition A"),
        ("cond_d", "cond_c", "Condition D vs Condition C"),
        ("cond_d", "cond_b", "Condition D vs Condition B"),
    ]

    independent_paired = {}
    for c1, c2, label in pairs:
        y1_em = [s[f"{c1}_em"] for s in recomputed_case_scores]
        y2_em = [s[f"{c2}_em"] for s in recomputed_case_scores]
        y1_cont = [s[f"{c1}_cont"] for s in recomputed_case_scores]
        y2_cont = [s[f"{c2}_cont"] for s in recomputed_case_scores]

        mcnemar_em = compute_mcnemar_exact(y1_em, y2_em)
        mcnemar_cont = compute_mcnemar_exact(y1_cont, y2_cont)

        # Context token differences
        t1 = [s[f"{c1}_tokens"] for s in recomputed_case_scores]
        t2 = [s[f"{c2}_tokens"] for s in recomputed_case_scores]
        token_deltas = [a - b for a, b in zip(t1, t2)]

        independent_paired[f"{c1}_vs_{c2}"] = {
            "comparison": label,
            "exact_match": mcnemar_em,
            "containment": mcnemar_cont,
            "token_delta": {
                "mean_delta": round(float(np.mean(token_deltas)), 2),
                "median_delta": round(float(np.median(token_deltas)), 2),
                "min_delta": int(np.min(token_deltas)),
                "max_delta": int(np.max(token_deltas)),
            }
        }

    # 6. Strata Performance Breakdown
    strata_audit = {
        "stratum_1_stage_c_regressions_n47": {"total": 0, "cond_a_em": 0, "cond_b_em": 0, "cond_c_em": 0, "cond_d_em": 0, "cond_e_em": 0},
        "stratum_2_stage_c_recoveries_n11": {"total": 0, "cond_a_em": 0, "cond_b_em": 0, "cond_c_em": 0, "cond_d_em": 0, "cond_e_em": 0},
        "stratum_3_remaining_n142": {"total": 0, "cond_a_em": 0, "cond_b_em": 0, "cond_c_em": 0, "cond_d_em": 0, "cond_e_em": 0},
        "diagnostic_gate2_subset_n31": {"total": 0, "cond_a_em": 0, "cond_b_em": 0, "cond_c_em": 0, "cond_d_em": 0, "cond_e_em": 0},
        "non_gate2_subset_n169": {"total": 0, "cond_a_em": 0, "cond_b_em": 0, "cond_c_em": 0, "cond_d_em": 0, "cond_e_em": 0},
    }

    # Load Stage C records to determine exact Stratum 1 and 2 membership
    stage_c_recs = {}
    with open(files_to_hash["eval_records_stage_c.jsonl"], "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            sc = json.loads(line)
            if "sample_id" in sc:
                stage_c_recs[sc["sample_id"]] = sc

    for s in recomputed_case_scores:
        cid = s["case_id"]
        sc = stage_c_recs.get(cid, {})
        sc_a = sc.get("cond_a", {}).get("exact_match", False)
        sc_b = sc.get("cond_b", {}).get("exact_match", False)

        target_stratum = None
        if sc_a and not sc_b:
            target_stratum = "stratum_1_stage_c_regressions_n47"
        elif not sc_a and sc_b:
            target_stratum = "stratum_2_stage_c_recoveries_n11"
        else:
            target_stratum = "stratum_3_remaining_n142"

        strata_audit[target_stratum]["total"] += 1
        for ck in cond_keys:
            if s[f"{ck}_em"]:
                strata_audit[target_stratum][f"{ck}_em"] += 1

        is_g2 = cid in records_gate2
        g2_key = "diagnostic_gate2_subset_n31" if is_g2 else "non_gate2_subset_n169"
        strata_audit[g2_key]["total"] += 1
        for ck in cond_keys:
            if s[f"{ck}_em"]:
                strata_audit[g2_key][f"{ck}_em"] += 1

    # 7. Sensitivity Analysis: Ambiguous Case 895b5134
    ambig_id = "895b5134173847ff8837c187a367cde0"
    scores_n199 = [s for s in recomputed_case_scores if s["case_id"] != ambig_id]
    y1_em_199 = [s["cond_e_em"] for s in scores_n199]
    y2_em_199 = [s["cond_d_em"] for s in scores_n199]
    mcnemar_199 = compute_mcnemar_exact(y1_em_199, y2_em_199)

    ambig_r = [r for r in records_exp4_4 if (r.get("case_id") or r.get("sample_id")) == ambig_id][0]

    sensitivity_audit = {
        "ambiguous_case_id": ambig_id,
        "ambiguous_case_prefix": "895b5134",
        "case_found_in_cohort": True,
        "case_condition_d_pred": ambig_r.get("cond_d", {}).get("predicted_answer"),
        "case_condition_e_pred": ambig_r.get("cond_e", {}).get("predicted_answer"),
        "case_d_em": ambig_r.get("cond_d", {}).get("exact_match"),
        "case_e_em": ambig_r.get("cond_e", {}).get("exact_match"),
        "full_cohort_n200": {
            "condition_e_em_pct": independent_summary["cond_e"]["exact_match_pct"],
            "condition_d_em_pct": independent_summary["cond_d"]["exact_match_pct"],
            "paired_e_vs_d": independent_paired["cond_e_vs_cond_d"]["exact_match"],
        },
        "excluding_ambiguous_case_n199": {
            "condition_e_em_count": sum(1 for x in y1_em_199 if x),
            "condition_e_em_pct": round(sum(1 for x in y1_em_199 if x) / 199 * 100.0, 2),
            "condition_d_em_count": sum(1 for x in y2_em_199 if x),
            "condition_d_em_pct": round(sum(1 for x in y2_em_199 if x) / 199 * 100.0, 2),
            "paired_e_vs_d": mcnemar_199,
        }
    }

    # 8. Regression and Win Analysis
    wins_e_over_d = []
    losses_e_over_d = []

    for r, s in zip(records_exp4_4, recomputed_case_scores):
        cid = s["case_id"]
        e_em = s["cond_e_em"]
        d_em = s["cond_d_em"]
        if e_em and not d_em:
            wins_e_over_d.append({
                "case_id": cid,
                "question": r["question"],
                "gold_answer": r["gold_answer"],
                "condition_d_prediction": r.get("cond_d", {}).get("predicted_answer", ""),
                "condition_e_prediction": r.get("cond_e", {}).get("predicted_answer", ""),
                "provenance": r.get("cond_e", {}).get("provenance", {}),
            })
        elif not e_em and d_em:
            losses_e_over_d.append({
                "case_id": cid,
                "question": r["question"],
                "gold_answer": r["gold_answer"],
                "condition_d_prediction": r.get("cond_d", {}).get("predicted_answer", ""),
                "condition_e_prediction": r.get("cond_e", {}).get("predicted_answer", ""),
                "provenance": r.get("cond_e", {}).get("provenance", {}),
            })

    discordant_analysis = {
        "wins_count": len(wins_e_over_d),
        "losses_count": len(losses_e_over_d),
        "wins": wins_e_over_d,
        "losses": losses_e_over_d,
    }

    # Write output JSON files
    with open(audit_out_dir / "independent_metrics.json", "w", encoding="utf-8") as f:
        json.dump({
            "independent_summary": independent_summary,
            "independent_paired_comparisons": independent_paired,
            "strata_audit": strata_audit,
            "sensitivity_analysis": sensitivity_audit,
            "discordant_analysis": discordant_analysis,
        }, f, indent=2)

    with open(audit_out_dir / "prediction_provenance_audit.json", "w", encoding="utf-8") as f:
        json.dump(provenance_audit, f, indent=2)

    with open(audit_out_dir / "integrity_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "files_hashed": hashes,
            "cohort_total_n": n_total,
            "unique_case_ids": len(set(s["case_id"] for s in recomputed_case_scores)),
            "score_recomputation_match": len(provenance_audit["score_recomputation_mismatches"]) == 0,
            "provenance_verified": len(provenance_audit["provenance_anomalies"]) == 0,
            "exact_mcnemar_significant_05": independent_paired["cond_e_vs_cond_d"]["exact_match"]["statistically_significant_05"],
            "ceiling_violations": independent_summary["cond_e"]["context_tokens"]["ceiling_violations"],
        }, f, indent=2)

    print("Independent audit script completed successfully.")
    print(f"Condition E EM: {independent_summary['cond_e']['exact_match_pct']}% ({independent_summary['cond_e']['exact_match_count']}/200)")
    print(f"Condition D EM: {independent_summary['cond_d']['exact_match_pct']}% ({independent_summary['cond_d']['exact_match_count']}/200)")
    print(f"Wins: {len(wins_e_over_d)}, Losses: {len(losses_e_over_d)}, p={independent_paired['cond_e_vs_cond_d']['exact_match']['p_value']}")
    print(f"Gate 2 reused: {provenance_audit['gate2_reused_count']}, newly generated: {provenance_audit['newly_generated_count']}")
    print(f"Gate 2 prediction matches: {provenance_audit['gate2_prediction_exact_matches_count']}/31")
    print(f"Exp 4.2 Condition D matches: {provenance_audit['condition_d_matches_exp4_2_count']}/200")
    print(f"Score recomputation mismatches: {len(provenance_audit['score_recomputation_mismatches'])}")
    print(f"Provenance anomalies: {len(provenance_audit['provenance_anomalies'])}")


if __name__ == "__main__":
    run_independent_audit()
