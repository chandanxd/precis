# Experiment 4: Controlled End-to-End Generation Pilot — Gate 2.1 Failure-Handling Correction Report

**Experiment Identifier**: `diagnostic_experiment_4_v1`  
**Evaluation Scope**: Gate 2.1 Failure-Handling Scoring Semantics, Token Telemetry Clarification & Test Suite Expansion  
**Date**: 2026-10-10  
**Status**: Completed — **Awaiting Explicit Review & Approval before Proceeding to Gate 3**  
**Execution Constraints Enforced**: Zero Production Code Modifications (`backend/src/precis/`), Zero Model Inference Executed, Ollama Daemon Remained Offline  

---

## 1. Executive Summary & Gate 2.1 Verdict

### Gate 2.1 Verdict: `GO (ALL FAILURE SEMANTICS & TOKEN TELEMETRY CORRECTED — AWAITING GATE 3 AUTHORIZATION)`

```
+---------------------------------------------------------------------------------------------------------+
|                                       GATE 2.1 VERDICT: GO                                              |
|                                                                                                         |
|  All 4 corrective requirements from Gate 2.1 review have been implemented and verified:                 |
|  1. Failure & Scoring Semantics:                                                                        |
|     - Explicit per-condition statuses: 'success', 'failed', 'unscorable', 'dry_run'.                    |
|     - Failed and unscorable inferences strictly receive exact_match=None, containment=None,             |
|       rouge_l=None. No incorrect-answer (False / 0.0) penalty is imputed.                                |
|     - Raw responses and operational error messages are fully preserved.                                 |
|  2. Explicit Denominators & Exclusions:                                                                 |
|     - Accuracy metrics report explicit scored_denominator = success_count.                             |
|     - If success_count == 0, metrics report null (unavailable) rather than misleading zeros (0.0%).     |
|     - Paired comparisons (McNemar exact tests) evaluate ONLY cases where both conditions succeeded.     |
|     - Excluded pairs are transparently reported with case IDs and specific exclusion reasons.          |
|  3. Clarified Token Telemetry:                                                                          |
|     - 'context_estimated_tokens': Heuristic subword estimate int(words * 1.3) of context alone.         |
|     - 'full_prompt_model_tokens': Total prompt token count evaluated by Ollama (prompt_eval_count),     |
|       covering system template, grounding rules, packed context, and query.                             |
|     - Removed any misleading claim of measuring context-only model tokens.                             |
|     - 'generated_tokens': Actual model output tokens (eval_count).                                      |
|  4. Integrity Tests & Safety Invariants:                                                                |
|     - Complete integrity suite expanded to 20/20 PASSED (37/37 across full test suite).                 |
|     - Zero model inference executed. Ollama daemon remained offline.                                    |
|     - Zero modifications to production code (`backend/src/precis/`) or frozen benchmark records.         |
|     - `git diff --check` clean; zero-inference dry run completed in new directory.                      |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. File Inventory & Cryptographic Checksums

All modified and newly generated artifacts for Gate 2.1 with exact file sizes and SHA-256 checksums:

| Artifact | Repository Path | File Size (Bytes) | SHA-256 Checksum | Purpose |
| :--- | :--- | :---: | :--- | :--- |
| **Runner Harness** | [`eval_experiment_4_v1.py`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py) | 66,055 | `95bb33291c01fb7bf03bada1362bef56b95910178a685d82076b94b5992d6ab6` | Corrected runner with explicit status handling and exclusion tracking |
| **Integrity Test Suite** | [`test_experiment_4_integrity.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_integrity.py) | 43,549 | `4c1eed5074810b5c291b1ed1de0eae3410325bdc65364d320a23122162b0601b` | 20 automated tests validating failure semantics, scoring, and telemetry |
| **Dry-Run Case Records** | [`dry_run_gate_2_1/eval_records_experiment_4.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/dry_run_gate_2_1/eval_records_experiment_4.jsonl) | 284,384 | `50dbb3c5dbfd3a671195905196060222dec093c4dfe353cfbf7bcddd1505ddc7` | Verified dry-run case records in non-existing directory |
| **Dry-Run Summary** | [`dry_run_gate_2_1/experiment_4_summary.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/dry_run_gate_2_1/experiment_4_summary.json) | 127,353 | `464c07bc5006e6c1d04fb7e531ee85b2bf1538ef846fb9c0a4fa00e58c89ce85` | Aggregated condition summaries, explicit denominators, and paired exclusions |
| **Gate 2.1 Report** | [`gate_2_1_report.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_2_1_report.md) | *(This file)* | *(Calculated post-write)* | Detailed Gate 2.1 audit report |

### Verification of Frozen Inputs (100% Bit-Identical):
- `sample_manifest.jsonl`: `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` (**MATCH**)
- `eval_records_stage_c.jsonl`: `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` (**MATCH**)
- `nq_dev.jsonl`: `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` (**MATCH**)

---

## 3. Corrected Failure-Handling Semantics

### 3.1. Explicit Per-Condition Statuses
Every prediction record across Conditions A, B, C, and D is assigned an explicit status:

1. **`success`**:
   - The model generated a usable, non-empty response string (`len(pred.strip()) > 0`).
   - `exact_match`, `containment`, and `rouge_l` are strictly computed as boolean / float metrics.
   - `error_message` is strictly `None`.
2. **`failed`**:
   - The model generation call raised an operational exception (e.g. `OllamaConnectionError`, `OllamaInferenceError`, socket timeout, or HTTP error).
   - `exact_match = None`, `containment = None`, `rouge_l = None`.
   - `predicted_answer = None`, `raw_response = None`.
   - `error_message` captures the full exception string.
3. **`unscorable`**:
   - The model generated an empty or whitespace-only response (`pred.strip() == ""`).
   - `exact_match = None`, `containment = None`, `rouge_l = None`.
   - `predicted_answer = ""`, `raw_response` preserves the exact response payload (including whitespace / newlines).
   - `error_message` captures `"Empty or whitespace model response"`.
4. **`dry_run`**:
   - Explicit offline execution mode where inference is intentionally bypassed.
   - `exact_match = None`, `containment = None`, `rouge_l = None`.
   - Context building, telemetry, and schema integrity are verified without model dispatch.

### 3.2. Contradictory State Rejection
The harness implements [`validate_condition_result()`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py#L675-L720), which is invoked on every record during execution and aggregation. It enforces:
- Any record with status `failed`, `unscorable`, or `dry_run` that has a non-null `exact_match`, `containment`, or `rouge_l` raises a `ValueError`.
- Any record with status `success` that has a null score, a non-boolean score, or a non-string `predicted_answer` raises a `ValueError`.
- Any unrecognized status literal raises a `ValueError`.

### 3.3. Frozen Baseline Status Validation
When loading frozen Condition A and Condition B records from `eval_records_stage_c.jsonl`:
- The runner explicitly reads `cond_raw.get("status")`.
- If `status == "success"`, scores are validated as boolean values.
- If `status != "success"`, scores are mapped to `None` and an explicit error message is attached; success is **never inferred** solely from the presence of data fields.

---

## 4. Denominator Accounting & Exclusion Rules

### 4.1. Condition-Level Denominators
Aggregation in [`compute_condition_summary()`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py#L740-L805) reports explicit counts for all possible outcomes:

```
Total Cases Attempted: attempted_count (N=58)
├── Successful Cases:  success_count
├── Failed Cases:      failed_count
├── Unscorable Cases:  unscorable_count
└── Dry-Run Cases:     dry_run_count
```

- **Scored Denominator**: `scored_denominator = success_count`.
- **Accuracy Rates**:
  $$\text{Exact Match Rate} = \frac{\text{exact\_match\_count}}{\text{scored\_denominator}}$$
  $$\text{Containment Rate} = \frac{\text{containment\_count}}{\text{scored\_denominator}}$$
- **All-Failed or Dry-Run Behavior**:
  If `scored_denominator == 0`, `exact_match_rate` and `containment_rate` return `null` (`None` in Python), **NOT `0.0` or `0.0%`**. This prevents misleading reporting of failures as 0% accuracy.
- **Unsuccessful Case Tracking**:
  The summary explicitly reports `unsuccessful_case_ids` partitioned by category:
  `{"failed": [case_id, ...], "unscorable": [case_id, ...]}`.

### 4.2. Paired Comparison Denominators & Exclusions
In paired evaluations (e.g., $C \text{ vs } A$, $C \text{ vs } B$, $D \text{ vs } A$, $D \text{ vs } B$, $D \text{ vs } C$):
1. **Valid Paired Cases**:
   A case is included in the paired comparison if and only if **both conditions** achieved `status == "success"` with valid, non-null scores.
2. **Excluded Pairs**:
   If either condition in the pair is `failed`, `unscorable`, or `dry_run`, the case is **strictly excluded** from the paired statistical test.
3. **Exclusion Reporting**:
   [`compute_paired_comparison_summary()`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py#L810-L875) transparently reports:
   - `attempted_pair_count`: Total pairs evaluated (e.g. 58).
   - `valid_paired_denominator`: Count of valid paired cases.
   - `evaluated_case_ids`: Exact list of case IDs included in the test.
   - `excluded_count`: Count of excluded pairs.
   - `excluded_case_ids`: Exact list of excluded case IDs.
   - `exclusion_details`: Per-case breakdown of reasons (e.g. `"cond_c status='failed' (LLM timeout)"`).
4. **Statistical Test Execution**:
   - McNemar's exact test is calculated **strictly over the valid paired cases**.
   - If `valid_paired_denominator == 0` (e.g. in dry-run or if a condition experienced 100% operational failure), `mcnemar_exact` returns `null` with `status: "unavailable"`. No imputed $p$-values are generated.

---

## 5. Clarified Token Telemetry

In response to the Gate 2.1 review, token measurement definitions have been clarified:

1. **`context_estimated_tokens`**:
   - Calculated via the subword heuristic: `int(len(context_text.split()) * 1.3)`.
   - Measures **only** the packed context string (clean prose, GFM table chunks, raw list items).
   - Strictly labeled as an estimated heuristic.
2. **`full_prompt_model_tokens`**:
   - Extracted directly from Ollama's `prompt_eval_count` metric in `InferenceResult`.
   - Represents the **entire concatenated prompt** token count evaluated by the model tokenizer, which includes:
     - `CONCISE_PROMPT_TEMPLATE` framing instructions
     - Grounding rules (negation, attribution, constraints)
     - Packed context text
     - User query
     - Generation triggers (`ANSWER:`)
   - The harness **makes no claim** to measure context-only model tokens, as the Ollama inference API evaluates the prompt sequence as a unified input without isolated sub-span token accounting.
3. **`generated_tokens`**:
   - Extracted directly from Ollama's `eval_count` metric in `InferenceResult`.
   - Measures the actual number of response completion tokens generated by the model.
4. **Removal of Obsolete Claims**:
   - The field `context_model_tokens` has been completely purged from the runner, tests, and documentation to eliminate any implication that context tokens were isolated at the tokenizer level.

---

## 6. Automated Test Suite Results (`test_experiment_4_integrity.py`)

The test suite in [`scripts/test_experiment_4_integrity.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_integrity.py) was expanded from 12 to 20 comprehensive unit and integrity tests:

```bash
backend/venv/bin/python3 -m pytest scripts/test_experiment_4_integrity.py -v
```

### Execution Log:
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/chandan/Projects/major-project/precis
plugins: anyio-4.14.1, cov-7.1.0
collected 20 items

scripts/test_experiment_4_integrity.py::test_exact_manifest_membership_and_58_case_union PASSED [  5%]
scripts/test_experiment_4_integrity.py::test_case_id_validation_missing_and_unexpected PASSED [ 10%]
scripts/test_experiment_4_integrity.py::test_frozen_baseline_reuse_and_provenance PASSED [ 15%]
scripts/test_experiment_4_integrity.py::test_frozen_baseline_status_validation_no_silent_imputation PASSED [ 20%]
scripts/test_experiment_4_integrity.py::test_condition_cd_record_schemas_and_paired_comparisons PASSED [ 25%]
scripts/test_experiment_4_integrity.py::test_failed_inference_never_receives_score_and_preserves_error PASSED [ 30%]
scripts/test_experiment_4_integrity.py::test_unscorable_inference_never_receives_score_and_preserves_raw_response PASSED [ 35%]
scripts/test_experiment_4_integrity.py::test_failed_inference_cannot_silently_count_as_incorrect_answer PASSED [ 40%]
scripts/test_experiment_4_integrity.py::test_aggregation_reports_failures_and_uses_correct_denominator PASSED [ 45%]
scripts/test_experiment_4_integrity.py::test_paired_tests_exclude_invalid_pairs_and_report_ids_and_reasons PASSED [ 50%]
scripts/test_experiment_4_integrity.py::test_all_failed_condition_returns_unavailable_metrics_not_zeros PASSED [ 55%]
scripts/test_experiment_4_integrity.py::test_successful_records_preserve_existing_scoring_behavior PASSED [ 60%]
scripts/test_experiment_4_integrity.py::test_validation_rejects_malformed_contradictory_status_score_combinations PASSED [ 65%]
scripts/test_experiment_4_integrity.py::test_token_telemetry_clarification_heuristic_vs_full_prompt PASSED [ 70%]
scripts/test_experiment_4_integrity.py::test_configuration_fingerprinting_determinism_and_sensitivity PASSED [ 75%]
scripts/test_experiment_4_integrity.py::test_directory_safety_and_overwrite_protection PASSED [ 80%]
scripts/test_experiment_4_integrity.py::test_mcnemar_exact_edge_cases PASSED [ 85%]
scripts/test_experiment_4_integrity.py::test_structural_retention_context_builders_separated_logging PASSED [ 90%]
scripts/test_experiment_4_integrity.py::test_intervention_bundle_documentation PASSED [ 95%]
scripts/test_experiment_4_integrity.py::test_zero_inference_dry_run_execution PASSED [100%]

============================== 20 passed in 4.52s ==============================
```

### Full Repository Regression Test:
```bash
backend/venv/bin/python3 -m pytest scripts/test_stage_c_safety_hardening.py scripts/test_experiment_4_integrity.py -q
.....................................                                    [100%]
37 passed in 4.78s
```

---

## 7. Verification of Safety & Environmental Invariants

1. **Zero LLM / Dense Embedding Invocations**:
   - `curl -s http://localhost:11434/api/tags` confirmed: Ollama daemon is completely offline.
   - Zero HTTP requests were made to port 11434.
2. **Production Code Isolation**:
   - `backend/src/precis/` has zero new changes in this turn (`git diff --name-only backend/src/precis/` matches pre-existing working-tree state from 2026-10-09).
3. **Frozen Benchmark Protection**:
   - Hashes for `sample_manifest.jsonl`, `eval_records_stage_c.jsonl`, and `nq_dev.jsonl` match preflight hashes with 100% precision.
4. **Git Tree Quality**:
   - `git diff --check` executed with code 0 (zero whitespace or formatting errors).
5. **Dry-Run Artifact Verification**:
   - Executed in a clean, non-existing directory `results/diagnostic_experiment_4_v1/dry_run_gate_2_1/`.
   - Verified that `eval_records_experiment_4.jsonl` (284 KB) and `experiment_4_summary.json` (127 KB) generated with full schema validity.

---

## 8. Remaining Operational Risks

| Operational Risk | Severity | Mitigation Implemented | Action Required for Gate 3 |
| :--- | :---: | :--- | :--- |
| **Ollama Daemon Inactivity** | High | Runner checks daemon reachable prior to live dispatch; raises `OllamaConnectionError` | Reviewer must approve starting daemon via `ollama serve &` |
| **Model Generation Timeout** | Medium | Requests timeout set to 120s; exceptions caught cleanly, logged as `failed`, denominator preserved | Monitor per-sample latency during Gate 3 smoke test |
| **Empty Model Output** | Low | Explicitly captured as `unscorable` with raw payload preserved; excluded from paired comparisons | Verified in tests `test_unscorable_inference_*` |
| **GPU / VRAM Contention** | Low | `qwen2.5-coder:7b` requires ~5.5 GB VRAM; verified available on NVIDIA RTX 3060 | Confirm host GPU availability before Gate 4 full run |

---

## 9. Gate 2.1 Recommendation & Stop Condition

### Recommendation: **`GO FOR GATE 3 SMOKE TEST (UPON USER APPROVAL)`**

All requirements from Gate 2.1 have been completed:
- Failure scoring semantics are corrected and mathematically sound.
- Denominators and paired exclusions are completely transparent.
- Token telemetry distinctions are precise and unambiguous.
- Test coverage is 100% green across all 20 integrity tests.

**Antigravity has stopped execution.** No model inference has been executed, the Ollama daemon has NOT been launched, and no further steps will be taken until explicit authorization for Gate 3 is provided by the reviewer.
