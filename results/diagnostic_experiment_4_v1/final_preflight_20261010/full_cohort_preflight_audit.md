# Précis Experiment 4.3: Full-Cohort Preflight Audit Report

**Document**: `full_cohort_preflight_audit.md`  
**Date**: October 10, 2026  
**Auditor**: Automated Diagnostic Preflight Harness  
**Scope**: Final Plan Audit, Prediction Reuse Reconciliation, and Readiness Assessment  
**Directory**: `results/diagnostic_experiment_4_v1/final_preflight_20261010/`  

---

## 1. Executive Summary & Readiness Verdict

This document presents the final independent preflight audit of the Experiment 4.3 full-cohort confirmatory evaluation plan.

### Overall Status: **READY FOR EXPLICIT AUTHORIZATION**
- **Zero Reuse Discrepancies**: All 31 existing Gate 2 Condition E predictions passed field-level and configuration verification.
- **Exact Cohort Partition**: The 200-case table-bearing manifest partitions exactly into 31 verified reused cases and **169 new generation cases** ($31 + 169 = 200$).
- **Zero Production Risk**: `backend/src/precis/` remains 100% untouched.
- **Execution Invariants Frozen**: Prompt, decoding, model, ceiling, thresholds, and scoring held strictly constant.
- **Proposed Inference Budget**: Exactly **169 model calls** to `qwen2.5-coder:7b`.
- **Execution State**: **PAUSED** (awaiting explicit user authorization).

---

## 2. Review of the Five Experimental Conditions

The full-cohort evaluation compares five conditions across all 200 table-bearing cases:

| Condition | Description | Provenance / Record Source | Execution Requirement |
| :---: | :--- | :--- | :---: |
| **A** | Raw HTML + Coref + Prose SVOA | Frozen Stage C (`eval_records_stage_c.jsonl`) | **0 calls (100% Reused)** |
| **B** | Decompiled Prose + Structured Adapter | Frozen Stage C (`eval_records_stage_c.jsonl`) | **0 calls (100% Reused)** |
| **C** | Structural Table Retention at $\theta=2.0$ | Frozen Exp 4.2 (`eval_records.jsonl`) | **0 calls (100% Reused)** |
| **D** | Structural Table Retention at $\theta=0.0$ | Frozen Exp 4.2 (`eval_records.jsonl`) | **0 calls (100% Reused)** |
| **E** | Structural Retention ($\theta=0.0$) + Candidate Content Lists | Gate 2 Stage 2B (31 cases) + New Inference (169 cases) | **169 calls** |

### Frozen Prediction Set Integrity (Conditions A–D)
All 200 cases in the table-bearing manifest have complete, valid predictions and scores in the historical records:
- **Condition A (Prose Baseline)**: 64 / 200 EM (32.0%)
- **Condition B (Stage C Decompilation)**: 28 / 200 EM (14.0%)
- **Condition C (Table Retention $\theta=2.0$)**: 61 / 200 EM (30.5%)
- **Condition D (Table Retention $\theta=0.0$)**: 99 / 200 EM (49.5%)

Zero model inference will be executed for Conditions A–D.

---

## 3. Cohort Alignment and Partition Audit

### 3.1 Manifest Verification
- Canonical manifest: `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl`.
- Total records: 300 (200 table-bearing, 100 prose-only).
- Table-bearing subset: Exactly **200 cases**.
- Duplicate IDs in manifest: **0**.
- Missing IDs: **0**.

### 3.2 Partition into 31 Reused and 169 New Cases
- **Reused Cohort ($N=31$)**:
  - Exactly matches the 31 cases evaluated in Gate 2 (`stage_2b_eval_records.jsonl`).
  - All 31 cases are verified members of the 200 table-bearing manifest.
  - Case IDs follow the exact monotonic sequence of appearance in the manifest.
  - Zero duplicate IDs.
- **New Generation Cohort ($N=169$)**:
  - Exactly 169 cases from the manifest that were not in Gate 2.
  - Intersection with reused cohort: $\emptyset$ (disjoint sets).
  - Union with reused cohort: Exactly matches the 200 manifest IDs.
  - Total proposed inference count: **169**.

---

## 4. Verification of Prediction Reuse for Condition E

Every single record among the 31 Gate 2 Condition E predictions was audited against the frozen manifest and Experiment 4.2 records.

### Configuration Match Audit
- **Model**: `qwen2.5-coder:7b` (exact string match).
- **Temperature**: `0.0` (greedy decoding, exact match).
- **Top-p**: `0.9` (exact match).
- **Seed**: Declared configuration constant `42` in both runners; deterministic argmax decoding confirmed by `temperature = 0.0`.
- **Max Generation Tokens**: `512` (exact match).
- **Context Ceiling**: `2,048` tokens (exact match; max observed context was 1,037 tokens).
- **Prompt Template**: `CONCISE_PROMPT_TEMPLATE` (exact character-for-character match).
- **Scoring Logic**: Same functions imported from `eval_table_selection_v2.py` (`check_exact_match` and `check_containment`).

### Per-Case Audit Findings
- **31 of 31 cases passed all verification checks** (100% pass rate).
- Question strings, gold answer lists, and primary gold answers match bit-identically across manifest, Exp 4.2, and Gate 2.
- Condition A reference metrics in Gate 2 match Exp 4.2 Condition D scores field-for-field.
- Full details recorded in [`prediction_reuse_audit.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/final_preflight_20261010/prediction_reuse_audit.json).

---

## 5. Denominator Integrity and Fault Tolerance Rules

To eliminate silent record attrition or unrecorded errors:

1. **Strict Non-Imputation Rule**:
   - Each case will be assigned an explicit status: `success`, `failed`, or `unscorable`.
   - Failed or unscorable model responses are **never imputed as False or dropped**.
   - Accuracy denominators will report both the strict full cohort ($N=200$) and the scorable cohort ($N_{\text{scorable}}$).
2. **Idempotent Checkpointing**:
   - The runner will append completed records immediately to disk.
   - If an evaluation is interrupted, re-launching the runner will read existing completed records and execute only the remaining unfinished case IDs.
   - Historical records and completed outputs are protected against overwrites.
3. **Context Ceiling Enforcement**:
   - Context is hard-capped at 2,048 tokens. If total context exceeds this limit, lower-ranked list items are budget-truncated with explicit telemetry flags.

---

## 6. Pre-Registered Endpoints and Statistical Methodology

### 6.1 Primary & Secondary Endpoints
- **Primary Endpoint**: Exact Match (EM) accuracy on the full 200-case cohort.
- **Secondary Endpoint**: Containment accuracy on the full 200-case cohort.
- **Paired Comparisons**:
  * **E vs. D**: Tests incremental value of list extraction over table retention ($\theta=0.0$).
  * **E vs. A**: Tests competitiveness against the clean prose baseline.
  * **E vs. C**: Tests against the initial Stage C threshold ($\theta=2.0$).
  * **E vs. B**: Tests against the Stage C decompilation baseline.

### 6.2 Statistical Testing
- Two-tailed exact McNemar test on paired binary discordant outcomes ($b = \text{wins}$, $c = \text{losses}$).
- Exact Binomial 95% confidence intervals on discordant percentage point differences $(b - c) / N$.
- Significance threshold: $\alpha = 0.05$.

### 6.3 Diagnostic Subgroups (Pre-Declared Exploratory Strata)
1. **Stratum 1 (Stage C Regressions, $N=47$)**: Measures reversal of P1 regressions.
2. **Stratum 2 (Stage C Recoveries, $N=11$)**: Measures preservation of P2 recoveries.
3. **Stratum 3 (Remaining Table-Bearing, $N=142$)**: Broken down into `both_loss` ($N=125$) and `both_win` ($N=17$).
4. **Diagnostic Subset ($N=31$)**: Tracks replication of Gate 2 list-omission recoveries.

---

## 7. Methodological Transparency & Selection Bias Acknowledgment

> [!IMPORTANT]
> ### Methodological Boundary of Gate 2
> In Gate 2, the 31 cases were selected specifically because Condition D failed exact match. Consequently:
> $$\text{Regressions}_{\text{EM}} \le \sum_{i \in \mathcal{S}} \mathbf{1}(\text{EM}_D(i) = \text{True}) = 0$$
> Zero EM regressions on Gate 2 was guaranteed by cohort definition. It does not establish regression safety on cases where Condition D was already successful (99 cases in the 200-case manifest).
> Evaluating all 200 cases is mandatory to determine whether list extraction introduces distractor regressions on those 99 baseline successes.

---

## 8. Resolution and Sensitivity Treatment of Case `895b5134`

As documented in [`ambiguous_case_review.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/final_preflight_20261010/ambiguous_case_review.md):
- Case `895b5134` (*"who has won the most superbowls as a player"*) contains an invalid premise constraint. The source documents Belichick as coach/coordinator and Dahlen as front office. The model answered `"Insufficient information"`, which is factually correct given the context, but scored `False` against NQ gold.
- **Pre-Registered Handling**:
  * **Primary Analysis Cohort ($N=200$)**: Retains `895b5134` to preserve strict fidelity to the frozen manifest.
  * **Sensitivity Analysis Cohort ($N=199$)**: Pre-registers re-estimation with `895b5134` excluded. (Because it is a tie where both Condition D and Condition E output `"Insufficient information"`, discordant pairs and McNemar $p$-values are unchanged).

---

## 9. Final Decision & Execution Readiness

| Preflight Check | Requirement | Result | Status |
| :--- | :--- | :---: | :---: |
| **Manifest Integrity** | 200 unique table-bearing cases | 200 unique | **PASS** |
| **Prediction Reuse** | 31 Gate 2 predictions verified | 31 / 31 verified | **PASS** |
| **Remainder Cohort** | Exactly 169 disjoint cases | 169 unique | **PASS** |
| **Conditions A–D** | 200 frozen records available | 200 / 200 complete | **PASS** |
| **Automated Tests** | 18 integrity & fixture tests | 18 / 18 passed | **PASS** |
| **Production Code** | Zero modifications to `backend/src/precis/` | 0 diffs | **PASS** |
| **Ambiguous Case** | Documented & pre-registered sensitivity | Documented | **PASS** |
| **Model Inferences** | Zero calls executed during preflight | 0 calls | **PASS** |

### **Readiness Status: READY FOR EXPLICIT AUTHORIZATION**

The evaluation harness, cohort partitions, prediction reuse, and statistical plans are completely reconciled and verified. Exactly **169 model calls** will be executed upon receiving your explicit authorization.
