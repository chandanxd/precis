# Experiment 4: Controlled End-to-End Generation Pilot — Gate 2 Integrity Report

**Experiment Identifier**: `diagnostic_experiment_4_v1`  
**Evaluation Scope**: Gate 2 Isolated Harness Implementation & Integrity Verification  
**Date**: 2026-10-10  
**Status**: Completed — **Awaiting Explicit Review & Approval for Gate 3**  
**Execution Constraints**: Zero Code Modifications to Production (`backend/src/precis/`), Zero LLM Inference Executed, Ollama Daemon Remained Offline  

---

## 1. Executive Summary & Gate 2 Verdict

### Gate 2 Verdict: `GO (PROCEED TO GATE 3 SMOKE TEST UPON APPROVAL)`

```
+---------------------------------------------------------------------------------------------------------+
|                                        GATE 2 VERDICT: GO                                               |
|                                                                                                         |
|  All 8 mandatory Gate 2 engineering and verification requirements PASSED:                                |
|  1. Isolated evaluation runner implemented at `scripts/eval_experiment_4_v1.py`.                        |
|  2. Comprehensive test suite implemented at `scripts/test_experiment_4_integrity.py` (12/12 PASSED).    |
|  3. Exact 58-case targeted unique union reconstructed (47 regressions + 11 recoveries, intersection=0).  |
|  4. Frozen Condition A and B baseline predictions verified for direct reuse with complete provenance.   |
|  5. Structural retention context builders implement separate telemetry across all 5 distinct stages:    |
|     Conversion, Selection, Row Retention (100% preserved), Chunking (500-token cap), and Context Packing|
|  6. Condition C vs B intervention bundle explicitly documented across code, schemas, and reports.       |
|  7. Token count schemas strictly distinguish subword heuristics from actual model tokenizer counts.    |
|  8. Artifact overwrite protection, configuration fingerprinting, and failure handling verified.        |
|                                                                                                         |
|  INVARIANCE GUARANTEE:                                                                                  |
|  Zero model inference was executed during Gate 2. Local Ollama daemon remained completely offline.      |
|  All production modules under `backend/src/precis/` remain 100% untouched.                              |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. File Inventory & Cryptographic Hashes

All newly created files for Gate 2 with their exact file sizes and SHA-256 checksums:

| Artifact | Repository Path | File Size (Bytes) | SHA-256 Checksum | Purpose |
| :--- | :--- | :---: | :--- | :--- |
| **Runner Harness** | `scripts/eval_experiment_4_v1.py` | 50,564 | `a07ad3370e7cd22146ae56301cdb1a5314a086d04b974e3555dafca8683d09f5` | Isolated runner for Conditions C & D with frozen A & B reuse |
| **Integrity Test Suite** | `scripts/test_experiment_4_integrity.py` | 26,580 | `6b03e5edba0e6af4e84a7f19456255ddc031870d1e637480cfff3b19abc8161e` | 12 automated unit and integrity tests covering all invariants |
| **Gate 2 Report** | `results/diagnostic_experiment_4_v1/gate_2_report.md` | *(This file)* | *(Calculated post-write)* | Comprehensive Gate 2 inspection and verification documentation |

### Verification of Frozen Inputs (Unmodified since Gate 1)
- `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl`: `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` (MATCH)
- `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl`: `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` (MATCH)
- `backend/data/nq_subset/nq_dev.jsonl`: `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` (MATCH)

---

## 3. Architecture & Implementation of `scripts/eval_experiment_4_v1.py`

### 3.1. Architectural Decisions & Key Protocol Invariants

1. **Intervention Bundle Definition (Condition C vs Condition B)**:
   > [!IMPORTANT]
   > The comparison between Condition C and Condition B evaluates an **intervention bundle**, NOT representation alone. Condition C changes two key pipeline stages simultaneously:
   > 1. **Representation**: Compact GFM Markdown tables with preserved headers vs. SVOA relational triples.
   > 2. **Row Retention & Chunking**: Retaining 100% of rows up to a 500-token per-table budget with contiguous row chunking and repeated headers vs. top-5 lexical keyword overlap row filtering.

2. **Strict Token Count Distinctions**:
   The runner and all schema dataclasses enforce unambiguous token naming:
   - `context_estimated_tokens`: Computed via heuristic `int(len(text.split()) * 1.3)`.
   - `context_model_tokens`: Actual tokenizer prompt token count evaluated by the LLM (from Ollama `prompt_eval_count`). Set to `None` during dry-run or if the tokenizer is uninvoked.
   - `generated_tokens`: Tokens generated by the LLM (from Ollama `eval_count`).
   Heuristic estimates are **never** reported as model tokens.

3. **Frozen Baseline Reuse**:
   - Condition A and Condition B are loaded directly from `eval_records_stage_c.jsonl` for the 58 cases in the targeted union.
   - All 58 cases have complete outputs, exact match, containment, token counts, and `status: "success"`.
   - Reused records carry provenance metadata referencing their original configuration fingerprint.

4. **Separated Logging of Context Building**:
   The structural retention context builders (`build_structural_retention_context`) explicitly log telemetry across 5 distinct stages:
   - **Stage 1 (Conversion)**: Source block ID, caption, original headers, rendered headers, header preservation status (`PRESERVED_EXPLICIT`, `TITLE_BANNER_TO_CAPTION`, `GENERATED_DEFAULT`), original rows, rendered rows, and conversion status.
   - **Stage 2 (Selection)**: Table block ID, relevance score, decision (`SELECTED` vs `REJECTED: below threshold 2.0`), threshold ($\theta=2.0$).
   - **Stage 3 (Row Retention)**: Original rows, retained rows, row retention rate (1.0), policy (`retain_all_rows_gfm_chunking`).
   - **Stage 4 (Chunking)**: Contiguous chunk index, start row, end row, row count, subword token estimate.
   - **Stage 5 (Packing)**: Clean prose tokens, table chunks packed count, table tokens packed, list items packed, list tokens packed, total context tokens, ceiling violation flag, zero context flag.

5. **Failure & Degraded Inference Handling (Strict Denominator Accounting)**:
   - If model generation fails (timeout, connection error, empty output), the runner catches the exception, logs `status: "failed"` with `error_message`, and marks `exact_match: False` and `containment: False`.
   - The case is **never dropped** from the evaluation denominator. The denominator remains strictly $N=58$.

6. **Directory Safety & Overwrite Protection**:
   - Output files (`eval_records_experiment_4.jsonl`, `experiment_4_summary.json`) are guarded against accidental overwrite.
   - If files exist, the runner raises `FileExistsError` unless `--force` is explicitly specified.

---

## 4. Test Suite Execution & Verification (`test_experiment_4_integrity.py`)

The automated test suite in `scripts/test_experiment_4_integrity.py` was executed using pytest in the project's virtual environment:

```bash
backend/venv/bin/python3 -m pytest scripts/test_experiment_4_integrity.py -v
```

### Test Results Summary:

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/chandan/Projects/major-project/precis
plugins: anyio-4.14.1, cov-7.1.0
collected 12 items

scripts/test_experiment_4_integrity.py::test_exact_manifest_membership_and_58_case_union PASSED [  8%]
scripts/test_experiment_4_integrity.py::test_case_id_validation_missing_and_unexpected PASSED [ 16%]
scripts/test_experiment_4_integrity.py::test_frozen_baseline_reuse_and_provenance PASSED [ 25%]
scripts/test_experiment_4_integrity.py::test_condition_cd_record_schemas_and_paired_comparisons PASSED [ 33%]
scripts/test_experiment_4_integrity.py::test_failed_or_degraded_inference_handling PASSED [ 41%]
scripts/test_experiment_4_integrity.py::test_configuration_fingerprinting_determinism_and_sensitivity PASSED [ 50%]
scripts/test_experiment_4_integrity.py::test_directory_safety_and_overwrite_protection PASSED [ 58%]
scripts/test_experiment_4_integrity.py::test_mcnemar_exact_edge_cases PASSED [ 66%]
scripts/test_experiment_4_integrity.py::test_structural_retention_context_builders_separated_logging PASSED [ 75%]
scripts/test_experiment_4_integrity.py::test_token_count_distinction_heuristic_vs_model PASSED [ 83%]
scripts/test_experiment_4_integrity.py::test_intervention_bundle_documentation PASSED [ 91%]
scripts/test_experiment_4_integrity.py::test_zero_inference_dry_run_execution PASSED [100%]

============================== 12 passed in 4.35s ==============================
```

### Verification Coverage by Test Case:

1. `test_exact_manifest_membership_and_58_case_union`:
   - Confirms 200 table-bearing cases in manifest.
   - Reconstructs exactly 47 regressions ($A=1, B=0$) and 11 recoveries ($A=0, B=1$).
   - Verifies disjointness ($|N_1 \cap N_2| = 0$) and union size ($|N_1 \cup N_2| = 58$).
2. `test_case_id_validation_missing_and_unexpected`:
   - Verifies that missing records raise `KeyError`, corrupted manifests raise `ValueError`, and unknown IDs raise `KeyError`.
3. `test_frozen_baseline_reuse_and_provenance`:
   - Verifies all 58 cases have valid, non-empty predictions and status="success" in Condition A and B.
   - Validates that Condition A EM is True for all 47 regressions and False for all 11 recoveries.
   - Validates that Condition B EM is False for all 47 regressions and True for all 11 recoveries.
4. `test_condition_cd_record_schemas_and_paired_comparisons`:
   - Validates schema fields: `exact_match`, `containment`, `rouge_l`, `context_estimated_tokens`, `context_model_tokens`, `generated_tokens`, `latency_ms`, `status`, `error_message`, `provenance`, `structural_retention_telemetry`.
   - Verifies paired diff calculations (`em_win`, `em_loss`, `token_delta`).
5. `test_failed_or_degraded_inference_handling`:
   - Mocks `OllamaInferenceError` (timeout/crash).
   - Verifies that `status="failed"` is logged, error message captured, exact match is False, and case is preserved in denominator ($N=1$).
6. `test_configuration_fingerprinting_determinism_and_sensitivity`:
   - Verifies that identical hyperparameter setups produce identical SHA-256 fingerprints.
   - Verifies sensitivity: altering temperature, top_p, seed, model, token ceiling, or input hashes changes the fingerprint.
7. `test_directory_safety_and_overwrite_protection`:
   - Verifies `FileExistsError` is raised if output files already exist and `--force` is False.
   - Verifies `--force` allows overwrite.
8. `test_mcnemar_exact_edge_cases`:
   - $b=0, c=0 \implies p=1.0, \text{OR}=1.0, \text{RiskDiff}=0.0$ (Zero discordant pairs).
   - $b=5, c=5 \implies p=1.0, \text{OR}=1.0, \text{RiskDiff}=0.0$ (Symmetric discordance).
   - $b=10, c=0 \implies p = 2/1024 \approx 0.001953, \text{OR}=\infty$ (Extreme one-sided).
   - $b=8, c=2 \implies p = 112/1024 = 0.109375, \text{OR}=4.0$ (Asymmetric split).
9. `test_structural_retention_context_builders_separated_logging`:
   - Verifies distinct telemetry blocks for Conversion, Selection, Row Retention (rate = 1.0), Chunking, and Packing.
10. `test_token_count_distinction_heuristic_vs_model`:
    - Validates `context_estimated_tokens` as `int(words * 1.3)` and `context_model_tokens` as nullable.
11. `test_intervention_bundle_documentation`:
    - Verifies docstrings and documentation explicitly describe Condition C vs B as an intervention bundle.
12. `test_zero_inference_dry_run_execution`:
    - Verifies dry-run runs cleanly with zero network or Ollama calls and writes valid output records with `status="dry_run"`.

---

## 5. End-to-End CLI Dry-Run Verification

The runner CLI was executed in `--dry-run` mode over all 58 cases:

```bash
backend/venv/bin/python3 scripts/eval_experiment_4_v1.py --dry-run
```

### Dry-Run Output:
- **Input Hashes**: Verified against preflight digests.
- **Cohort**: 58 cases evaluated ($47 \text{ regressions} + 11 \text{ recoveries}$).
- **Configuration Fingerprint**: `9fc71ebca6501b6b58aca481010a6c144416298b6aa91334f7bc0ca353bfa1c3`.
- **Condition A Reused**: 47 / 58 EM (81.0%), Mean tokens: 542.4.
- **Condition B Reused**: 11 / 58 EM (19.0%), Mean tokens: 106.7.
- **Condition C Context Built**: Mean estimated tokens: 280.0 (51.6% compression vs Condition A).
- **Condition D Context Built**: Mean estimated tokens: 289.9 (46.5% compression vs Condition A).
- **Execution Mode**: Zero LLM calls; dry-run output cleanly verified.

---

## 6. Readiness for Gate 3 (Smoke Test)

### Proposed Gate 3 Scope:
Before launching the full 58-case generation pilot in Gate 4, Gate 3 will execute a live end-to-end smoke test on **5 explicitly identified cases**:

1. `2c62d7eb04924071959544f85e978b8b` (P1 Regression — Secretary of State for Northern Ireland)
2. `a16cca39f27e4d78a64de2d8285bc4bf` (P1 Regression — Next Guest Needs No Introduction)
3. `3f0497f4a228459c8b2201e7f871a520` (P1 Regression — Gunsmoke to the Last Man filming location)
4. `16caa32e50d342878340cacefe5a417a` (P2 Recovery — Leading African producer of wool)
5. `00d7c7cc7b534abeaf1f9dded1d3639b` (P2 Recovery — Chris Grandy in 13 Going on 30)

### Pre-conditions for Gate 3:
1. **User Authorization**: Explicit approval of this Gate 2 report.
2. **Ollama Daemon Activation**: The local Ollama daemon must be started (`ollama serve &`) prior to running Gate 3.

---

## 7. Gate 2 Recommendation & Next Action

### Recommendation: `GO FOR GATE 3 SMOKE TEST`

All harness implementations, integrity tests, schema validations, and safety protections are verified and complete.

**Antigravity has stopped execution.** No model inference has been executed, and no further actions will be taken until explicit authorization for Gate 3 is provided by the reviewer.
