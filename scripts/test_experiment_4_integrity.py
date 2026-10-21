#!/usr/bin/env python3
"""
Test Suite: Experiment 4 Harness and Integrity Tests (Gate 2.1).

Validates all mandatory pre-inference invariants for Experiment 4:
1. Exact manifest membership and 58-case union reconstruction (47 regressions + 11 recoveries).
2. Detection and rejection of duplicate, missing, and unexpected case IDs.
3. Frozen Condition A and B baseline prediction reuse, status validation, and provenance.
4. Condition C and D record schemas and paired comparison calculation.
5. Failed inference never receives valid EM/containment score (strictly None).
6. Unscorable empty inference never receives valid EM/containment score (strictly None).
7. Failed/unscorable inference cannot silently count as an incorrect answer or distort accuracy.
8. Aggregation reports cases attempted, success, failed, unscorable, and uses scored_denominator.
9. Paired comparisons exclude invalid pairs, track evaluated case IDs, excluded case IDs, and reasons.
10. All-failed condition returns explicit unavailable metrics (None) rather than misleading zeros.
11. Successful records preserve existing scoring behavior.
12. Schema validation rejects malformed or contradictory status/score combinations.
13. Configuration fingerprinting determinism and parameter sensitivity.
14. Output directory safety and artifact overwrite protection.
15. Edge cases in McNemar's exact test (zero discordant, symmetric, asymmetric, extreme, empty).
16. Structural retention context builders with separated logging across all 5 stages.
17. Token telemetry: distinct context_estimated_tokens, full_prompt_model_tokens, generated_tokens.
18. Explicit documentation of the Condition C vs B intervention bundle.
19. Zero-inference guarantee in dry-run mode.
"""

import copy
import json
import math
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/src and scripts are on import path
REPO_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from eval_experiment_4_v1 import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SEED,
    DEFAULT_TEMP,
    DEFAULT_TOKEN_CEILING,
    DEFAULT_TOP_P,
    EXPERIMENT_ID,
    MAX_TABLE_TOKENS,
    SMOKE_TEST_CASE_IDS,
    TABLE_SELECTION_THRESHOLD,
    ConditionResult,
    ContextPackingTelemetry,
    Experiment4CaseRecord,
    RowRetentionTelemetry,
    StructuralRetentionTelemetry,
    TableChunkTelemetry,
    TableConversionTelemetry,
    TableSelectionTelemetry,
    build_structural_retention_context,
    compute_condition_summary,
    compute_configuration_fingerprint,
    compute_mcnemar_exact,
    compute_paired_comparison_summary,
    compute_sha256,
    estimate_text_tokens,
    load_frozen_baseline_records,
    make_paired_case_diff,
    render_gfm_table,
    render_list_items,
    run_experiment_4,
    validate_case_record,
    validate_cohort_membership,
    validate_condition_result,
)
from precis.pipeline.inference import InferenceResult, OllamaConnectionError, OllamaInferenceError


@pytest.fixture
def repo_inputs():
    manifest_path = REPO_ROOT / "results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl"
    stage_c_path = REPO_ROOT / "results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl"
    dataset_path = REPO_ROOT / "backend/data/nq_subset/nq_dev.jsonl"
    return manifest_path, stage_c_path, dataset_path


# ==============================================================================
# 1. Manifest Membership and 58-Case Union Reconstruction
# ==============================================================================

def test_exact_manifest_membership_and_58_case_union(repo_inputs):
    manifest_path, stage_c_path, _ = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]

    all_table_cases = [
        m for m in manifest_records
        if m.get("type") == "sample_record" and m.get("stratum") == "table_bearing"
    ]
    assert len(all_table_cases) == 200, f"Expected 200 table_bearing cases, found {len(all_table_cases)}"

    stage_c_records = load_frozen_baseline_records(stage_c_path, {m["sample_id"] for m in all_table_cases})
    assert len(stage_c_records) == 200, f"Expected 200 Stage C records, found {len(stage_c_records)}"

    regressions, recoveries, union_cases = validate_cohort_membership(manifest_records, stage_c_records)

    assert len(regressions) == 47, f"Expected exactly 47 regressions, found {len(regressions)}"
    assert len(recoveries) == 11, f"Expected exactly 11 recoveries, found {len(recoveries)}"

    # Strict disjointness: intersection must be exactly 0
    intersection = set(regressions) & set(recoveries)
    assert len(intersection) == 0, f"Regressions and recoveries must be strictly disjoint, found {intersection}"

    # Union must be exactly 58 unique cases
    assert len(union_cases) == 58, f"Expected 58 cases in union, found {len(union_cases)}"
    assert set(union_cases) == (set(regressions) | set(recoveries))


# ==============================================================================
# 2. Case ID Validation: Handling Duplicates, Missing, and Unexpected IDs
# ==============================================================================

def test_case_id_validation_missing_and_unexpected(repo_inputs):
    manifest_path, stage_c_path, _ = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]

    all_table_cases = [
        m for m in manifest_records
        if m.get("type") == "sample_record" and m.get("stratum") == "table_bearing"
    ]
    stage_c_records = load_frozen_baseline_records(stage_c_path, {m["sample_id"] for m in all_table_cases})

    # Test 1: Missing record in Stage C raises KeyError
    corrupted_stage_c = dict(stage_c_records)
    first_cid = all_table_cases[0]["sample_id"]
    del corrupted_stage_c[first_cid]
    with pytest.raises(KeyError, match=f"Missing case ID in Stage C records: {first_cid}"):
        validate_cohort_membership(manifest_records, corrupted_stage_c)

    # Test 2: Incomplete confirmatory manifest raises ValueError
    incomplete_manifest = [m for m in manifest_records if m.get("sample_id") != first_cid]
    with pytest.raises(ValueError, match="Cohort validation failed: expected 200 table_bearing cases"):
        validate_cohort_membership(incomplete_manifest, stage_c_records)

    # Test 3: Load frozen baselines with unknown case ID raises KeyError
    with pytest.raises(KeyError, match="Failed to load frozen baselines"):
        load_frozen_baseline_records(stage_c_path, {"non_existent_case_id_12345"})


# ==============================================================================
# 3. Frozen A/B Baseline Reuse and Provenance
# ==============================================================================

def test_frozen_baseline_reuse_and_provenance(repo_inputs):
    manifest_path, stage_c_path, _ = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]

    stage_c_records = load_frozen_baseline_records(
        stage_c_path,
        {m["sample_id"] for m in manifest_records if m.get("stratum") == "table_bearing"},
    )
    regressions, recoveries, union_cases = validate_cohort_membership(manifest_records, stage_c_records)

    for cid in union_cases:
        rec = stage_c_records[cid]
        cond_a = rec["cond_a"]
        cond_b = rec["cond_b"]

        # Status must be successful
        assert cond_a.get("status") == "success", f"Case {cid} Condition A status not success"
        assert cond_b.get("status") == "success", f"Case {cid} Condition B status not success"

        # Predictions must be non-empty strings
        assert isinstance(cond_a.get("predicted_answer"), str)
        assert isinstance(cond_b.get("predicted_answer"), str)

        # Regressions check (Cond A = True, Cond B = False)
        if cid in regressions:
            assert cond_a["exact_match"] is True, f"Regression {cid} should have Cond A EM True"
            assert cond_b["exact_match"] is False, f"Regression {cid} should have Cond B EM False"

        # Recoveries check (Cond A = False, Cond B = True)
        if cid in recoveries:
            assert cond_a["exact_match"] is False, f"Recovery {cid} should have Cond A EM False"
            assert cond_b["exact_match"] is True, f"Recovery {cid} should have Cond B EM True"

        # Provenance check: config_fingerprint exists
        assert rec.get("config_fingerprint") is not None


def test_frozen_baseline_status_validation_no_silent_imputation():
    # If a frozen record has status != 'success', exact_match must be set to None
    synthetic_records = [
        Experiment4CaseRecord(
            case_id="case_syn_1",
            question="Q?",
            gold_answer="Gold",
            answers=["Gold"],
            stratum="table_bearing",
            priority_cohort="other",
            cond_a={
                "condition_id": "cond_a_reference",
                "predicted_answer": None,
                "raw_response": None,
                "exact_match": None,
                "containment": None,
                "rouge_l": None,
                "context_estimated_tokens": 100,
                "full_prompt_model_tokens": None,
                "generated_tokens": 0,
                "latency_ms": 0,
                "status": "failed",
                "error_message": "Frozen baseline failed",
                "provenance": {"source": "test"},
            },
            cond_b={
                "condition_id": "cond_b_baseline",
                "predicted_answer": "Valid B",
                "raw_response": "Valid B",
                "exact_match": True,
                "containment": True,
                "rouge_l": 1.0,
                "context_estimated_tokens": 50,
                "full_prompt_model_tokens": None,
                "generated_tokens": 0,
                "latency_ms": 0,
                "status": "success",
                "error_message": None,
                "provenance": {"source": "test"},
            },
        )
    ]
    summary_a = compute_condition_summary(synthetic_records, "cond_a")
    assert summary_a["success_count"] == 0
    assert summary_a["failed_count"] == 1
    assert summary_a["exact_match_count"] is None
    assert summary_a["exact_match_rate"] is None  # Never silently imputed as 0.0


# ==============================================================================
# 4. Condition C/D Record Schemas & Paired Comparisons
# ==============================================================================

def test_condition_cd_record_schemas_and_paired_comparisons():
    res_a = {
        "condition_id": "cond_a_reference",
        "predicted_answer": "Answer A",
        "raw_response": "Answer A",
        "exact_match": True,
        "containment": True,
        "rouge_l": 1.0,
        "context_estimated_tokens": 100,
        "full_prompt_model_tokens": None,
        "generated_tokens": 5,
        "latency_ms": 120,
        "status": "success",
        "error_message": None,
        "provenance": {"source": "stage_c"},
        "structural_retention_telemetry": None,
    }
    res_b = {
        "condition_id": "cond_b_baseline",
        "predicted_answer": "Wrong B",
        "raw_response": "Wrong B",
        "exact_match": False,
        "containment": False,
        "rouge_l": 0.0,
        "context_estimated_tokens": 50,
        "full_prompt_model_tokens": None,
        "generated_tokens": 4,
        "latency_ms": 110,
        "status": "success",
        "error_message": None,
        "provenance": {"source": "stage_c"},
        "structural_retention_telemetry": None,
    }
    res_c = {
        "condition_id": "cond_c_structural_retention_table_only",
        "predicted_answer": "Answer C",
        "raw_response": "Answer C",
        "exact_match": True,
        "containment": True,
        "rouge_l": 1.0,
        "context_estimated_tokens": 80,
        "full_prompt_model_tokens": 250,  # Full prompt token count from Ollama
        "generated_tokens": 6,
        "latency_ms": 130,
        "status": "success",
        "error_message": None,
        "provenance": {"model": "qwen2.5-coder:7b"},
        "structural_retention_telemetry": {"conversion": [], "selection": [], "row_retention": [], "chunking": [], "packing": {}},
    }
    res_d = copy.deepcopy(res_c)
    res_d["condition_id"] = "cond_d_structural_retention_with_lists"

    case_rec = Experiment4CaseRecord(
        case_id="test_case_001",
        question="What is the answer?",
        gold_answer="Answer A",
        answers=["Answer A"],
        stratum="table_bearing",
        priority_cohort="P1_regression",
        cond_a=res_a,
        cond_b=res_b,
        cond_c=res_c,
        cond_d=res_d,
        c_vs_a=make_paired_case_diff(res_c, res_a),
        c_vs_b=make_paired_case_diff(res_c, res_b),
        d_vs_a=make_paired_case_diff(res_d, res_a),
        d_vs_b=make_paired_case_diff(res_d, res_b),
        d_vs_c=make_paired_case_diff(res_d, res_c),
    )

    validate_case_record(case_rec)
    d = asdict(case_rec)
    assert d["case_id"] == "test_case_001"
    assert d["c_vs_b"]["status"] == "valid"
    assert d["c_vs_b"]["em_win"] is True  # C is correct (True), B is incorrect (False) -> Win
    assert d["c_vs_b"]["em_loss"] is False
    assert d["c_vs_a"]["em_win"] is False  # Both correct -> No win
    assert d["c_vs_a"]["token_delta"] == -20  # 80 - 100 = -20 tokens


# ==============================================================================
# 5. Failed & Unscorable Inference Scoring Semantics (Gate 2.1 Corrections)
# ==============================================================================

def test_failed_inference_never_receives_score_and_preserves_error(repo_inputs):
    manifest_path, stage_c_path, dataset_path = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset_docs = {json.loads(line)["doc_id"]: json.loads(line) for line in f if line.strip()}

    sample_cases = [m for m in manifest_records if m.get("type") == "sample_record" and m.get("stratum") == "table_bearing"]
    target_cids = [sample_cases[0]["sample_id"]]
    stage_c_records = load_frozen_baseline_records(stage_c_path, set(target_cids))

    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Simulate OllamaInferenceError
        with patch("eval_experiment_4_v1.check_ollama", return_value=True), \
             patch("eval_experiment_4_v1.generate_answer", side_effect=OllamaInferenceError("Operational connection timeout")):

            summary = run_experiment_4(
                target_case_ids=target_cids,
                manifest_records=manifest_records,
                dataset_docs=dataset_docs,
                frozen_stage_c=stage_c_records,
                output_dir=temp_dir,
                dry_run=False,
                force=True,
            )

            # Check written case record
            with open(temp_dir / "eval_records_experiment_4.jsonl", "r") as f:
                lines = [json.loads(l) for l in f if l.strip()]

            case_line = [l for l in lines if l.get("case_id") == target_cids[0]][0]
            cond_c = case_line["cond_c"]

            # Must be status='failed'
            assert cond_c["status"] == "failed"
            # Scores must be strictly None
            assert cond_c["exact_match"] is None
            assert cond_c["containment"] is None
            assert cond_c["rouge_l"] is None
            # Error message must be preserved
            assert "Operational connection timeout" in cond_c["error_message"]
            # Paired diff must be excluded, not marked as loss
            assert case_line["c_vs_a"]["status"] == "excluded"
            assert case_line["c_vs_a"]["em_win"] is None
            assert case_line["c_vs_a"]["em_loss"] is None

    finally:
        shutil.rmtree(temp_dir)


def test_unscorable_inference_never_receives_score_and_preserves_raw_response(repo_inputs):
    manifest_path, stage_c_path, dataset_path = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset_docs = {json.loads(line)["doc_id"]: json.loads(line) for line in f if line.strip()}

    sample_cases = [m for m in manifest_records if m.get("type") == "sample_record" and m.get("stratum") == "table_bearing"]
    target_cids = [sample_cases[0]["sample_id"]]
    stage_c_records = load_frozen_baseline_records(stage_c_path, set(target_cids))

    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Simulate empty response from Ollama
        mock_empty_res = InferenceResult(
            answer="   \n  ",
            model="qwen2.5-coder:7b",
            latency_ms=150,
            tokens_generated=2,
            prompt_tokens=300,
        )
        with patch("eval_experiment_4_v1.check_ollama", return_value=True), \
             patch("eval_experiment_4_v1.generate_answer", return_value=mock_empty_res):

            summary = run_experiment_4(
                target_case_ids=target_cids,
                manifest_records=manifest_records,
                dataset_docs=dataset_docs,
                frozen_stage_c=stage_c_records,
                output_dir=temp_dir,
                dry_run=False,
                force=True,
            )

            with open(temp_dir / "eval_records_experiment_4.jsonl", "r") as f:
                lines = [json.loads(l) for l in f if l.strip()]

            case_line = [l for l in lines if l.get("case_id") == target_cids[0]][0]
            cond_c = case_line["cond_c"]

            # Must be status='unscorable'
            assert cond_c["status"] == "unscorable"
            # Scores must be strictly None
            assert cond_c["exact_match"] is None
            assert cond_c["containment"] is None
            assert cond_c["rouge_l"] is None
            # Raw response preserved
            assert cond_c["raw_response"] == "   \n  "
            # Token counts preserved
            assert cond_c["full_prompt_model_tokens"] == 300
            assert cond_c["generated_tokens"] == 2

    finally:
        shutil.rmtree(temp_dir)


def test_failed_inference_cannot_silently_count_as_incorrect_answer():
    # If 5 cases run: 2 correct, 1 incorrect, 2 failed
    # Scored denominator is 3 (not 5). EM rate is 2/3 = 66.7%, NOT 2/5 = 40.0%
    records = []
    for i in range(5):
        if i < 2:
            cond_c = {"condition_id": "c", "status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100, "full_prompt_model_tokens": 200, "generated_tokens": 5, "latency_ms": 100}
        elif i == 2:
            cond_c = {"condition_id": "c", "status": "success", "exact_match": False, "containment": False, "rouge_l": 0.0, "context_estimated_tokens": 100, "full_prompt_model_tokens": 200, "generated_tokens": 5, "latency_ms": 100}
        elif i == 3:
            cond_c = {"condition_id": "c", "status": "failed", "exact_match": None, "containment": None, "rouge_l": None, "context_estimated_tokens": 100, "full_prompt_model_tokens": None, "generated_tokens": 0, "latency_ms": 0}
        else:
            cond_c = {"condition_id": "c", "status": "unscorable", "exact_match": None, "containment": None, "rouge_l": None, "context_estimated_tokens": 100, "full_prompt_model_tokens": 180, "generated_tokens": 0, "latency_ms": 80}

        records.append(Experiment4CaseRecord(
            case_id=f"cid_{i}",
            question="Q?",
            gold_answer="A",
            answers=["A"],
            stratum="table_bearing",
            priority_cohort="P1_regression",
            cond_a={"condition_id": "a", "status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100},
            cond_b={"condition_id": "b", "status": "success", "exact_match": False, "containment": False, "rouge_l": 0.0, "context_estimated_tokens": 100},
            cond_c=cond_c,
            cond_d=copy.deepcopy(cond_c),
        ))

    summary = compute_condition_summary(records, "cond_c")
    assert summary["attempted_count"] == 5
    assert summary["success_count"] == 3
    assert summary["failed_count"] == 1
    assert summary["unscorable_count"] == 1
    assert summary["scored_denominator"] == 3
    assert summary["exact_match_count"] == 2
    assert math.isclose(summary["exact_match_rate"], 2.0 / 3.0, rel_tol=1e-6)
    assert not math.isclose(summary["exact_match_rate"], 2.0 / 5.0, rel_tol=1e-6)


# ==============================================================================
# 6. Aggregation Reporting & Paired Exclusions
# ==============================================================================

def test_aggregation_reports_failures_and_uses_correct_denominator():
    records = [
        Experiment4CaseRecord(
            case_id="case_f1",
            question="Q1",
            gold_answer="A",
            answers=["A"],
            stratum="table_bearing",
            priority_cohort="other",
            cond_a={"condition_id": "a", "status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100},
            cond_b={"condition_id": "b", "status": "success", "exact_match": False, "containment": False, "rouge_l": 0.0, "context_estimated_tokens": 100},
            cond_c={"condition_id": "c", "status": "failed", "exact_match": None, "containment": None, "rouge_l": None, "context_estimated_tokens": 100},
        ),
        Experiment4CaseRecord(
            case_id="case_u1",
            question="Q2",
            gold_answer="A",
            answers=["A"],
            stratum="table_bearing",
            priority_cohort="other",
            cond_a={"condition_id": "a", "status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100},
            cond_b={"condition_id": "b", "status": "success", "exact_match": False, "containment": False, "rouge_l": 0.0, "context_estimated_tokens": 100},
            cond_c={"condition_id": "c", "status": "unscorable", "exact_match": None, "containment": None, "rouge_l": None, "context_estimated_tokens": 100},
        ),
        Experiment4CaseRecord(
            case_id="case_s1",
            question="Q3",
            gold_answer="A",
            answers=["A"],
            stratum="table_bearing",
            priority_cohort="other",
            cond_a={"condition_id": "a", "status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100},
            cond_b={"condition_id": "b", "status": "success", "exact_match": False, "containment": False, "rouge_l": 0.0, "context_estimated_tokens": 100},
            cond_c={"condition_id": "c", "status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100, "full_prompt_model_tokens": 200, "generated_tokens": 5},
        ),
    ]

    summary = compute_condition_summary(records, "cond_c")
    assert summary["attempted_count"] == 3
    assert summary["success_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["unscorable_count"] == 1
    assert summary["scored_denominator"] == 1
    assert summary["exact_match_count"] == 1
    assert summary["exact_match_rate"] == 1.0
    assert summary["unsuccessful_case_ids"]["failed"] == ["case_f1"]
    assert summary["unsuccessful_case_ids"]["unscorable"] == ["case_u1"]


def test_paired_tests_exclude_invalid_pairs_and_report_ids_and_reasons():
    # 4 records:
    # case 1: A success, C success
    # case 2: A success, C success
    # case 3: A success, C failed -> Excluded
    # case 4: A success, C unscorable -> Excluded
    records = [
        Experiment4CaseRecord(
            case_id="c1", question="Q", gold_answer="A", answers=["A"], stratum="t", priority_cohort="p",
            cond_a={"status": "success", "exact_match": True},
            cond_b={"status": "success", "exact_match": False},
            cond_c={"status": "success", "exact_match": True},
        ),
        Experiment4CaseRecord(
            case_id="c2", question="Q", gold_answer="A", answers=["A"], stratum="t", priority_cohort="p",
            cond_a={"status": "success", "exact_match": True},
            cond_b={"status": "success", "exact_match": False},
            cond_c={"status": "success", "exact_match": False},
        ),
        Experiment4CaseRecord(
            case_id="c3", question="Q", gold_answer="A", answers=["A"], stratum="t", priority_cohort="p",
            cond_a={"status": "success", "exact_match": True},
            cond_b={"status": "success", "exact_match": False},
            cond_c={"status": "failed", "exact_match": None, "error_message": "LLM timeout"},
        ),
        Experiment4CaseRecord(
            case_id="c4", question="Q", gold_answer="A", answers=["A"], stratum="t", priority_cohort="p",
            cond_a={"status": "success", "exact_match": True},
            cond_b={"status": "success", "exact_match": False},
            cond_c={"status": "unscorable", "exact_match": None, "error_message": "Empty response"},
        ),
    ]

    paired_summary = compute_paired_comparison_summary(records, "cond_c", "cond_a", metric="exact_match")
    assert paired_summary["status"] == "computed"
    assert paired_summary["attempted_pair_count"] == 4
    assert paired_summary["valid_paired_denominator"] == 2
    assert paired_summary["evaluated_case_ids"] == ["c1", "c2"]
    assert paired_summary["excluded_count"] == 2
    assert paired_summary["excluded_case_ids"] == ["c3", "c4"]
    assert len(paired_summary["exclusion_details"]) == 2
    assert "LLM timeout" in paired_summary["exclusion_details"][0]["reason"]
    assert "Empty response" in paired_summary["exclusion_details"][1]["reason"]
    # McNemar evaluated on 2 valid pairs:
    assert paired_summary["mcnemar_exact"]["total_n"] == 2


def test_all_failed_condition_returns_unavailable_metrics_not_zeros():
    # If a condition fails 100% of cases, it must return unavailable (None), not 0.0%
    records = [
        Experiment4CaseRecord(
            case_id=f"c_{i}", question="Q", gold_answer="A", answers=["A"], stratum="t", priority_cohort="p",
            cond_a={"status": "success", "exact_match": True, "containment": True, "rouge_l": 1.0, "context_estimated_tokens": 100},
            cond_b={"status": "success", "exact_match": False, "containment": False, "rouge_l": 0.0, "context_estimated_tokens": 100},
            cond_c={"status": "failed", "exact_match": None, "containment": None, "rouge_l": None, "context_estimated_tokens": 100, "error_message": "Crash"},
        )
        for i in range(5)
    ]

    summary_c = compute_condition_summary(records, "cond_c")
    assert summary_c["status"] == "unavailable"
    assert summary_c["attempted_count"] == 5
    assert summary_c["success_count"] == 0
    assert summary_c["failed_count"] == 5
    assert summary_c["scored_denominator"] == 0
    assert summary_c["exact_match_count"] is None
    assert summary_c["exact_match_rate"] is None  # NOT 0.0
    assert summary_c["containment_rate"] is None  # NOT 0.0
    assert summary_c["mean_rouge_l"] is None

    # Paired comparison with Condition A
    paired = compute_paired_comparison_summary(records, "cond_c", "cond_a", metric="exact_match")
    assert paired["status"] == "unavailable"
    assert paired["valid_paired_denominator"] == 0
    assert paired["excluded_count"] == 5
    assert paired["mcnemar_exact"] is None  # Not calculated over imputed zeros


def test_successful_records_preserve_existing_scoring_behavior():
    # Verify standard check_exact_match and check_containment functionality
    from eval_table_selection_v2 import check_exact_match, check_containment
    assert check_exact_match("August 18, 1998", "August 18 , 1998") is True
    assert check_exact_match("August 19, 1998", "August 18 , 1998") is False
    assert check_containment("The album was released August 18, 1998", "August 18 , 1998") is True
    assert check_containment("The album was released in 1999", "August 18 , 1998") is False


# ==============================================================================
# 7. Contradictory State & Malformed Combination Rejection
# ==============================================================================

def test_validation_rejects_malformed_contradictory_status_score_combinations():
    # 1. status='failed' with exact_match=False must raise ValueError
    with pytest.raises(ValueError, match="Contradictory state: status='failed' cannot have scored metrics"):
        validate_condition_result({
            "status": "failed",
            "exact_match": False,
            "containment": None,
            "rouge_l": None,
        })

    # 2. status='failed' with exact_match=True must raise ValueError
    with pytest.raises(ValueError, match="Contradictory state: status='failed' cannot have scored metrics"):
        validate_condition_result({
            "status": "failed",
            "exact_match": True,
            "containment": None,
            "rouge_l": None,
        })

    # 3. status='unscorable' with containment=False must raise ValueError
    with pytest.raises(ValueError, match="Contradictory state: status='unscorable' cannot have scored metrics"):
        validate_condition_result({
            "status": "unscorable",
            "exact_match": None,
            "containment": False,
            "rouge_l": None,
        })

    # 4. status='dry_run' with scored exact_match must raise ValueError
    with pytest.raises(ValueError, match="Contradictory state: status='dry_run' cannot have scored metrics"):
        validate_condition_result({
            "status": "dry_run",
            "exact_match": True,
            "containment": None,
            "rouge_l": None,
        })

    # 5. status='success' with exact_match=None must raise ValueError
    with pytest.raises(ValueError, match="Contradictory state: status='success' must have scored metrics"):
        validate_condition_result({
            "status": "success",
            "predicted_answer": "answer",
            "exact_match": None,
            "containment": True,
            "rouge_l": 1.0,
        })

    # 6. status='success' with non-boolean exact_match must raise ValueError
    with pytest.raises(ValueError, match="Type error: status='success' requires boolean exact_match"):
        validate_condition_result({
            "status": "success",
            "predicted_answer": "answer",
            "exact_match": "not_a_bool",
            "containment": True,
            "rouge_l": 1.0,
        })

    # 7. Invalid status literal must raise ValueError
    with pytest.raises(ValueError, match="Invalid condition status 'unknown_status'"):
        validate_condition_result({
            "status": "unknown_status",
            "exact_match": None,
        })


# ==============================================================================
# 8. Token Telemetry Clarification
# ==============================================================================

def test_token_telemetry_clarification_heuristic_vs_full_prompt():
    text = "This is a five word sentence."
    est = estimate_text_tokens(text)
    # words = 6 -> int(6 * 1.3) = 7
    assert est == int(len(text.split()) * 1.3)

    # ConditionResult enforces context_estimated_tokens (heuristic) and full_prompt_model_tokens (full prompt model count)
    res = ConditionResult(
        condition_id="cond_c",
        predicted_answer="Test",
        raw_response="Test",
        exact_match=True,
        containment=True,
        rouge_l=1.0,
        context_estimated_tokens=est,
        full_prompt_model_tokens=350,  # Full prompt token count including template, context, question
        generated_tokens=10,
    )
    validate_condition_result(asdict(res))
    assert res.context_estimated_tokens == est
    assert res.full_prompt_model_tokens == 350
    assert res.generated_tokens == 10
    # Must NOT have misleading 'context_model_tokens' in dataclass fields
    assert not hasattr(res, "context_model_tokens")


# ==============================================================================
# 9. Configuration Fingerprinting
# ==============================================================================

def test_configuration_fingerprinting_determinism_and_sensitivity():
    fp1 = compute_configuration_fingerprint(
        model="qwen2.5-coder:7b",
        temperature=0.0,
        top_p=0.9,
        seed=42,
        input_hashes={"manifest": "abc"},
    )
    fp2 = compute_configuration_fingerprint(
        model="qwen2.5-coder:7b",
        temperature=0.0,
        top_p=0.9,
        seed=42,
        input_hashes={"manifest": "abc"},
    )
    assert fp1 == fp2, "Fingerprint must be strictly deterministic"

    assert compute_configuration_fingerprint(temperature=0.7) != fp1
    assert compute_configuration_fingerprint(seed=123) != fp1
    assert compute_configuration_fingerprint(model="llama3:8b") != fp1
    assert compute_configuration_fingerprint(token_ceiling=1024) != fp1
    assert compute_configuration_fingerprint(input_hashes={"manifest": "def"}) != fp1


# ==============================================================================
# 10. Directory Safety and Overwrite Protection
# ==============================================================================

def test_directory_safety_and_overwrite_protection(repo_inputs):
    manifest_path, stage_c_path, dataset_path = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset_docs = {json.loads(line)["doc_id"]: json.loads(line) for line in f if line.strip()}

    sample_cases = [m for m in manifest_records if m.get("type") == "sample_record" and m.get("stratum") == "table_bearing"]
    target_cid = sample_cases[0]["sample_id"]
    stage_c_records = load_frozen_baseline_records(stage_c_path, {target_cid})

    temp_dir = Path(tempfile.mkdtemp())
    try:
        dummy_file = temp_dir / "eval_records_experiment_4.jsonl"
        dummy_file.write_text("existing content")

        with pytest.raises(FileExistsError, match="Artifact overwrite protection"):
            run_experiment_4(
                target_case_ids=[target_cid],
                manifest_records=manifest_records,
                dataset_docs=dataset_docs,
                frozen_stage_c=stage_c_records,
                output_dir=temp_dir,
                dry_run=True,
                force=False,
            )

        run_experiment_4(
            target_case_ids=[target_cid],
            manifest_records=manifest_records,
            dataset_docs=dataset_docs,
            frozen_stage_c=stage_c_records,
            output_dir=temp_dir,
            dry_run=True,
            force=True,
        )
        assert dummy_file.exists()
        assert dummy_file.read_text() != "existing content"

    finally:
        shutil.rmtree(temp_dir)


# ==============================================================================
# 11. McNemar's Exact Test Edge Cases
# ==============================================================================

def test_mcnemar_exact_edge_cases():
    # Zero discordant pairs (b=0, c=0)
    res_zero = compute_mcnemar_exact([True, True, False, False], [True, True, False, False])
    assert res_zero["discordant_pairs"] == 0
    assert res_zero["p_value"] == 1.0
    assert res_zero["odds_ratio"] == 1.0
    assert res_zero["risk_difference"] == 0.0

    # Symmetric discordant pairs (b=5, c=5)
    y1_sym = [True] * 5 + [False] * 5 + [True] * 5
    y2_sym = [False] * 5 + [True] * 5 + [True] * 5
    res_sym = compute_mcnemar_exact(y1_sym, y2_sym)
    assert res_sym["cond1_wins"] == 5
    assert res_sym["cond2_wins"] == 5
    assert res_sym["p_value"] == 1.0
    assert res_sym["risk_difference"] == 0.0
    assert res_sym["odds_ratio"] == 1.0

    # Extreme one-sided discordance (b=10, c=0)
    y1_ext = [True] * 10
    y2_ext = [False] * 10
    res_ext = compute_mcnemar_exact(y1_ext, y2_ext)
    assert res_ext["cond1_wins"] == 10
    assert res_ext["cond2_wins"] == 0
    assert math.isclose(res_ext["p_value"], 2.0 / 1024.0, rel_tol=1e-6)
    assert res_ext["odds_ratio"] == float("inf")
    assert res_ext["risk_difference"] == 1.0

    # Asymmetric split (b=8, c=2, n_disc=10)
    y1_asym = [True] * 8 + [False] * 2
    y2_asym = [False] * 8 + [True] * 2
    res_asym = compute_mcnemar_exact(y1_asym, y2_asym)
    assert res_asym["cond1_wins"] == 8
    assert res_asym["cond2_wins"] == 2
    assert math.isclose(res_asym["p_value"], 112.0 / 1024.0, rel_tol=1e-6)
    assert res_asym["odds_ratio"] == 4.0
    assert math.isclose(res_asym["risk_difference"], 0.6, rel_tol=1e-6)

    # Empty sample returns unavailable
    res_empty = compute_mcnemar_exact([], [])
    assert res_empty["status"] == "unavailable"
    assert res_empty["total_n"] == 0
    assert res_empty["p_value"] is None

    # Mismatched length raises ValueError
    with pytest.raises(ValueError, match="Mismatched sample lengths"):
        compute_mcnemar_exact([True, False], [True])


# ==============================================================================
# 12. Structural Retention Context Builders: Separated Logging
# ==============================================================================

def test_structural_retention_context_builders_separated_logging():
    sample_doc = """
    <html>
    <body>
    <p>General introduction to the document.</p>
    <table>
      <caption>Tournament Summary</caption>
      <tr><th>Year</th><th>Winner</th><th>Runner Up</th></tr>
      <tr><td>2018</td><td>France</td><td>Croatia</td></tr>
      <tr><td>2014</td><td>Germany</td><td>Argentina</td></tr>
      <tr><td>2010</td><td>Spain</td><td>Netherlands</td></tr>
    </table>
    <p>Narrative conclusion following the tournament.</p>
    <ul>
      <li>Top scorer: Harry Kane</li>
      <li>Best player: Luka Modric</li>
    </ul>
    </body>
    </html>
    """

    query = "who won the tournament in 2018"
    ctx, telem = build_structural_retention_context(
        raw_doc=sample_doc,
        query=query,
        table_threshold=0.0,
        include_lists=True,
        max_table_tokens=500,
        token_ceiling=2048,
    )

    # Stage 1: Conversion
    assert len(telem.conversion) == 1
    conv = telem.conversion[0]
    assert conv["source_block_id"] == 0
    assert conv["conversion_status"] == "SUCCESS"
    assert conv["original_row_count"] == 3
    assert conv["rendered_row_count"] == 3
    assert conv["row_preservation_rate"] == 1.0
    assert "Winner" in conv["rendered_headers"]

    # Stage 2: Selection
    assert len(telem.selection) == 1
    sel = telem.selection[0]
    assert sel["block_id"] == 0
    assert sel["decision"].startswith("SELECTED")

    # Stage 3: Row Retention (100% row preservation)
    assert len(telem.row_retention) == 1
    ret = telem.row_retention[0]
    assert ret["block_id"] == 0
    assert ret["original_rows"] == 3
    assert ret["retained_rows"] == 3
    assert ret["row_retention_rate"] == 1.0
    assert ret["policy"] == "retain_all_rows_gfm_chunking"

    # Stage 4: Chunking
    assert len(telem.chunking) >= 1
    chk = telem.chunking[0]
    assert chk["chunk_idx"] == 0
    assert chk["start_row"] == 0
    assert chk["end_row"] == 2
    assert chk["row_count"] == 3
    assert chk["estimated_tokens"] > 0

    # Stage 5: Packed Context Assembly
    pack = telem.packing
    assert pack["clean_prose_estimated_tokens"] > 0
    assert pack["table_chunks_packed_count"] >= 1
    assert pack["list_items_packed_count"] == 2
    assert pack["total_context_estimated_tokens"] > 0
    assert pack["ceiling_violation"] is False
    assert pack["zero_context"] is False

    assert "France" in ctx
    assert "Harry Kane" in ctx


# ==============================================================================
# 13. Intervention Bundle Documentation Verification
# ==============================================================================

def test_intervention_bundle_documentation():
    import eval_experiment_4_v1
    docstring = eval_experiment_4_v1.__doc__
    assert docstring is not None
    assert "INTERVENTION BUNDLE" in docstring
    assert "Condition C differs from Condition B in BOTH" in docstring
    assert "row retention" in docstring.lower()
    assert "full_prompt_model_tokens" in docstring
    assert "context_estimated_tokens" in docstring


# ==============================================================================
# 14. Zero-Inference Dry-Run Execution
# ==============================================================================

def test_zero_inference_dry_run_execution(repo_inputs):
    manifest_path, stage_c_path, dataset_path = repo_inputs

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = [json.loads(line) for line in f if line.strip()]
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset_docs = {json.loads(line)["doc_id"]: json.loads(line) for line in f if line.strip()}

    sample_cases = [m for m in manifest_records if m.get("type") == "sample_record" and m.get("stratum") == "table_bearing"]
    target_cids = [m["sample_id"] for m in sample_cases[:2]]
    stage_c_records = load_frozen_baseline_records(stage_c_path, set(target_cids))

    temp_dir = Path(tempfile.mkdtemp())
    try:
        summary = run_experiment_4(
            target_case_ids=target_cids,
            manifest_records=manifest_records,
            dataset_docs=dataset_docs,
            frozen_stage_c=stage_c_records,
            output_dir=temp_dir,
            dry_run=True,
            force=True,
        )

        assert summary["metadata"]["dry_run"] is True
        assert summary["metadata"]["total_cases"] == 2

        # Check records on disk
        rec_file = temp_dir / "eval_records_experiment_4.jsonl"
        assert rec_file.exists()
        with open(rec_file, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]

        assert lines[0]["type"] == "run_header"
        assert lines[0]["dry_run"] is True
        assert len(lines) == 3

        for case_line in lines[1:]:
            assert case_line["cond_c"]["status"] == "dry_run"
            assert case_line["cond_d"]["status"] == "dry_run"
            # Scores must be None in dry-run
            assert case_line["cond_c"]["exact_match"] is None
            assert case_line["cond_d"]["exact_match"] is None
            assert "structural_retention_telemetry" in case_line["cond_c"]

        # Summary check: dry-run reports exact_match_rate as None (not 0.0)
        assert summary["condition_summaries"]["cond_c"]["status"] == "dry_run"
        assert summary["condition_summaries"]["cond_c"]["exact_match_rate"] is None

    finally:
        shutil.rmtree(temp_dir)


def test_smoke_test_cohort_and_manifest_membership(repo_inputs):
    """
    Validate the Gate 3 smoke-test cohort:
    1. SMOKE_TEST_CASE_IDS has exactly 5 cases.
    2. All 5 cases exist in sample_manifest.jsonl and belong to table_bearing stratum.
    3. All 5 cases exist in eval_records_stage_c.jsonl with valid status='success'.
    4. Exact membership matches the Gate 3 approved scope.
    """
    manifest_path, stage_c_path, _ = repo_inputs

    assert len(SMOKE_TEST_CASE_IDS) == 5, f"Expected 5 smoke test cases, found {len(SMOKE_TEST_CASE_IDS)}"

    expected_ids = [
        "2c62d7eb04924071959544f85e978b8b",
        "a16cca39f27e4d78a64de2d8285bc4bf",
        "3f0497f4a228459c8b2201e7f871a520",
        "16caa32e50d342878340cacefe5a417a",
        "00d7c7cc7b534abeaf1f9dded1d3639b",
    ]
    assert SMOKE_TEST_CASE_IDS == expected_ids, f"Mismatch in smoke test case IDs: {SMOKE_TEST_CASE_IDS}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_records = {
            m["sample_id"]: m for m in [json.loads(line) for line in f if line.strip()]
            if m.get("type") == "sample_record"
        }

    for sid in SMOKE_TEST_CASE_IDS:
        assert sid in manifest_records, f"Smoke test case {sid} missing from manifest"
        assert manifest_records[sid].get("stratum") == "table_bearing", f"Smoke test case {sid} must be table_bearing"

    stage_c_records = load_frozen_baseline_records(stage_c_path, set(SMOKE_TEST_CASE_IDS))
    assert len(stage_c_records) == 5, f"Expected 5 Stage C records, found {len(stage_c_records)}"
    for sid in SMOKE_TEST_CASE_IDS:
        rec = stage_c_records[sid]
        assert rec["cond_a"]["status"] == "success", f"Case {sid} Cond A status != success"
        assert rec["cond_b"]["status"] == "success", f"Case {sid} Cond B status != success"

