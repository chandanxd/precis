"""
Précis Experiment 4.3 Gate 2 Runner: Isolated List-Extraction Evaluation.

Targeted diagnostic evaluation of the isolated list extractor on the 31 verified
extraction-omission cases from Gate 1.

Conditions:
- Condition A (Reference): Frozen Experiment 4.2 Condition D (theta=0.0, tables only).
- Condition B (Candidate): Condition D (theta=0.0) + Candidate List Extractor.

Stages:
- Stage 2A: Deterministic evidence recovery, context verification, token accounting.
- Stage 2B: Targeted live generation pilot on qwen2.5-coder:7b (if Stage 2A passes).

Enforces:
- Zero edits to backend/src/precis/
- Exact 2,048 token context ceiling
- Strict failure accounting and non-imputation
- Full provenance and paired comparison reporting
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

import scipy.stats
from diagnostic_list_extractor import (
    extract_lists_from_html,
    is_nav_or_boilerplate_list,
    render_list_to_markdown,
)
from eval_experiment_4_2_threshold import (
    build_table_retention_context,
    estimate_text_tokens,
    generate_answer,
    compute_mcnemar_exact,
)
from eval_table_selection_v2 import (
    check_containment,
    check_exact_match,
    check_rouge_l,
    contains_answer,
)

EXPERIMENT_ID = "diagnostic_experiment_4_3_gate2"
DEFAULT_TOKEN_CEILING = 2048
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_TEMP = 0.0
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 512
DEFAULT_SEED = 42

OUTPUT_DIR = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "gate_2_list_extraction_20261010"


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_gate2_inputs() -> Dict[str, Any]:
    expected = {
        "sample_manifest.jsonl": ("results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl", "011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7"),
        "eval_records_stage_c.jsonl": ("results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl", "e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687"),
        "nq_dev.jsonl": ("backend/data/nq_subset/nq_dev.jsonl", "14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491"),
        "eval_records.jsonl": ("results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl", "d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0"),
        "eval_experiment_4_2_threshold.py": ("scripts/eval_experiment_4_2_threshold.py", "2ebabbcfb247721935366f69999fd798c9fcd6105cbf44e5967435a582fac606"),
    }
    verifications = {}
    for name, (rel_path, exp_hash) in expected.items():
        p = REPO_ROOT / rel_path
        if not p.exists():
            raise FileNotFoundError(f"Missing required input file: {p}")
        actual_hash = compute_file_sha256(p)
        if actual_hash != exp_hash:
            raise ValueError(f"Hash mismatch on {name}: expected {exp_hash}, got {actual_hash}")
        verifications[name] = {"path": str(p), "sha256": actual_hash, "match": True}
    return verifications


def load_31_target_cases() -> List[Dict[str, Any]]:
    inv_path = REPO_ROOT / "results" / "diagnostic_experiment_4_v1" / "failure_attribution_20261010" / "failure_inventory.jsonl"
    if not inv_path.exists():
        raise FileNotFoundError(f"Missing Gate 1 failure inventory: {inv_path}")

    cases = []
    with open(inv_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            # Auditable criteria from Gate 1
            cat = rec.get("failure_classification", {}).get("revised_gate_1_category", "")
            if cat.startswith("EXTRACTION_OMISSION_LIST"):
                cases.append(rec)

    if len(cases) != 31:
        raise ValueError(f"Expected exactly 31 target cases from Gate 1 inventory, found {len(cases)}")
    return cases


def build_candidate_condition_b_context(
    raw_doc: str,
    query: str,
    token_ceiling: int = DEFAULT_TOKEN_CEILING,
) -> Tuple[str, Dict[str, Any]]:
    """
    Construct packed prompt context combining Condition D tables (theta=0.0)
    plus extracted content lists from diagnostic_list_extractor.
    """
    # 1. Base table context from Condition D
    ctx_base, telem_base = build_table_retention_context(
        raw_doc=raw_doc,
        query=query,
        table_threshold=0.0,
        max_table_tokens=500,
        token_ceiling=token_ceiling,
    )

    # 2. Extract lists
    blocks = extract_lists_from_html(raw_doc)
    content_blocks = [b for b in blocks if not is_nav_or_boilerplate_list(b)]

    packed_parts: List[str] = []
    if ctx_base.strip():
        packed_parts.append(ctx_base.strip())

    cur_tokens = estimate_text_tokens(ctx_base) if ctx_base.strip() else 0
    lists_packed = 0
    list_items_packed = 0
    list_tokens_packed = 0

    for b in content_blocks:
        md_list = render_list_to_markdown(b)
        list_chunk = f"### Structured List:\n{md_list}"
        tok_est = estimate_text_tokens(list_chunk)

        if cur_tokens + tok_est <= token_ceiling:
            packed_parts.append(list_chunk)
            cur_tokens += tok_est
            lists_packed += 1
            list_items_packed += len(b.items)
            list_tokens_packed += tok_est
        else:
            # Partial packing if remaining budget allows
            remaining = token_ceiling - cur_tokens
            if remaining > 50:
                truncated_lines = []
                sub_tok = 0
                for line in md_list.split("\n"):
                    l_tok = estimate_text_tokens(line)
                    if sub_tok + l_tok <= remaining:
                        truncated_lines.append(line)
                        sub_tok += l_tok
                    else:
                        break
                if truncated_lines:
                    packed_parts.append("### Structured List (Budget Truncated):\n" + "\n".join(truncated_lines))
                    cur_tokens += sub_tok
                    lists_packed += 1
                    list_items_packed += len(truncated_lines)
                    list_tokens_packed += sub_tok
            break

    full_context = "\n\n".join(packed_parts)
    telemetry = {
        "base_table_telemetry": telem_base,
        "content_list_blocks_found": len(content_blocks),
        "list_blocks_packed": lists_packed,
        "list_items_packed": list_items_packed,
        "list_tokens_estimated": list_tokens_packed,
        "total_context_estimated_tokens": cur_tokens,
        "ceiling_violation": cur_tokens > token_ceiling,
        "zero_context": len(full_context.strip()) == 0,
    }
    return full_context, telemetry


def run_stage_2a(
    target_cases: List[Dict[str, Any]],
    nq_docs: Dict[str, Dict[str, Any]],
    output_dir: Path,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Stage 2A: Deterministic evidence recovery and context verification.
    Returns (all_passed, records).
    """
    print("\n" + "=" * 80)
    print("STAGE 2A: DETERMINISTIC EVIDENCE RECOVERY & CONTEXT VERIFICATION")
    print("=" * 80)

    stage_2a_records = []
    all_passed = True
    retained_count = 0
    max_tokens = 0
    ceiling_violations = 0

    for idx, c in enumerate(target_cases, 1):
        cid = c["case_id"]
        q = c["question"]
        answers = c["answers"]
        gold = c["gold_answer"]
        doc = nq_docs.get(cid, {})
        html_doc = doc.get("document", "")

        # Build Candidate Condition B context
        ctx_b, telem_b = build_candidate_condition_b_context(html_doc, q, token_ceiling=DEFAULT_TOKEN_CEILING)

        # Measure evidence
        in_extracted_lists = any(contains_answer(html_doc, a) for a in answers)  # verified in Gate 1
        blocks = extract_lists_from_html(html_doc)
        content_blocks = [b for b in blocks if not is_nav_or_boilerplate_list(b)]
        list_text_all = "\n\n".join(render_list_to_markdown(b) for b in content_blocks)
        gold_in_content_lists = any(contains_answer(list_text_all, a) for a in answers)
        gold_in_packed_context = any(contains_answer(ctx_b, a) for a in answers)

        tok_est = telem_b["total_context_estimated_tokens"]
        if tok_est > max_tokens:
            max_tokens = tok_est
        if telem_b["ceiling_violation"]:
            ceiling_violations += 1
            all_passed = False

        if gold_in_packed_context:
            retained_count += 1
        else:
            all_passed = False

        record = {
            "case_id": cid,
            "question": q,
            "gold_answer": gold,
            "answers": answers,
            "gate_1_category": c["failure_classification"]["revised_gate_1_category"],
            "stage_2a_metrics": {
                "gold_in_content_lists": gold_in_content_lists,
                "gold_in_packed_context": gold_in_packed_context,
                "content_list_blocks_count": telem_b["content_list_blocks_found"],
                "list_blocks_packed": telem_b["list_blocks_packed"],
                "list_items_packed": telem_b["list_items_packed"],
                "list_tokens_estimated": telem_b["list_tokens_estimated"],
                "base_table_tokens_estimated": telem_b["base_table_telemetry"]["total_context_estimated_tokens"],
                "total_context_tokens_estimated": tok_est,
                "ceiling_violation": telem_b["ceiling_violation"],
                "zero_context": telem_b["zero_context"],
            },
            "structural_provenance": {
                "excerpt": c["structural_location"]["exact_source_excerpt"],
                "source_tag": c["structural_location"]["source_tag"],
            },
            "status": "PASS" if gold_in_packed_context and not telem_b["ceiling_violation"] else "FAIL",
        }
        stage_2a_records.append(record)
        print(f"[{idx:02d}/31] {cid[:8]} | ListToks: {telem_b['list_tokens_estimated']:4d} | TotalToks: {tok_est:4d} | InContext: {gold_in_packed_context} | Status: {record['status']}")

    out_file = output_dir / "stage_2a_evidence_recovery.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in stage_2a_records:
            f.write(json.dumps(r) + "\n")

    print("\n" + "-" * 80)
    print(f"Stage 2A Verification Summary:")
    print(f"  Target Cases: {len(target_cases)}")
    print(f"  Evidence Retained in Packed Context: {retained_count} / {len(target_cases)} ({retained_count / len(target_cases) * 100:.1f}%)")
    print(f"  Max Context Tokens: {max_tokens} (Ceiling: {DEFAULT_TOKEN_CEILING})")
    print(f"  Ceiling Violations: {ceiling_violations}")
    print(f"  Stage 2A Gate Result: {'PASSED (Eligible for Stage 2B)' if all_passed else 'FAILED'}")
    print(f"  Saved to: {out_file}")
    print("-" * 80)

    return all_passed, stage_2a_records


def run_stage_2b(
    target_cases: List[Dict[str, Any]],
    stage_2a_records: List[Dict[str, Any]],
    nq_docs: Dict[str, Dict[str, Any]],
    output_dir: Path,
    dry_run: bool = False,
    base_url: str = "http://localhost:11434",
) -> Dict[str, Any]:
    """
    Stage 2B: Targeted live generation pilot.
    Evaluates Condition B vs Condition A (Reference).
    """
    print("\n" + "=" * 80)
    print("STAGE 2B: TARGETED GENERATION PILOT (Condition B vs Condition A)")
    print("=" * 80)

    stage_2b_records = []
    regressions = []
    wins = []
    losses = []
    ties = []

    a_em_count = 0
    b_em_count = 0
    a_cont_count = 0
    b_cont_count = 0

    start_time = time.time()

    for idx, c in enumerate(target_cases, 1):
        cid = c["case_id"]
        q = c["question"]
        answers = c["answers"]
        gold = c["gold_answer"]
        doc = nq_docs.get(cid, {})
        html_doc = doc.get("document", "")

        # Condition A (Reference): From Experiment 4.2 Condition D
        pred_a = c["predictions"]["cond_d"]
        em_a = c["exact_matches"]["cond_d"]
        cont_a = c["containments"]["cond_d"]
        if em_a: a_em_count += 1
        if cont_a: a_cont_count += 1

        # Condition B Context
        ctx_b, telem_b = build_candidate_condition_b_context(html_doc, q, token_ceiling=DEFAULT_TOKEN_CEILING)

        # Condition B Inference
        if dry_run:
            pred_b = "[DRY_RUN_PLACEHOLDER]"
            raw_b = ""
            status_b = "dry_run"
            err_b = None
            prompt_tokens_b = None
            gen_tokens_b = 0
            lat_b = 0
            em_b = None
            cont_b = None
            rouge_b = None
        else:
            try:
                res = generate_answer(
                    query=q,
                    context=ctx_b,
                    model=DEFAULT_MODEL,
                    temperature=DEFAULT_TEMP,
                    top_p=DEFAULT_TOP_P,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    prompt_style="concise",
                    base_url=base_url,
                )
                raw_b = res.answer if res.answer is not None else ""
                pred_b = raw_b.strip()
                prompt_tokens_b = res.prompt_tokens
                gen_tokens_b = res.tokens_generated
                lat_b = res.latency_ms

                if not pred_b:
                    status_b = "unscorable"
                    err_b = "Empty model completion"
                    em_b = None
                    cont_b = None
                    rouge_b = None
                else:
                    status_b = "success"
                    err_b = None
                    em_b = check_exact_match(pred_b, gold, answers)
                    cont_b = check_containment(pred_b, gold, answers)
                    rouge_b = check_rouge_l(pred_b, gold, answers)
                    if em_b: b_em_count += 1
                    if cont_b: b_cont_count += 1

            except Exception as exc:
                pred_b = None
                raw_b = None
                status_b = "failed"
                err_b = str(exc)
                prompt_tokens_b = None
                gen_tokens_b = 0
                lat_b = 0
                em_b = None
                cont_b = None
                rouge_b = None

        # Paired comparisons
        em_win = bool(em_b and not em_a)
        em_loss = bool(not em_b and em_a)
        cont_win = bool(cont_b and not cont_a)
        cont_loss = bool(not cont_b and cont_a)

        if em_win:
            wins.append(cid)
        elif em_loss:
            losses.append(cid)
            regressions.append({
                "case_id": cid,
                "question": q,
                "gold": gold,
                "pred_a": pred_a,
                "pred_b": pred_b,
                "type": "EXACT_MATCH_REGRESSION",
            })
        else:
            ties.append(cid)

        record = {
            "case_id": cid,
            "question": q,
            "gold_answer": gold,
            "answers": answers,
            "condition_a_reference": {
                "condition_id": "cond_d_exp42_reference",
                "predicted_answer": pred_a,
                "exact_match": em_a,
                "containment": cont_a,
                "context_estimated_tokens": c["cond_c"]["context_estimated_tokens"] if "cond_c" in c else 0, # telem
            },
            "condition_b_candidate": {
                "condition_id": "cond_b_list_extraction_candidate",
                "predicted_answer": pred_b,
                "raw_response": raw_b,
                "exact_match": em_b,
                "containment": cont_b,
                "rouge_l": rouge_b,
                "status": status_b,
                "error_message": err_b,
                "context_estimated_tokens": telem_b["total_context_estimated_tokens"],
                "full_prompt_model_tokens": prompt_tokens_b,
                "generated_tokens": gen_tokens_b,
                "latency_ms": lat_b,
                "telemetry": telem_b,
            },
            "paired_transition": {
                "em_win": em_win,
                "em_loss": em_loss,
                "containment_win": cont_win,
                "containment_loss": cont_loss,
            },
        }
        stage_2b_records.append(record)

        sym = "WIN" if em_win else "REGRESS" if em_loss else "TIE"
        print(f"[{idx:02d}/31] {cid[:8]} | [{sym}] Pred B: '{str(pred_b)[:35]}' | Gold: '{gold[:25]}' | EM_B: {em_b}")

    total_time = time.time() - start_time

    # Output files
    eval_file = output_dir / "stage_2b_eval_records.jsonl"
    with open(eval_file, "w", encoding="utf-8") as f:
        for r in stage_2b_records:
            f.write(json.dumps(r) + "\n")

    reg_file = output_dir / "regression_audit.jsonl"
    with open(reg_file, "w", encoding="utf-8") as f:
        for r in regressions:
            f.write(json.dumps(r) + "\n")

    # Paired McNemar Test
    y_b = [r["condition_b_candidate"]["exact_match"] for r in stage_2b_records if r["condition_b_candidate"]["status"] == "success"]
    y_a = [r["condition_a_reference"]["exact_match"] for r in stage_2b_records if r["condition_b_candidate"]["status"] == "success"]
    mcnemar_res = compute_mcnemar_exact(y_b, y_a) if y_b else {"p_value": None, "odds_ratio": None, "significant": False}

    summary = {
        "cohort_size": len(target_cases),
        "execution_time_seconds": round(total_time, 2),
        "dry_run": dry_run,
        "condition_a_reference": {
            "exact_match_count": a_em_count,
            "exact_match_rate": round(a_em_count / len(target_cases), 4),
            "containment_count": a_cont_count,
            "containment_rate": round(a_cont_count / len(target_cases), 4),
        },
        "condition_b_candidate": {
            "exact_match_count": b_em_count,
            "exact_match_rate": round(b_em_count / len(target_cases), 4),
            "containment_count": b_cont_count,
            "containment_rate": round(b_cont_count / len(target_cases), 4),
        },
        "paired_comparison": {
            "cond_b_wins": len(wins),
            "cond_b_losses": len(losses),
            "ties": len(ties),
            "net_wins": len(wins) - len(losses),
            "percentage_point_diff": round((b_em_count - a_em_count) / len(target_cases) * 100, 2),
            "mcnemar_exact_p_value": mcnemar_res.get("mcnemar_p_value", mcnemar_res.get("p_value")),
            "odds_ratio": mcnemar_res.get("odds_ratio"),
            "statistically_significant_05": mcnemar_res.get("significant_05", False),
            "small_sample_limitation": "Pilot cohort (N=31) selected on baseline failure; results are diagnostic and not an unbiased confirmatory estimate.",
        },
        "regressions": {
            "regression_count": len(regressions),
            "regression_case_ids": [r["case_id"] for r in regressions],
        },
    }

    sum_file = output_dir / "paired_comparison_summary.json"
    with open(sum_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("STAGE 2B PILOT SUMMARY:")
    print(f"  Condition A Exact Match: {a_em_count} / {len(target_cases)} ({a_em_count / len(target_cases) * 100:.1f}%)")
    print(f"  Condition B Exact Match: {b_em_count} / {len(target_cases)} ({b_em_count / len(target_cases) * 100:.1f}%)")
    print(f"  Condition A Containment: {a_cont_count} / {len(target_cases)} ({a_cont_count / len(target_cases) * 100:.1f}%)")
    print(f"  Condition B Containment: {b_cont_count} / {len(target_cases)} ({b_cont_count / len(target_cases) * 100:.1f}%)")
    print(f"  Net Wins: +{len(wins) - len(losses)} (Wins: {len(wins)}, Losses: {len(losses)}, Ties: {len(ties)})")
    print(f"  McNemar p-value: {mcnemar_res['p_value']}")
    print(f"  Regressions: {len(regressions)}")
    print("=" * 80)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Précis Experiment 4.3 Gate 2 Runner")
    parser.add_argument("--dry-run", action="store_true", help="Perform Stage 2A only, or skip live model dispatch in Stage 2B")
    parser.add_argument("--stage2a-only", action="store_true", help="Run Stage 2A deterministic verification and stop")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama API base URL")
    args = parser.parse_args()

    print("================================================================================")
    print("PRÉCIS EXPERIMENT 4.3: GATE 2 ISOLATED LIST-EXTRACTION EVALUATION")
    print("================================================================================")

    # 1. Preflight
    print("\n[Step 1] Verifying Preflight Inputs & SHA-256 Hashes...")
    verifications = verify_gate2_inputs()
    print("All input hashes verified successfully.")

    # 2. Load 31 target cases
    print("\n[Step 2] Loading 31 Target Cases from Gate 1 Inventory...")
    target_cases = load_31_target_cases()
    print(f"Successfully loaded {len(target_cases)} cases.")

    # Load NQ dataset
    print("\n[Step 3] Loading NQ Source Documents...")
    nq_path = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"
    with open(nq_path, "r", encoding="utf-8") as f:
        nq_docs = {json.loads(line)["doc_id"]: json.loads(line) for line in f}
    print(f"Loaded {len(nq_docs)} raw documents.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Stage 2A
    stage2a_passed, stage2a_records = run_stage_2a(target_cases, nq_docs, OUTPUT_DIR)
    if not stage2a_passed:
        print("\nERROR: Stage 2A failed deterministic verification. Stopping before Stage 2B.")
        sys.exit(1)

    if args.stage2a_only:
        print("\nStage 2A completed successfully. Halting as requested by --stage2a-only.")
        sys.exit(0)

    # 4. Stage 2B
    summary = run_stage_2b(
        target_cases=target_cases,
        stage_2a_records=stage2a_records,
        nq_docs=nq_docs,
        output_dir=OUTPUT_DIR,
        dry_run=args.dry_run,
        base_url=args.base_url,
    )
    print("\nGate 2 Execution Finished Successfully.")


if __name__ == "__main__":
    main()
