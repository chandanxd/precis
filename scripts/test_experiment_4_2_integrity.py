#!/usr/bin/env python3
"""
Integrity Test Suite for Précis Experiment 4.2: Full-Cohort Table-Selection Threshold Evaluation.

Validates all 10 mandatory pre-inference and analytical invariants:
1. Exact 200-case cohort membership, uniqueness, and stratum consistency.
2. Threshold as the sole manipulated variable (Condition C theta=2.0 vs Condition D theta=0.0).
3. Configuration fingerprint determinism and parameter sensitivity.
4. Correct success / failed / unscorable handling and zero-imputation guardrails.
5. Paired comparison accounting (valid pairs vs excluded pairs, transparent reasons).
6. Null metric handling (all-failed condition returns None rather than misleading 0.0%).
7. JSON serialization and read-back round-trip validation.
8. Context ceiling validation (all packed contexts strictly respect 2,048 tokens).
9. Protection against overwriting existing artifacts without explicit force.
10. Bit-for-bit preservation of all frozen source hashes (manifest, Stage C, nq_dev).
"""

import copy
import json
import math
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/src and scripts are on import path
REPO_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from eval_experiment_4_2_threshold import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SEED,
    DEFAULT_TEMP,
    DEFAULT_TOKEN_CEILING,
    DEFAULT_TOP_P,
    EXPERIMENT_ID,
    EXPECTED_DATASET_HASH,
    EXPECTED_MANIFEST_HASH,
    EXPECTED_STAGE_C_HASH,
    MAX_TABLE_TOKENS,
    build_table_retention_context,
    compute_config_fingerprint,
    compute_condition_summary,
    compute_file_sha256,
    compute_mcnemar_exact,
    compute_paired_comparison_summary,
    load_and_verify_frozen_cohort,
    make_paired_case_diff,
    render_gfm_table_chunks,
    run_experiment_4_2,
)
from eval_structural_decompilation_v3 import StructuralDocumentParser, StructuredBlock


class TestExperiment42CohortIntegrity:
    """Test Suite 1: Frozen Cohort Membership, Hashes, and Uniqueness."""

    def test_frozen_source_hashes(self):
        """Invariant 10: Frozen source digests must match canonical pre-registered hashes bit-for-bit."""
        manifest_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest.jsonl"
        stage_c_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "eval_records_stage_c.jsonl"
        dataset_path = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

        assert compute_file_sha256(manifest_path) == EXPECTED_MANIFEST_HASH
        assert compute_file_sha256(stage_c_path) == EXPECTED_STAGE_C_HASH
        assert compute_file_sha256(dataset_path) == EXPECTED_DATASET_HASH

    def test_cohort_exact_membership_and_uniqueness(self):
        """Invariant 1: Cohort must contain exactly 200 unique table-bearing cases."""
        manifest_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest.jsonl"
        stage_c_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "eval_records_stage_c.jsonl"
        dataset_path = REPO_ROOT / "backend" / "data" / "nq_subset" / "nq_dev.jsonl"

        manifest_cases, stage_c_records, raw_docs = load_and_verify_frozen_cohort(
            manifest_path, stage_c_path, dataset_path
        )

        assert len(manifest_cases) == 200
        assert len(stage_c_records) >= 200
        assert len(raw_docs) == 200

        cids = [m["sample_id"] for m in manifest_cases]
        assert len(set(cids)) == 200

        # Verify Stage C baseline success and classifications
        regs = 0
        recs = 0
        both_w = 0
        both_l = 0

        for cid in cids:
            assert cid in stage_c_records
            rec = stage_c_records[cid]
            assert rec["cond_a"]["status"] == "success"
            assert rec["cond_b"]["status"] == "success"

            em_a = bool(rec["cond_a"]["exact_match"])
            em_b = bool(rec["cond_b"]["exact_match"])

            if em_a and not em_b:
                regs += 1
            elif not em_a and em_b:
                recs += 1
            elif em_a and em_b:
                both_w += 1
            else:
                both_l += 1

        assert regs == 47, f"Expected 47 Stage C regressions, found {regs}"
        assert recs == 11, f"Expected 11 Stage C recoveries, found {recs}"
        assert both_w == 17, f"Expected 17 both win cases, found {both_w}"
        assert both_l == 125, f"Expected 125 both loss cases, found {both_l}"
        assert regs + recs + both_w + both_l == 200


class TestExperiment42InterventionIsolation:
    """Test Suite 2: Threshold as Sole Manipulated Variable."""

    def test_threshold_selection_difference(self):
        """Invariant 2: Condition C (theta=2.0) vs Condition D (theta=0.0) isolates selection."""
        # Construct sample document with a table having low query overlap (score < 2.0)
        html_doc = """
        <html>
        <p>Introduction to the tournament.</p>
        <table>
            <tr><th>Year</th><th>Winner</th><th>Runner-up</th></tr>
            <tr><td>2018</td><td>France</td><td>Croatia</td></tr>
            <tr><td>2014</td><td>Germany</td><td>Argentina</td></tr>
            <tr><td>2010</td><td>Spain</td><td>Netherlands</td></tr>
            <tr><td>2006</td><td>Italy</td><td>France</td></tr>
        </table>
        </html>
        """
        # Query with low overlap (score between 0 and 2.0)
        query = "who won the championship"

        ctx_c, telem_c = build_table_retention_context(html_doc, query, table_threshold=2.0)
        ctx_d, telem_d = build_table_retention_context(html_doc, query, table_threshold=0.0)

        # Under theta=0.0, the table MUST be selected
        assert telem_d["selected_tables_count"] >= 1
        assert "France" in ctx_d

        # Verify ceiling invariance
        assert not telem_c["ceiling_violation"]
        assert not telem_d["ceiling_violation"]

    def test_negative_constraint_rejection_at_theta_0(self):
        """Invariant 2: Negative constraint exclusion must be respected even at theta=0.0."""
        html_doc = """
        <html>
        <p>Overview of awards.</p>
        <table>
            <caption>Excellence in Acting</caption>
            <tr><th>Recipient</th><th>Year</th></tr>
            <tr><td>Alice</td><td>2020</td></tr>
        </table>
        </html>
        """
        # Query explicitly excluding 'Excellence in Acting'
        query = "who received the award other than Excellence in Acting"

        ctx_d, telem_d = build_table_retention_context(html_doc, query, table_threshold=0.0)
        # Should be rejected due to negative entity penalty (-100.0)
        assert telem_d["selected_tables_count"] == 0
        assert "Alice" not in ctx_d


class TestExperiment42ConfigFingerprint:
    """Test Suite 3: Configuration Fingerprint Determinism & Sensitivity."""

    def test_fingerprint_determinism(self):
        fp1 = compute_config_fingerprint()
        fp2 = compute_config_fingerprint()
        assert fp1 == fp2
        assert len(fp1) == 64

    def test_fingerprint_sensitivity(self):
        fp_base = compute_config_fingerprint(temperature=0.0)
        fp_temp = compute_config_fingerprint(temperature=0.7)
        assert fp_base != fp_temp

        fp_model = compute_config_fingerprint(model="llama3:8b")
        assert fp_base != fp_model


class TestExperiment42FailureHandlingAndScoring:
    """Test Suite 4 & 6: Explicit Status Accounting and Null Metric Safeguards."""

    def test_failed_and_unscorable_inferences_never_score_false(self):
        """Invariant 4: Failed or unscorable responses must have EM=None, never False."""
        records = [
            {
                "case_id": "c1",
                "cond_c": {
                    "status": "failed",
                    "error_message": "Timeout",
                    "exact_match": None,
                    "containment": None,
                    "rouge_l": None,
                },
                "cond_d": {
                    "status": "success",
                    "exact_match": True,
                    "containment": True,
                    "rouge_l": 1.0,
                },
            },
            {
                "case_id": "c2",
                "cond_c": {
                    "status": "unscorable",
                    "error_message": "Empty response",
                    "exact_match": None,
                    "containment": None,
                    "rouge_l": None,
                },
                "cond_d": {
                    "status": "success",
                    "exact_match": False,
                    "containment": False,
                    "rouge_l": 0.0,
                },
            },
            {
                "case_id": "c3",
                "cond_c": {
                    "status": "success",
                    "exact_match": True,
                    "containment": True,
                    "rouge_l": 1.0,
                },
                "cond_d": {
                    "status": "success",
                    "exact_match": True,
                    "containment": True,
                    "rouge_l": 1.0,
                },
            },
        ]

        summary_c = compute_condition_summary(records, "cond_c")
        assert summary_c["cases_attempted"] == 3
        assert summary_c["status_counts"]["success"] == 1
        assert summary_c["status_counts"]["failed"] == 1
        assert summary_c["status_counts"]["unscorable"] == 1
        assert summary_c["scored_denominator"] == 1
        assert summary_c["exact_match_count"] == 1
        assert summary_c["exact_match_rate"] == 1.0

    def test_all_failed_condition_returns_none_not_zero(self):
        """Invariant 6: If all inferences fail, rates must be None, NOT 0.0%."""
        records = [
            {
                "case_id": "c1",
                "cond_c": {
                    "status": "failed",
                    "error_message": "Error 500",
                    "exact_match": None,
                    "containment": None,
                    "rouge_l": None,
                },
            }
        ]
        summary_c = compute_condition_summary(records, "cond_c")
        assert summary_c["scored_denominator"] == 0
        assert summary_c["exact_match_rate"] is None
        assert summary_c["containment_rate"] is None


class TestExperiment42PairedComparisons:
    """Test Suite 5: Paired Comparison Accounting & McNemar's Test."""

    def test_paired_diff_exclusion_on_failure(self):
        """Invariant 5: Cases where either condition failed must be excluded from paired diffs."""
        c_fail = {"status": "failed", "exact_match": None}
        d_succ = {"status": "success", "exact_match": True}

        diff = make_paired_case_diff(d_succ, c_fail)
        assert diff["status"] == "excluded"
        assert "cond2 status='failed'" in diff["reason"]
        assert diff["em_win"] is None

    def test_mcnemar_exact_properties(self):
        """Invariant 5: McNemar exact test correctness and edge cases."""
        # Zero discordant pairs
        y1 = [True, False, True]
        y2 = [True, False, True]
        res = compute_mcnemar_exact(y1, y2)
        assert res["discordant_pairs"] == 0
        assert res["p_value"] == 1.0
        assert res["odds_ratio"] == 1.0
        assert res["risk_difference"] == 0.0

        # Asymmetric discordant pairs
        y1_asym = [True, True, True, False]
        y2_asym = [False, False, True, False]
        # b = 2 (cond1 win), c = 0 (cond2 win)
        res_asym = compute_mcnemar_exact(y1_asym, y2_asym)
        assert res_asym["cond1_wins"] == 2
        assert res_asym["cond2_wins"] == 0
        assert res_asym["net_wins_cond1"] == 2
        assert res_asym["risk_difference"] == 0.5
        assert res_asym["odds_ratio"] == "inf"
        assert res_asym["p_value"] == 0.5  # binomtest(2, 2, 0.5) two-sided is 0.5


class TestExperiment42ContextCeilingAndSerialization:
    """Test Suite 7, 8 & 9: Context Ceiling, Directory Protection, and Serialization."""

    def test_context_ceiling_enforcement(self):
        """Invariant 8: Context generator must never exceed 2,048 token ceiling."""
        large_rows = [[f"Cell_{r}_{c}" for c in range(10)] for r in range(500)]
        table_html = "<table><tr>" + "".join(f"<th>H{c}</th>" for c in range(10)) + "</tr>"
        for r in large_rows:
            table_html += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
        table_html += "</table>"

        ctx, telem = build_table_retention_context(table_html, "query cell", table_threshold=0.0, token_ceiling=2048)
        assert not telem["ceiling_violation"]
        assert telem["total_context_estimated_tokens"] <= 2048

    def test_output_directory_protection(self):
        """Invariant 9: Must refuse to overwrite non-empty output directory without --force."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "output"
            out.mkdir()
            (out / "dummy.txt").write_text("existing data")

            with pytest.raises(FileExistsError):
                run_experiment_4_2(output_dir=out, dry_run=True, force=False)

    def test_json_serialization_and_readback(self):
        """Invariant 7: Aggregation outputs must be 100% valid JSON and readable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "test_run"
            res = run_experiment_4_2(output_dir=out, dry_run=True, smoke_test=True, force=True)

            sum_file = out / "aggregate_summary.json"
            paired_file = out / "paired_comparisons.json"
            records_file = out / "eval_records.jsonl"
            audit_file = out / "regression_recovery_audit.jsonl"

            assert sum_file.exists()
            assert paired_file.exists()
            assert records_file.exists()
            assert audit_file.exists()

            with open(sum_file, "r", encoding="utf-8") as f:
                loaded_sum = json.load(f)
                assert loaded_sum["metadata"]["total_cases"] == 5

            with open(paired_file, "r", encoding="utf-8") as f:
                loaded_paired = json.load(f)
                assert "d_vs_c" in loaded_paired["exact_match"]
