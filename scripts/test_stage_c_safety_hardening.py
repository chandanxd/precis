#!/usr/bin/env python3
"""
Targeted Deterministic Safety Tests for Précis Experiment 3 (Stage C Preflight Hardening).

Tests:
1. Direct Stage B exclusion extraction and header handling.
2. Direct overlap and duplicate ID detection in manifest generator.
3. Configuration fingerprint determinism and sensitivity.
4. Non-empty Stage C artifact overwrite protection (FileExistsError without --resume).
5. Resume validation (fingerprint match verification, mismatch rejection, malformed record rejection).
6. Upstream prose-only invariance diagnostics.

Zero LLM calls, zero network calls, zero modifications to experiment artifacts.
"""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from eval_structural_decompilation_v3 import (
    DEFAULT_MODEL,
    DEFAULT_TEMP,
    DEFAULT_TOP_P,
    DEFAULT_SEED,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOKEN_CEILING,
    StructuralDocumentParser,
    compute_stage_c_config_fingerprint,
    audit_and_generate_manifest,
    run_stage_c_confirmatory,
    compute_aggregate_summary,
    validate_stage_c_record,
)


class TestStageCSafetyHardening(unittest.TestCase):

    def test_01_stage_b_manifest_direct_exclusion(self):
        """Verify that sample_manifest_stage_b.jsonl is explicitly parsed and excludes all 59 cases."""
        stage_b_path = REPO_ROOT / "results" / "diagnostic_structural_decompilation_v3" / "sample_manifest_stage_b.jsonl"
        self.assertTrue(stage_b_path.exists(), "Stage B manifest must exist for preflight test")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            synthetic_docs = {}
            for i in range(250):
                synthetic_docs[f"t_{i:04d}"] = {
                    "doc_id": f"t_{i:04d}",
                    "question": f"table q {i}",
                    "gold_answer": "ans",
                    "document": f"<Table><Tr><Td>cell {i}</Td></Tr></Table>",
                }
            for i in range(150):
                synthetic_docs[f"p_{i:04d}"] = {
                    "doc_id": f"p_{i:04d}",
                    "question": f"prose q {i}",
                    "gold_answer": "ans",
                    "document": f"Prose document {i} with no tags.",
                }

            manifest_records, exclusions, m_hash = audit_and_generate_manifest(
                synthetic_docs, tmp_path, seed=42, allow_resume=False
            )

            stage_b_sample_ids = set()
            with open(stage_b_path) as fp:
                for line in fp:
                    d = json.loads(line)
                    if d.get("type") == "sample_record":
                        stage_b_sample_ids.add(d["sample_id"])

            self.assertEqual(len(stage_b_sample_ids), 59, "Stage B manifest must contain exactly 59 sample records")
            missing = stage_b_sample_ids - exclusions
            self.assertEqual(len(missing), 0, f"Stage B IDs missing from exclusions: {missing}")

            self.assertNotIn("manifest_header", exclusions)
            self.assertNotIn("stage_b_diagnostic_replay", exclusions)

    def test_02_manifest_overlap_and_duplicate_assertion(self):
        """Verify that audit_and_generate_manifest detects duplicates and overlaps."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            synthetic_docs = {}
            synthetic_docs["bad74caad55343f9ad68de7cd705689a"] = {
                "doc_id": "bad74caad55343f9ad68de7cd705689a",
                "question": "q",
                "gold_answer": "a",
                "document": "<Table><Tr><Td>cell</Td></Tr></Table>",
            }
            for i in range(250):
                synthetic_docs[f"t_{i:04d}"] = {
                    "doc_id": f"t_{i:04d}",
                    "question": f"q {i}",
                    "gold_answer": "a",
                    "document": "<Table><Tr><Td>cell</Td></Tr></Table>",
                }
            for i in range(150):
                synthetic_docs[f"p_{i:04d}"] = {
                    "doc_id": f"p_{i:04d}",
                    "question": f"q {i}",
                    "gold_answer": "a",
                    "document": "prose only",
                }

            manifest, exclusions, _ = audit_and_generate_manifest(
                synthetic_docs, tmp_path, seed=42, allow_resume=False
            )
            sampled_ids = {r["sample_id"] for r in manifest}
            self.assertNotIn("bad74caad55343f9ad68de7cd705689a", sampled_ids)

    def test_03_config_fingerprint_determinism_and_sensitivity(self):
        """Verify configuration fingerprinting stability and sensitivity to changes."""
        fp1 = compute_stage_c_config_fingerprint(model="qwen2.5-coder:7b", manifest_hash="abc123")
        fp2 = compute_stage_c_config_fingerprint(model="qwen2.5-coder:7b", manifest_hash="abc123")
        self.assertEqual(fp1["fingerprint"], fp2["fingerprint"], "Fingerprints must be deterministic")

        fp_diff_model = compute_stage_c_config_fingerprint(model="other:7b", manifest_hash="abc123")
        self.assertNotEqual(fp1["fingerprint"], fp_diff_model["fingerprint"])

        fp_diff_temp = compute_stage_c_config_fingerprint(temp=0.7, manifest_hash="abc123")
        self.assertNotEqual(fp1["fingerprint"], fp_diff_temp["fingerprint"])

        fp_diff_manifest = compute_stage_c_config_fingerprint(manifest_hash="xyz789")
        self.assertNotEqual(fp1["fingerprint"], fp_diff_manifest["fingerprint"])

    def test_04_manifest_overwrite_protection(self):
        """Verify that existing non-empty sample_manifest.jsonl refuses overwrite without --resume."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            manifest_file = tmp_path / "sample_manifest.jsonl"
            manifest_file.write_text("existing content\n")

            with self.assertRaises(FileExistsError) as ctx:
                audit_and_generate_manifest({}, tmp_path, seed=42, allow_resume=False)
            self.assertIn("SAFETY ERROR", str(ctx.exception))

    def test_05_record_overwrite_and_resume_validation(self):
        """Verify that run_stage_c_confirmatory gates on non-empty files and verifies fingerprints."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_file = tmp_path / "eval_records_stage_c.jsonl"
            out_file.write_text("line 1\n")

            # 1. Without allow_resume -> FileExistsError
            with self.assertRaises(FileExistsError) as ctx:
                run_stage_c_confirmatory(
                    docs={}, manifest_records=[], model=DEFAULT_MODEL,
                    output_dir=tmp_path, manifest_hash="m_hash_1", allow_resume=False
                )
            self.assertIn("SAFETY ERROR", str(ctx.exception))

            # 2. With allow_resume but mismatched fingerprint -> ValueError
            cfg = compute_stage_c_config_fingerprint(model=DEFAULT_MODEL, manifest_hash="m_hash_1")
            header_mismatch = {
                "type": "run_header",
                "config_fingerprint": "different_fingerprint_00000000",
                "config": {},
            }
            out_file.write_text(json.dumps(header_mismatch) + "\n")

            with self.assertRaises(ValueError) as ctx:
                run_stage_c_confirmatory(
                    docs={}, manifest_records=[], model=DEFAULT_MODEL,
                    output_dir=tmp_path, manifest_hash="m_hash_1", allow_resume=True
                )
            self.assertIn("fingerprint mismatch", str(ctx.exception))

            # 3. With matching fingerprint and allow_resume -> loads cleanly
            manifest_records = [{"type": "sample_record", "sample_id": "sid_001", "stratum": "prose_only"}]
            matching_header = {
                "type": "run_header",
                "config_fingerprint": cfg["fingerprint"],
                "config": cfg["config"],
            }
            sample_rec = {
                "type": "sample_record",
                "config_fingerprint": cfg["fingerprint"],
                "sample_id": "sid_001",
                "stratum": "prose_only",
                "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "ans", "context_tokens": 10},
                "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "ans", "context_tokens": 10, "struct_facts": 0},
                "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "ans", "context_tokens": 10, "struct_facts": 0},
                "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                "invariance_audit": {"upstream_invariant": True},
            }
            out_file.write_text(json.dumps(matching_header) + "\n" + json.dumps(sample_rec) + "\n")

            loaded = run_stage_c_confirmatory(
                docs={}, manifest_records=manifest_records, model=DEFAULT_MODEL,
                output_dir=tmp_path, manifest_hash="m_hash_1", allow_resume=True
            )
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["sample_id"], "sid_001")

    def test_06_prose_only_upstream_invariance_diagnostics(self):
        """Verify that StructuralDocumentParser preserves exact byte identity on prose-only content."""
        prose_fixture = "Mount Everest is Earth's highest mountain above sea level, located in the Mahalangur Himal sub-range of the Himalayas."
        parser = StructuralDocumentParser(prose_fixture)
        clean_prose, blocks = parser.parse()

        self.assertEqual(clean_prose, prose_fixture, "Prose-only document must have byte-identical clean_prose")
        self.assertEqual(len(blocks), 0, "Prose-only document must yield exactly zero structured blocks")

        table_fixture = "Surrounding prose.<Table><Tr><Td>cell</Td></Tr></Table>Trailing prose."
        parser_tbl = StructuralDocumentParser(table_fixture)
        clean_tbl_prose, tbl_blocks = parser_tbl.parse()
        self.assertNotEqual(clean_tbl_prose, table_fixture)
        self.assertEqual(len(tbl_blocks), 1)

    def test_07_duplicate_candidate_samples_assertion(self):
        """Verify that audit_and_generate_manifest fires its real duplicate assertion when candidates share an ID."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            synthetic_docs = {}
            # Supply 2 distinct dict entries that carry the exact same doc_id
            synthetic_docs["doc_key_alpha"] = {
                "doc_id": "duplicate_id_999",
                "question": "q alpha",
                "gold_answer": "a",
                "document": "<Table><Tr><Td>cell alpha</Td></Tr></Table>",
            }
            synthetic_docs["doc_key_beta"] = {
                "doc_id": "duplicate_id_999",
                "question": "q beta",
                "gold_answer": "a",
                "document": "<Table><Tr><Td>cell beta</Td></Tr></Table>",
            }
            # Fill remaining candidates to reach exactly 200 table and 100 prose
            for i in range(198):
                synthetic_docs[f"t_fill_{i:04d}"] = {
                    "doc_id": f"t_fill_{i:04d}",
                    "question": f"table q {i}",
                    "gold_answer": "ans",
                    "document": f"<Table><Tr><Td>cell {i}</Td></Tr></Table>",
                }
            for i in range(100):
                synthetic_docs[f"p_fill_{i:04d}"] = {
                    "doc_id": f"p_fill_{i:04d}",
                    "question": f"prose q {i}",
                    "gold_answer": "ans",
                    "document": f"Prose doc {i}",
                }

            with self.assertRaises(AssertionError) as ctx:
                audit_and_generate_manifest(synthetic_docs, tmp_path, seed=42, allow_resume=False)
            self.assertIn("Duplicate IDs in confirmatory sample", str(ctx.exception))

    def test_08_duplicate_resumed_records_rejection(self):
        """Verify that run_stage_c_confirmatory and compute_aggregate_summary reject duplicate resumed sample IDs."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_file = tmp_path / "eval_records_stage_c.jsonl"

            cfg = compute_stage_c_config_fingerprint(model=DEFAULT_MODEL, manifest_hash="m_hash_1")
            header = {
                "type": "run_header",
                "config_fingerprint": cfg["fingerprint"],
                "config": cfg["config"],
            }
            rec1 = {
                "type": "sample_record",
                "config_fingerprint": cfg["fingerprint"],
                "sample_id": "sid_duplicate_42",
                "stratum": "table_bearing",
                "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "ans", "context_tokens": 100},
                "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "ans", "context_tokens": 90, "struct_facts": 2},
                "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "ans", "context_tokens": 90, "struct_facts": 2},
                "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": -10},
                "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": -10},
            }
            rec2 = dict(rec1)
            manifest_records = [{"type": "sample_record", "sample_id": "sid_duplicate_42", "stratum": "table_bearing"}]

            out_file.write_text(
                json.dumps(header) + "\n" +
                json.dumps(rec1) + "\n" +
                json.dumps(rec2) + "\n"
            )

            # run_stage_c_confirmatory must reject resume with ValueError identifying the duplicate ID
            with self.assertRaises(ValueError) as ctx:
                run_stage_c_confirmatory(
                    docs={}, manifest_records=manifest_records, model=DEFAULT_MODEL,
                    output_dir=tmp_path, manifest_hash="m_hash_1", allow_resume=True
                )
            self.assertIn("Duplicate resumed record detected", str(ctx.exception))
            self.assertIn("sid_duplicate_42", str(ctx.exception))

            # compute_aggregate_summary must also reject the duplicate records
            with self.assertRaises(ValueError) as ctx_agg:
                compute_aggregate_summary([rec1, rec2], tmp_path)
            self.assertIn("Duplicate record detected in aggregate summary calculation", str(ctx_agg.exception))
            self.assertIn("sid_duplicate_42", str(ctx_agg.exception))

    def test_09_unexpected_resumed_sample_id_rejection(self):
        """Verify that resume rejects records with sample IDs not present in the active manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_file = tmp_path / "eval_records_stage_c.jsonl"
            cfg = compute_stage_c_config_fingerprint(model=DEFAULT_MODEL, manifest_hash="m_hash_1")
            header = {"type": "run_header", "config_fingerprint": cfg["fingerprint"], "config": cfg["config"]}
            manifest_records = [{"type": "sample_record", "sample_id": "sid_expected", "stratum": "table_bearing"}]
            rec = {
                "type": "sample_record",
                "config_fingerprint": cfg["fingerprint"],
                "sample_id": "sid_unexpected",
                "stratum": "table_bearing",
                "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10},
                "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
                "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
                "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
            }
            out_file.write_text(json.dumps(header) + "\n" + json.dumps(rec) + "\n")
            with self.assertRaises(ValueError) as ctx:
                run_stage_c_confirmatory(
                    docs={}, manifest_records=manifest_records, model=DEFAULT_MODEL,
                    output_dir=tmp_path, manifest_hash="m_hash_1", allow_resume=True
                )
            self.assertIn("unexpected sample_id", str(ctx.exception))
            self.assertIn("sid_unexpected", str(ctx.exception))

    def test_10_missing_condition_rejection(self):
        """Verify that records missing condition A, B, or C are rejected."""
        manifest_records = [{"type": "sample_record", "sample_id": "sid_001", "stratum": "table_bearing"}]
        cfg = compute_stage_c_config_fingerprint(model=DEFAULT_MODEL, manifest_hash="m_hash_1")
        # Missing cond_c
        incomplete_rec = {
            "type": "sample_record",
            "config_fingerprint": cfg["fingerprint"],
            "sample_id": "sid_001",
            "stratum": "table_bearing",
            "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10},
            "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
            "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
            "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
        }
        with self.assertRaises(ValueError) as ctx:
            validate_stage_c_record(incomplete_rec, manifest_sids={"sid_001"})
        self.assertIn("missing required condition 'cond_c'", str(ctx.exception))

    def test_11_invalid_or_failed_inference_status_rejection(self):
        """Verify that records with failed, unscorable, or missing status are rejected."""
        rec_failed = {
            "type": "sample_record",
            "sample_id": "sid_001",
            "stratum": "table_bearing",
            "cond_a": {"status": "failed", "exact_match": False, "containment": False, "predicted_answer": "", "context_tokens": 0},
            "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
            "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
            "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
            "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
        }
        with self.assertRaises(ValueError) as ctx:
            validate_stage_c_record(rec_failed)
        self.assertIn("invalid or failed status 'failed'", str(ctx.exception))

    def test_12_aggregation_fewer_than_300_samples_rejection(self):
        """Verify that compute_aggregate_summary rejects cohorts with fewer than 300 unique samples."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            records = []
            for i in range(10):  # only 10 records
                records.append({
                    "type": "sample_record",
                    "sample_id": f"sid_{i}",
                    "stratum": "table_bearing",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                })
            with self.assertRaises(ValueError) as ctx:
                compute_aggregate_summary(records, tmp_path)
            self.assertIn("Incomplete cohort for aggregate summary", str(ctx.exception))
            self.assertIn("Found 10 unique samples", str(ctx.exception))

    def test_13_aggregation_wrong_stratum_counts_rejection(self):
        """Verify that compute_aggregate_summary rejects cohorts where stratum counts differ from 200/100."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            records = []
            # 250 table, 50 prose instead of 200/100
            for i in range(250):
                records.append({
                    "type": "sample_record",
                    "sample_id": f"tbl_{i}",
                    "stratum": "table_bearing",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 1},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                })
            for i in range(50):
                records.append({
                    "type": "sample_record",
                    "sample_id": f"pro_{i}",
                    "stratum": "prose_only",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 0},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 10, "struct_facts": 0},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "invariance_audit": {"upstream_invariant": True},
                })
            with self.assertRaises(ValueError) as ctx:
                compute_aggregate_summary(records, tmp_path)
            self.assertIn("Stratum 1 (table-bearing) count mismatch", str(ctx.exception))

    def test_14_failed_overhead_guardrail_enforcement(self):
        """Verify that overhead > +10% triggers guardrail failure and raises when enforced."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            records = []
            # 200 table bearing where tok_b = 200 vs tok_a = 100 (+100% overhead)
            for i in range(200):
                records.append({
                    "type": "sample_record",
                    "sample_id": f"tbl_{i}",
                    "stratum": "table_bearing",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 200, "struct_facts": 1},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 200, "struct_facts": 1},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 100},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 100},
                })
            for i in range(100):
                records.append({
                    "type": "sample_record",
                    "sample_id": f"pro_{i}",
                    "stratum": "prose_only",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100, "struct_facts": 0},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100, "struct_facts": 0},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "invariance_audit": {"upstream_invariant": True},
                })
            # enforce_guardrails=True must raise RuntimeError
            with self.assertRaises(RuntimeError) as ctx:
                compute_aggregate_summary(records, tmp_path, enforce_guardrails=True, allow_overwrite=True)
            self.assertIn("GUARDRAIL FAILURE", str(ctx.exception))
            self.assertIn("overhead_passed=False", str(ctx.exception))

            # enforce_guardrails=False returns summary with FAIL_GUARDRAIL
            summary = compute_aggregate_summary(records, tmp_path, enforce_guardrails=False, allow_overwrite=True)
            self.assertEqual(summary["confirmatory_outcome"], "FAIL_GUARDRAIL")
            self.assertFalse(summary["overhead_guardrail_passed"])

    def test_15_failed_prose_only_invariance_enforcement(self):
        """Verify that upstream_invariant=False in prose-only stratum triggers guardrail failure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            records = []
            for i in range(200):
                records.append({
                    "type": "sample_record",
                    "sample_id": f"tbl_{i}",
                    "stratum": "table_bearing",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 105, "struct_facts": 1},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 105, "struct_facts": 1},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 5},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 5},
                })
            for i in range(100):
                # Sample 0 has invariance violation
                inv_passed = (i != 0)
                records.append({
                    "type": "sample_record",
                    "sample_id": f"pro_{i}",
                    "stratum": "prose_only",
                    "cond_a": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100},
                    "cond_b": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100, "struct_facts": 0},
                    "cond_c": {"status": "success", "exact_match": True, "containment": True, "predicted_answer": "a", "context_tokens": 100, "struct_facts": 0},
                    "b_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "c_vs_a": {"em_win": False, "em_loss": False, "token_delta": 0},
                    "invariance_audit": {"upstream_invariant": inv_passed},
                })
            with self.assertRaises(RuntimeError) as ctx:
                compute_aggregate_summary(records, tmp_path, enforce_guardrails=True, allow_overwrite=True)
            self.assertIn("upstream_invariance_passed=False", str(ctx.exception))

            summary = compute_aggregate_summary(records, tmp_path, enforce_guardrails=False, allow_overwrite=True)
            self.assertEqual(summary["confirmatory_outcome"], "FAIL_GUARDRAIL")
            self.assertFalse(summary["upstream_invariance_guardrail_passed"])

    def test_16_aggregate_summary_overwrite_protection(self):
        """Verify that existing non-empty aggregate_summary.json refuses overwrite without allow_overwrite."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            summary_file = tmp_path / "aggregate_summary.json"
            summary_file.write_text("existing summary\n")
            with self.assertRaises(FileExistsError) as ctx:
                compute_aggregate_summary([], tmp_path, allow_overwrite=False)
            self.assertIn("SAFETY ERROR", str(ctx.exception))
            self.assertIn("already exists", str(ctx.exception))

    def test_17_validation_failure_before_any_output_mutation(self):
        """Verify that candidate validation failure prevents writing historical_exclusions.json, and exclusions overwrite is gated."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            exclusions_file = tmp_path / "historical_exclusions.json"

            # 1. Existing exclusions file refuses overwrite without allow_resume
            exclusions_file.write_text("existing exclusions\n")
            with self.assertRaises(FileExistsError) as ctx:
                audit_and_generate_manifest({}, tmp_path, allow_resume=False)
            self.assertIn("Non-empty historical exclusions file already exists", str(ctx.exception))

            # 2. When candidate pool fails validation (e.g. insufficient table candidates), exclusions_file is NOT created/mutated
            exclusions_file.unlink()
            synthetic_docs = {}
            for i in range(10):  # only 10 candidates instead of 200
                synthetic_docs[f"t_{i}"] = {
                    "doc_id": f"t_{i}",
                    "question": "q",
                    "gold_answer": "a",
                    "document": "<table><tr><td>c</td></tr></table>"
                }
            with self.assertRaises(AssertionError):
                audit_and_generate_manifest(synthetic_docs, tmp_path, allow_resume=False)
            self.assertFalse(exclusions_file.exists(), "historical_exclusions.json must NOT be written when candidate validation fails")


if __name__ == "__main__":
    unittest.main()
