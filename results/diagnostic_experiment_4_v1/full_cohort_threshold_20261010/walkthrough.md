# Experiment 4.2: Full-Cohort Table-Selection Threshold Evaluation — Walkthrough

## Summary of Accomplishments

Experiment 4.2 successfully conducted a controlled generation evaluation on the **frozen 200-case table-bearing confirmatory cohort** to determine whether relaxing the query-aware table-selection threshold from $\theta=2.0$ (Condition C) to $\theta=0.0$ (Condition D) improves end-to-end answer accuracy, answer containment, and regression recovery.

### Key Milestones Completed:
1. **Bit-for-Bit Preflight Verification**: Manifest, Stage C historical records, and NQ Dev dataset hashes were verified against their pre-registered SHA-256 digests.
2. **Intervention Isolation**: The selection threshold was isolated as the **sole experimental variable**; representation, header handling, 100% row retention within selected tables (up to 500-token chunks), 2,048 token context ceiling, model, prompt, decoding, and scoring were bit-for-bit identical between Condition C and Condition D (`include_lists = False` for both).
3. **Rigorous Test Coverage**: Developed 13 new integrity tests covering cohort uniqueness, threshold isolation, config fingerprinting, error accounting, McNemar properties, context ceilings, directory protection, and JSON serialization. All 13 passed, along with 21 Gate 4 tests and 17 Stage C safety tests.
4. **Execution of Full 200-Case Evaluation**: Evaluated all 200 cases across Conditions C and D in 104.8 seconds on a local NVIDIA RTX 3060 GPU with 0 timeouts, 0 exceptions, and 100% successful predictions.
5. **Serializing Validated Diagnostic Outputs**: Produced `eval_records.jsonl`, `aggregate_summary.json`, `paired_comparisons.json`, `regression_recovery_audit.jsonl`, `preflight_report.md`, and `investigation_report.md`.

---

## Key Experimental Results

```
+---------------------------------------------------------------------------------------------------------+
| Condition                      | Exact Match (EM) | Containment | Mean Context Tok | Net Wins vs Cond C |
+--------------------------------+------------------+-------------+------------------+--------------------+
| Cond A (Reference Naive RAG)   | 64 / 200 (32.0%) | 87 (43.5%)  | 618.8 tokens     | +3 net wins        |
| Cond B (Stage C Decompilation) | 28 / 200 (14.0%) | 39 (19.5%)  | 155.4 tokens     | -33 net wins       |
| Cond C (Retention theta=2.0)   | 61 / 200 (30.5%) | 79 (39.5%)  | 195.4 tokens     | [Baseline C]       |
| Cond D (Retention theta=0.0)   | 99 / 200 (49.5%) | 122 (61.0%) | 326.4 tokens     | +38 net wins (0 L) |
+---------------------------------------------------------------------------------------------------------+
```

### Statistical Significance:
- **Condition D vs Condition C**: Net wins: **+38** (38 D-wins, 0 C-wins). McNemar's exact test $p = 7.28 \times 10^{-12}$ ($p < 10^{-11}$). Risk difference: **+19.0 pp** [95% CI: +13.56%, +24.44%].
- **Condition D vs Condition A**: Net wins: **+35** (50 D-wins, 15 A-wins). McNemar's exact test $p = 1.57 \times 10^{-5}$ ($p < 10^{-4}$). Risk difference: **+17.5 pp** [95% CI: +9.98%, +25.02%].
- **Condition C vs Condition A**: Indistinguishable from baseline ($p = 0.795$).

### Failure Pathway Shift:
- `SELECTION_FAILURE` was **completely eliminated** (59 cases in C $\to$ **0 cases in D**).
- `GENERATION_REASONING_FAILURE` (44 cases, 22.0%) and `EXTRACTION_OMISSION` (34 cases, 17.0%) are now the dominant residual error categories.

---

## Artifact File Map & Hashes

| Artifact | File Path | SHA-256 Digest |
| :--- | :--- | :--- |
| Preflight Report | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/preflight_report.md` | `0c8f69a02ddf0d3ca8ff0e359b4d3f22bfab178778fdfb329b03e14381daf6e8` |
| Evaluation Records | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl` | `d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0` |
| Aggregate Summary | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/aggregate_summary.json` | `61106ab8d421b662ed9d95c672bee7efc119f8cf62eb08e12efaedb47b9df5d4` |
| Paired Comparisons | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/paired_comparisons.json` | `0ec3cbff263560cc6e602ddeddceab1f317af638ec7c8fd1ac2ea49bf73c9851` |
| Regression Recovery Audit | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/regression_recovery_audit.jsonl` | `2820b856c1bfe49e0d90dc964eccd6f9b3d867f51bc335611459b466d83401cc` |
| Investigation Report | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/investigation_report.md` | `46ea3e271ce1bdb98d3a5b6f4a9532413b76993c9402c2c5dbb8d626681d80b1` |
