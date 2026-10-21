# Experiment 4.5.6: Cohort and Provenance Audit

**Audit Date**: 2026-10-10  
**Target Evaluation**: Gate 5 Confirmatory Production-Path Evaluation  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Cohort**: Canonical 200-Case Table-Bearing Cohort (Experiments 4.2 & 4.4)

---

## 1. Executive Summary

This audit independently verifies the integrity, provenance, cross-alignment, and scoring semantics of the 200-case table-bearing cohort across all canonical frozen reference conditions:
- **Condition A**: Prose Baseline (`eval_records_stage_c.jsonl`)
- **Condition B**: Stage C Decompiled Prose Baseline (`eval_records_stage_c.jsonl`)
- **Condition C**: Table Retention at $\theta=2.0$ (`full_cohort_threshold_20261010/eval_records.jsonl`)
- **Condition D**: Table Retention at $\theta=0.0$ (`full_cohort_threshold_20261010/eval_records.jsonl`)
- **Condition E**: In-Memory Tables ($\theta=0.0$) + Lists (`full_cohort_evaluation_20261010/eval_records.jsonl`)

All 200 case IDs, questions, gold answers, alternative answers, and predictions were audited bit-identically. **Zero cross-alignment mismatches or scoring discrepancies were identified.**

---

## 2. Cohort Membership and Uniqueness

- **Manifest Source**: `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl`
- **Total Manifest Records**: 200 table-bearing cases (out of 500 total sample records).
- **Unique Case IDs**: Exactly 200 unique IDs (`len(set(cids)) == 200`).
- **Completeness**: All 200 cases exist across Stage C, Experiment 4.2, and Experiment 4.4 records without omissions or substitutions.

---

## 3. Five-Condition Historical Benchmark Verification ($N=200$)

Every historical prediction was re-scored against the canonical evaluation functions (`check_exact_match` and `check_containment` from `eval_table_selection_v2.py`). The calculated scores match the stored records with 100% agreement:

| Condition | Description | Stored EM | Verified EM | Stored Cont | Verified Cont | Match Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **A** | Prose Baseline (Coref + Prose SVOA) | 64 / 200 (32.0%) | 64 / 200 (32.0%) | 87 / 200 (43.5%) | 87 / 200 (43.5%) | **100% EXACT** |
| **B** | Stage C Decompiled Prose | 28 / 200 (14.0%) | 28 / 200 (14.0%) | 39 / 200 (19.5%) | 39 / 200 (19.5%) | **100% EXACT** |
| **C** | Table Retention ($\theta=2.0$) | 61 / 200 (30.5%) | 61 / 200 (30.5%) | 79 / 200 (39.5%) | 79 / 200 (39.5%) | **100% EXACT** |
| **D** | Table Retention ($\theta=0.0$) | 99 / 200 (49.5%) | 99 / 200 (49.5%) | 122 / 200 (61.0%) | 122 / 200 (61.0%) | **100% EXACT** |
| **E** | Tables ($\theta=0.0$) + Content Lists | 108 / 200 (54.0%) | 108 / 200 (54.0%) | 137 / 200 (68.5%) | 137 / 200 (68.5%) | **100% EXACT** |

### McNemar Primary Contrast (Condition E vs. Condition D, $N=200$)
- **Contingency Table**:
  - Both Positive ($a$): 96
  - Cond E Positive, Cond D Negative ($b$, Wins): 12
  - Cond E Negative, Cond D Positive ($c$, Losses): 3
  - Both Negative ($d$): 89
- **Net Discordant Delta**: $+9$ ($+4.50$ percentage points)
- **Exact Two-Sided McNemar Test**:
  $$p = 2 \times \sum_{k=12}^{15} \binom{15}{k} 0.5^{15} = 0.03515625 \quad (p < 0.05)$$
- **95% Confidence Interval for Risk Difference**: $[+0.76\%, +8.24\%]$

---

## 4. Ambiguous Premise Case Analysis (Bill Belichick)

### Case Details
- **Case ID**: `895b5134173847ff8837c187a367cde0`
- **Question**: `"who has won the most superbowls as a player"`
- **Gold Answer**: `"Bill Belichick"` (Note: Bill Belichick won 8 Super Bowls as defensive coordinator and head coach, but zero as a player).
- **Condition D Prediction**: `"Insufficient information"` ($\text{EM}=\text{False}$)
- **Condition E Prediction**: `"Insufficient information"` ($\text{EM}=\text{False}$)

### Handling in Evaluation
1. **Primary Evaluation ($N=200$)**:
   The case remains strictly in the primary cohort to preserve identical sample membership with Experiments 4.2 and 4.4.
2. **Sensitivity Analysis ($N=199$, Excluding Case `895b5134`)**:
   Because both Condition D and Condition E produced `"Insufficient information"` and scored $\text{EM}=\text{False}$, the case falls into cell $d$ (both negative). Excluding it removes one concordant negative pair ($89 \to 88$) while leaving the discordant pair counts ($b=12, c=3$) completely unchanged:
   - **Condition E EM**: $108 / 199 = 54.27\%$
   - **Condition D EM**: $99 / 199 = 49.75\%$
   - **Net EM Delta**: $+9$ ($+4.52$ percentage points)
   - **Exact Two-Sided McNemar $p$-value**:
     $$p = 2 \times \sum_{k=12}^{15} \binom{15}{k} 0.5^{15} = 0.03515625$$
   - **95% Confidence Interval**: $[+0.76\%, +8.29\%]$
   - **Conclusion**: The statistical significance of Condition E over Condition D is robust and completely unaffected by the ambiguous premise in case `895b5134`.

---

## 5. Cohort Strata Breakdown

The cohort is partitioned into three mutually exclusive strata established in Stage C / Experiment 4.2:

1. **Stratum 1 (Stage C Regressions, $N=47$)**:
   - Cases where Condition A was correct ($\text{EM}=\text{True}$) but Stage C decompilation regressed ($\text{EM}=\text{False}$).
   - Condition D recovered 37/47 (78.7%).
   - Condition E recovered 41/47 (87.2%).
2. **Stratum 2 (Stage C Recoveries, $N=11$)**:
   - Cases where Condition A was incorrect but Stage C succeeded.
   - Condition D achieved 4/11 (36.4%).
   - Condition E achieved 5/11 (45.5%).
3. **Stratum 3 (Remaining Baseline Cases, $N=142$)**:
   - Cases concordant in Stage C (both succeeded or both failed).
   - Condition D achieved 58/142 (40.8%).
   - Condition E achieved 62/142 (43.7%).

Additionally, the **Gate 2 Diagnostic Subset ($N=31$)** and **Non-Gate-2 Subset ($N=169$)** are tracked for historical continuity.

---

## 6. Audit Conclusion

The cohort provenance and reference baselines are 100% verified. No repair, modification, or imputation of frozen data occurred. The evaluation framework is fully prepared for paired statistical comparison with the proposed production-path candidate condition.
