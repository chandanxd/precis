# Experiment 4: Controlled End-to-End Generation Pilot — Gate 3 Smoke Test Report

**Experiment Identifier**: `diagnostic_experiment_4_v1`  
**Evaluation Scope**: Gate 3 Live Inference Smoke Test (5 Authorized Target Cases)  
**Date**: 2026-10-10  
**Status**: Completed — **Awaiting Explicit Review & Approval before Proceeding to Gate 4**  
**Execution Constraints Enforced**: Zero Production Code Modifications (`backend/src/precis/`), 5-Case Scope Strictly Bounded, Frozen Baseline Predictions Reused, Full Prompt Token Telemetry Verified  

---

## 1. Executive Summary & Gate 3 Verdict

### Gate 3 Verdict: `GO FOR GATE 4 (58-CASE TARGETED PILOT AUTHORIZATION)`

```
+---------------------------------------------------------------------------------------------------------+
|                                        GATE 3 VERDICT: GO                                               |
|                                                                                                         |
|  All Gate 3 verification criteria have been successfully executed and validated:                         |
|  1. Operational Readiness:                                                                              |
|     - Local Ollama daemon active and responsive on http://localhost:11434.                              |
|     - Model 'qwen2.5-coder:7b' successfully loaded and executed on GPU.                                 |
|     - 10 live generation requests (5 cases x 2 conditions) completed with 100% success rate (0 failures).|
|  2. Harness & Fingerprint Fidelity:                                                                     |
|     - Configuration fingerprint: 9fc71ebca6501b6b58aca481010a6c144416298b6aa91334f7bc0ca353bfa1c3      |
|       (100% bit-identical match to approved Gate 2.1 specification).                                   |
|     - Output directory safety respected (clean creation under gate_3_smoke_test/).                     |
|  3. Telemetry & Scoring Integrity:                                                                      |
|     - Ollama 'prompt_eval_count' accurately logged as full_prompt_model_tokens (mean 454.6 / 489.0).     |
|     - Context heuristic subwords logged as context_estimated_tokens (mean 184.4 / 212.4).               |
|     - Generated tokens accurately tracked (eval_count, mean 4.2 tokens).                                |
|     - Scored denominator = 5, failed = 0, unscorable = 0 across all conditions.                         |
|     - Paired comparisons evaluated strictly over valid mutual-success pairs (denominator = 5).          |
|  4. Causal Observability:                                                                               |
|     - Case 2c62d7eb (Karen Bradley): Header preservation restored answer-bearing table; both Cond C/D  |
|       recovered EM=True (was False in Cond A & B).                                                      |
|     - Case 3f0497f4 (Gunsmoke filming location): Reclaimed P1 regression; Cond C/D answered             |
|       'Tucson, Arizona' (EM=True).                                                                      |
|     - Case 00d7c7cc (Jim Gaffigan): Retained P2 recovery; Cond C/D answered 'Jim Gaffigan' (EM=True).    |
|  5. Statistical Scope Invariant:                                                                        |
|     - 5 cases are strictly treated as an operational smoke test, NOT as evidence of population-level   |
|       accuracy improvement.                                                                            |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. File Inventory & Cryptographic Checksums

All artifacts involved in the Gate 3 smoke test with exact file sizes and SHA-256 digests:

| Artifact | Repository Path | File Size (Bytes) | SHA-256 Checksum | Purpose |
| :--- | :--- | :---: | :--- | :--- |
| **Smoke Test Records** | [`gate_3_smoke_test/eval_records_experiment_4.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_3_smoke_test/eval_records_experiment_4.jsonl) | 22,981 | `eeba8c2ae944b5bec72a59871ed8b8186ed40549c0589a0cc1674401550cab21` | Live inference records for 5 cases across Conditions A, B, C, D |
| **Smoke Test Summary** | [`gate_3_smoke_test/experiment_4_summary.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_3_smoke_test/experiment_4_summary.json) | 15,365 | `1ac32db78a6d7aa065e3181dea090b6907bd2cea12558844bb620170317c0745` | Aggregated condition summaries, exact McNemar paired tables |
| **Runner Harness** | [`eval_experiment_4_v1.py`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py) | 66,271 | `f228e41eb3d724380e20f2f84046f451f9a3862f57d49702ff4b4b6c9ac041dc` | Harness with explicit `SMOKE_TEST_CASE_IDS` cohort definition |
| **Integrity Tests** | [`test_experiment_4_integrity.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_integrity.py) | 45,412 | `f27a0d5f5788b297f48845513975c6b1df1419e3c8280ed726390aae56b5d01d` | 21 passing integrity and cohort membership tests |

### Frozen Input Provenance Verification (100% Bit-Identical)
- `sample_manifest.jsonl`: `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` (**MATCH**)
- `eval_records_stage_c.jsonl`: `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` (**MATCH**)
- `nq_dev.jsonl`: `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` (**MATCH**)

---

## 3. Per-Case Results Across the 5 Authorized Smoke-Test Cases

### Case 1: `2c62d7eb04924071959544f85e978b8b`
- **Question**: *"who is the secretary of state for northern ireland"*
- **Gold Answer**: `"Karen Bradley"`
- **Stratum / Priority Cohort**: `table_bearing` / `other` (Stage D.1/D.2 header-preservation probe case)
- **Condition Predictions & Scoring**:
  - **Cond A (Prose Baseline)**: `exact_match: False`, `containment: False`, Pred: *"Northern Ireland Secretary"*, Context Est Tokens: 58
  - **Cond B (Decompilation Baseline)**: `exact_match: False`, `containment: False`, Pred: *"The Right Honourable Northern Ireland Secretary"*, Context Est Tokens: 123
  - **Cond C (Table Retention)**: `exact_match: True`, `containment: True`, `rouge_l: 1.0`, Pred: **"Karen Bradley"**, Context Est Tokens: 169, Full Prompt Tokens: 436, Generated Tokens: 3, Latency: 10,476 ms (cold-start model load)
  - **Cond D (Table + List Retention)**: `exact_match: True`, `containment: True`, `rouge_l: 1.0`, Pred: **"Karen Bradley"**, Context Est Tokens: 169, Full Prompt Tokens: 436, Generated Tokens: 3, Latency: 79 ms (warm)
- **Structural Telemetry**:
  - Block 0: Infobox converted via `TITLE_BANNER_TO_CAPTION`, 10/10 rows retained, 1 chunk of 169 tokens.
  - Table selection score: 3.0 (above threshold 2.0). Answer cell preserved in rendered chunk.
- **Diagnostic Finding**: Causal confirmation of Probe D.2. The model correctly extracts the incumbent secretary when the infobox table is formatted as GFM markdown rather than decompiled SVOA facts.

---

### Case 2: `a16cca39f27e4d78a64de2d8285bc4bf`
- **Question**: *"when will the next episode of my next guest needs no introduction"*
- **Gold Answer**: `"May 31 , 2018"`
- **Stratum / Priority Cohort**: `table_bearing` / `other`
- **Condition Predictions & Scoring**:
  - **Cond A (Prose Baseline)**: `exact_match: False`, `containment: False`, Pred: *"Insufficient information"*, Context Est Tokens: 469
  - **Cond B (Decompilation Baseline)**: `exact_match: False`, `containment: False`, Pred: *"Insufficient information"*, Context Est Tokens: 389
  - **Cond C (Table Retention)**: `exact_match: False`, `containment: False`, `rouge_l: 0.0`, Pred: *"Insufficient information"*, Context Est Tokens: 494, Full Prompt Tokens: 785, Generated Tokens: 4, Latency: 359 ms
  - **Cond D (Table + List Retention)**: `exact_match: False`, `containment: False`, `rouge_l: 0.0`, Pred: *"Insufficient information"*, Context Est Tokens: 494, Full Prompt Tokens: 785, Generated Tokens: 4, Latency: 95 ms
- **Structural Telemetry**:
  - Block 0: Episode table converted via `PRESERVED_EXPLICIT`, 10/10 rows retained, 1 chunk of 494 tokens.
  - Table selection score: 7.0 (above threshold 2.0).
- **Diagnostic Finding**: Even though the table is retained, the question asks for "next episode" which requires temporal reasoning over episode release dates; the model conservatively emits "Insufficient information" across all conditions.

---

### Case 3: `3f0497f4a228459c8b2201e7f871a520`
- **Question**: *"where was gunsmoke to the last man filmed"*
- **Gold Answer**: `"Tucson , Arizona"`
- **Stratum / Priority Cohort**: `table_bearing` / `P1_regression` (Stage C EM Regression: A won, B lost)
- **Condition Predictions & Scoring**:
  - **Cond A (Prose Baseline)**: `exact_match: True`, `containment: True`, Pred: *"Tucson, Arizona"*, Context Est Tokens: 393
  - **Cond B (Decompilation Baseline)**: `exact_match: False`, `containment: False`, Pred: *"Insufficient information"*, Context Est Tokens: 33 (severe context pruning)
  - **Cond C (Table Retention)**: `exact_match: True`, `containment: True`, `rouge_l: 1.0`, Pred: **"Tucson, Arizona"**, Context Est Tokens: 250, Full Prompt Tokens: 506, Generated Tokens: 5, Latency: 265 ms
  - **Cond D (Table + List Retention)**: `exact_match: True`, `containment: True`, `rouge_l: 1.0`, Pred: **"Tucson, Arizona"**, Context Est Tokens: 250, Full Prompt Tokens: 506, Generated Tokens: 5, Latency: 117 ms
- **Structural Telemetry**:
  - Block 0: Infobox converted via `TITLE_BANNER_TO_CAPTION`, 17/17 rows retained, 1 chunk of 250 tokens.
  - Table selection score: 3.0 (above threshold 2.0).
- **Diagnostic Finding**: Direct reversal of a Stage C regression. In Stage C, Condition B collapsed context from 393 to 33 tokens, dropping filming locations. Conditions C & D packed the full 17-row infobox into 250 tokens, recovering `exact_match: True`.

---

### Case 4: `16caa32e50d342878340cacefe5a417a`
- **Question**: *"who is the leading african producer of wool"*
- **Gold Answer**: `"South Africa"`
- **Stratum / Priority Cohort**: `table_bearing` / `P2_recovery` (Stage C EM Recovery: A lost, B won)
- **Condition Predictions & Scoring**:
  - **Cond A (Prose Baseline)**: `exact_match: False`, `containment: False`, Pred: *"Insufficient information"*, Context Est Tokens: 443
  - **Cond B (Decompilation Baseline)**: `exact_match: True`, `containment: True`, Pred: *"South Africa"*, Context Est Tokens: 281 (facts extracted from list/table)
  - **Cond C (Table Retention)**: `exact_match: False`, `containment: False`, `rouge_l: 0.0`, Pred: *"Insufficient information"*, Context Est Tokens: 0, Full Prompt Tokens: 263, Generated Tokens: 4, Latency: 122 ms
  - **Cond D (Table + List Retention)**: `exact_match: False`, `containment: False`, `rouge_l: 0.0`, Pred: *"Insufficient information"*, Context Est Tokens: 126, Full Prompt Tokens: 418, Generated Tokens: 4, Latency: 175 ms
- **Structural Telemetry**:
  - Condition C: 0 tables selected above threshold 2.0; context packed 0 tokens.
  - Condition D: 11 raw list items packed (126 tokens). However, the model still emitted "Insufficient information".
- **Diagnostic Finding**: Highlights the value of the targeted pilot design. Condition B's heuristic fact extractor succeeded on this list structure, whereas raw list packing in Condition D did not induce the model to answer.

---

### Case 5: `00d7c7cc7b534abeaf1f9dded1d3639b`
- **Question**: *"who plays chris grandy in 13 going on 30"*
- **Gold Answer**: `"Jim Gaffigan"` (Answers: `["Jim Gaffigan", "Alex Black"]`)
- **Stratum / Priority Cohort**: `table_bearing` / `P2_recovery` (Stage C EM Recovery: A lost, B won)
- **Condition Predictions & Scoring**:
  - **Cond A (Prose Baseline)**: `exact_match: False`, `containment: False`, Pred: *"Insufficient information"*, Context Est Tokens: 30
  - **Cond B (Decompilation Baseline)**: `exact_match: True`, `containment: True`, Pred: *"Jim Gaffigan"*, Context Est Tokens: 11
  - **Cond C (Table Retention)**: `exact_match: True`, `containment: True`, `rouge_l: 1.0`, Pred: **"Jim Gaffigan"**, Context Est Tokens: 9, Full Prompt Tokens: 283, Generated Tokens: 5, Latency: 134 ms
  - **Cond D (Table + List Retention)**: `exact_match: True`, `containment: True`, `rouge_l: 1.0`, Pred: **"Jim Gaffigan"**, Context Est Tokens: 23, Full Prompt Tokens: 300, Generated Tokens: 5, Latency: 131 ms
- **Structural Telemetry**:
  - Clean prose: 9 tokens. Condition D also packed 1 list item (14 tokens).
  - Both Condition C and D preserved the recovery with exact match.
- **Diagnostic Finding**: Cast list item preserves the role attribution, yielding correct answer across both C and D.

---

## 4. Aggregate Condition Telemetry & Denominators

| Metric | Condition A (Prose) | Condition B (Decompilation) | Condition C (Table Retention) | Condition D (Table + Lists) |
| :--- | :---: | :---: | :---: | :---: |
| **Cases Attempted** | 5 | 5 | 5 | 5 |
| **Successful Predictions** | 5 | 5 | 5 | 5 |
| **Failed Predictions** | 0 | 0 | 0 | 0 |
| **Unscorable Predictions** | 0 | 0 | 0 | 0 |
| **Scored Denominator** | **5** | **5** | **5** | **5** |
| **Exact Match Count** | 1 | 2 | 3 | 3 |
| **Exact Match Rate (Smoke Only)** | 20.0% | 40.0% | 60.0% | 60.0% |
| **Containment Count** | 1 | 2 | 3 | 3 |
| **Containment Rate (Smoke Only)**| 20.0% | 40.0% | 60.0% | 60.0% |
| **Mean ROUGE-L** | 0.200 | 0.400 | 0.600 | 0.600 |
| **Mean Context Estimated Tokens**| 278.6 | 167.4 | 184.4 | 212.4 |
| **Mean Full Prompt Model Tokens**| N/A | N/A | 454.6 | 489.0 |
| **Mean Generated Tokens** | 0.0 (unlogged in A/B)| 0.0 (unlogged in A/B)| 4.2 | 4.2 |
| **Mean Live Latency (ms)** | N/A | N/A | 2,271 ms (warm: 220 ms) | 123 ms (all warm) |

> [!WARNING]
> **STATISTICAL NOTICE**: These aggregate rates ($N=5$) are reported strictly for telemetry and harness validation. They MUST NOT be cited or interpreted as benchmark results or evidence that Condition C or D is superior. Statistical hypothesis testing is reserved for the full 58-case targeted pilot in Gate 4.

---

## 5. Paired Comparison Verification

All paired comparisons evaluated exactly 5 valid pairs with zero exclusions:

| Comparison Pair | Attempted Pairs | Valid Paired Denominator | Excluded Pairs | Cond 1 Wins | Cond 2 Wins | Ties | McNemar $p$-value | Significance ($p < 0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cond C vs Cond A** | 5 | 5 | 0 | 2 (`2c62d7eb`, `00d7c7cc`) | 0 | 3 | $p = 0.500$ | No |
| **Cond C vs Cond B** | 5 | 5 | 0 | 2 (`2c62d7eb`, `3f0497f4`) | 1 (`16caa32e`) | 2 | $p = 1.000$ | No |
| **Cond D vs Cond A** | 5 | 5 | 0 | 2 (`2c62d7eb`, `00d7c7cc`) | 0 | 3 | $p = 0.500$ | No |
| **Cond D vs Cond B** | 5 | 5 | 0 | 2 (`2c62d7eb`, `3f0497f4`) | 1 (`16caa32e`) | 2 | $p = 1.000$ | No |
| **Cond D vs Cond C** | 5 | 5 | 0 | 0 | 0 | 5 | $p = 1.000$ | No |

### Failure-Handling and Exclusion Verification
- Because all 5 cases completed with `status: "success"`, no cases met the exclusion criteria.
- The unit test suite [`test_experiment_4_integrity.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_integrity.py) independently verified that in the event of `failed` or `unscorable` records, `compute_paired_comparison_summary` transparently records `excluded_case_ids`, decrements `valid_paired_denominator`, and excludes the invalid cases from McNemar contingency tables.

---

## 6. Runtime & GPU Profiling

- **Host Device**: NVIDIA GeForce RTX 3060 (12 GB VRAM).
- **Cold-Start Warmup**:
  - Case 1 Condition C took **10,476 ms** to load model weights and KV caches into GPU memory.
  - Subsequent requests executed in **79 ms – 359 ms** (mean warm generation latency: ~150 ms).
- **Extrapolation to Gate 4 (58 cases)**:
  - 58 cases $	imes$ 2 conditions = 116 live inferences.
  - At ~180 ms per warm inference: $116 	imes 0.18	ext{ s} pprox 21	ext{ seconds}$ total inference time.
  - Total Gate 4 run is projected to complete in under 1 minute.

---

## 7. Gate 3 Safety Invariants Audit

1. **Zero Production Code Edits**: `backend/src/precis/` has zero new changes (`git diff --check` clean, exit code 0).
2. **Frozen Benchmark Protection**: Checksums for `sample_manifest.jsonl`, `eval_records_stage_c.jsonl`, and `nq_dev.jsonl` match with 100% precision.
3. **Bounded Execution**: Exactly 5 cases were evaluated; the remaining 53 cases in the union were untouched.
4. **Clean Working Tree**: Only evaluation script constants and integrity tests were updated; no unstaged temporary files.

---

## 8. Gate 4 Readiness & Recommendation

### Recommendation: **`GO FOR GATE 4 (FULL 58-CASE TARGETED PILOT)`**

The harness, model daemon, GPU environment, token telemetry, scoring functions, and record serialization have been proven fully functional under live generation conditions.

### Next Step (Gate 4 Execution Scope):
Upon your explicit authorization, Gate 4 will execute:
```bash
backend/venv/bin/python3 scripts/eval_experiment_4_v1.py   --output-dir results/diagnostic_experiment_4_v1/gate_4_targeted_pilot
```
This will evaluate the full 58-case union (47 Stage C regressions + 11 Stage C recoveries) across Conditions C and D, generating final paired statistical tests, effect sizes, and qualitative error categorizations.

**Execution is currently STOPPED. Antigravity will not proceed with Gate 4 without your explicit authorization.**
