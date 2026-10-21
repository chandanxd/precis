"""
Précis Experiment 4.8.0: Final Confirmatory Evaluation of Candidate G
(Guarded Structural-Priority Context Packing)

Evaluates Candidate Condition G against frozen Conditions A, B, C, D, E, and F
across the canonical 200-case table-bearing cohort.

Enforces:
- Hard 2,048-token context ceiling.
- Zero modifications to production codebase under backend/src/precis/ or backend/main.py.
- Zero live reruns of historical Conditions A-F (reused directly from frozen records).
- Exactly 200 live inference calls to Ollama qwen2.5-coder:7b (one per case for Condition G).
- Strict non-imputation of failures/unscorable cases.
- Idempotent checkpointing and resumption.
- Pre-registered paired comparisons, exact McNemar tests, strata, and regression tracking.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
SRC_DIR = REPO_ROOT / "backend" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import requests
import scipy.stats

from precis.api.security import sanitize_document
from precis.graph.store import FactStore
from precis.pipeline.inference import generate_answer
from precis.pipeline.orchestrator import assemble_query_context, ingest_document
from eval_experiment_4_2_threshold import compute_mcnemar_exact, estimate_text_tokens
from eval_table_selection_v2 import (
    check_containment,
    check_exact_match,
    check_rouge_l,
)

EXPERIMENT_ID = "diagnostic_experiment_4_8_0_final_confirmatory"
DEFAULT_TOKEN_CEILING = 2048
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42
AMBIGUOUS_CASE_ID = "895b5134173847ff8837c187a367cde0"

MANIFEST_PATH = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest.jsonl"
GATE5_PATH = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "gate_5_confirmatory_evaluation_20261010" / "eval_records.jsonl"
NQ_PATH = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

OUTPUT_DIR = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "experiment_4_8_0_final_confirmatory_20261011"


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_inputs() -> Dict[str, Any]:
    expected = {
        "sample_manifest.jsonl": (MANIFEST_PATH, "011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7"),
        "eval_records_gate5.jsonl": (GATE5_PATH, "edfeec16d87cdf5f168ceb7f8c947a875a0f237dc1c6074ca9ad22e28f600011"),
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
    """Compute 95% CI for net percentage point difference (b - c) / n."""
    diff = (b - c) / n
    var = (b + c - ((b - c) ** 2) / n) / (n ** 2)
    se = (var ** 0.5) if var > 0 else 0.0
    z = scipy.stats.norm.ppf(1 - (1 - confidence) / 2)
    margin = z * se
    return round((diff - margin) * 100, 2), round((diff + margin) * 100, 2)


def analyze_condition_pair(cases: List[Dict[str, Any]], cond_base_key: str, cond_cand_key: str):
    """Compute paired McNemar test and contingency table."""
    tt_em = sum(1 for c in cases if c[cond_base_key]["exact_match"] and c[cond_cand_key]["exact_match"])
    tf_em = sum(1 for c in cases if c[cond_base_key]["exact_match"] and not c[cond_cand_key]["exact_match"])  # losses
    ft_em = sum(1 for c in cases if not c[cond_base_key]["exact_match"] and c[cond_cand_key]["exact_match"])  # wins
    ff_em = sum(1 for c in cases if not c[cond_base_key]["exact_match"] and not c[cond_cand_key]["exact_match"])

    y_cand_em = [bool(c[cond_cand_key]["exact_match"]) for c in cases]
    y_base_em = [bool(c[cond_base_key]["exact_match"]) for c in cases]
    mcnemar_em = compute_mcnemar_exact(y_cand_em, y_base_em)
    ci_low_em, ci_high_em = binomial_ci_discordant(b=ft_em, c=tf_em, n=len(cases))

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
            "statistically_significant_05": mcnemar_em.get("statistically_significant_05", False),
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
            "statistically_significant_05": mcnemar_cont.get("statistically_significant_05", False),
        },
    }


def compute_condition_rates(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(cases)
    return {
        cond_key: {
            "exact_match_count": sum(1 for c in cases if c[cond_key]["exact_match"]),
            "exact_match_rate": round(sum(1 for c in cases if c[cond_key]["exact_match"]) / n * 100, 2),
            "containment_count": sum(1 for c in cases if c[cond_key]["containment"]),
            "containment_rate": round(sum(1 for c in cases if c[cond_key]["containment"]) / n * 100, 2),
        }
        for cond_key in ["cond_a", "cond_b", "cond_c", "cond_d", "cond_e", "cond_f", "cond_g"]
    }


def main():
    parser = argparse.ArgumentParser(description="Précis Experiment 4.8.0 Final Confirmatory Runner")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama API base URL")
    parser.add_argument("--dry-run", action="store_true", help="Do not call model inference; output mock responses")
    args = parser.parse_args()

    print("=" * 80)
    print("PRÉCIS EXPERIMENT 4.8.0: FINAL CONFIRMATORY EVALUATION (CANDIDATE G)")
    print("=" * 80)

    # 1. Input integrity
    print("\n[Step 1] Verifying Preflight SHA-256 Digests...")
    verifications = verify_inputs()
    print("All frozen input files verified successfully bit-identically.")

    # 2. Ollama Daemon check
    if not args.dry_run:
        print(f"\n[Step 2] Verifying Ollama Daemon at {args.base_url} for '{DEFAULT_MODEL}'...")
        ping_ollama(args.base_url, DEFAULT_MODEL)
        print("Ollama daemon is healthy and model is loaded.")
    else:
        print("\n[Step 2] Dry-run mode: skipping live daemon check.")

    # 3. Load Manifest and Frozen Inputs
    print("\n[Step 3] Loading Cohorts & Frozen Inputs...")
    manifest_records = [json.loads(l) for l in MANIFEST_PATH.read_text().splitlines() if l.strip()]
    table_bearing_manifest = [r for r in manifest_records if r.get("type") == "sample_record" and r.get("stratum") == "table_bearing"]
    if len(table_bearing_manifest) != 200:
        raise ValueError(f"Expected exactly 200 table-bearing cases in manifest, found {len(table_bearing_manifest)}")

    gate5_records = {json.loads(l)["case_id"]: json.loads(l) for l in GATE5_PATH.read_text().splitlines() if l.strip() and json.loads(l).get("type") != "run_header"}
    if len(gate5_records) != 200:
        raise ValueError(f"Expected exactly 200 cases in Gate 5 records, found {len(gate5_records)}")

    # Load NQ Docs
    print("Loading NQ source documents...")
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

    # 4. Execute Full-Cohort Evaluation for Condition G
    print("\n" + "=" * 80)
    print("EXECUTING LIVE CANDIDATE G EVALUATION (200 cases)")
    print("=" * 80)

    all_case_records: List[Dict[str, Any]] = []
    checkpointed_count = 0
    generated_count = 0

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
            "prompt_style": "concise",
            "feature_flag": "PRECIS_ENABLE_LIST_EXTRACTION=true",
            "pipeline": "candidate_g_guarded_structural_priority_packing",
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

            # Load frozen Conditions A-F from Gate 5 records
            g5_rec = gate5_records[cid]
            cond_a = g5_rec["cond_a"]
            cond_b = g5_rec["cond_b"]
            cond_c = g5_rec["cond_c"]
            cond_d = g5_rec["cond_d"]
            cond_e = g5_rec["cond_e"]
            cond_f = g5_rec["cond_f"]

            # Live generation for Condition G (Candidate G: Guarded Structural-Priority Context Packing)
            doc_entry = nq_docs.get(cid, {})
            html_doc = doc_entry.get("document", "")
            clean_text = sanitize_document(html_doc)

            collection_name = f"exp48_g_{cid[:12]}_{idx}"
            store = FactStore(in_memory=True, collection_name=collection_name)

            t_pipe_start = time.perf_counter()
            try:
                # 1. Ingestion: extract & persist both SVOA facts and structural blocks
                ingest_res = ingest_document(
                    text=clean_text,
                    source_doc=cid,
                    store=store,
                    enable_list_extraction=True,
                    raw_document=html_doc,
                )

                # 2. Query retrieval & context assembly via the production path
                assembled = assemble_query_context(
                    query=q,
                    store=store,
                    token_ceiling=DEFAULT_TOKEN_CEILING,
                    enable_list_extraction=True,
                    raw_document=None,  # Forces Path B: persisted structural evidence retrieval from store
                )

                context_g = assembled.context
                telem_g = assembled.telemetry
                facts_packed_g = assembled.facts_packed
                use_structural_g = assembled.use_structural

                if args.dry_run:
                    pred_g = "[DRY_RUN_MOCK]"
                    raw_g = pred_g
                    status_g = "dry_run"
                    err_g = None
                    prompt_tokens_g = None
                    gen_tokens_g = 0
                    lat_g = 0
                    em_g = False
                    cont_g = False
                    rouge_g = 0.0
                else:
                    t_gen_start = time.perf_counter()
                    try:
                        res = generate_answer(
                            query=q,
                            context=context_g,
                            model=DEFAULT_MODEL,
                            temperature=DEFAULT_TEMP,
                            top_p=DEFAULT_TOP_P,
                            max_tokens=DEFAULT_MAX_TOKENS,
                            prompt_style="concise",
                            base_url=args.base_url,
                        )
                        raw_g = res.answer if res.answer is not None else ""
                        pred_g = raw_g.strip()
                        prompt_tokens_g = res.prompt_tokens
                        gen_tokens_g = res.tokens_generated
                        lat_g = res.latency_ms

                        if not pred_g:
                            status_g = "unscorable"
                            err_g = "Empty model completion"
                            em_g = None
                            cont_g = None
                            rouge_g = None
                        else:
                            status_g = "success"
                            err_g = None
                            em_g = check_exact_match(pred_g, gold, answers)
                            cont_g = check_containment(pred_g, gold, answers)
                            rouge_g = check_rouge_l(pred_g, gold, answers)
                    except Exception as exc:
                        pred_g = None
                        raw_g = None
                        status_g = "failed"
                        err_g = str(exc)
                        prompt_tokens_g = None
                        gen_tokens_g = 0
                        lat_g = 0
                        em_g = None
                        cont_g = None
                        rouge_g = None

                cond_g = {
                    "condition_id": "cond_g_guarded_structural_priority_packing",
                    "predicted_answer": pred_g,
                    "raw_response": raw_g,
                    "exact_match": em_g,
                    "containment": cont_g,
                    "rouge_l": rouge_g,
                    "context": context_g,
                    "context_estimated_tokens": assembled.tokens_used,
                    "full_prompt_model_tokens": prompt_tokens_g,
                    "generated_tokens": gen_tokens_g,
                    "latency_ms": lat_g,
                    "status": status_g,
                    "error_message": err_g,
                    "facts_packed": facts_packed_g,
                    "use_structural": use_structural_g,
                    "telemetry": telem_g,
                    "provenance": {
                        "source": "live_generation",
                        "pipeline": "candidate_g_guarded_structural_priority_packing",
                        "feature_flag": True,
                    },
                }

            except Exception as pipe_exc:
                cond_g = {
                    "condition_id": "cond_g_guarded_structural_priority_packing",
                    "predicted_answer": None,
                    "raw_response": None,
                    "exact_match": None,
                    "containment": None,
                    "rouge_l": None,
                    "context": "",
                    "context_estimated_tokens": 0,
                    "full_prompt_model_tokens": None,
                    "generated_tokens": 0,
                    "latency_ms": 0,
                    "status": "pipeline_failed",
                    "error_message": str(pipe_exc),
                    "facts_packed": 0,
                    "use_structural": False,
                    "telemetry": {},
                    "provenance": {
                        "source": "live_generation",
                        "pipeline": "candidate_g_guarded_structural_priority_packing",
                        "feature_flag": True,
                    },
                }

            record = {
                "case_id": cid,
                "stratum": m.get("stratum", "table_bearing"),
                "priority_cohort": g5_rec.get("priority_cohort", "unknown"),
                "question": q,
                "gold_answer": gold,
                "answers": answers,
                "is_ambiguous_case": (cid == AMBIGUOUS_CASE_ID),
                "cond_a": cond_a,
                "cond_b": cond_b,
                "cond_c": cond_c,
                "cond_d": cond_d,
                "cond_e": cond_e,
                "cond_f": cond_f,
                "cond_g": cond_g,
                "g_vs_e": {
                    "em_win": bool(not cond_e["exact_match"] and cond_g["exact_match"]),
                    "em_loss": bool(cond_e["exact_match"] and not cond_g["exact_match"]),
                    "cont_win": bool(not cond_e["containment"] and cond_g["containment"]),
                    "cont_loss": bool(cond_e["containment"] and not cond_g["containment"]),
                },
                "g_vs_f": {
                    "em_win": bool(not cond_f["exact_match"] and cond_g["exact_match"]),
                    "em_loss": bool(cond_f["exact_match"] and not cond_g["exact_match"]),
                    "cont_win": bool(not cond_f["containment"] and cond_g["containment"]),
                    "cont_loss": bool(cond_f["containment"] and not cond_g["containment"]),
                },
                "g_vs_d": {
                    "em_win": bool(not cond_d["exact_match"] and cond_g["exact_match"]),
                    "em_loss": bool(cond_d["exact_match"] and not cond_g["exact_match"]),
                    "cont_win": bool(not cond_d["containment"] and cond_g["containment"]),
                    "cont_loss": bool(cond_d["containment"] and not cond_g["containment"]),
                },
                "g_vs_a": {
                    "em_win": bool(not cond_a["exact_match"] and cond_g["exact_match"]),
                    "em_loss": bool(cond_a["exact_match"] and not cond_g["exact_match"]),
                    "cont_win": bool(not cond_a["containment"] and cond_g["containment"]),
                    "cont_loss": bool(cond_a["containment"] and not cond_g["containment"]),
                },
            }

            out_f.write(json.dumps(record) + "\n")
            out_f.flush()
            all_case_records.append(record)
            generated_count += 1

            if idx % 10 == 0 or idx == len(table_bearing_manifest):
                g_em = sum(1 for r in all_case_records if r["cond_g"]["exact_match"])
                g_cont = sum(1 for r in all_case_records if r["cond_g"]["containment"])
                print(f"[{idx}/200] Progress: Cond G EM = {g_em}/{idx} ({g_em/idx*100:.1f}%), Cont = {g_cont}/{idx} ({g_cont/idx*100:.1f}%)")

    print(f"\nExecution finished. Total evaluated: {len(all_case_records)} (Generated: {generated_count}, Checkpointed: {checkpointed_count}).")

    # 5. Analysis & Metric Aggregation
    print("\n[Step 5] Computing Aggregate Metrics & Statistical Tests...")
    rates = compute_condition_rates(all_case_records)
    print("\nSummary Rates (N=200):")
    for k, v in rates.items():
        print(f"  {k.upper()}: EM = {v['exact_match_count']}/200 ({v['exact_match_rate']}%), Cont = {v['containment_count']}/200 ({v['containment_rate']}%)")

    pair_g_vs_e = analyze_condition_pair(all_case_records, "cond_e", "cond_g")
    pair_g_vs_f = analyze_condition_pair(all_case_records, "cond_f", "cond_g")
    pair_g_vs_d = analyze_condition_pair(all_case_records, "cond_d", "cond_g")
    pair_g_vs_a = analyze_condition_pair(all_case_records, "cond_a", "cond_g")

    paired_summary = {
        "g_vs_e": pair_g_vs_e,
        "g_vs_f": pair_g_vs_f,
        "g_vs_d": pair_g_vs_d,
        "g_vs_a": pair_g_vs_a,
    }

    # Strata Breakdown
    # Stratum 1: Historical Stage C regressions (47 cases)
    # Stratum 2: Historical Stage C recoveries (11 cases)
    # Stratum 3: Remaining concordant cases (142 cases)
    # Gate 2 List subset: 31 cases
    strat_1_cases = [r for r in all_case_records if r.get("priority_cohort") == "decomp_regression"]
    strat_2_cases = [r for r in all_case_records if r.get("priority_cohort") == "decomp_recovery"]
    strat_3_cases = [r for r in all_case_records if r.get("priority_cohort") in ("both_win", "both_loss")]
    list_cases = [r for r in all_case_records if any(m["sample_id"] == r["case_id"] and m.get("has_list") for m in table_bearing_manifest)]

    strata_summary = {
        "stratum_1_stage_c_regressions_n47": {
            "n": len(strat_1_cases),
            "cond_a_em": sum(1 for r in strat_1_cases if r["cond_a"]["exact_match"]),
            "cond_d_em": sum(1 for r in strat_1_cases if r["cond_d"]["exact_match"]),
            "cond_e_em": sum(1 for r in strat_1_cases if r["cond_e"]["exact_match"]),
            "cond_f_em": sum(1 for r in strat_1_cases if r["cond_f"]["exact_match"]),
            "cond_g_em": sum(1 for r in strat_1_cases if r["cond_g"]["exact_match"]),
        },
        "stratum_2_stage_c_recoveries_n11": {
            "n": len(strat_2_cases),
            "cond_a_em": sum(1 for r in strat_2_cases if r["cond_a"]["exact_match"]),
            "cond_d_em": sum(1 for r in strat_2_cases if r["cond_d"]["exact_match"]),
            "cond_e_em": sum(1 for r in strat_2_cases if r["cond_e"]["exact_match"]),
            "cond_f_em": sum(1 for r in strat_2_cases if r["cond_f"]["exact_match"]),
            "cond_g_em": sum(1 for r in strat_2_cases if r["cond_g"]["exact_match"]),
        },
        "stratum_3_remaining_concordant_n142": {
            "n": len(strat_3_cases),
            "cond_a_em": sum(1 for r in strat_3_cases if r["cond_a"]["exact_match"]),
            "cond_d_em": sum(1 for r in strat_3_cases if r["cond_d"]["exact_match"]),
            "cond_e_em": sum(1 for r in strat_3_cases if r["cond_e"]["exact_match"]),
            "cond_f_em": sum(1 for r in strat_3_cases if r["cond_f"]["exact_match"]),
            "cond_g_em": sum(1 for r in strat_3_cases if r["cond_g"]["exact_match"]),
        },
        "gate_2_list_subset_n31": {
            "n": len(list_cases),
            "cond_a_em": sum(1 for r in list_cases if r["cond_a"]["exact_match"]),
            "cond_d_em": sum(1 for r in list_cases if r["cond_d"]["exact_match"]),
            "cond_e_em": sum(1 for r in list_cases if r["cond_e"]["exact_match"]),
            "cond_f_em": sum(1 for r in list_cases if r["cond_f"]["exact_match"]),
            "cond_g_em": sum(1 for r in list_cases if r["cond_g"]["exact_match"]),
        },
    }

    # N=199 Sensitivity Analysis
    n199_cases = [r for r in all_case_records if not r.get("is_ambiguous_case")]
    rates_n199 = compute_condition_rates(n199_cases)
    pair_g_vs_e_n199 = analyze_condition_pair(n199_cases, "cond_e", "cond_g")
    pair_g_vs_f_n199 = analyze_condition_pair(n199_cases, "cond_f", "cond_g")
    pair_g_vs_d_n199 = analyze_condition_pair(n199_cases, "cond_d", "cond_g")
    pair_g_vs_a_n199 = analyze_condition_pair(n199_cases, "cond_a", "cond_g")

    # Invariants & Telemetry
    tokens_used = [r["cond_g"]["context_estimated_tokens"] for r in all_case_records]
    ceiling_violations = sum(1 for t in tokens_used if t > DEFAULT_TOKEN_CEILING)
    zero_context_cases = sum(1 for r in all_case_records if not r["cond_g"]["context"].strip())
    structural_packed_cases = sum(1 for r in all_case_records if r["cond_g"]["use_structural"])

    telemetry_summary = {
        "ceiling_violations": ceiling_violations,
        "zero_context_cases": zero_context_cases,
        "structural_packed_cases": structural_packed_cases,
        "context_tokens": {
            "mean": round(sum(tokens_used) / len(tokens_used), 2),
            "median": sorted(tokens_used)[len(tokens_used) // 2],
            "min": min(tokens_used),
            "max": max(tokens_used),
        },
    }

    # Save candidate_g_metrics.json
    metrics_payload = {
        "experiment_id": EXPERIMENT_ID,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_cases": len(all_case_records),
        "condition_rates_n200": rates,
        "condition_rates_n199": rates_n199,
        "paired_comparisons_n200": paired_summary,
        "paired_comparisons_n199": {
            "g_vs_e": pair_g_vs_e_n199,
            "g_vs_f": pair_g_vs_f_n199,
            "g_vs_d": pair_g_vs_d_n199,
            "g_vs_a": pair_g_vs_a_n199,
        },
        "strata_summary": strata_summary,
        "telemetry_summary": telemetry_summary,
    }

    with open(OUTPUT_DIR / "candidate_g_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    # Save per_example_results.json
    with open(OUTPUT_DIR / "per_example_results.json", "w", encoding="utf-8") as f:
        json.dump(all_case_records, f, indent=2)

    print("\nSaved candidate_g_metrics.json and per_example_results.json.")


if __name__ == "__main__":
    main()
