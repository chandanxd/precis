# Experiment 4.4: Independent Audit Walkthrough

**Audit Date**: 2026-10-10  
**Evaluator**: Independent Audit Suite  
**Audit Directory**: `results/diagnostic_experiment_4_v1/independent_audit_20261010/`  
**Verdict**: **AUDIT PASSED: READY FOR EXPLICIT APPROVAL OF A CONTROLLED INTEGRATION**

---

## 1. Audit Overview

This independent audit verified the Experiment 4.4 full-cohort confirmatory evaluation on the frozen 200-case table-bearing cohort.

The evaluation evaluated **Condition E** (structural table retention at $\theta=0.0$ plus content list extraction) against:
- **Condition D**: Structural table retention at $\theta=0.0$ alone.
- **Condition C**: Structural table retention at $\theta=2.0$ (Stage C threshold).
- **Condition B**: Stage C decompiled triple representation.
- **Condition A**: Frozen prose baseline.

The audit was executed under strict safety constraints: **zero modifications to `backend/src/precis/`**, zero live inference during the audit, and zero network calls.

---

## 2. Key Verified Findings

### 2.1 Empirical Confirmatory Performance ($N=200$)
- **Condition E Exact Match**: **54.0% (108 / 200)** vs Condition D's **49.5% (99 / 200)** ($+4.50$ percentage points, $+9$ net wins).
- **Condition E Containment**: **68.5% (137 / 200)** vs Condition D's **61.0% (122 / 200)** ($+7.50$ percentage points, $+15$ net wins).
- **Prose Baseline Victory**: Outperforms Condition A (**32.0% EM, 64 / 200**) by **+22.00 percentage points (+44 net wins)** with $p = 5.21 \times 10^{-9}$.

### 2.2 Paired Hypothesis Testing (Exact McNemar Test)
- **Discordant Transitions (E vs. D)**: 12 wins, 3 losses, 185 ties.
- **Statistical Significance**: $p = 0.03515625 < 0.05$ (**Statistically Significant**).
- **95% Confidence Interval for Risk Difference**: $[+0.76\%, +8.24\%]$.
- **Odds Ratio**: $4.00$.

### 2.3 Provenance & Score Integrity
- **Gate 2 Reuse (31 cases)**: 31/31 predictions match Gate 2 Stage 2B bit-for-bit.
- **Exp 4.2 Condition D (200 cases)**: 200/200 predictions match Experiment 4.2 bit-for-bit.
- **Independent Score Evaluation**: 0 score mismatches across all 1,000 predictions (2,000 evaluations).
- **Provenance Anomalies**: Exactly 0.

### 2.4 Context Length Compliance
- Condition E mean context: 409.4 tokens (median 281.0, max 2046 tokens).
- Exactly **0 / 200 context ceiling violations** ($>2048$ tokens).

---

## 3. Detailed Deliverables in Audit Directory

All audit artifacts have been created in `results/diagnostic_experiment_4_v1/independent_audit_20261010/`:

1. [independent_audit_report.md](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/independent_audit_report.md): Full comprehensive audit report, methodology, and recommendations.
2. [regression_review.md](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/regression_review.md): Bit-level forensic analysis of the 3 regressions against Condition D (`3f5983b2`, `ef634417`, `8f1f9bd9`).
3. [extractor_safety_review.md](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/extractor_safety_review.md): In-depth safety review of the HTML parser state machine, heuristics, edge cases, and test results.
4. [independent_metrics.json](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/independent_metrics.json): Independently recomputed metrics, contingency tables, strata performance, and sensitivity analysis.
5. [prediction_provenance_audit.json](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/prediction_provenance_audit.json): Provenance verification records for all 200 cases.
6. [integrity_report.json](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/independent_audit_20261010/integrity_report.json): Cryptographic input and output hash verification digests.
7. [test_experiment_4_4_audit_extractor.py](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_4_audit_extractor.py): Suite of 15 unit and safety tests (15/15 passed).

---

## 4. Next Steps for Controlled Integration

Having completed and passed this independent audit, the implementation is ready for explicit authorization by the user for a controlled production integration:
1. **Feature-Flagged Ingestion**: Integrate `RobustListParser` behind a configuration toggle (`ENABLE_LIST_EXTRACTION`).
2. **Table-List Deduplication**: Add a token overlap safeguard to prevent appending lists whose items already exist in selected table cells.
3. **Exact Token Deductions**: Account for section header token overhead during partial line packing.
