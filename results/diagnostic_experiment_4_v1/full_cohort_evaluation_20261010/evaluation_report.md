# Précis Experiment 4.4: Full-Cohort Confirmatory Evaluation Report

**Document**: `evaluation_report.md`  
**Date**: October 10, 2026  
**Cohort**: Frozen 200-Case Table-Bearing Confirmatory Cohort  
**Evaluator**: `scripts/eval_experiment_4_4_full_cohort.py`  
**Directory**: `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/`  

---

## 1. Executive Summary

This report documents the results of the **full-cohort confirmatory evaluation** on the canonical 200-case table-bearing cohort. The objective was to determine whether combining structural table retention at $\theta=0.0$ with an isolated content-list extractor (**Condition E**) delivers statistically significant, regression-safe improvements over table retention alone (**Condition D**) and the baseline clean prose system (**Condition A**).

### Primary Findings
1. **New Peak Accuracy**:
   - **Condition E (Tables + Lists)** achieved **108 / 200 Exact Match (54.0%)** and **137 / 200 Containment (68.5%)**.
   - This represents the **highest end-to-end question answering accuracy** achieved across all Précis experiments to date.
2. **Statistically Significant Gain over Condition D (Tables Only)**:
   - Condition E gained **+9 net Exact Match wins** ($+4.5$ percentage points, shifting EM from 49.5% to 54.0%).
   - Paired discordant transitions: **12 wins, 3 losses, 185 ties** (win-to-loss ratio: **4.0x**).
   - Exact two-tailed McNemar test: **$p = 0.03515625$** ($p < 0.05$, statistically significant).
   - 95% Confidence Interval for net difference: **$[+0.76\%, +8.24\%]$**.
3. **Decisive Superiority over the Clean Prose Baseline (Condition A)**:
   - Condition E outperformed the prose baseline by **+44 net wins** ($+22.0$ percentage points, shifting EM from 32.0% to 54.0%).
   - Paired discordant transitions: **52 wins, 8 losses, 140 ties** (win-to-loss ratio: **6.5x**).
   - Exact two-tailed McNemar test: **$p = 5.21 \times 10^{-9}$** ($p < 10^{-8}$).
4. **Substantial Reversal of Stage C Regressions**:
   - In historical Stage C, decompilation caused 47 regressions.
   - Condition E recovered **41 of the 47 regressions (87.2% recovery rate)**, compared to 37/47 (78.7%) for Condition D and 21/47 (44.7%) for Condition C.
5. **Zero Token Ceiling Violations**:
   - Total context never exceeded the 2,048-token ceiling across all 200 cases.

---

## 2. Five-Condition Benchmark Comparison ($N=200$)

| Condition | Description | Exact Match (EM) | Containment | Net EM vs. A | Net EM vs. D |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **A** | Prose Baseline (Coref + Prose SVOA) | 64 / 200 (32.0%) | 87 / 200 (43.5%) | Baseline (0.0 pp) | -17.5 pp |
| **B** | Stage C Decompiled Prose + Struct Adapter | 28 / 200 (14.0%) | 39 / 200 (19.5%) | -18.0 pp | -35.5 pp |
| **C** | Structural Table Retention ($\theta=2.0$) | 61 / 200 (30.5%) | 79 / 200 (39.5%) | -1.5 pp | -19.0 pp |
| **D** | Structural Table Retention ($\theta=0.0$) | 99 / 200 (49.5%) | 122 / 200 (61.0%) | +17.5 pp | Baseline (0.0 pp) |
| **E** | **Tables ($\theta=0.0$) + Content Lists** | **108 / 200 (54.0%)** | **137 / 200 (68.5%)** | **+22.0 pp** ($p < 10^{-8}$) | **+4.5 pp** ($p = 0.035$) |

$$\begin{array}{c}
\text{Exact Match Progression: } \\
\text{Condition B (14.0\%)} \longrightarrow \text{Condition C (30.5\%)} \longrightarrow \text{Condition A (32.0\%)} \longrightarrow \text{Condition D (49.5\%)} \longrightarrow \mathbf{\text{Condition E (54.0\%)}}
\end{array}$$

---

## 3. Paired Contingency Tables and McNemar Tests

### 3.1 Primary Contrast: Condition E vs. Condition D (Tables Only)

$$\begin{array}{c|cc|c}
\text{Exact Match} & \text{Cond E Correct} & \text{Cond E Incorrect} & \text{Total} \\
\hline
\text{Cond D Correct} & 96 & 3 & 99 \\
\text{Cond D Incorrect} & 12 & 89 & 101 \\
\hline
\text{Total} & 108 & 92 & 200
\end{array}$$

- **Wins ($D \to E$)**: 12
- **Losses ($E < D$)**: 3
- **Ties**: 185 (96 both correct, 89 both incorrect)
- **Net Discordant Delta**: $+9$ ($+4.50$ percentage points)
- **Two-Tailed Exact McNemar Test**:
  $$p = 2 \times \sum_{k=12}^{15} \binom{15}{k} 0.5^{15} = 0.03515625 \quad (p < 0.05)$$
- **95% Confidence Interval for Delta**: $[+0.76\%, +8.24\%]$
- **Conclusion**: Statistically significant improvement. Adding lists provides genuine incremental value over tables alone.

$$\begin{array}{c|cc|c}
\text{Containment} & \text{Cond E Correct} & \text{Cond E Incorrect} & \text{Total} \\
\hline
\text{Cond D Correct} & 120 & 2 & 122 \\
\text{Cond D Incorrect} & 17 & 61 & 78 \\
\hline
\text{Total} & 137 & 63 & 200
\end{array}$$

- **Containment Wins**: 17, **Losses**: 2, **Net Delta**: $+15$ ($+7.50$ pp)
- **Two-Tailed Exact McNemar Test**: $p = 0.0007286 \quad (p < 10^{-3})$
- **95% Confidence Interval**: $[+3.36\%, +11.64\%]$

---

### 3.2 Secondary Contrast: Condition E vs. Condition A (Prose Baseline)

$$\begin{array}{c|cc|c}
\text{Exact Match} & \text{Cond E Correct} & \text{Cond E Incorrect} & \text{Total} \\
\hline
\text{Cond A Correct} & 56 & 8 & 64 \\
\text{Cond A Incorrect} & 52 & 84 & 136 \\
\hline
\text{Total} & 108 & 92 & 200
\end{array}$$

- **Wins ($A \to E$)**: 52
- **Losses ($E < A$)**: 8
- **Ties**: 140 (56 both correct, 84 both incorrect)
- **Net Discordant Delta**: $+44$ ($+22.00$ percentage points)
- **Two-Tailed Exact McNemar Test**:
  $$p = 5.20569 \times 10^{-9} \quad (p < 10^{-8})$$
- **95% Confidence Interval for Delta**: $[+15.05\%, +28.95\%]$
- **Conclusion**: Overwhelmingly statistically significant superiority over the baseline.

---

### 3.3 Condition E vs. Condition C and Condition B

- **E vs. Condition C ($\theta=2.0$)**:
  - Wins: 48, Losses: 1, Net: $+47$ ($+23.50$ pp)
  - McNemar exact $p = 1.776 \times 10^{-13}$
  - 95% CI: $[+17.46\%, +29.54\%]$
- **E vs. Condition B (Stage C Decompilation)**:
  - Wins: 85, Losses: 5, Net: $+80$ ($+40.00$ pp)
  - McNemar exact $p = 7.533 \times 10^{-20}$
  - 95% CI: $[+32.54\%, +47.46\%]$

---

## 4. Diagnostic Strata Breakdown

| Subgroup / Stratum | Cohort Size ($N$) | Cond A EM | Cond B EM | Cond C EM | Cond D EM | Cond E EM | Recovery / Net Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stratum 1: Stage C Regressions** | 47 | 47 (100.0%) | 0 (0.0%) | 21 (44.7%) | 37 (78.7%) | **41 (87.2%)** | **87.2% Recovered** (+4 vs D) |
| **Stratum 2: Stage C Recoveries** | 11 | 0 (0.0%) | 11 (100.0%) | 8 (72.7%) | 8 (72.7%) | **8 (72.7%)** | **72.7% Preserved** (0 delta vs D) |
| **Stratum 3: Remaining Cases** | 142 | 17 (12.0%) | 17 (12.0%) | 32 (22.5%) | 54 (38.0%) | **59 (41.5%)** | **+5 net wins** vs D (+42 vs A) |
| *Diagnostic Gate 2 List Subset* | 31 | 7 (22.6%) | 5 (16.1%) | 0 (0.0%) | 0 (0.0%) | **11 (35.5%)** | **+11 net wins** vs D |

### Key Strata Insights
1. **Stratum 1 (Historical Regressions)**: Condition E recovers 41 of the 47 regressions, leaving only 6 unrecovered regressions.
2. **Stratum 2 (Historical Recoveries)**: Exactly 8 of the 11 recoveries are preserved under Condition E, identical to Conditions C and D.
3. **Stratum 3 (Remaining Cohort)**: Condition E achieves an additional $+5$ net wins over Condition D in the broad cohort.

---

## 5. Audit of All Regressions

A central motivation for evaluating the full 200-case cohort was to test regression safety on baseline-success cases.

### 5.1 Regressions Against Condition D ($N=3$)
Out of 99 cases answered correctly by Condition D, **96 remained correct under Condition E (97.0% retention)**. Exactly 3 cases regressed:
1. `3f5983b2`: *"who is the minister of youth in namibia"*  
   - Gold: `Erastus Utoni` | Cond D: `Erastus Utoni` | Cond E: `Insufficient information`  
   - *Cause*: A brief minister listing in clean prose was pushed lower by extracted ministry department lists.
2. `ef634417`: *"who sings the song rock you like a hurricane"*  
   - Gold: `Scorpions` | Cond D: `Scorpions` | Cond E: `Rudolf Schenker, Klaus Meine, Herman Rarebell`  
   - *Cause*: Model extracted the songwriters list instead of the band name. Note that containment was achieved.
3. `8f1f9bd9`: *"what is the definition of the name thomas"*  
   - Gold: `twin` | Cond D: `Twin` | Cond E: `Aramaic: twin`  
   - *Cause*: Model output etymological language tag. Note that containment was achieved.

**Safety Ratio**: 12 wins vs. 3 losses = **4.0x win-to-loss ratio**.

### 5.2 Regressions Against Condition A ($N=8$)
Out of 64 cases answered correctly by Condition A, **56 remained correct under Condition E (87.5% retention)**. Exactly 8 cases regressed (while Condition E gained 52 new wins over Condition A).
- **Safety Ratio**: 52 wins vs. 8 losses = **6.5x win-to-loss ratio**.

---

## 6. Pre-Registered Sensitivity Analysis (Case `895b5134`)

As pre-registered, we conducted a sensitivity analysis excluding the ambiguous premise-constraint case `895b5134`:

| Metric | Primary Cohort ($N=200$) | Sensitivity Cohort ($N=199$) | Delta / Impact |
| :--- | :---: | :---: | :---: |
| **Condition E Exact Match** | 108 / 200 (54.00%) | 108 / 199 (54.27%) | $+0.27$ pp |
| **Condition D Exact Match** | 99 / 200 (49.50%) | 99 / 199 (49.75%) | $+0.25$ pp |
| **E vs. D Net Wins** | +9 wins (+4.50 pp) | +9 wins (+4.52 pp) | Identical |
| **E vs. D McNemar $p$-value** | **0.03515625** | **0.03515625** | Identical ($p < 0.05$) |
| **E vs. A Net Wins** | +44 wins (+22.00 pp) | +44 wins (+22.11 pp) | Identical |

**Conclusion**: Because case `895b5134` was a tie (both conditions correctly abstained with `"Insufficient information"`), excluding it does not alter discordant pairs ($b=12, c=3$) or the statistical significance of any endpoint.

---

## 7. Decision Rule Assessment and Promotion Recommendation

We evaluate the pre-registered decision rules from the evaluation plan:

| Pre-Registered Promotion Criterion | Threshold / Rule | Observed Value | Verdict |
| :--- | :--- | :---: | :---: |
| **1. Statistical Superiority over Cond D** | McNemar $p < 0.05$ on EM | $p = 0.03515625$ | **MET** |
| **2. Superiority over Prose Baseline** | $\text{EM}_E \ge \text{EM}_A$ on full cohort | 54.0% vs. 32.0% ($+22.0$ pp, $p < 10^{-8}$) | **MET** |
| **3. Regression Safety Ratio** | $\text{Wins}_{E > D} \ge 2 \times \text{Losses}_{E < D}$ | 12 wins $\ge 2 \times 3$ losses ($4.0\times$) | **MET** |
| **4. Context Ceiling Compliance** | Zero ceiling violations ($N=200$) | 0 violations (max 2,046 tokens) | **MET** |

### **Final Recommendation: PROCEED TO PRODUCTION INTEGRATION**

**Scientific Justification**:
1. The structural table retention ($\theta=0.0$) plus content-list extraction pipeline (**Condition E**) resolves the long-standing tension between structured tabular extraction and unstructured prose.
2. It definitively outperforms the clean prose baseline by **$+22.0$ percentage points**, overturning the regression that stalled Stage C.
3. It incrementally outperforms table-only retention by **$+4.5$ percentage points** with formal statistical significance ($p = 0.035$).
4. It achieves an outstanding **97.0% retention rate** on baseline table successes while adding 12 new wins.

**Next Steps**:
Promote `scripts/diagnostic_list_extractor.py` and `build_candidate_condition_b_context` logic into the production pipeline (`backend/src/precis/`).
