# Experiment 4.4: Independent Results Audit and Production-Readiness Review

**Audit Date**: 2026-10-10  
**Evaluator**: Independent Audit Suite  
**Evaluated Target**: `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/`  
**Evaluation Cohort**: Frozen 200-case table-bearing confirmatory cohort  
**Final Audit Verdict**: **AUDIT PASSED: READY FOR EXPLICIT APPROVAL OF A CONTROLLED INTEGRATION**

---

## 1. Executive Summary

An independent, audit-only verification of the Experiment 4.4 full-cohort confirmatory evaluation was conducted. The audit performed bit-level input verification, prediction provenance checking across all 200 cases, independent recalculation of all metrics using canonical scoring functions, exact McNemar paired hypothesis testing, context token distribution analysis, stratified sub-cohort evaluation, sensitivity testing, and safety testing of the list extraction pipeline.

### Key Verified Results
1. **Accuracy Gain**: Condition E (combining structural table retention at $\theta=0.0$ with list extraction) improves Exact Match from **49.5% (99/200)** in Condition D to **54.0% (108/200)**, representing an absolute improvement of **+4.50 percentage points (+9 net wins)**.
2. **Containment Gain**: Answer containment improves from **61.0% (122/200)** in Condition D to **68.5% (137/200)** in Condition E (**+7.50 percentage points, +15 net wins**).
3. **Statistical Significance**: The primary paired comparison (Condition E vs. Condition D) yields **12 wins**, **3 losses**, and **185 ties**. The two-sided exact McNemar test yields $p = 0.035156 < 0.05$ (Statistically Significant), with a 95% Confidence Interval for risk difference of $[+0.76\%, +8.24\%]$ and an odds ratio of $4.00$.
4. **Superiority over Prose Baseline**: Compared to the frozen Condition A prose baseline (32.0% EM, 64/200), Condition E delivers **52 wins vs. 8 losses** ($p = 5.21 \times 10^{-9}$), resolving the multi-week regression dilemma where structural decompilation had lagged the raw text baseline.
5. **Zero Provenance Anomalies**: All 31 reused Gate 2 Stage 2B predictions match stored records bit-for-bit; all 200 Condition D predictions match Experiment 4.2 records bit-for-bit; 169 cases were newly generated under identical canonical hyperparameters; exactly 0 score mismatches occurred across all 1,000 evaluations.
6. **Zero Context Violations**: Context lengths remain strictly controlled (mean 409 tokens, median 281 tokens, max 2046 tokens). Exactly 0/200 cases exceeded the 2048-token context ceiling.
7. **Failure Modes Audited**: The 3 observed regressions against Condition D (`3f5983b2`, `ef634417`, `8f1f9bd9`) were thoroughly diagnosed: 2 were caused by list-introduced distractor/salience interference, while 1 was a formatting variation preserving containment.

---

## 2. Input and Artifact Verification

All input datasets, historical baselines, and evaluation records were verified against their recorded cryptographic SHA-256 hashes:

| File Name | Relative Path | Verified SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- |
| `sample_manifest.jsonl` | `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** |
| `eval_records_stage_c.jsonl` | `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** |
| `nq_dev.jsonl` | `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** |
| `eval_records_exp4_2.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl` | `d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0` | **MATCH** |
| `failure_inventory_gate1.jsonl` | `results/diagnostic_experiment_4_v1/failure_attribution_20261010/failure_inventory.jsonl` | `748037a0a0d718b684f1021487476f2b2fd3692103aac44c8b556255b84ef08c` | **MATCH** |
| `gate2_stage_2b_eval_records.jsonl` | `results/diagnostic_experiment_4_v1/gate_2_list_extraction_20261010/stage_2b_eval_records.jsonl` | `417fab9df822674e128c052fae2ad5153a9b8f96faf6e9995760eec334fc9e4f` | **MATCH** |
| `eval_records_exp4_4.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/eval_records.jsonl` | `73df76085485fbead2b67fa6a783be3c10420edbf8d9afa9c42203d6737f2c47` | **MATCH** |
| `aggregate_summary.json` | `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/aggregate_summary.json` | `180acec1e14bac3f0b8b4ee9c462a46446b29aaf21c701f627adfd52a2c8469c` | **MATCH** |
| `paired_comparisons.json` | `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/paired_comparisons.json` | `8f9b7a112a0eed6c1de7d27c411cc43f5d580eab7e099c578c50b6c431502b42` | **MATCH** |
| `regression_audit.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/regression_audit.jsonl` | `12365a4cdb608ec2bfdc70347571d2ecda38ce05a27c9adf6f05d831a299d40d` | **MATCH** |
| `evaluation_report.md` | `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/evaluation_report.md` | `0c7d14920f00452b0a6a4b631ba7516bbb1067211ab55fd4606b7a790595fbb1` | **MATCH** |

---

## 3. Prediction Provenance and Score Recomputation

An automated audit script (`scripts/audit_experiment_4_4.py`) was executed to inspect every evaluation record independently:
- **Total Records Checked**: 200 case records (plus 1 valid run header record).
- **Gate 2 Reused Cases**: Exactly 31 records. Bit-for-bit comparison of predicted answers against `gate2_stage_2b_eval_records.jsonl` confirmed **31/31 exact matches** (0 mismatches, 0 discrepancies).
- **Experiment 4.4 Generated Cases**: Exactly 169 records. Provenance metadata correctly marked `reused: False, source: 'live_generation'`.
- **Condition D Provenance**: Exactly 200 records. Bit-for-bit comparison against `full_cohort_threshold_20261010/eval_records.jsonl` confirmed **200/200 exact matches** (0 mismatches).
- **Independent Score Evaluation**: Predictions across all 5 conditions (1,000 condition predictions, 2,000 evaluations) were re-evaluated with `check_exact_match` and `check_containment` from `eval_table_selection_v2.py`.
  - **Exact Match Mismatches**: **0**
  - **Containment Mismatches**: **0**
  - **Provenance Anomalies**: **0**

---

## 4. Recomputed Empirical Confirmatory Rates ($N=200$)

The verified performance metrics for all experimental conditions across the full 200-case cohort are as follows:

| Condition | Configuration | Exact Match (Count) | Exact Match (%) | Containment (Count) | Containment (%) | Mean Context Tokens | Median Context Tokens | Max Context Tokens | Ceiling Violations ($>2048$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Condition A** | Prose Baseline | 64 / 200 | 32.0% | 87 / 200 | 43.5% | 618.8 | 367.0 | 2048 | 0 |
| **Condition B** | Stage C Decompilation | 28 / 200 | 14.0% | 39 / 200 | 19.5% | 155.4 | 63.0 | 1778 | 0 |
| **Condition C** | Retention ($\theta=2.0$) | 61 / 200 | 30.5% | 79 / 200 | 39.5% | 195.4 | 79.5 | 1161 | 0 |
| **Condition D** | Retention ($\theta=0.0$) | 99 / 200 | 49.5% | 122 / 200 | 61.0% | 326.4 | 235.0 | 1242 | 0 |
| **Condition E** | Tables ($\theta=0.0$) + Lists | **108 / 200** | **54.0%** | **137 / 200** | **68.5%** | **409.4** | **281.0** | **2046** | **0** |

---

## 5. Statistical Hypothesis Testing & Paired Discordant Analysis

Paired comparisons were recomputed directly from the 200 matched cases using exact two-sided binomial tests (McNemar's test) and 95% confidence intervals for risk difference:

### 5.1 Primary Intervention: Condition E vs. Condition D

Contingency table for Exact Match ($N=200$):
$$\begin{array}{c|cc|c}
& \text{Cond D: True} & \text{Cond D: False} & \text{Total} \\
\hline
\text{Cond E: True} & 96 & 12 & 108 \\
\text{Cond E: False} & 3 & 89 & 92 \\
\hline
\text{Total} & 99 & 101 & 200
\end{array}$$

- **Wins ($b$)**: 12
- **Losses ($c$)**: 3
- **Ties ($a + d$)**: 185 ($96 + 89$)
- **Net Delta**: $+9$ wins (**$+4.50$ percentage points**)
- **Exact McNemar $p$-value**: **$p = 0.03515625 < 0.05$ (Statistically Significant)**
- **Odds Ratio**: $4.00$
- **95% Confidence Interval for Risk Difference**: $[+0.76\%, +8.24\%]$

Contingency table for Containment ($N=200$):
$$\begin{array}{c|cc|c}
& \text{Cond D: True} & \text{Cond D: False} & \text{Total} \\
\hline
\text{Cond E: True} & 120 & 17 & 137 \\
\text{Cond E: False} & 2 & 61 & 63 \\
\hline
\text{Total} & 122 & 78 & 200
\end{array}$$

- **Wins ($b$)**: 17
- **Losses ($c$)**: 2
- **Net Delta**: $+15$ wins (**$+7.50$ percentage points**)
- **Exact McNemar $p$-value**: **$p = 0.000729 < 0.001$ (Highly Significant)**
- **95% Confidence Interval for Risk Difference**: $[+3.36\%, +11.64\%]$

### 5.2 Benchmark Comparison: Condition E vs. Condition A (Prose Baseline)

- **Exact Match Contingency**: Both True: 56, E-only (Wins): 52, A-only (Losses): 8, Both False: 84
- **Net Delta**: $+44$ wins (**$+22.00$ percentage points**)
- **Exact McNemar $p$-value**: **$p = 5.21 \times 10^{-9}$ (Decisively Significant)**
- **95% Confidence Interval**: $[+15.05\%, +28.95\%]$

### 5.3 Summary of All Paired Comparisons (Exact Match)

| Paired Comparison | Wins | Losses | Ties | Net Delta | Odds Ratio | Exact McNemar $p$ | Significant ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Condition E vs. Condition D** | **12** | **3** | **185** | **+9 (+4.50 pp)** | **4.00** | **0.035156** | **YES** |
| **Condition E vs. Condition A** | 52 | 8 | 140 | +44 (+22.00 pp) | 6.50 | $5.21 \times 10^{-9}$ | **YES** |
| **Condition E vs. Condition C** | 48 | 1 | 151 | +47 (+23.50 pp) | 48.00 | $1.78 \times 10^{-13}$ | **YES** |
| **Condition E vs. Condition B** | 85 | 5 | 110 | +80 (+40.00 pp) | 17.00 | $7.53 \times 10^{-20}$ | **YES** |
| **Condition D vs. Condition A** | 48 | 13 | 139 | +35 (+17.50 pp) | 3.69 | $7.13 \times 10^{-6}$ | **YES** |
| **Condition D vs. Condition C** | 38 | 0 | 162 | +38 (+19.00 pp) | $\infty$ | $7.28 \times 10^{-12}$ | **YES** |
| **Condition D vs. Condition B** | 79 | 8 | 113 | +71 (+35.50 pp) | 9.88 | $3.58 \times 10^{-16}$ | **YES** |

---

## 6. Strata Breakdown

To determine whether gains are localized or generalized, the cohort was decomposed into three historical Stage C strata and the diagnostic Gate 2 partition:

| Sub-Cohort | Cases ($N$) | Cond A EM | Cond B EM | Cond C EM | Cond D EM | Cond E EM | E vs D Net Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stratum 1** (Stage C Regressions) | 47 | 47 (100%) | 0 (0.0%) | 21 (44.7%) | 37 (78.7%) | **41 (87.2%)** | **+4 (+8.5 pp)** |
| **Stratum 2** (Stage C Recoveries) | 11 | 0 (0.0%) | 11 (100%) | 8 (72.7%) | 8 (72.7%) | **8 (72.7%)** | **0 (0.0 pp)** |
| **Stratum 3** (Remaining Cases) | 142 | 17 (12.0%) | 17 (12.0%) | 32 (22.5%) | 54 (38.0%) | **59 (41.5%)** | **+5 (+3.5 pp)** |
| **Diagnostic Gate 2 Target Cohort** | 31 | 7 (22.6%) | 5 (16.1%) | 0 (0.0%) | 0 (0.0%) | **11 (35.5%)** | **+11 (+35.5 pp)** |
| **Non-Gate 2 Cases** | 169 | 57 (33.7%) | 23 (13.6%) | 61 (36.1%) | 99 (58.6%) | **97 (57.4%)** | **-2 (-1.2 pp)** |

### Strata Findings
1. **Stratum 1 Recovery**: Condition E achieves **41 / 47 (87.2%)** on the historical P1 regressions, surpassing Condition D (37/47) and approaching Condition A's 100%.
2. **Stratum 2 Stability**: Condition E retains **8 / 11 (72.7%)** of Stage C recoveries without introducing any regressions in this stratum.
3. **Generalization (Stratum 3)**: Condition E achieves **59 / 142 (41.5%)**, outperforming Condition D (54/142) and vastly outperforming Condition A (17/142).
4. **Targeted vs Non-Targeted Split**: In the 31 cases specifically targeted for list omissions, Condition E generated **11 wins and 0 losses** (+11 net). Across the remaining 169 cases, Condition E had **1 win and 3 losses** (-2 net), demonstrating that while list extraction is overwhelmingly positive on list-bearing omissions, unconstrained list appending on non-omission documents carries a mild distractor risk (2 cases).

---

## 7. Sensitivity Analysis: Ambiguous Case `895b5134`

Case `895b5134173847ff8837c187a367cde0` was identified during preflight audits as having ambiguous gold references.
- **Observed Predictions**: Both Condition D and Condition E predicted `"Insufficient information"` (Exact Match: **False** in both).
- **Discordant Impact**: Because both conditions failed identically, this case constitutes a concordant tie ($d$). It contributes 0 to the discordant pairs ($b$ and $c$).
- **Metrics on $N=199$**:
  - Condition E EM: **108 / 199 (54.27%)**
  - Condition D EM: **99 / 199 (49.75%)**
  - Concordant Pairs: 184; Discordant Pairs: 15 ($b=12, c=3$)
  - Exact McNemar $p$-value: **$p = 0.03515625$ (Unchanged, Statistically Significant)**
- **Conclusion**: The empirical findings and statistical significance are 100% robust to the inclusion or exclusion of this ambiguous case.

---

## 8. Extractor Safety & Regression Audit Summary

Detailed analyses are provided in [regression_review.md](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/regression_review.md) and [extractor_safety_review.md](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/extractor_safety_review.md).

### Summary of Regressions:
1. `3f5983b2`: Extracted nested sub-list `Deputy: Agnes Tjongarero` bound to the minister's heading, causing ambiguity that prompted the model to answer "Insufficient information".
2. `ef634417`: Extracted songwriters from an infobox table into a standalone trailing list, inducing recency bias where the LLM answered with the human songwriters rather than the performing band.
3. `8f1f9bd9`: Extracted 0 lists (context was identical to Condition D); model answered `Aramaic: twin` instead of `Twin`, preserving containment.

### Safety Test Suite:
All **15/15 unit and safety tests** in `scripts/test_experiment_4_4_audit_extractor.py` passed, verifying:
- Deterministic markdown rendering of key-value and ordered/unordered lists.
- Resilient recovery from unclosed tags and malformed markup.
- Guaranteed precedence of clean prose over structured lists.
- Zero context ceiling violations across realistic document lengths.

---

## 9. Production-Readiness Assessment & Audit Verdict

### Production Readiness Criteria Matrix

| Criterion | Requirement | Result | Evaluation |
| :--- | :--- | :--- | :---: |
| **Statistical Efficacy** | $p < 0.05$ on confirmatory cohort | $p = 0.035156$ ($+4.50$ pp EM, $+7.50$ pp Cont) | **PASS** |
| **Benchmark Recovery** | Outperform frozen prose baseline | $54.0\%$ vs $32.0\%$ ($p = 5.21 \times 10^{-9}$) | **PASS** |
| **Provenance Integrity** | 100% auditable provenance, zero fabrications | 31/31 Gate 2 matches, 200/200 Exp 4.2 matches | **PASS** |
| **Safety Invariants** | Zero production edits, zero ceiling breaches | 0 edits to `backend/src/precis/`, max 2046 tokens | **PASS** |
| **Robustness Under Stress**| Pass comprehensive parser/safety tests | 15/15 safety tests passed | **PASS** |
| **Distractor Risk Control** | Quantified regression rate and mitigation path | 3 losses vs 12 wins (4.0:1 ratio); deduplication path | **PASS** |

### Final Audit Verdict

$$\mathbf{AUDIT\ PASSED:\ READY\ FOR\ EXPLICIT\ APPROVAL\ OF\ A\ CONTROLLED\ INTEGRATION}$$

---

## 10. Recommended Controlled Integration Plan

The auditor recommends that any future production integration follow these strict guardrails:
1. **Feature Flagging**: Introduce list extraction under a configurable feature flag (e.g., `ENABLE_STRUCTURAL_LIST_RETENTION=true`), keeping the existing fallback path available.
2. **Table-List Deduplication Guard**: Before appending an extracted list section, verify that its tokens do not heavily overlap ($> 80\%$) with already retained table cells. This simple guard prevents regressions of the `ef634417` type.
3. **Exact Token Deductions**: Update the partial packing loop to deduct section header tokens (~10 tokens) from available budget headroom.
4. **Staged Production Verification**: Test the integrated pipeline on unit tests and an end-to-end smoke test before enabling the flag by default.
