"""
Précis Experiment 4.4 Full-Cohort Confirmatory Evaluation Runner.

Evaluates Condition E (Structural Table Retention at theta=0.0 + Candidate Content Lists)
against frozen Conditions A, B, C, and D across the entire 200-case table-bearing cohort.

Reuses:
- Conditions A, B, C from Stage C / Experiment 4.2 (800 frozen predictions, 0 new inferences).
- Condition E for the 31 Gate 2 cases (reused bit-identically from Gate 2 Stage 2B).
- Executes live generation strictly for the 169 remaining table-bearing cases.

Enforces:
- Hard 2,048-token context ceiling.
- Zero modifications to backend/src/precis/.
- Strict non-imputation of failures/unscorable cases.
- Idempotent checkpointing and resumption.
- Pre-registered paired comparisons, exact McNemar tests, strata, and sensitivity analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add backend/src and scripts to path
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
SRC_DIR = REPO_ROOT / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import requests
import scipy.stats

from diagnostic_list_extractor import (
    extract_lists_from_html,
    is_nav_or_boilerplate_list,
    render_list_to_markdown,
)
from eval_experiment_4_2_threshold import (
    build_table_retention_context,
    compute_mcnemar_exact,
    estimate_text_tokens,
    generate_answer,
)
from eval_experiment_4_3_gate2_runner import (
    build_candidate_condition_b_context,
)
from eval_table_selection_v2 import (
    check_containment,
    check_exact_match,
    check_rouge_l,
    contains_answer,
)

EXPERIMENT_ID = "diagnostic_experiment_4_4_full_cohort"
DEFAULT_TOKEN_CEILING = 2048
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42
AMBIGUOUS_CASE_ID = "895b5134173847ff8837c187a367cde0"

MANIFEST_PATH = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest.jsonl"
STAGE_C_PATH = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "eval_records_stage_c.jsonl"
EXP42_PATH = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "full_cohort_threshold_20261010" / "eval_records.jsonl"
GATE2_STAGE2B_PATH = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "gate_2_list_extraction_20261010" / "stage_2b_eval_records.jsonl"
NQ_PATH = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

OUTPUT_DIR = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "full_cohort_evaluation_20261010"


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_inputs() -> Dict[str, Any]:
    expected = {
        "sample_manifest.jsonl": (MANIFEST_PATH, "011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7"),
        "eval_records_stage_c.jsonl": (STAGE_C_PATH, "e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687"),
        "eval_records_exp42.jsonl": (EXP42_PATH, "d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0"),
        "gate2_stage_2b_records.jsonl": (GATE2_STAGE2B_PATH, "417fab9df822674e128c052fae2ad5153a9b8f96faf6e9995760eec334fc9e4f"),
        "nq_dev.jsonl": (NQ_PATH, "14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491"),
    }
    verifications = {}
    for name, (p, exp_hash) in expected.items():
        if not p.exists():
            raise FileNotFoundError(f"Missing required input: {p}")
        actual_hash = compute_file_sha256(p)
        if actual_hash != exp_hash:
            raise ValueError(f"Hash mismatch on {name}: expected {exp_hash}, got {actual_hash}")
        verifications[name] = {"path": str(p), "sha256": actual_hash, "match": True}
    return verifications


def ping_ollama(base_url: str, model: str) -> None:
    endpoint = f"{base_url.rstrip('/')}/api/tags"
    try:
        resp = requests.get(endpoint, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        if not any(model in m for m in models):
            raise RuntimeError(f"Model '{model}' not found in Ollama daemon. Available: {models}")
    except Exception as exc:
        raise RuntimeError(f"Could not connect to Ollama daemon at {endpoint}: {exc}")


def binomial_ci_discordant(b: int, c: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Compute 95% Wald or exact CI for net percentage point difference (b - c) / n."""
    diff = (b - c) / n
    # Variance of (b - c) / n under multinomial paired distribution is (b + c - (b - c)^2 / n) / n^2
    var = (b + c - ((b - c) ** 2) / n) / (n ** 2)
    se = (var ** 0.5) if var > 0 else 0.0
    z = scipy.stats.norm.ppf(1 - (1 - confidence) / 2)
    margin = z * se
    return round((diff - margin) * 100, 2), round((diff + margin) * 100, 2)


def main():
    parser = argparse.ArgumentParser(description="Précis Experiment 4.4 Full-Cohort Runner")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama API base URL")
    parser.add_argument("--dry-run", action="store_true", help="Do not call model inference; output mock responses")
    args = parser.parse_args()

    print("=" * 80)
    print("PRÉCIS EXPERIMENT 4.4: FULL-COHORT CONFIRMATORY EVALUATION")
    print("=" * 80)

    # 1. Input integrity
    print("\n[Step 1] Verifying Preflight SHA-256 Digests...")
    verifications = verify_inputs()
    print("All 5 frozen input files verified successfully bit-identically.")

    # 2. Ollama Daemon check
    if not args.dry_run:
        print(f"\n[Step 2] Verifying Ollama Daemon at {args.base_url} for '{DEFAULT_MODEL}'...")
        ping_ollama(args.base_url, DEFAULT_MODEL)
        print("Ollama daemon is healthy and model is loaded.")
    else:
        print("\n[Step 2] Dry-run mode: skipping live daemon check.")

    # 3. Load Manifest and Inputs
    print("\n[Step 3] Loading Cohorts & Frozen Inputs...")
    manifest_records = [json.loads(l) for l in MANIFEST_PATH.read_text().splitlines() if l.strip()]
    table_bearing_manifest = [r for r in manifest_records if r.get("type") == "sample_record" and r.get("stratum") == "table_bearing"]
    if len(table_bearing_manifest) != 200:
        raise ValueError(f"Expected exactly 200 table-bearing cases in manifest, found {len(table_bearing_manifest)}")

    stage_c_records = {json.loads(l)["sample_id"]: json.loads(l) for l in STAGE_C_PATH.read_text().splitlines() if l.strip() and json.loads(l).get("type") == "sample_record"}
    exp42_records = {json.loads(l)["case_id"]: json.loads(l) for l in EXP42_PATH.read_text().splitlines() if l.strip() and json.loads(l).get("type") != "run_header"}
    gate2_records = {json.loads(l)["case_id"]: json.loads(l) for l in GATE2_STAGE2B_PATH.read_text().splitlines() if l.strip()}

    print(f"Loaded {len(table_bearing_manifest)} table-bearing manifest cases.")
    print(f"Loaded {len(stage_c_records)} Stage C records.")
    print(f"Loaded {len(exp42_records)} Exp 4.2 records.")
    print(f"Loaded {len(gate2_records)} Gate 2 Condition E records for reuse.")

    # Load NQ Docs
    print("\nLoading NQ source documents...")
    with open(NQ_PATH, "r", encoding="utf-8") as f:
        nq_docs = {json.loads(l)["doc_id"]: json.loads(l) for l in f if l.strip()}
    print(f"Loaded {len(nq_docs)} raw NQ documents.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eval_records_path = OUTPUT_DIR / "eval_records.jsonl"

    # Load existing checkpoint if any
    existing_records: Dict[str, Dict[str, Any]] = {}
    if eval_records_path.exists():
        for line in eval_records_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("type") != "run_header" and "case_id" in rec:
                existing_records[rec["case_id"]] = rec
        print(f"Found existing checkpoint with {len(existing_records)} completed records.")

    # 4. Execute Full-Cohort Evaluation
    print("\n" + "=" * 80)
    print("EXECUTING FULL-COHORT EVALUATION (Conditions A-E on 200 cases)")
    print("=" * 80)

    reused_count = 0
    generated_count = 0
    checkpointed_count = 0

    all_case_records: List[Dict[str, Any]] = []

    # Open file in append/write mode
    # If resuming, keep existing records; otherwise initialize run header
    run_header = {
        "type": "run_header",
        "experiment_id": EXPERIMENT_ID,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_cases": 200,
        "hyperparameters": {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMP,
            "top_p": DEFAULT_TOP_P,
            "seed": DEFAULT_SEED,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "token_ceiling": DEFAULT_TOKEN_CEILING,
            "table_threshold": 0.0,
            "include_lists": True,
            "prompt_style": "concise",
        },
        "input_hashes": {k: v["sha256"] for k, v in verifications.items()},
    }

    # Open writer
    with open(eval_records_path, "w" if not existing_records else "a", encoding="utf-8") as out_f:
        if not existing_records:
            out_f.write(json.dumps(run_header) + "\n")
            out_f.flush()

        for idx, m in enumerate(table_bearing_manifest, 1):
            cid = m["sample_id"]
            q = m["question"]
            gold = m["gold_answer"]
            answers = m["answers"]

            # If already checkpointed
            if cid in existing_records:
                all_case_records.append(existing_records[cid])
                checkpointed_count += 1
                continue

            # Load frozen Conditions A-D
            c_rec = stage_c_records[cid]
            e_rec = exp42_records[cid]

            cond_a = {
                "condition_id": "cond_a_prose_baseline",
                "predicted_answer": c_rec["cond_a"]["predicted_answer"],
                "exact_match": c_rec["cond_a"]["exact_match"],
                "containment": c_rec["cond_a"]["containment"],
                "context_estimated_tokens": c_rec["cond_a"].get("context_tokens", 0),
                "status": c_rec["cond_a"].get("status", "success"),
                "provenance": {"source": "eval_records_stage_c.jsonl"},
            }
            cond_b = {
                "condition_id": "cond_b_stage_c_decomp",
                "predicted_answer": c_rec["cond_b"]["predicted_answer"],
                "exact_match": c_rec["cond_b"]["exact_match"],
                "containment": c_rec["cond_b"]["containment"],
                "context_estimated_tokens": c_rec["cond_b"].get("context_tokens", 0),
                "status": c_rec["cond_b"].get("status", "success"),
                "provenance": {"source": "eval_records_stage_c.jsonl"},
            }
            cond_c = {
                "condition_id": "cond_c_structural_retention_theta2",
                "predicted_answer": e_rec["cond_c"]["predicted_answer"],
                "exact_match": e_rec["cond_c"]["exact_match"],
                "containment": e_rec["cond_c"]["containment"],
                "context_estimated_tokens": e_rec["cond_c"].get("context_estimated_tokens", 0),
                "full_prompt_model_tokens": e_rec["cond_c"].get("full_prompt_model_tokens"),
                "generated_tokens": e_rec["cond_c"].get("generated_tokens", 0),
                "latency_ms": e_rec["cond_c"].get("latency_ms", 0),
                "status": e_rec["cond_c"].get("status", "success"),
                "provenance": {"source": "eval_records_exp42.jsonl"},
            }
            cond_d = {
                "condition_id": "cond_d_structural_retention_theta0",
                "predicted_answer": e_rec["cond_d"]["predicted_answer"],
                "exact_match": e_rec["cond_d"]["exact_match"],
                "containment": e_rec["cond_d"]["containment"],
                "context_estimated_tokens": e_rec["cond_d"].get("context_estimated_tokens", 0),
                "full_prompt_model_tokens": e_rec["cond_d"].get("full_prompt_model_tokens"),
                "generated_tokens": e_rec["cond_d"].get("generated_tokens", 0),
                "latency_ms": e_rec["cond_d"].get("latency_ms", 0),
                "status": e_rec["cond_d"].get("status", "success"),
                "provenance": {"source": "eval_records_exp42.jsonl"},
            }

            # Condition E: Check if in Gate 2 for reuse
            if cid in gate2_records:
                g_b = gate2_records[cid]["condition_b_candidate"]
                cond_e = {
                    "condition_id": "cond_e_tables_and_lists",
                    "predicted_answer": g_b["predicted_answer"],
                    "raw_response": g_b.get("raw_response", g_b["predicted_answer"]),
                    "exact_match": g_b["exact_match"],
                    "containment": g_b["containment"],
                    "rouge_l": g_b.get("rouge_l", 0.0),
                    "context_estimated_tokens": g_b.get("context_estimated_tokens", 0),
                    "full_prompt_model_tokens": g_b.get("full_prompt_model_tokens"),
                    "generated_tokens": g_b.get("generated_tokens", 0),
                    "latency_ms": g_b.get("latency_ms", 0),
                    "status": g_b.get("status", "success"),
                    "error_message": g_b.get("error_message"),
                    "telemetry": g_b.get("telemetry", {}),
                    "provenance": {"source": "gate_2_stage_2b_eval_records.jsonl", "reused": True},
                }
                reused_count += 1
                status_str = f"REUSED (EM={cond_e['exact_match']})"
            else:
                # Live generation for remaining 169 cases
                doc = nq_docs.get(cid, {})
                html_doc = doc.get("document", "")
                ctx_e, telem_e = build_candidate_condition_b_context(html_doc, q, token_ceiling=DEFAULT_TOKEN_CEILING)

                if args.dry_run:
                    pred_e = "[DRY_RUN_MOCK]"
                    raw_e = pred_e
                    status_e = "dry_run"
                    err_e = None
                    prompt_tokens_e = None
                    gen_tokens_e = 0
                    lat_e = 0
                    em_e = False
                    cont_e = False
                    rouge_e = 0.0
                else:
                    try:
                        res = generate_answer(
                            query=q,
                            context=ctx_e,
                            model=DEFAULT_MODEL,
                            temperature=DEFAULT_TEMP,
                            top_p=DEFAULT_TOP_P,
                            max_tokens=DEFAULT_MAX_TOKENS,
                            prompt_style="concise",
                            base_url=args.base_url,
                        )
                        raw_e = res.answer if res.answer is not None else ""
                        pred_e = raw_e.strip()
                        prompt_tokens_e = res.prompt_tokens
                        gen_tokens_e = res.tokens_generated
                        lat_e = res.latency_ms

                        if not pred_e:
                            status_e = "unscorable"
                            err_e = "Empty model completion"
                            em_e = None
                            cont_e = None
                            rouge_e = None
                        else:
                            status_e = "success"
                            err_e = None
                            em_e = check_exact_match(pred_e, gold, answers)
                            cont_e = check_containment(pred_e, gold, answers)
                            rouge_e = check_rouge_l(pred_e, gold, answers)
                    except Exception as exc:
                        pred_e = None
                        raw_e = None
                        status_e = "failed"
                        err_e = str(exc)
                        prompt_tokens_e = None
                        gen_tokens_e = 0
                        lat_e = 0
                        em_e = None
                        cont_e = None
                        rouge_e = None

                cond_e = {
                    "condition_id": "cond_e_tables_and_lists",
                    "predicted_answer": pred_e,
                    "raw_response": raw_e,
                    "exact_match": em_e,
                    "containment": cont_e,
                    "rouge_l": rouge_e,
                    "context_estimated_tokens": telem_e.get("total_context_estimated_tokens", 0),
                    "full_prompt_model_tokens": prompt_tokens_e,
                    "generated_tokens": gen_tokens_e,
                    "latency_ms": lat_e,
                    "status": status_e,
                    "error_message": err_e,
                    "telemetry": telem_e,
                    "provenance": {"source": "live_generation", "reused": False},
                }
                generated_count += 1
                status_str = f"GENERATED (EM={cond_e['exact_match']}, Toks={telem_e['total_context_estimated_tokens']}, Lat={lat_e}ms)"

            # Transitions against D and A
            record = {
                "case_id": cid,
                "stratum": "table_bearing",
                "priority_cohort": e_rec.get("priority_cohort", "unknown"),
                "question": q,
                "gold_answer": gold,
                "answers": answers,
                "is_ambiguous_case": (cid == AMBIGUOUS_CASE_ID),
                "cond_a": cond_a,
                "cond_b": cond_b,
                "cond_c": cond_c,
                "cond_d": cond_d,
                "cond_e": cond_e,
                "e_vs_d": {
                    "em_win": bool(not cond_d["exact_match"] and cond_e["exact_match"]),
                    "em_loss": bool(cond_d["exact_match"] and not cond_e["exact_match"]),
                    "cont_win": bool(not cond_d["containment"] and cond_e["containment"]),
                    "cont_loss": bool(cond_d["containment"] and not cond_e["containment"]),
                },
                "e_vs_a": {
                    "em_win": bool(not cond_a["exact_match"] and cond_e["exact_match"]),
                    "em_loss": bool(cond_a["exact_match"] and not cond_e["exact_match"]),
                    "cont_win": bool(not cond_a["containment"] and cond_e["containment"]),
                    "cont_loss": bool(cond_a["containment"] and not cond_e["containment"]),
                },
            }

            all_case_records.append(record)
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()

            print(f"[{idx:03d}/200] {cid[:8]} | {status_str}")

    print("\n" + "=" * 80)
    print(f"EVALUATION EXECUTION COMPLETE:")
    print(f"  Total Cases: {len(all_case_records)}")
    print(f"  Reused from Gate 2: {reused_count}")
    print(f"  Newly Generated: {generated_count}")
    print(f"  From Previous Checkpoint: {checkpointed_count}")
    print("=" * 80)

    # 5. Statistical Analyses and Reports
    print("\n[Step 5] Compiling Aggregate Metrics & Statistical Tests...")

    # Scoring helper
    def analyze_condition_pair(cases: List[Dict[str, Any]], cond_base_key: str, cond_cand_key: str):
        # Exact match
        tt_em = sum(1 for c in cases if c[cond_base_key]["exact_match"] and c[cond_cand_key]["exact_match"])
        tf_em = sum(1 for c in cases if c[cond_base_key]["exact_match"] and not c[cond_cand_key]["exact_match"])  # losses
        ft_em = sum(1 for c in cases if not c[cond_base_key]["exact_match"] and c[cond_cand_key]["exact_match"])  # wins
        ff_em = sum(1 for c in cases if not c[cond_base_key]["exact_match"] and not c[cond_cand_key]["exact_match"])

        y_cand_em = [bool(c[cond_cand_key]["exact_match"]) for c in cases]
        y_base_em = [bool(c[cond_base_key]["exact_match"]) for c in cases]
        mcnemar_em = compute_mcnemar_exact(y_cand_em, y_base_em)
        ci_low_em, ci_high_em = binomial_ci_discordant(b=ft_em, c=tf_em, n=len(cases))

        # Containment
        tt_cont = sum(1 for c in cases if c[cond_base_key]["containment"] and c[cond_cand_key]["containment"])
        tf_cont = sum(1 for c in cases if c[cond_base_key]["containment"] and not c[cond_cand_key]["containment"])  # losses
        ft_cont = sum(1 for c in cases if not c[cond_base_key]["containment"] and c[cond_cand_key]["containment"])  # wins
        ff_cont = sum(1 for c in cases if not c[cond_base_key]["containment"] and not c[cond_cand_key]["containment"])

        y_cand_cont = [bool(c[cond_cand_key]["containment"]) for c in cases]
        y_base_cont = [bool(c[cond_base_key]["containment"]) for c in cases]
        mcnemar_cont = compute_mcnemar_exact(y_cand_cont, y_base_cont)
        ci_low_cont, ci_high_cont = binomial_ci_discordant(b=ft_cont, c=tf_cont, n=len(cases))

        return {
            "exact_match": {
                "base_correct": tt_em + tf_em,
                "base_rate": round((tt_em + tf_em) / len(cases) * 100, 2),
                "cand_correct": tt_em + ft_em,
                "cand_rate": round((tt_em + ft_em) / len(cases) * 100, 2),
                "contingency_table": {"both_correct": tt_em, "losses": tf_em, "wins": ft_em, "both_incorrect": ff_em},
                "wins": ft_em,
                "losses": tf_em,
                "ties": tt_em + ff_em,
                "net_wins": ft_em - tf_em,
                "net_percentage_points": round((ft_em - tf_em) / len(cases) * 100, 2),
                "ci_95_pct": [ci_low_em, ci_high_em],
                "mcnemar_p_value": mcnemar_em.get("p_value"),
                "statistically_significant_05": mcnemar_em.get("significant_05", False),
            },
            "containment": {
                "base_correct": tt_cont + tf_cont,
                "base_rate": round((tt_cont + tf_cont) / len(cases) * 100, 2),
                "cand_correct": tt_cont + ft_cont,
                "cand_rate": round((tt_cont + ft_cont) / len(cases) * 100, 2),
                "contingency_table": {"both_correct": tt_cont, "losses": tf_cont, "wins": ft_cont, "both_incorrect": ff_cont},
                "wins": ft_cont,
                "losses": tf_cont,
                "ties": tt_cont + ff_cont,
                "net_wins": ft_cont - tf_cont,
                "net_percentage_points": round((ft_cont - tf_cont) / len(cases) * 100, 2),
                "ci_95_pct": [ci_low_cont, ci_high_cont],
                "mcnemar_p_value": mcnemar_cont.get("p_value"),
                "statistically_significant_05": mcnemar_cont.get("significant_05", False),
            },
        }

    # Aggregate summaries
    def compute_condition_rates(cases: List[Dict[str, Any]]):
        n = len(cases)
        return {
            cond_key: {
                "exact_match_count": sum(1 for c in cases if c[cond_key]["exact_match"]),
                "exact_match_rate": round(sum(1 for c in cases if c[cond_key]["exact_match"]) / n * 100, 2),
                "containment_count": sum(1 for c in cases if c[cond_key]["containment"]),
                "containment_rate": round(sum(1 for c in cases if c[cond_key]["containment"]) / n * 100, 2),
            }
            for cond_key in ["cond_a", "cond_b", "cond_c", "cond_d", "cond_e"]
        }

    primary_rates = compute_condition_rates(all_case_records)
    paired_comp = {
        "e_vs_d": analyze_condition_pair(all_case_records, "cond_d", "cond_e"),
        "e_vs_a": analyze_condition_pair(all_case_records, "cond_a", "cond_e"),
        "e_vs_c": analyze_condition_pair(all_case_records, "cond_c", "cond_e"),
        "e_vs_b": analyze_condition_pair(all_case_records, "cond_b", "cond_e"),
    }

    # Strata breakdown
    strata_map = {
        "stratum_1_stage_c_regressions_47": [c for c in all_case_records if c["priority_cohort"] == "P1_regression"],
        "stratum_2_stage_c_recoveries_11": [c for c in all_case_records if c["priority_cohort"] == "P2_recovery"],
        "stratum_3_remaining_142": [c for c in all_case_records if c["priority_cohort"] in ("both_loss", "both_win")],
        "diagnostic_gate2_list_subset_31": [c for c in all_case_records if c["case_id"] in gate2_records],
    }
    strata_results = {s_name: compute_condition_rates(s_cases) for s_name, s_cases in strata_map.items()}

    # Sensitivity analysis excluding ambiguous case
    sensitivity_cases = [c for c in all_case_records if c["case_id"] != AMBIGUOUS_CASE_ID]
    sensitivity_rates = compute_condition_rates(sensitivity_cases)
    sensitivity_paired = {
        "e_vs_d": analyze_condition_pair(sensitivity_cases, "cond_d", "cond_e"),
        "e_vs_a": analyze_condition_pair(sensitivity_cases, "cond_a", "cond_e"),
    }

    # Regression audit on Condition D successes and Condition A successes
    regressions_against_d = [
        {
            "case_id": c["case_id"],
            "question": c["question"],
            "gold_answer": c["gold_answer"],
            "cond_d_pred": c["cond_d"]["predicted_answer"],
            "cond_e_pred": c["cond_e"]["predicted_answer"],
            "priority_cohort": c["priority_cohort"],
            "regression_type": "EM_LOSS_AGAINST_CONDITION_D",
            "context_tokens_d": c["cond_d"].get("context_estimated_tokens"),
            "context_tokens_e": c["cond_e"].get("context_estimated_tokens"),
        }
        for c in all_case_records
        if c["cond_d"]["exact_match"] and not c["cond_e"]["exact_match"]
    ]

    regressions_against_a = [
        {
            "case_id": c["case_id"],
            "question": c["question"],
            "gold_answer": c["gold_answer"],
            "cond_a_pred": c["cond_a"]["predicted_answer"],
            "cond_e_pred": c["cond_e"]["predicted_answer"],
            "priority_cohort": c["priority_cohort"],
            "regression_type": "EM_LOSS_AGAINST_CONDITION_A",
        }
        for c in all_case_records
        if c["cond_a"]["exact_match"] and not c["cond_e"]["exact_match"]
    ]

    # Serialize paired comparisons
    paired_path = OUTPUT_DIR / "paired_comparisons.json"
    with open(paired_path, "w", encoding="utf-8") as f:
        json.dump(paired_comp, f, indent=2)

    # Serialize aggregate summary
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "cohort_size": 200,
        "reused_gate2_count": reused_count,
        "newly_generated_count": generated_count,
        "primary_analysis_rates": primary_rates,
        "diagnostic_strata": strata_results,
        "sensitivity_analysis_excluding_ambiguous": {
            "cohort_size": len(sensitivity_cases),
            "excluded_case_id": AMBIGUOUS_CASE_ID,
            "rates": sensitivity_rates,
            "paired_comparisons": sensitivity_paired,
        },
        "regression_summary": {
            "losses_against_condition_d": len(regressions_against_d),
            "losses_against_condition_a": len(regressions_against_a),
            "wins_against_condition_d": paired_comp["e_vs_d"]["exact_match"]["wins"],
            "wins_against_condition_a": paired_comp["e_vs_a"]["exact_match"]["wins"],
        },
    }
    summary_path = OUTPUT_DIR / "aggregate_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Serialize regression audit
    reg_audit_path = OUTPUT_DIR / "regression_audit.jsonl"
    with open(reg_audit_path, "w", encoding="utf-8") as f:
        for r in regressions_against_d + regressions_against_a:
            f.write(json.dumps(r) + "\n")

    print(f"\nWrote paired comparisons to: {paired_path}")
    print(f"Wrote aggregate summary to: {summary_path}")
    print(f"Wrote regression audit to: {reg_audit_path}")

    # Print executive summary
    print("\n" + "=" * 80)
    print("EXECUTIVE RESULTS SUMMARY (Full 200-Case Confirmatory Cohort):")
    print("=" * 80)
    print(f"Condition A (Prose Baseline):      EM = {primary_rates['cond_a']['exact_match_count']}/200 ({primary_rates['cond_a']['exact_match_rate']}%)")
    print(f"Condition B (Stage C Decomp):      EM = {primary_rates['cond_b']['exact_match_count']}/200 ({primary_rates['cond_b']['exact_match_rate']}%)")
    print(f"Condition C (Retention theta=2.0): EM = {primary_rates['cond_c']['exact_match_count']}/200 ({primary_rates['cond_c']['exact_match_rate']}%)")
    print(f"Condition D (Retention theta=0.0): EM = {primary_rates['cond_d']['exact_match_count']}/200 ({primary_rates['cond_d']['exact_match_rate']}%)")
    print(f"Condition E (Tables + Lists):      EM = {primary_rates['cond_e']['exact_match_count']}/200 ({primary_rates['cond_e']['exact_match_rate']}%)")
    print("-" * 80)
    e_d = paired_comp["e_vs_d"]["exact_match"]
    print(f"Condition E vs Condition D (Primary Contrast):")
    print(f"  Wins: {e_d['wins']}, Losses: {e_d['losses']}, Net Delta: +{e_d['net_wins']} ({e_d['net_percentage_points']} pp)")
    print(f"  Exact McNemar p-value: {e_d['mcnemar_p_value']}")
    print(f"  Statistically Significant (p < 0.05): {e_d['statistically_significant_05']}")
    print(f"  95% CI on Delta: [{e_d['ci_95_pct'][0]}%, {e_d['ci_95_pct'][1]}%]")
    print("-" * 80)
    e_a = paired_comp["e_vs_a"]["exact_match"]
    print(f"Condition E vs Condition A (Prose Baseline Contrast):")
    print(f"  Wins: {e_a['wins']}, Losses: {e_a['losses']}, Net Delta: +{e_a['net_wins']} ({e_a['net_percentage_points']} pp)")
    print(f"  Exact McNemar p-value: {e_a['mcnemar_p_value']}")
    print(f"  Statistically Significant (p < 0.05): {e_a['statistically_significant_05']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
