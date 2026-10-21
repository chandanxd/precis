# Experiment 4.3: Final Preflight Reconciliation Walkthrough

## Overview & Status

The final preflight reconciliation for the Experiment 4.3 full-cohort confirmatory evaluation has been completed.
All review artifacts are isolated in:
`results/diagnostic_experiment_4_v1/final_preflight_20261010/`

- **Final Readiness Verdict**: **READY FOR EXPLICIT AUTHORIZATION**
- **Proposed Inference Budget**: Exactly **169 model calls** to `qwen2.5-coder:7b`.
- **Current State**: Execution halted. Zero model inference executed. Awaiting explicit user command.

---

## 1. Resolution of the Ambiguous Case (`895b5134`)

We performed a complete factual, prompt, and semantic audit of case `895b5134173847ff8837c187a367cde0`:
- **Question**: *"who has won the most superbowls as a player"*
- **NQ Gold Answer**: `['Bill Belichick', 'Neal Dahlen']`
- **Source Document**: The raw HTML text lists Bill Belichick winning as **defensive coordinator** and **head coach**, and Neal Dahlen winning as **personnel staff** and **general manager**.
- **Finding**: Neither individual won those Super Bowls as a **player**. The query contains a premise constraint that is contradicted by the source text.
- **Model Behavior**: When presented with the extracted list under Condition E, `qwen2.5-coder:7b` correctly obeyed prompt instructions and answered **"Insufficient information"**.
- **Scoring**: Because NQ annotators accepted the names without verifying the player constraint, the model's factually accurate response scored `False`.
- **Pre-Registered Handling**:
  * **Primary Analysis ($N=200$)**: Retained to ensure strict fidelity to the frozen manifest and historical records.
  * **Sensitivity Analysis ($N=199$)**: Pre-registered with `895b5134` excluded. Because this case was a tie (`Insufficient information` under both Condition D and Condition E), excluding it does not alter discordant pairs (11 wins, 0 losses, $p = 0.0009765$).

Full details are documented in [`ambiguous_case_review.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/final_preflight_20261010/ambiguous_case_review.md).

---

## 2. Condition E Prediction Reuse Verification

All 31 Gate 2 Condition E predictions were independently audited against the canonical manifest and Experiment 4.2 records:
- **ID Alignment**: All 31 cases are members of the 200 table-bearing manifest, appearing in identical monotonic sequence.
- **Configuration Parity**: Model (`qwen2.5-coder:7b`), greedy decoding (`temperature: 0.0`, `top_p: 0.9`), seed (`42`), generation limit (`512`), context ceiling (`2,048`), prompt template (`CONCISE_PROMPT_TEMPLATE`), and scoring functions match identically.
- **Audit Outcome**: Exactly **31 of 31 cases PASSED** all verification checks (100% pass rate).
- Full record details are serialized in [`prediction_reuse_audit.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/final_preflight_20261010/prediction_reuse_audit.json).

---

## 3. Full-Cohort Partition and Plan Verification

- **Total Table-Bearing Manifest**: 200 cases (0 duplicates, 0 missing).
- **Conditions A–D (Frozen)**: All 200 cases have complete, valid predictions in historical records:
  * Condition A (Prose Baseline): 64 / 200 EM (32.0%)
  * Condition B (Stage C Decompilation): 28 / 200 EM (14.0%)
  * Condition C (Table Retention $\theta=2.0$): 61 / 200 EM (30.5%)
  * Condition D (Table Retention $\theta=0.0$): 99 / 200 EM (49.5%)
- **Condition E Partition**:
  * Reused from Gate 2: Exactly **31 cases**.
  * Remaining to generate: Exactly **169 cases**.
  * Total proposed inference count: **169**.
- **Pre-Registered Endpoints**: Exact Match (primary) and Containment (secondary) evaluated with two-tailed exact McNemar tests and 95% binomial confidence intervals across all 200 cases and across diagnostic strata (47 regressions, 11 recoveries, 142 remaining).

Full details are documented in [`full_cohort_preflight_audit.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/final_preflight_20261010/full_cohort_preflight_audit.md).

---

## 4. Deliverables Index

All deliverables for this final preflight are verified and saved in `results/diagnostic_experiment_4_v1/final_preflight_20261010/`:
1. `ambiguous_case_review.md` (4,964 bytes): Detailed factual and semantic resolution of case `895b5134`.
2. `prediction_reuse_audit.json` (21,799 bytes): Machine-readable audit confirming 31/31 prediction reuse.
3. `full_cohort_preflight_audit.md` (7,758 bytes): Comprehensive full-cohort preflight audit report.
4. `integrity_report.json` (4,447 bytes): Verification of SHA-256 hashes, test suite results, and safety invariants.
5. `walkthrough.md` (this document): Summary guide to findings and decisions.

---

## 5. Final Readiness Verdict

### **READY FOR EXPLICIT AUTHORIZATION**

There are **zero execution blockers**. All preconditions, prediction reuse verifications, safety invariants, and plan alignments are satisfied. Exactly **169 model inferences** will be executed upon receiving your explicit authorization.
