# Experiment 4.2 Independent Audit: Walkthrough

## Overview

This walkthrough documents the independent audit of the **Experiment 4.2 Full-Cohort Table-Selection Threshold Evaluation** (`results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/`).

The evaluation examined whether relaxing the table-selection threshold from $\theta=2.0$ (Condition C) to $\theta=0.0$ (Condition D) improved end-to-end question answering on the frozen 200-case table-bearing confirmatory cohort. The original report claimed an Exact Match improvement from 30.5% to 49.5%, zero regressions, and presented an evidence-path table with apparent internal discrepancies.

---

## What Was Done

### 1. Cryptographic Digest Verification
- Verified bit-level SHA-256 digests for all 10 experiment artifacts:
  - `sample_manifest.jsonl`, `eval_records_stage_c.jsonl`, `nq_dev.jsonl`, `eval_records.jsonl`, `aggregate_summary.json`, `paired_comparisons.json`, `regression_recovery_audit.jsonl`, `investigation_report.md`, `preflight_report.md`, and `walkthrough.md`.
  - Verified experiment runner (`scripts/eval_experiment_4_2_threshold.py`) and integrity test suite (`scripts/test_experiment_4_2_integrity.py`).
  - Successfully ran the 13-test integrity suite (`pytest scripts/test_experiment_4_2_integrity.py`), achieving 100% pass rate.
  - Documented in `hash_verification.json`.

### 2. Independent Metric & Statistical Recomputation
- Recomputed all condition-level metrics and paired statistical tests directly from raw evaluation records (`eval_records.jsonl`, $N=200$):
  - **Condition A (Prose Baseline)**: EM = 32.0% (64/200), Containment = 43.5% (87/200).
  - **Condition B (Stage C SVOA)**: EM = 14.0% (28/200), Containment = 19.5% (39/200).
  - **Condition C (Retention $\theta=2.0$)**: EM = 30.5% (61/200), Containment = 39.5% (79/200).
  - **Condition D (Retention $\theta=0.0$)**: EM = 49.5% (99/200), Containment = 61.0% (122/200).
  - **D vs C Comparison**: 38 wins, 0 losses, McNemar $p = 7.28 \times 10^{-12}$, $+19.0$ percentage points.
  - **D vs A Comparison**: 50 wins, 15 losses, McNemar $p = 1.57 \times 10^{-5}$, $+17.5$ percentage points.
  - **Zero Regressions Invariant**: Exactly 0 EM regressions and 0 containment regressions between Condition D and Condition C.
  - Verified 100% agreement between raw records and precomputed summary files.
  - Documented in `recomputed_metrics.json`.

### 3. Forensic Audit of the Evidence-Path Discrepancy
- Identified the exact root cause of why packed context counts (108 in C, 167 in D) exceeded selected table counts (105 in C, 164 in D):
  - Context packing prefixes non-tabular `clean_prose` before markdown tables.
  - In exactly 3 cases (`3f5983b2...`, `a5c30bbe...`, `00d7c7cc...`), the gold answer resided in clean prose (HTML lists `<li>`) rather than any extracted `<table>`.
  - In all 3 cases, clean prose preserved the answer into the packed context.
  - Zero packing truncations occurred: 105/105 tables in C and 164/164 tables in D containing gold answers retained their evidence in packed context.
  - Provided a corrected evidence-path table separating table-only funnel telemetry from combined context telemetry.

### 4. Case-Level Evidence & Failure Taxonomy Reconstruction
- Generated `case_level_evidence_audit.jsonl` covering all 200 cases with mutually exclusive failure categories:
  - Verified elimination of selection failures: 59 cases (29.5%) under $\theta=2.0 \to$ 0 cases (0.0%) under $\theta=0.0$.
  - Reconciled remaining failures in Condition D: 44 generation/reasoning errors (45 prose-aware) and 34 extraction omissions (33 prose-aware).
  - Reconciled historical Stage C P1/P2 subgroups: Condition D recovers 37/47 P1 regressions (78.7%), preserves 8/11 P2 recoveries (72.7%), and unlocks 42/125 recoveries on double-loss cases.

---

## Deliverables Generated

All files were written strictly to `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/`:
1. `audit_report.md` (comprehensive audit report with exact replacement wording).
2. `case_level_evidence_audit.jsonl` (full case-by-case evidence and failure taxonomy for all 200 cases).
3. `recomputed_metrics.json` (complete recomputed metrics, token counts, and paired comparisons).
4. `hash_verification.json` (cryptographic SHA-256 digest verifications).
5. `walkthrough.md` (audit process walkthrough).

---

## Audit Verdict

**Status**: `VERIFIED WITH REPORTING CORRECTIONS`  
The core empirical findings are fully verified. The evidence-path reporting discrepancy is fully explained with zero code errors. No further inference or production changes were made.
