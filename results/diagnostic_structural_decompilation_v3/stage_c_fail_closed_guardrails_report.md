# Précis Experiment 3: Stage C Fail-Closed Guardrails and Execution Safety Corrections Report

**Date**: 2026-10-10  
**Phase**: Pre-Execution Hardening (Stage C Confirmatory Preflight)  
**Status**: Safety Patches Implemented & Verified Offline (17/17 Tests Passing)  
**Inference Status**: Zero LLM Inference / Zero Network Calls / Zero Artifact Overwrites  

---

## 1. Summary of Confirmed Corrections

Following the independent read-only audit of Précis Experiment 3 Stage C execution safety, five targeted, fail-closed corrections were implemented across `scripts/eval_structural_decompilation_v3.py` and validated in `scripts/test_stage_c_safety_hardening.py`.

### Correction 1: Strict Resume Manifest Membership
- **Mechanism**: In `run_stage_c_confirmatory()`, the active manifest's sample IDs are compiled into a lookup set `manifest_sids = {item["sample_id"] for item in manifest_records if "sample_id" in item}`.
- **Fail-Closed Gate**: When reading existing records during a resumed run, every line is validated via `validate_stage_c_record(d, manifest_sids=manifest_sids, line_idx=line_idx)`. Any resumed record with a `sample_id` not present in `manifest_sids` raises `ValueError("[SAFETY ERROR] Record at line {X} has unexpected sample_id '{sid}' which is not present in the active confirmatory manifest!")`.
- **Integrity**: Existing duplicate-ID checks (`sid in existing_sids`) and configuration fingerprint validation (`rec_fp == current_fingerprint`) are strictly preserved.

### Correction 2: Complete Record & Condition Validation on Resume
- **Mechanism**: The helper `validate_stage_c_record()` inspects each record dictionary before it can be added to `existing_sids`.
- **Fail-Closed Gate**:
  - Requires valid `type == "sample_record"` and valid `stratum` (`"table_bearing"` or `"prose_only"`).
  - Requires all three condition dictionaries (`cond_a`, `cond_b`, `cond_c`) to be present.
  - Requires `status == "success"` for each condition. Any `"failed"`, `"unscorable"`, or missing status raises `ValueError`.
  - Enforces required fields (`exact_match: bool`, `containment: bool`, `context_tokens: int >= 0`, `predicted_answer: str`, and `struct_facts: int` for B/C).
  - Enforces pairwise comparison fields (`b_vs_a`, `c_vs_a`) and prose-only `invariance_audit`.
- **Protection**: Partially populated records or operational failures cannot be silently skipped or treated as completed.

### Correction 3: Fail-Closed Aggregation Completeness
- **Mechanism**: In `compute_aggregate_summary()`, complete cohort verification is enforced before computing metrics or writing summary files.
- **Fail-Closed Gate**:
  - Validates every record via `validate_stage_c_record(r, manifest_sids=manifest_sids)`.
  - Rejects duplicate records (`ValueError`).
  - Asserts exactly 300 unique samples (`len(seen_sample_ids) == 300`).
  - Asserts exact stratum distribution (200 `table_bearing` and 100 `prose_only`).
  - Both normal full-run execution and `--aggregate-only` verify the active 300-case manifest before computing summary metrics.

### Correction 4: Hard Guardrail Enforcement
- **Mechanism**: Preregistered token overhead guardrail ($\le +10\%$) and Stratum 2 upstream invariance are promoted from purely informational annotations to execution criteria.
- **Fail-Closed Gate**:
  - The aggregate summary records `"confirmatory_outcome": "PASS" | "FAIL_GUARDRAIL"`, `"overhead_guardrail_passed": bool`, and `"upstream_invariance_guardrail_passed": bool`.
  - In `main()` and `--aggregate-only`, `compute_aggregate_summary()` is called with `enforce_guardrails=True`.
  - If either guardrail fails, the summary is written to disk for auditability and a `RuntimeError` is immediately raised, causing the process to terminate with non-zero exit code.

### Correction 5: Artifact Write Ordering & Overwrite Protection
- **Mechanism**: Output files are guarded against premature creation and unvalidated overwrite.
- **Fail-Closed Gate**:
  - In `audit_and_generate_manifest()`, writing `historical_exclusions.json` is deferred until **after** sampling validation (uniqueness, disjointness, candidate counts) completely succeeds.
  - If a non-empty `historical_exclusions.json` or `aggregate_summary.json` already exists in the target output directory, a `FileExistsError` is raised unless `--resume` / `allow_overwrite=True` is explicitly passed.
  - No automatic truncate or unlink operations are performed during error recovery.

---

## 2. Cryptographic Hashes (SHA-256)

### Modified Code Files
| File Path | SHA-256 Checksum | Prior Hash | Status |
| :--- | :--- | :--- | :--- |
| `scripts/eval_structural_decompilation_v3.py` | `ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4` | `ecaef3b3...` | Updated |
| `scripts/test_stage_c_safety_hardening.py` | `104e7fd40bde96411c975fcd2943e1aafe2ea85d24157652000a229abae503f5` | `b5ec3749...` | Updated |

### Preserved Historical Evidence & Reports (Byte-Identical)
| File Path | SHA-256 Checksum | Integrity Status |
| :--- | :--- | :--- |
| `results/.../stage_a_results.json` | `46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32` | **Preserved** (Unchanged) |
| `results/.../stage_a_results_corrected.json` | `46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32` | **Preserved** (Unchanged) |
| `results/.../eval_records_stage_b.jsonl` | `ac1c294dbd916bac334b6de6a3947cd3faf99f8567ab01b4a459203644920c08` | **Preserved** (Unchanged) |
| `results/.../sample_manifest_stage_b.jsonl` | `114350aebec8ac07285535825370835a861c945427e5f558b6e0e76de4eed8d4` | **Preserved** (Unchanged) |
| `results/.../stage_b_replay.json` | `1192386c90f67ac6ceb07de98eb7611a81ecd6e8296e350311e574947cbec094` | **Preserved** (Unchanged) |
| `results/.../stage_b_report.md` | `6c10becb52f893d1e8776f0979503d9a7d10e46618c00afe62992e76477015f4` | **Preserved** (Unchanged) |
| `results/.../stage_c_safety_hardening_report.md` | `075e5c3d359596ef097add475fd80c095ee46fa46a97abb645fd68e17bce23ae` | **Preserved** (Unchanged) |
| `results/.../stage_c_final_safety_corrections_report.md` | `3e83f240be6e83f4f46bcabd38b3316eb2c84dbc6f1758a0c642fd3e0d7b985e` | **Preserved** (Unchanged) |

---

## 3. Test Suite Verification (17/17 Passing)

Execution command: `backend/venv/bin/python -m unittest scripts/test_stage_c_safety_hardening.py -v`  
Result: `Ran 17 tests in 0.073s. OK.`

| # | Test Name | Purpose / Verified Invariant | Result |
| :--- | :--- | :--- | :--- |
| 1 | `test_01_stage_b_manifest_direct_exclusion` | Verifies explicit parsing and exclusion of all 59 Stage B cases | `ok` |
| 2 | `test_02_manifest_overlap_and_duplicate_assertion` | Verifies detection and exclusion of diagnostic overlap cases | `ok` |
| 3 | `test_03_config_fingerprint_determinism_and_sensitivity` | Verifies configuration fingerprint determinism and parameter sensitivity | `ok` |
| 4 | `test_04_manifest_overwrite_protection` | Verifies non-empty manifest overwrite prevention without `--resume` | `ok` |
| 5 | `test_05_record_overwrite_and_resume_validation` | Verifies record overwrite gating, fingerprint check, and clean resume | `ok` |
| 6 | `test_06_prose_only_upstream_invariance_diagnostics` | Verifies byte identity and zero structured blocks on clean prose | `ok` |
| 7 | `test_07_duplicate_candidate_samples_assertion` | Verifies candidate duplicate ID assertion | `ok` |
| 8 | `test_08_duplicate_resumed_records_rejection` | Verifies rejection of duplicate sample IDs in runner and summary | `ok` |
| 9 | `test_09_unexpected_resumed_sample_id_rejection` | Verifies rejection of resumed sample IDs not in active manifest | `ok` |
| 10 | `test_10_missing_condition_rejection` | Verifies rejection of records missing condition A, B, or C | `ok` |
| 11 | `test_11_invalid_or_failed_inference_status_rejection` | Verifies rejection of records with failed/unscorable status | `ok` |
| 12 | `test_12_aggregation_fewer_than_300_samples_rejection` | Verifies rejection of aggregate summary on incomplete cohorts ($N < 300$) | `ok` |
| 13 | `test_13_aggregation_wrong_stratum_counts_rejection` | Verifies rejection of aggregate summary when strata differ from 200/100 | `ok` |
| 14 | `test_14_failed_overhead_guardrail_enforcement` | Verifies hard failure and `FAIL_GUARDRAIL` outcome when overhead $> +10\%$ | `ok` |
| 15 | `test_15_failed_prose_only_invariance_enforcement` | Verifies hard failure when Stratum 2 upstream invariance fails | `ok` |
| 16 | `test_16_aggregate_summary_overwrite_protection` | Verifies overwrite protection on existing `aggregate_summary.json` | `ok` |
| 17 | `test_17_validation_failure_before_any_output_mutation` | Verifies no files written before candidate validation succeeds | `ok` |

---

## 4. Current Limitations & Operational Status

1. **Inference Daemon Offline**: The local Ollama daemon was not started, in strict accordance with the execution freeze.
2. **Fresh Independent Audit Prerequisite**: In accordance with the protocol instructions, Stage C execution is **not authorized** until an independent read-only audit verifies that these fixes close all confirmed safety gaps.
