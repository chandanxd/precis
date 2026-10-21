# Précis Experiment 3: Final Stage C Safety Corrections Report

This document records the two narrowly scoped safety corrections implemented in response to the independent Stage C safety review.

## 1. Summary of Corrections

### Correction 1: Rejection of Duplicate Resumed Records
- **File**: `scripts/eval_structural_decompilation_v3.py`
- **Locations**:
  1. [`run_stage_c_confirmatory()`](scripts/eval_structural_decompilation_v3.py#L1468-L1480):
     - When inspecting existing Stage C JSONL records during resume, verifies `sample_id` uniqueness against `existing_sids`.
     - If a duplicate `sample_id` is detected, execution raises `ValueError(f"[SAFETY ERROR] Duplicate resumed record detected at line {line_idx+1}! Sample ID '{sid}' appears multiple times in {out_file}. Refusing to resume corrupted records with duplicate entries.")`.
     - Explicitly refuses silent deduplication.
  2. [`compute_aggregate_summary()`](scripts/eval_structural_decompilation_v3.py#L1583-L1595):
     - Iterates through input records and tracks seen sample IDs.
     - If any duplicate `sample_id` is present, raises `ValueError(f"[SAFETY ERROR] Duplicate record detected in aggregate summary calculation (record {r_idx+1})! Sample ID '{sid}' appears multiple times. Refusing to compute metrics on corrupted records with duplicates.")`.

### Correction 2: Genuine Duplicate-Sample Negative Test
- **File**: `scripts/test_stage_c_safety_hardening.py`
- **Location**: `test_07_duplicate_candidate_samples_assertion` and `test_08_duplicate_resumed_records_rejection`:
  - `test_07`: Supplies two distinct dictionary items carrying the identical `doc_id` (`duplicate_id_999`) along with filler candidate documents. Validates that `audit_and_generate_manifest()` triggers the real assertion `assert len(unique_selected_ids) == len(selected_ids)` with `AssertionError: CRITICAL: Duplicate IDs in confirmatory sample: 1 duplicates found!`.
  - `test_08`: Writes a synthetic JSONL file with duplicate `sample_id` records. Validates that `run_stage_c_confirmatory()` and `compute_aggregate_summary()` both raise `ValueError` identifying the duplicate ID (`sid_duplicate_42`).

---

## 2. Verification Commands and Actual Outputs

### A. Python Syntax Compilation
**Command**:
```bash
backend/venv/bin/python -m py_compile scripts/eval_structural_decompilation_v3.py scripts/test_stage_c_safety_hardening.py
```
**Output**: Exited with code 0 (zero errors).

### B. Targeted Safety Test Suite
**Command**:
```bash
backend/venv/bin/python scripts/test_stage_c_safety_hardening.py
```
**Output**:
```
Exclusions cataloged: 600
Available table/list candidates: 250 (Required: 200)
Available prose-only candidates: 150 (Required: 100)
Successfully wrote 300 samples to /tmp/tmp4yaun1h4/sample_manifest.jsonl (manifest_hash: f1363396055f...)
.Exclusions cataloged: 600
Available table/list candidates: 250 (Required: 200)
Available prose-only candidates: 150 (Required: 100)
Successfully wrote 300 samples to /tmp/tmp4secz6ck/sample_manifest.jsonl (manifest_hash: f1363396055f...)
...
================================================================================
RUNNING STAGE C: CONFIRMATORY DUAL-STRATUM EVALUATION (N=0)
================================================================================
Active Stage C Configuration Fingerprint: f040c88cb4ccc81db343a0560fa12cd0b75eae9d7180f18c50464756c593f1f1

================================================================================
RUNNING STAGE C: CONFIRMATORY DUAL-STRATUM EVALUATION (N=0)
================================================================================
Active Stage C Configuration Fingerprint: f040c88cb4ccc81db343a0560fa12cd0b75eae9d7180f18c50464756c593f1f1

================================================================================
RUNNING STAGE C: CONFIRMATORY DUAL-STRATUM EVALUATION (N=0)
================================================================================
Active Stage C Configuration Fingerprint: f040c88cb4ccc81db343a0560fa12cd0b75eae9d7180f18c50464756c593f1f1
Validated resume: loaded 1 existing matching confirmatory records (Fingerprint: f040c88cb4cc...).
..Exclusions cataloged: 600
Available table/list candidates: 200 (Required: 200)
Available prose-only candidates: 100 (Required: 100)
.
================================================================================
RUNNING STAGE C: CONFIRMATORY DUAL-STRATUM EVALUATION (N=0)
================================================================================
Active Stage C Configuration Fingerprint: f040c88cb4ccc81db343a0560fa12cd0b75eae9d7180f18c50464756c593f1f1
.
----------------------------------------------------------------------
Ran 8 tests in 0.042s

OK
```

---

## 3. Harness Fingerprints & Artifact Verification

- **Final Harness SHA-256**: `ecaef3b3553767055d1ea32c425a31430a510c25ec434fa839e81e756f2d08b5` (`scripts/eval_structural_decompilation_v3.py`)
- **Test Suite SHA-256**: `b5ec3749c8ea7cf54c2ea6410a8d85e1bef7660c547e0b212a9313e7ff2798d0` (`scripts/test_stage_c_safety_hardening.py`)
- **Stage A Artifact Hashes**:
  - `stage_a_results.json`: `46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32` (untouched)
  - `stage_a_results_corrected.json`: `46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32` (untouched)
- **Stage B Artifact Hashes**:
  - `eval_records_stage_b.jsonl`: `ac1c294dbd916bac334b6de6a3947cd3faf99f8567ab01b4a459203644920c08` (untouched)
  - `sample_manifest_stage_b.jsonl`: `114350aebec8ac07285535825370835a861c945427e5f558b6e0e76de4eed8d4` (untouched)
  - `stage_b_replay.json`: `1192386c90f67ac6ceb07de98eb7611a81ecd6e8296e350311e574947cbec094` (untouched)
  - `stage_b_report.md`: `6c10becb52f893d1e8776f0979503d9a7d10e46618c00afe62992e76477015f4` (untouched)

---

## 4. Execution Command for Stage C (When Authorized)

```bash
backend/venv/bin/python scripts/eval_structural_decompilation_v3.py --stage-c-only
```
If safely resuming an interrupted confirmatory run:
```bash
backend/venv/bin/python scripts/eval_structural_decompilation_v3.py --stage-c-only --resume
```
