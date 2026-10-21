# Experiment 4.4: Full-Cohort Confirmatory Evaluation — Walkthrough

## Overview & Status

The full-cohort confirmatory evaluation for **Experiment 4.4** (`results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/`) has completed successfully.

- **Status**: **COMPLETE — CRITERIA MET FOR PRODUCTION INTEGRATION**
- **Evaluation Scope**: Canonical 200-case table-bearing cohort.
- **Inference Confinement**: Exactly 31 Gate 2 cases reused bit-identically + 169 cases generated live on `qwen2.5-coder:7b`. Zero failed or unscorable cases (100% completion rate).
- **Safety Invariants**: Zero modifications to production code (`backend/src/precis/`), 0 context ceiling violations.

---

## Key Results Summary

### 1. Five-Condition Benchmark Performance

$$\begin{array}{lcccc}
\hline
\textbf{Condition} & \textbf{Exact Match (EM)} & \textbf{Containment} & \textbf{Net vs. A (Prose)} & \textbf{Net vs. D (Tables)} \\
\hline
\text{A: Prose Baseline} & 64 / 200 \ (32.0\%) & 87 / 200 \ (43.5\%) & \text{Baseline} & -17.5\text{ pp} \\
\text{B: Stage C Decompilation} & 28 / 200 \ (14.0\%) & 39 / 200 \ (19.5\%) & -18.0\text{ pp} & -35.5\text{ pp} \\
\text{C: Table Retention } (\theta=2.0) & 61 / 200 \ (30.5\%) & 79 / 200 \ (39.5\%) & -1.5\text{ pp} & -19.0\text{ pp} \\
\text{D: Table Retention } (\theta=0.0) & 99 / 200 \ (49.5\%) & 122 / 200 \ (61.0\%) & +17.5\text{ pp} & \text{Baseline} \\
\textbf{E: Tables } (\theta=0.0) \textbf{ + Lists} & \mathbf{108 / 200 \ (54.0\%)} & \mathbf{137 / 200 \ (68.5\%)} & \mathbf{+22.0\text{ pp}} \ (p < 10^{-8}) & \mathbf{+4.5\text{ pp}} \ (p = 0.035) \\
\hline
\end{array}$$

### 2. Primary Paired Contrast: Condition E vs. Condition D (Tables Only)
- **Wins**: 12, **Losses**: 3, **Ties**: 185
- **Net Discordant Delta**: **+9 net wins (+4.50 percentage points)**
- **Two-Tailed Exact McNemar Test**: **$p = 0.03515625$** ($p < 0.05$, statistically significant)
- **95% Confidence Interval for Delta**: $[+0.76\%, +8.24\%]$
- **Win-to-Loss Ratio**: **4.0x**

### 3. Contrast vs. Clean Prose Baseline (Condition A)
- **Wins**: 52, **Losses**: 8, **Ties**: 140
- **Net Discordant Delta**: **+44 net wins (+22.00 percentage points)**
- **Two-Tailed Exact McNemar Test**: **$p = 5.21 \times 10^{-9}$** ($p < 10^{-8}$)
- **Win-to-Loss Ratio**: **6.5x**

---

## Diagnostic Strata Breakdown

- **Stratum 1 (Historical Stage C Regressions, $N=47$)**:
  * Condition E recovered **41 of 47 regressions (87.2% recovery rate)**, compared to 37/47 for Condition D and 21/47 for Condition C.
- **Stratum 2 (Historical Stage C Recoveries, $N=11$)**:
  * Condition E preserved **8 of 11 recoveries (72.7%)**, identical to Conditions C and D.
- **Stratum 3 (Remaining Cohort, $N=142$)**:
  * Condition E achieved **59 / 142 (41.5% EM)**, gaining $+5$ net wins over Condition D (54/142) and $+42$ net wins over Condition A (17/142).
- **Diagnostic List Subset ($N=31$)**:
  * Condition E achieved **11 / 31 (35.5% EM)** vs. 0/31 for Conditions C and D, replicating Gate 2 findings with zero drift.

---

## Regression Safety Audit

Out of 99 cases answered correctly by Condition D:
- **96 cases remained correct under Condition E (97.0% retention rate)**.
- Exactly 3 cases regressed (`3f5983b2`, `ef634417`, `8f1f9bd9`), with 2 of the 3 still achieving containment.
- With 12 new wins vs. 3 losses, the pipeline achieved a **4.0x safety ratio**.

---

## Pre-Registered Sensitivity Analysis (Case `895b5134`)

- Primary Cohort ($N=200$): EM = 54.00%, Net Delta vs. D = $+4.50$ pp, $p = 0.03515625$.
- Sensitivity Cohort ($N=199$): EM = 54.27%, Net Delta vs. D = $+4.52$ pp, $p = 0.03515625$.
- Discordant pairs are completely unchanged ($b=12, c=3$). The finding is robust.

---

## Deliverables Generated

The following files are located in `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/`:
1. `eval_records.jsonl` (945 KB): 200 case-level evaluation records with prompt telemetry and scoring.
2. `aggregate_summary.json` (8 KB): Aggregated metrics, strata breakdowns, and sensitivity analyses.
3. `paired_comparisons.json` (4 KB): Contingency tables, discordant transitions, McNemar tests, and 95% CIs.
4. `regression_audit.jsonl` (3 KB): Case-by-case audit of all regressions against Conditions D and A.
5. `evaluation_report.md` (12 KB): Full confirmatory evaluation report.
6. `integrity_report.json` (4 KB): Machine-readable verification of input/output SHA-256 digests and tests.
7. `walkthrough.md` (this document): Summary walkthrough of findings.

---

## Final Recommendation

### **PROCEED TO PRODUCTION INTEGRATION**

All pre-registered promotion criteria have been satisfied:
1. Significant gain over table retention ($p = 0.035 < 0.05$).
2. Substantial superiority over prose baseline ($+22.0$ pp, $p < 10^{-8}$).
3. High retention on baseline successes (97.0%, 4.0x win-to-loss ratio).
4. Zero token ceiling violations.
