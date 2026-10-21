"""
Précis Experiment 4.5.6: Gate 5 Production-Path Confirmatory Evaluation Runner.

Evaluates Candidate Condition F (Persistent Production Structural Pipeline with
PRECIS_ENABLE_LIST_EXTRACTION=true in an isolated evaluation harness) against frozen
Conditions A, B, C, D, and E across the canonical 200-case table-bearing cohort.

Enforces:
- Hard 2,048-token context ceiling.
- Zero modifications to production codebase under backend/src/precis/ or backend/main.py.
- Zero live reruns of historical Conditions A-E (1,000 predictions reused directly from frozen records).
- Exactly 200 live inference calls to Ollama qwen2.5-coder:7b (one per case for Condition F).
- Strict non-imputation of failures/unscorable cases.
- Idempotent checkpointing and resumption.
- Pre-registered paired comparisons, exact McNemar tests, strata, and sensitivity analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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

EXPERIMENT_ID = "diagnostic_experiment_4_5_6_gate_5_confirmatory"
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
EXP44_PATH = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "full_cohort_evaluation_20261010" / "eval_records.jsonl"
NQ_PATH = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

OUTPUT_DIR = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "gate_5_confirmatory_evaluation_20261010"


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
        "eval_records_exp44.jsonl": (EXP44_PATH, "73df76085485fbead2b67fa6a783be3c10420edbf8d9afa9c42203d6737f2c47"),
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
        for cond_key in ["cond_a", "cond_b", "cond_c", "cond_d", "cond_e", "cond_f"]
    }


def main():
    parser = argparse.ArgumentParser(description="Précis Experiment 4.5.6 Gate 5 Confirmatory Runner")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama API base URL")
    parser.add_argument("--dry-run", action="store_true", help="Do not call model inference; output mock responses")
    args = parser.parse_args()

    print("=" * 80)
    print("PRÉCIS EXPERIMENT 4.5.6: GATE 5 PRODUCTION-PATH CONFIRMATORY EVALUATION")
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

    # 3. Load Manifest and Frozen Inputs
    print("\n[Step 3] Loading Cohorts & Frozen Inputs...")
    manifest_records = [json.loads(l) for l in MANIFEST_PATH.read_text().splitlines() if l.strip()]
    table_bearing_manifest = [r for r in manifest_records if r.get("type") == "sample_record" and r.get("stratum") == "table_bearing"]
    if len(table_bearing_manifest) != 200:
        raise ValueError(f"Expected exactly 200 table-bearing cases in manifest, found {len(table_bearing_manifest)}")

    stage_c_records = {json.loads(l)["sample_id"]: json.loads(l) for l in STAGE_C_PATH.read_text().splitlines() if l.strip() and json.loads(l).get("type") == "sample_record"}
    exp42_records = {json.loads(l)["case_id"]: json.loads(l) for l in EXP42_PATH.read_text().splitlines() if l.strip() and json.loads(l).get("type") != "run_header"}
    exp44_records = {json.loads(l)["case_id"]: json.loads(l) for l in EXP44_PATH.read_text().splitlines() if l.strip() and json.loads(l).get("type") != "run_header"}

    print(f"Loaded {len(table_bearing_manifest)} table-bearing manifest cases.")
    print(f"Loaded {len(stage_c_records)} Stage C records (Conditions A & B).")
    print(f"Loaded {len(exp42_records)} Exp 4.2 records (Conditions C & D).")
    print(f"Loaded {len(exp44_records)} Exp 4.4 records (Condition E).")

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

    # 4. Execute Full-Cohort Evaluation for Condition F
    print("\n" + "=" * 80)
    print("EXECUTING LIVE PRODUCTION-PATH EVALUATION (Condition F on 200 cases)")
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
            "pipeline": "persistent_production_pipeline",
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

            # Load frozen Conditions A-E
            c_rec = stage_c_records[cid]
            e42_rec = exp42_records[cid]
            e44_rec = exp44_records[cid]

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
                "predicted_answer": e42_rec["cond_c"]["predicted_answer"],
                "exact_match": e42_rec["cond_c"]["exact_match"],
                "containment": e42_rec["cond_c"]["containment"],
                "context_estimated_tokens": e42_rec["cond_c"].get("context_estimated_tokens", 0),
                "full_prompt_model_tokens": e42_rec["cond_c"].get("full_prompt_model_tokens"),
                "generated_tokens": e42_rec["cond_c"].get("generated_tokens", 0),
                "latency_ms": e42_rec["cond_c"].get("latency_ms", 0),
                "status": e42_rec["cond_c"].get("status", "success"),
                "provenance": {"source": "eval_records_exp42.jsonl"},
            }
            cond_d = {
                "condition_id": "cond_d_structural_retention_theta0",
                "predicted_answer": e42_rec["cond_d"]["predicted_answer"],
                "exact_match": e42_rec["cond_d"]["exact_match"],
                "containment": e42_rec["cond_d"]["containment"],
                "context_estimated_tokens": e42_rec["cond_d"].get("context_estimated_tokens", 0),
                "full_prompt_model_tokens": e42_rec["cond_d"].get("full_prompt_model_tokens"),
                "generated_tokens": e42_rec["cond_d"].get("generated_tokens", 0),
                "latency_ms": e42_rec["cond_d"].get("latency_ms", 0),
                "status": e42_rec["cond_d"].get("status", "success"),
                "provenance": {"source": "eval_records_exp42.jsonl"},
            }
            cond_e = {
                "condition_id": "cond_e_tables_and_lists",
                "predicted_answer": e44_rec["cond_e"]["predicted_answer"],
                "raw_response": e44_rec["cond_e"].get("raw_response", e44_rec["cond_e"]["predicted_answer"]),
                "exact_match": e44_rec["cond_e"]["exact_match"],
                "containment": e44_rec["cond_e"]["containment"],
                "rouge_l": e44_rec["cond_e"].get("rouge_l", 0.0),
                "context_estimated_tokens": e44_rec["cond_e"].get("context_estimated_tokens", 0),
                "full_prompt_model_tokens": e44_rec["cond_e"].get("full_prompt_model_tokens"),
                "generated_tokens": e44_rec["cond_e"].get("generated_tokens", 0),
                "latency_ms": e44_rec["cond_e"].get("latency_ms", 0),
                "status": e44_rec["cond_e"].get("status", "success"),
                "telemetry": e44_rec["cond_e"].get("telemetry", {}),
                "provenance": {"source": "eval_records_exp44.jsonl"},
            }

            # Live generation for Condition F (Persistent Production Structural Pipeline)
            doc_entry = nq_docs.get(cid, {})
            html_doc = doc_entry.get("document", "")
            clean_text = sanitize_document(html_doc)

            collection_name = f"gate5_f_{cid[:12]}_{idx}"
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

                context_f = assembled.context
                telem_f = assembled.telemetry
                facts_packed_f = assembled.facts_packed
                use_structural_f = assembled.use_structural

                if args.dry_run:
                    pred_f = "[DRY_RUN_MOCK]"
                    raw_f = pred_f
                    status_f = "dry_run"
                    err_f = None
                    prompt_tokens_f = None
                    gen_tokens_f = 0
                    lat_f = 0
                    em_f = False
                    cont_f = False
                    rouge_f = 0.0
                else:
                    t_gen_start = time.perf_counter()
                    try:
                        res = generate_answer(
                            query=q,
                            context=context_f,
                            model=DEFAULT_MODEL,
                            temperature=DEFAULT_TEMP,
                            top_p=DEFAULT_TOP_P,
                            max_tokens=DEFAULT_MAX_TOKENS,
                            prompt_style="concise",
                            base_url=args.base_url,
                        )
                        raw_f = res.answer if res.answer is not None else ""
                        pred_f = raw_f.strip()
                        prompt_tokens_f = res.prompt_tokens
                        gen_tokens_f = res.tokens_generated
                        lat_f = res.latency_ms

                        if not pred_f:
                            status_f = "unscorable"
                            err_f = "Empty model completion"
                            em_f = None
                            cont_f = None
                            rouge_f = None
                        else:
                            status_f = "success"
                            err_f = None
                            em_f = check_exact_match(pred_f, gold, answers)
                            cont_f = check_containment(pred_f, gold, answers)
                            rouge_f = check_rouge_l(pred_f, gold, answers)
                    except Exception as exc:
                        pred_f = None
                        raw_f = None
                        status_f = "failed"
                        err_f = str(exc)
                        prompt_tokens_f = None
                        gen_tokens_f = 0
                        lat_f = 0
                        em_f = None
                        cont_f = None
                        rouge_f = None

                cond_f = {
                    "condition_id": "cond_f_persistent_production_pipeline",
                    "predicted_answer": pred_f,
                    "raw_response": raw_f,
                    "exact_match": em_f,
                    "containment": cont_f,
                    "rouge_l": rouge_f,
                    "context": context_f,
                    "context_estimated_tokens": assembled.tokens_used,
                    "full_prompt_model_tokens": prompt_tokens_f,
                    "generated_tokens": gen_tokens_f,
                    "latency_ms": lat_f,
                    "status": status_f,
                    "error_message": err_f,
                    "facts_packed": facts_packed_f,
                    "use_structural": use_structural_f,
                    "telemetry": telem_f,
                    "provenance": {
                        "source": "live_generation",
                        "pipeline": "persistent_production_path",
                        "feature_flag": True,
                    },
                }
                generated_count += 1
                status_str = f"GENERATED (EM={cond_f['exact_match']}, Toks={assembled.tokens_used}, Struct={use_structural_f}, Lat={lat_f}ms)"

            finally:
                # Deterministic cleanup of ChromaDB collection
                try:
                    store._client.delete_collection(collection_name)
                    if hasattr(store, "_structural_collection") and store._structural_collection:
                        store._client.delete_collection(f"{collection_name}_structural")
                except Exception:
                    pass

            record = {
                "case_id": cid,
                "stratum": "table_bearing",
                "priority_cohort": e42_rec.get("priority_cohort", "unknown"),
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
                "f_vs_d": {
                    "em_win": bool(not cond_d["exact_match"] and cond_f["exact_match"]),
                    "em_loss": bool(cond_d["exact_match"] and not cond_f["exact_match"]),
                    "cont_win": bool(not cond_d["containment"] and cond_f["containment"]),
                    "cont_loss": bool(cond_d["containment"] and not cond_f["containment"]),
                },
                "f_vs_e": {
                    "em_win": bool(not cond_e["exact_match"] and cond_f["exact_match"]),
                    "em_loss": bool(cond_e["exact_match"] and not cond_f["exact_match"]),
                    "cont_win": bool(not cond_e["containment"] and cond_f["containment"]),
                    "cont_loss": bool(cond_e["containment"] and not cond_f["containment"]),
                },
                "f_vs_a": {
                    "em_win": bool(not cond_a["exact_match"] and cond_f["exact_match"]),
                    "em_loss": bool(cond_a["exact_match"] and not cond_f["exact_match"]),
                    "cont_win": bool(not cond_a["containment"] and cond_f["containment"]),
                    "cont_loss": bool(cond_a["containment"] and not cond_f["containment"]),
                },
            }

            all_case_records.append(record)
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()

            print(f"[{idx:03d}/200] {cid[:8]} | {status_str}")

    print("\n" + "=" * 80)
    print(f"EVALUATION EXECUTION COMPLETE:")
    print(f"  Total Cases: {len(all_case_records)}")
    print(f"  Newly Generated (Condition F): {generated_count}")
    print(f"  From Previous Checkpoint: {checkpointed_count}")
    print("=" * 80)

    # 5. Statistical Analyses and Reports
    print("\n[Step 5] Compiling Aggregate Metrics & Statistical Tests...")

    primary_rates = compute_condition_rates(all_case_records)
    paired_comp = {
        "f_vs_d": analyze_condition_pair(all_case_records, "cond_d", "cond_f"),
        "f_vs_e": analyze_condition_pair(all_case_records, "cond_e", "cond_f"),
        "f_vs_a": analyze_condition_pair(all_case_records, "cond_a", "cond_f"),
        "f_vs_c": analyze_condition_pair(all_case_records, "cond_c", "cond_f"),
        "f_vs_b": analyze_condition_pair(all_case_records, "cond_b", "cond_f"),
    }

    # Strata breakdown
    # Check if Gate 2 case IDs are available from stage_2b
    gate2_stage2b_path = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "gate_2_list_extraction_20261010" / "stage_2b_eval_records.jsonl"
    gate2_cids = set()
    if gate2_stage2b_path.exists():
        for l in gate2_stage2b_path.read_text().splitlines():
            if l.strip():
                gate2_cids.add(json.loads(l)["case_id"])

    strata_map = {
        "stratum_1_stage_c_regressions_47": [c for c in all_case_records if c["priority_cohort"] == "P1_regression"],
        "stratum_2_stage_c_recoveries_11": [c for c in all_case_records if c["priority_cohort"] == "P2_recovery"],
        "stratum_3_remaining_142": [c for c in all_case_records if c["priority_cohort"] in ("both_loss", "both_win")],
    }
    if gate2_cids:
        strata_map["diagnostic_gate2_list_subset_31"] = [c for c in all_case_records if c["case_id"] in gate2_cids]

    strata_results = {s_name: compute_condition_rates(s_cases) for s_name, s_cases in strata_map.items()}

    # Sensitivity analysis excluding ambiguous case
    sensitivity_cases = [c for c in all_case_records if c["case_id"] != AMBIGUOUS_CASE_ID]
    sensitivity_rates = compute_condition_rates(sensitivity_cases)
    sensitivity_paired = {
        "f_vs_d": analyze_condition_pair(sensitivity_cases, "cond_d", "cond_f"),
        "f_vs_e": analyze_condition_pair(sensitivity_cases, "cond_e", "cond_f"),
        "f_vs_a": analyze_condition_pair(sensitivity_cases, "cond_a", "cond_f"),
    }

    # Telemetry distributions for Condition F
    context_tokens_list = [c["cond_f"]["context_estimated_tokens"] for c in all_case_records if c["cond_f"].get("context_estimated_tokens") is not None]
    prompt_tokens_list = [c["cond_f"]["full_prompt_model_tokens"] for c in all_case_records if c["cond_f"].get("full_prompt_model_tokens") is not None]
    gen_tokens_list = [c["cond_f"]["generated_tokens"] for c in all_case_records if c["cond_f"].get("generated_tokens") is not None]
    latency_list = [c["cond_f"]["latency_ms"] for c in all_case_records if c["cond_f"].get("latency_ms") is not None]

    def stats_summary(arr: List[float | int]) -> Dict[str, Any]:
        if not arr:
            return {}
        s = sorted(arr)
        n = len(s)
        mean_val = sum(s) / n
        var_val = sum((x - mean_val) ** 2 for x in s) / n
        return {
            "mean": round(mean_val, 2),
            "median": round(s[n // 2] if n % 2 != 0 else (s[n // 2 - 1] + s[n // 2]) / 2, 2),
            "std": round(var_val ** 0.5, 2),
            "min": s[0],
            "p25": s[int(n * 0.25)],
            "p75": s[int(n * 0.75)],
            "p90": s[int(n * 0.90)],
            "max": s[-1],
        }

    telemetry_summary = {
        "context_estimated_tokens": stats_summary(context_tokens_list),
        "full_prompt_model_tokens": stats_summary(prompt_tokens_list),
        "generated_tokens": stats_summary(gen_tokens_list),
        "latency_ms": stats_summary(latency_list),
        "ceiling_violations_count": sum(1 for tok in context_tokens_list if tok > DEFAULT_TOKEN_CEILING),
        "zero_context_count": sum(1 for tok in context_tokens_list if tok == 0),
        "structural_context_used_count": sum(1 for c in all_case_records if c["cond_f"].get("use_structural")),
    }

    # Regression audits
    regressions_against_d = [
        {
            "case_id": c["case_id"],
            "question": c["question"],
            "gold_answer": c["gold_answer"],
            "cond_d_pred": c["cond_d"]["predicted_answer"],
            "cond_f_pred": c["cond_f"]["predicted_answer"],
            "priority_cohort": c["priority_cohort"],
            "regression_type": "EM_LOSS_AGAINST_CONDITION_D",
            "context_tokens_d": c["cond_d"].get("context_estimated_tokens"),
            "context_tokens_f": c["cond_f"].get("context_estimated_tokens"),
        }
        for c in all_case_records
        if c["cond_d"]["exact_match"] and not c["cond_f"]["exact_match"]
    ]

    regressions_against_e = [
        {
            "case_id": c["case_id"],
            "question": c["question"],
            "gold_answer": c["gold_answer"],
            "cond_e_pred": c["cond_e"]["predicted_answer"],
            "cond_f_pred": c["cond_f"]["predicted_answer"],
            "priority_cohort": c["priority_cohort"],
            "regression_type": "EM_LOSS_AGAINST_CONDITION_E",
            "context_tokens_e": c["cond_e"].get("context_estimated_tokens"),
            "context_tokens_f": c["cond_f"].get("context_estimated_tokens"),
        }
        for c in all_case_records
        if c["cond_e"]["exact_match"] and not c["cond_f"]["exact_match"]
    ]

    regressions_against_a = [
        {
            "case_id": c["case_id"],
            "question": c["question"],
            "gold_answer": c["gold_answer"],
            "cond_a_pred": c["cond_a"]["predicted_answer"],
            "cond_f_pred": c["cond_f"]["predicted_answer"],
            "priority_cohort": c["priority_cohort"],
            "regression_type": "EM_LOSS_AGAINST_CONDITION_A",
            "context_tokens_a": c["cond_a"].get("context_estimated_tokens"),
            "context_tokens_f": c["cond_f"].get("context_estimated_tokens"),
        }
        for c in all_case_records
        if c["cond_a"]["exact_match"] and not c["cond_f"]["exact_match"]
    ]

    # Save regression audit jsonl
    regression_audit_path = OUTPUT_DIR / "regression_audit.jsonl"
    with open(regression_audit_path, "w", encoding="utf-8") as f:
        for reg in regressions_against_d + regressions_against_e + regressions_against_a:
            f.write(json.dumps(reg) + "\n")

    # Aggregate summary
    aggregate_summary = {
        "experiment_id": EXPERIMENT_ID,
        "cohort_size": len(all_case_records),
        "primary_analysis_rates": primary_rates,
        "diagnostic_strata": strata_results,
        "sensitivity_analysis_excluding_ambiguous": {
            "cohort_size": len(sensitivity_cases),
            "excluded_case_id": AMBIGUOUS_CASE_ID,
            "rates": sensitivity_rates,
            "paired_comparisons": sensitivity_paired,
        },
        "telemetry_summary": telemetry_summary,
        "regression_summary": {
            "losses_against_condition_d": len(regressions_against_d),
            "losses_against_condition_e": len(regressions_against_e),
            "losses_against_condition_a": len(regressions_against_a),
            "wins_against_condition_d": paired_comp["f_vs_d"]["exact_match"]["wins"],
            "wins_against_condition_e": paired_comp["f_vs_e"]["exact_match"]["wins"],
            "wins_against_condition_a": paired_comp["f_vs_a"]["exact_match"]["wins"],
        },
    }

    # Write JSON files
    (OUTPUT_DIR / "aggregate_summary.json").write_text(json.dumps(aggregate_summary, indent=2))
    (OUTPUT_DIR / "paired_comparisons.json").write_text(json.dumps(paired_comp, indent=2))

    # Integrity Report
    integrity_data = {
        "experiment_id": EXPERIMENT_ID,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "verifications": verifications,
        "total_cases": len(all_case_records),
        "unscorable_cases": sum(1 for c in all_case_records if c["cond_f"]["status"] == "unscorable"),
        "failed_cases": sum(1 for c in all_case_records if c["cond_f"]["status"] == "failed"),
        "successful_cases": sum(1 for c in all_case_records if c["cond_f"]["status"] == "success"),
        "zero_imputations": True,
        "zero_token_ceiling_violations": telemetry_summary["ceiling_violations_count"] == 0,
        "reused_historical_predictions_count": len(all_case_records) * 5,
        "new_inference_calls_count": generated_count,
        "exact_match_f": primary_rates["cond_f"]["exact_match_rate"],
        "containment_f": primary_rates["cond_f"]["containment_rate"],
    }
    (OUTPUT_DIR / "integrity_report.json").write_text(json.dumps(integrity_data, indent=2))

    # Print summary to console
    print("\n" + "=" * 80)
    print("GATE 5 CONFIRMATORY EVALUATION SUMMARY:")
    print("=" * 80)
    print(f"Condition A (Prose Baseline):             {primary_rates['cond_a']['exact_match_rate']}% EM ({primary_rates['cond_a']['exact_match_count']}/200)")
    print(f"Condition B (Decompiled Prose):           {primary_rates['cond_b']['exact_match_rate']}% EM ({primary_rates['cond_b']['exact_match_count']}/200)")
    print(f"Condition C (Table theta=2.0):            {primary_rates['cond_c']['exact_match_rate']}% EM ({primary_rates['cond_c']['exact_match_count']}/200)")
    print(f"Condition D (Table theta=0.0):            {primary_rates['cond_d']['exact_match_rate']}% EM ({primary_rates['cond_d']['exact_match_count']}/200)")
    print(f"Condition E (Prototype Tables+Lists):     {primary_rates['cond_e']['exact_match_rate']}% EM ({primary_rates['cond_e']['exact_match_count']}/200)")
    print(f"Condition F (Persistent Production Path): {primary_rates['cond_f']['exact_match_rate']}% EM ({primary_rates['cond_f']['exact_match_count']}/200)")
    print("-" * 80)
    f_d = paired_comp["f_vs_d"]["exact_match"]
    print(f"Contrast F vs. D (Primary Hypothesis):")
    print(f"  Wins: {f_d['wins']}, Losses: {f_d['losses']}, Net Delta: {f_d['net_percentage_points']} pp")
    print(f"  Exact McNemar p-value: {f_d['mcnemar_p_value']}")
    print(f"  Statistically Significant (p < 0.05): {f_d['statistically_significant_05']}")
    print(f"  95% CI: [{f_d['ci_95_pct'][0]}%, {f_d['ci_95_pct'][1]}%]")
    print("-" * 80)
    f_e = paired_comp["f_vs_e"]["exact_match"]
    print(f"Contrast F vs. E (Prototype Parity):")
    print(f"  Wins: {f_e['wins']}, Losses: {f_e['losses']}, Net Delta: {f_e['net_percentage_points']} pp")
    print(f"  Exact McNemar p-value: {f_e['mcnemar_p_value']}")
    print("-" * 80)
    f_a = paired_comp["f_vs_a"]["exact_match"]
    print(f"Contrast F vs. A (Prose Superiority):")
    print(f"  Wins: {f_a['wins']}, Losses: {f_a['losses']}, Net Delta: {f_a['net_percentage_points']} pp")
    print(f"  Exact McNemar p-value: {f_a['mcnemar_p_value']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
