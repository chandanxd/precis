# Experiment 4.2: Full-Cohort Table-Selection Threshold Evaluation — Final Investigation Report

**Experiment Identifier**: `diagnostic_experiment_4_2_threshold`  
**Evaluation Scope**: Full Canonical 200-Case Table-Bearing Confirmatory Stratum (Précis Experiment 3)  
**Date**: 2026-10-10  
**Status**: Completed — **Decisive Experimental Finding**  
**Execution Constraints Enforced**: Zero Production Code Modifications (`backend/src/precis/`), Frozen Baseline Predictions Reused, Strict Status Accounting, Zero Data Imputation, Selection Threshold as Sole Manipulated Variable  

---

## 1. Executive Summary & Core Diagnostic Findings

Experiment 4.2 evaluated the causal impact of relaxing the query-aware table selection threshold from $\theta = 2.0$ (Condition C) to $\theta = 0.0$ (Condition D) across the complete, frozen 200-case table-bearing confirmatory cohort from Précis Experiment 3. Condition A (Reference Naive RAG) and Condition B (Stage C SVOA Decompilation) predictions were frozen and reused directly from verified historical records.

```
+----------------------------------------------------------------------------------------------------------------+
|                                      EXPERIMENT 4.2 EXECUTIVE VERDICT                                         |
|                                                                                                                |
|  1. Decisive Impact of Threshold Relaxation (Condition D vs Condition C):                                     |
|     - Relaxing table selection from theta=2.0 to theta=0.0 dramatically improves accuracy:                      |
|       * Exact Match (EM): 99/200 (49.5%) vs 61/200 (30.5%) — Net Wins: +38 (+19.0 pp), p = 7.28e-12             |
|       * Answer Containment: 122/200 (61.0%) vs 79/200 (39.5%) — Net Wins: +43 (+21.5 pp), p = 2.27e-13         |
|       * Zero Regressions: Condition D introduced EXACTLY 0 EM regressions and 0 Containment regressions        |
|         relative to Condition C (Discordant pairs: 38 D-wins vs 0 C-wins).                                     |
|                                                                                                                |
|  2. Decisive Superiority Over Original Prose Baseline (Condition D vs Condition A):                            |
|     - Condition D significantly and decisively outperforms the original reference Naive RAG baseline:         |
|       * Exact Match (EM): 99/200 (49.5%) vs 64/200 (32.0%) — Net Wins: +35 (+17.5 pp), p = 1.57e-05             |
|       * Answer Containment: 122/200 (61.0%) vs 87/200 (43.5%) — Net Wins: +35 (+17.5 pp), p = 1.03e-04         |
|       * Odds Ratio: 3.33 (50 paired wins vs 15 paired losses against Condition A).                             |
|                                                                                                                |
|  3. Context Economy Maintained:                                                                                |
|     - Mean context size under Condition D is 326.4 estimated tokens (median 235.0, P95 966.0).                  |
|     - This represents a 47.3% token reduction relative to Condition A (618.8 mean tokens),                    |
|       with ZERO context ceiling violations (>2,048 tokens).                                                    |
|                                                                                                                |
|  4. Forensic Root Cause Shift:                                                                                 |
|     - Table selection failures are COMPLETELY ELIMINATED under Condition D (59 cases in C -> 0 cases in D).    |
|     - Residual failure surface is now dominated by:                                                            |
|       * Generation / Reasoning Over Retained Tables: 44 cases (22.0%)                                          |
|       * List / Prose Extraction Omissions (No table in source): 34 cases (17.0%)                               |
|       * Surface Form / Lexical Normalization Mismatches: 23 cases (11.5%)                                      |
+----------------------------------------------------------------------------------------------------------------+
```

---

## 2. Preflight Audit & Input Provenance Verification

All input files and experimental preconditions were verified bit-for-bit prior to inference:

| Artifact Path | Expected SHA-256 Digest | Measured SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** |
| `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** |
| `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** |

- **Configuration Fingerprint**: `81aacc9186b973dc90abe728d37ad5a7337c6c7de7b463a62e3f16135ebae5c7`
- **Model Hardware & Daemon**: NVIDIA GeForce RTX 3060 (12 GB VRAM), `qwen2.5-coder:7b` resident in GPU memory; 0 connection drops, 0 timeouts.
- **Harness & Integrity Test Suites**:
  - `scripts/test_experiment_4_2_integrity.py`: 13/13 passed.
  - `scripts/test_experiment_4_integrity.py`: 21/21 passed.
  - `scripts/test_stage_c_safety_hardening.py`: 17/17 passed.
  - `git diff --check`: 0 issues.

---

## 3. Full-Cohort Accuracy & Telemetry Results

All 200 cases were successfully evaluated across all conditions with zero operational failures (`failed=0`, `unscorable=0`). All accuracy metrics are reported over the true scored denominator ($N=200$).

| Metric / Attribute | Condition A (Prose Baseline) | Condition B (Stage C SVOA) | Condition C (Table Retention $\theta=2.0$) | Condition D (Table Retention $\theta=0.0$) |
| :--- | :---: | :---: | :---: | :---: |
| **Cases Attempted / Scored** | 200 / 200 | 200 / 200 | 200 / 200 | 200 / 200 |
| **Execution Status** | 100% Success | 100% Success | 100% Success | 100% Success |
| **Exact Match (EM) Count** | 64 | 28 | 61 | **99** |
| **Exact Match (EM) Rate** | **32.0%** | **14.0%** | **30.5%** | **49.5%** |
| **Answer Containment Count** | 87 | 39 | 79 | **122** |
| **Answer Containment Rate** | **43.5%** | **19.5%** | **39.5%** | **61.0%** |
| **Mean ROUGE-L** | — | — | 0.3726 | **0.5846** |
| **Median ROUGE-L** | — | — | 0.0000 | **0.8286** |
| **Context Tokens (Mean)** | 618.8 | 155.4 | 195.4 | **326.4** |
| **Context Tokens (Median)** | 367.0 | 63.0 | 79.5 | **235.0** |
| **Context Tokens (P95)** | 2,041.0 | 549.0 | 809.0 | **966.0** |
| **Full Prompt Tokens (Mean)** | — | — | 506.6 | **672.5** |
| **Full Prompt Tokens (Median)**| — | — | 347.5 | **538.5** |
| **Full Prompt Tokens (P95)** | — | — | 1,351.0 | **1,488.0** |
| **Mean Generated Tokens** | — | — | 5.9 | 6.7 |
| **Mean Latency (ms)** | — | — | 278.1 ms | 241.0 ms |
| **Empty Context Count (Rate)**| 2 (1.0%) | 71 (35.5%) | 90 (45.0%) | **31 (15.5%)** |
| **Evidence in Context (Rate)**| — | — | 108 (54.0%) | **167 (83.5%)** |

> [!NOTE]
> For Condition A and Condition B, prompt tokens, generated tokens, and ROUGE-L were not tracked in the historical Stage C logs; those fields are preserved as null rather than imputed.

---

## 4. Paired Statistical Comparisons

Paired tests were computed strictly over identical cases ($N=200$). Because all cases had `status == "success"`, 0 cases were excluded from paired comparisons.

### A. Exact Match (EM) Paired Comparisons

| Comparison Pair | Relationship Tested | Cond 1 Wins ($b$) | Cond 2 Wins ($c$) | Ties ($a+d$) | Net Wins ($b-c$) | Absolute $\Delta$ pp | Odds Ratio | 95% Confidence Interval | McNemar Exact $p$-value | Significance ($\alpha=0.05$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **D vs C** | **Threshold Relaxation ($\theta=0.0$ vs $\theta=2.0$)** | **38** | **0** | **162** | **+38** | **+19.0 pp** | **$\infty$** | **[+13.56%, +24.44%]** | **$7.28 \times 10^{-12}$** | **YES ($p < 10^{-11}$)** |
| **D vs A** | **Relaxed Retention vs Naive Prose Baseline** | **50** | **15** | **135** | **+35** | **+17.5 pp** | **3.33** | **[+9.98%, +25.02%]** | **$1.57 \times 10^{-5}$** | **YES ($p < 10^{-4}$)** |
| **D vs B** | **Relaxed Retention vs Stage C SVOA** | **79** | **8** | **113** | **+71** | **+35.5 pp** | **9.88** | **[+27.80%, +43.20%]** | **$8.38 \times 10^{-16}$** | **YES ($p < 10^{-15}$)** |
| **C vs B** | **Standard Retention vs Stage C SVOA** | **41** | **8** | **151** | **+33** | **+16.5 pp** | **5.13** | **[+10.03%, +22.97%]** | **$1.96 \times 10^{-6}$** | **YES ($p < 10^{-5}$)** |
| **C vs A** | **Standard Retention vs Naive Prose Baseline** | **28** | **31** | **141** | **-3** | **-1.5 pp** | **0.90** | **[-9.02%, +6.02%]** | **0.7948** | **NO ($p \approx 0.79$)** |

### B. Answer Containment Paired Comparisons

| Comparison Pair | Relationship Tested | Cond 1 Wins ($b$) | Cond 2 Wins ($c$) | Ties ($a+d$) | Net Wins ($b-c$) | Absolute $\Delta$ pp | Odds Ratio | 95% Confidence Interval | McNemar Exact $p$-value | Significance ($\alpha=0.05$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **D vs C** | **Threshold Relaxation ($\theta=0.0$ vs $\theta=2.0$)** | **43** | **0** | **157** | **+43** | **+21.5 pp** | **$\infty$** | **[+15.81%, +27.19%]** | **$2.27 \times 10^{-13}$** | **YES ($p < 10^{-12}$)** |
| **D vs A** | **Relaxed Retention vs Naive Prose Baseline** | **57** | **22** | **121** | **+35** | **+17.5 pp** | **2.59** | **[+9.13%, +25.87%]** | **$1.03 \times 10^{-4}$** | **YES ($p < 10^{-3}$)** |
| **D vs B** | **Relaxed Retention vs Stage C SVOA** | **93** | **10** | **97** | **+83** | **+41.5 pp** | **9.30** | **[+33.39%, +49.61%]** | **$5.20 \times 10^{-18}$** | **YES ($p < 10^{-17}$)** |
| **C vs B** | **Standard Retention vs Stage C SVOA** | **50** | **10** | **140** | **+40** | **+20.0 pp** | **5.00** | **[+12.93%, +27.07%]** | **$1.62 \times 10^{-7}$** | **YES ($p < 10^{-6}$)** |
| **C vs A** | **Standard Retention vs Naive Prose Baseline** | **31** | **39** | **130** | **-8** | **-4.0 pp** | **0.79** | **[-12.18%, +4.18%]** | **0.4030** | **NO ($p \approx 0.40$)** |

---

## 5. Regression & Recovery Forensic Audit

### A. Stage C Historical Cohort Breakdown

The 200 cases were historically partitioned by their Stage C outcome into four groups. Here is how Condition C and Condition D performed across each group:

1. **Stage C P1 Regressions (Cond A Correct, Cond B Incorrect, $N=47$)**:
   - Condition C recovered: **21 / 47 (44.7%)**
   - Condition D recovered: **37 / 47 (78.7%)**
   - **Net recovery gain from $\theta=0.0$**: **+16 additional cases recovered** (+34.0 pp).
   - Only 10 P1 regressions remain unrecovered in Condition D (6 generation/reasoning errors, 4 extraction omissions).

2. **Stage C P2 Recoveries (Cond A Incorrect, Cond B Correct, $N=11$)**:
   - Condition C preserved: **8 / 11 (72.7%)**
   - Condition D preserved: **8 / 11 (72.7%)**
   - Zero degradation in P2 preservation between Condition C and Condition D.

3. **Stage C Both Win (Cond A Correct, Cond B Correct, $N=17$)**:
   - Condition C correct: **12 / 17 (70.6%)**
   - Condition D correct: **12 / 17 (70.6%)**
   - Identical performance between C and D.

4. **Stage C Both Loss (Cond A Incorrect, Cond B Incorrect, $N=125$)**:
   - Condition C won: **20 / 125 (16.0%)**
   - Condition D won: **42 / 125 (33.6%)**
   - **Net win gain from $\theta=0.0$**: **+22 brand new recoveries** on historically hopeless cases!

### B. Transitions Between Condition D and Condition C

- **Cases where D fixes a C failure (`d_fixes_c`)**: **38 cases (19.0%)**
- **Cases where D regresses a C success (`d_regresses_c`)**: **0 cases (0.0%)**
- **Monotonic improvement property**: Lowering the threshold to $\theta=0.0$ produced purely monotonic improvements with zero accuracy regressions.

---

## 6. Evidence Pathway Analysis & Failure Taxonomy

By tracing the answer string from the raw document through extraction, selection, context packing, and generation, every failure is definitively categorized:

```
Total Table-Bearing Cases (N = 200)
│
├── Gold Evidence in Source HTML: 200 / 200 (100.0%)
│   │
│   ├── Evidence in Extracted Document Tables: 164 / 200 (82.0%)
│   │   │
│   │   ├── Condition C (theta = 2.0):
│   │   │   ├── Table Selected: 105 / 164 (64.0%)
│   │   │   └── Table Rejected (SELECTION_FAILURE): 59 / 164 (36.0%) ───> 59 cases failed due to theta=2.0
│   │   │
│   │   └── Condition D (theta = 0.0):
│   │       ├── Table Selected: 164 / 164 (100.0%)
│   │       └── Table Rejected (SELECTION_FAILURE): 0 / 164 (0.0%) ─────> ZERO selection failures!
│   │
│   └── Evidence in Prose / Lists Only (EXTRACTION_OMISSION): 36 / 200 (18.0%)
│       (Source document contained tables, but the answer resided in unextracted text or lists)
```

### Complete Failure Breakdown Across the Full Cohort

| Failure Classification | Description | Condition C Count (Rate) | Condition D Count (Rate) | Impact of $\theta=0.0$ |
| :--- | :--- | :---: | :---: | :---: |
| **`NONE_CORRECT`** | Model answered correctly (EM = True) | 61 (30.5%) | **99 (49.5%)** | **+38 correct answers** |
| **`SELECTION_FAILURE`** | Table contained evidence, but was rejected by threshold $\theta$ | 59 (29.5%) | **0 (0.0%)** | **ELIMINATED (-59 cases)** |
| **`GENERATION_REASONING_FAILURE`** | Table in context, but model produced wrong row/distractor | 28 (14.0%) | 44 (22.0%) | Shifted from selection to generation (+16) |
| **`EXTRACTION_OMISSION`** | Evidence in source, but absent from extracted tables (in lists/prose) | 34 (17.0%) | 34 (17.0%) | Unchanged (structural limit of table-only) |
| **`SURFACE_FORM_MISMATCH`** | Model contained gold answer (Containment=True), but EM=False | 18 (9.0%) | 23 (11.5%) | Phrasing / normalization variance (+5) |
| **`PACKING_FAILURE`** | Selected table truncated by 2,048 token context ceiling | 0 (0.0%) | 0 (0.0%) | 0 ceiling truncations in either condition |
| **`NO_EVIDENCE_IN_SOURCE`** | Gold answer absent from raw HTML document | 0 (0.0%) | 0 (0.0%) | 100% source sufficiency |

---

## 7. Context Efficiency and Ceiling Compliance

1. **Context Ceiling Invariant**:
   - Context ceiling: 2,048 estimated tokens.
   - Condition C maximum packed tokens: **1,161 tokens** (0 violations).
   - Condition D maximum packed tokens: **1,242 tokens** (0 violations).
   - 100% compliance with the context budget across all 200 cases.

2. **Context Size vs Baseline**:
   - Condition A (Prose Baseline): Mean = **618.8 tokens**, Median = **367.0 tokens**.
   - Condition C (Retention $\theta=2.0$): Mean = **195.4 tokens** (-68.4% vs A).
   - Condition D (Retention $\theta=0.0$): Mean = **326.4 tokens** (-47.3% vs A).
   - Condition D achieves higher accuracy (49.5% vs 32.0%) while cutting context size nearly in half!

3. **Prompt and Inference Latency**:
   - Mean latency under Condition D: **241.0 ms** per query on local RTX 3060.
   - Mean generation length: **6.7 tokens** (highly extractive, compliant with conciseness guidelines).

---

## 8. Final Decision Report

The 7 mandatory evaluation questions are answered below based strictly on measured evidence:

| Question | Measured Empirical Finding | Interpretive Verdict |
| :--- | :--- | :--- |
| **1. Did $\theta=0.0$ improve Exact Match relative to $\theta=2.0$?** | **YES.** EM increased from 30.5% (61/200) to **49.5% (99/200)**. Net change: **+38 wins, 0 losses** ($p = 7.28 \times 10^{-12}$). | Decisive, statistically overwhelming improvement. |
| **2. Did it improve containment?** | **YES.** Containment increased from 39.5% (79/200) to **61.0% (122/200)**. Net change: **+43 wins, 0 losses** ($p = 2.27 \times 10^{-13}$). | Decisive improvement in evidence accessibility. |
| **3. What accuracy regressions did it introduce?** | **ZERO.** Condition D introduced **0 EM regressions** and **0 containment regressions** relative to Condition C. | Relaxing $\theta$ had purely monotonic upside on this cohort. |
| **4. What happened to context and prompt-token costs?** | Mean context tokens increased from 195.4 to 326.4 (+131.0 tokens). Mean full-prompt tokens increased from 506.6 to 672.5 (+165.9 tokens). | Modest token increase that remains 47.3% smaller than Condition A (618.8 tokens). |
| **5. Did either condition beat the original prose baseline on the full cohort?** | **YES. Condition D beat Condition A decisively**: 49.5% EM vs 32.0% EM (+17.5 pp, $p = 1.57 \times 10^{-5}$); 61.0% vs 43.5% Containment ($p = 1.03 \times 10^{-4}$). Condition C did not ($p = 0.79$). | First structured retention condition to significantly beat the prose baseline. |
| **6. Which failure category remains the dominant blocker?** | Table selection failure is **completely eliminated (0 cases)**. The dominant remaining blocker is **`GENERATION_REASONING_FAILURE` (44 cases, 22.0%)**, followed by **`EXTRACTION_OMISSION` (34 cases, 17.0%)**. | Bottleneck has shifted from retrieval/selection to reasoning over distractor rows. |
| **7. Is the evidence sufficient to justify another isolated experiment?** | **YES.** The evidence justifies testing targeted row-level prioritization and list integration to address the remaining 78 failure cases. | Full empirical justification established. |

---

## 9. Final Verification & Artifact Hashes

The generated diagnostic artifacts are stored in `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/`:

| Artifact Name | Relative Path | SHA-256 Digest |
| :--- | :--- | :--- |
| `preflight_report.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/preflight_report.md` | *See Manifest* |
| `eval_records.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl` | *Generated* |
| `aggregate_summary.json` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/aggregate_summary.json` | *Generated* |
| `paired_comparisons.json` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/paired_comparisons.json` | *Generated* |
| `regression_recovery_audit.jsonl`| `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/regression_recovery_audit.jsonl`| *Generated* |
| `investigation_report.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/investigation_report.md` | *Current Document* |
| `walkthrough.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/walkthrough.md` | *Generated* |
