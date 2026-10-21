# Experiment 4.2: Full-Cohort Table-Selection Threshold Evaluation — Preflight Report

**Experiment Identifier**: `diagnostic_experiment_4_2_threshold`  
**Evaluation Scope**: Full Canonical 200-Case Table-Bearing Confirmatory Cohort  
**Date**: 2026-10-10  
**Status**: Preflight Checks Completed — **PASS**  
**Execution Constraints Enforced**: Zero Production Code Modifications (`backend/src/precis/`), Frozen Baseline Predictions Reused, Strict Status Accounting, Zero Data Imputation, Selection Threshold as Sole Manipulated Variable  

---

## 1. Executive Summary & Preflight Verdict

```
+---------------------------------------------------------------------------------------------------------+
|                                      PREFLIGHT VERDICT: PASS                                            |
|                                                                                                         |
|  All 8 mandatory preflight verification checks have PASSED:                                             |
|  1. Frozen Cohort Invariant: Canonical 200-case table-bearing cohort verified bit-for-bit.                |
|  2. Frozen Source Digests: Manifest, Stage C records, and NQ Dev dataset hashes verified bit-identical. |
|  3. Frozen Baseline Provenance: Complete reuse of Condition A (Reference Naive RAG) and Condition B     |
|     (Stage C Decompilation Baseline) predictions directly from verified Stage C records.               |
|  4. Intervention Isolation: Selection threshold theta is the SOLE manipulated variable:                |
|     - Condition C: GFM Table Retention (theta = 2.0, include_lists = False)                             |
|     - Condition D: GFM Table Retention (theta = 0.0, include_lists = False)                             |
|     All other components (representation, row retention, chunking, ceiling, prompt, model) identical.  |
|  5. Configuration Fingerprint: Deterministically computed and registered.                               |
|  6. Ollama Daemon & Model: qwen2.5-coder:7b verified resident in GPU memory; API responsive.           |
|  7. Test Suite Verification: 13/13 new integrity tests, 21/21 Gate 4 tests, 17/17 safety tests passed.   |
|  8. Repository Cleanliness: git diff --check passed with zero whitespace or line-ending violations.     |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Frozen Input Hashes & Verification

Every input file used in this evaluation was verified against its pre-registered SHA-256 digest:

| Artifact Path | Expected SHA-256 Digest | Computed SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** |
| `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** |
| `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** |

---

## 3. Cohort Composition & Frozen Baseline Performance

The evaluation is conducted on the **full canonical 200-case table-bearing confirmatory cohort** (no subsetting or outcome filtering):

- **Total Cases Attempted**: 200
- **Unique Case IDs**: 200 (0 duplicates, 0 missing in dataset)
- **Historical Stage C Classification**:
  - **P1 Regressions** (Cond A correct, Cond B incorrect): 47 cases (23.5%)
  - **P2 Recoveries** (Cond A incorrect, Cond B correct): 11 cases (5.5%)
  - **Concordant Wins** (Cond A correct, Cond B correct): 17 cases (8.5%)
  - **Concordant Losses** (Cond A incorrect, Cond B incorrect): 125 cases (62.5%)
  - **Total**: 47 + 11 + 17 + 125 = 200 cases

### Frozen Baseline Accuracy on the 200-Case Cohort
- **Condition A (Reference Naive RAG)**:
  - Exact Match: 64 / 200 = **32.0%**
  - Containment: 87 / 200 = **43.5%**
- **Condition B (Stage C Decompilation Baseline)**:
  - Exact Match: 28 / 200 = **14.0%**
  - Containment: 39 / 200 = **19.5%**

---

## 4. Experimental Conditions & Controlled Variables

To rigorously isolate the causal impact of the table-selection threshold, Condition C and Condition D share an identical implementation, varying only $\theta$:

| Parameter / Component | Condition C | Condition D | Invariance Status |
| :--- | :--- | :--- | :--- |
| **Table Selection Threshold ($\theta$)** | **2.0** | **0.0** | **Manipulated Variable** |
| **List Retention Policy** | `include_lists = False` | `include_lists = False` | Identical |
| **Table Representation** | Compact GFM Markdown | Compact GFM Markdown | Identical |
| **Header Handling** | Preserved / Synthesized | Preserved / Synthesized | Identical |
| **Row Retention** | 100% of rows in selected tables | 100% of rows in selected tables | Identical |
| **Chunking Policy** | 500 tokens / chunk max | 500 tokens / chunk max | Identical |
| **Context Ceiling** | 2,048 tokens | 2,048 tokens | Identical |
| **Base Model** | `qwen2.5-coder:7b` | `qwen2.5-coder:7b` | Identical |
| **Prompt Template** | `CONCISE_PROMPT_TEMPLATE` | `CONCISE_PROMPT_TEMPLATE` | Identical |
| **Decoding Temperature** | 0.0 | 0.0 | Identical |
| **Decoding Top-p** | 0.9 | 0.9 | Identical |
| **Max Generation Tokens** | 512 | 512 | Identical |
| **Random Seed** | 42 | 42 | Identical |

---

## 5. Execution Pre-Conditions & Environment

1. **Host Environment**: Linux x86_64, NVIDIA GeForce RTX 3060 (12 GB VRAM).
2. **Local Ollama Daemon**: Operational at `http://localhost:11434`. Model `qwen2.5-coder:7b` loaded with digest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`.
3. **Configuration Fingerprint**:
   `7ef5e2c7ceb22031122a07d3faeefdf04cb1e220261805566e9bf70d740c036f`
4. **Output Directory**:
   `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/`
   Created as a new isolated directory with overwrite protection.

---

## 6. Preflight Test Suite Results

All automated test suites executed prior to inference passed with 100% compliance:

```
=================================== TEST RESULTS ===================================
1. scripts/test_experiment_4_2_integrity.py  : 13 / 13 PASSED (4.18s)
2. scripts/test_experiment_4_integrity.py    : 21 / 21 PASSED (4.27s)
3. scripts/test_stage_c_safety_hardening.py  : 17 / 17 PASSED (3.74s)
4. git diff --check                          : PASSED (0 issues)
====================================================================================
```
