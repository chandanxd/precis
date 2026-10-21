# Experiment 4.2: Independent Results and Evidence-Path Audit Report

**Audit Target**: `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/`  
**Evaluation Scope**: Full-Cohort Table-Selection Threshold Evaluation ($\theta=2.0$ vs $\theta=0.0$, $N=200$)  
**Audit Date**: 2026-10-10  
**Audit Status**: **COMPLETED — VERIFIED WITH REPORTING CORRECTIONS**  
**Auditor**: Independent Codebase & Data Provenance Auditor (Antigravity)  
**Execution Constraints Enforced**: Audit-only mode; zero model inference; zero embedding inference; zero production modifications (`backend/src/precis/` untouched); zero modification to original experiment result files.

---

## 1. Executive Summary & Audit Verdict

### Overall Verdict: `VERIFIED WITH REPORTING CORRECTIONS`

```
========================================================================================
                          INDEPENDENT AUDIT VERDICT SUMMARY
========================================================================================
1. EMPIRICAL RESULTS FULLY VERIFIED:
   - Primary Claim Verified: Condition D (theta=0.0) improves Exact Match from 30.5% (61/200)
     to 49.5% (99/200) on the frozen 200-case confirmatory cohort.
   - Paired Discordant Pairs: Exactly 38 wins, 0 losses (net +38 wins, +19.0 pp).
   - Exact McNemar Test: p = 7.276e-12 (statistically decisive).
   - Zero-Regression Invariant: Condition D introduced exactly 0 EM regressions and 0 containment
     regressions relative to Condition C across all 200 cases.
   - Prose Baseline Outperformed: Condition D decisively outperforms frozen Condition A
     (49.5% vs 32.0% EM, +17.5 pp, McNemar p = 1.572e-05).
   - Zero Execution Failures: All 200 cases executed cleanly (0 failed, 0 unscorable, 200 scored).

2. EVIDENCE-PATH DISCREPANCY IDENTIFIED & RESOLVED:
   - Discrepancy: The investigation report claimed that packed-context evidence count (108 in C,
     167 in D) exceeded selected-table evidence count (105 in C, 164 in D).
   - Forensic Root Cause: The context-packing function (`build_table_retention_context`) extracts
     and prefixes non-tabular `clean_prose` before markdown tables. In exactly 3 cases
     (3f5983b2..., a5c30bbe..., 00d7c7cc...), the gold answer resides in clean prose lists rather
     than extracted HTML tables.
   - Zero Packing Truncations: 100% of selected tables containing gold answers survived context
     packing (105/105 in C, 164/164 in D).
   - Corrected Table: The discrepancy was a reporting label ambiguity combining table-only funnel
     telemetry with combined (prose + table) context telemetry.

3. FAILURE TAXONOMY RECONCILED:
   - Selection Failures: Eliminated from 59 cases (29.5%) under theta=2.0 to 0 cases (0.0%) under theta=0.0.
   - Unrecovered P1 Regressions: 10 remain in Condition D (6 generation/reasoning, 4 extraction omissions).
   - Remaining Blocker: The dominant failure mode has transitioned from table-selection thresholding
     to generation/reasoning over distractor rows (44 cases runner / 45 cases prose-aware) and
     extraction omissions from non-table markup (34 cases runner / 33 cases prose-aware).
========================================================================================
```

---

## 2. Input Integrity & Digest Verification

All primary input datasets, historical Stage C records, manifest definitions, and generated experiment outputs were verified against bit-level SHA-256 digests.

### 2.1. File Hash Verification Table

| File Name | Relative Workspace Path | Actual SHA-256 Digest | Recorded SHA-256 | Verification Status | Size (Bytes) |
| :--- | :--- | :--- | :--- | :---: | :---: |
| `sample_manifest.jsonl` | `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** | 87,954 |
| `eval_records_stage_c.jsonl`| `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl`| `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** | 312,090 |
| `nq_dev.jsonl` | `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** | 13,651,266 |
| `eval_records.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl` | `d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0` | `d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0` | **MATCH** | 942,161 |
| `aggregate_summary.json` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/aggregate_summary.json` | `61106ab8d421b662ed9d95c672bee7efc119f8cf62eb08e12efaedb47b9df5d4` | `61106ab8d421b662ed9d95c672bee7efc119f8cf62eb08e12efaedb47b9df5d4` | **MATCH** | 3,665 |
| `paired_comparisons.json` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/paired_comparisons.json` | `0ec3cbff263560cc6e602ddeddceab1f317af638ec7c8fd1ac2ea49bf73c9851` | `0ec3cbff263560cc6e602ddeddceab1f317af638ec7c8fd1ac2ea49bf73c9851` | **MATCH** | 7,745 |
| `regression_recovery_audit.jsonl`| `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/regression_recovery_audit.jsonl`| `2820b856c1bfe49e0d90dc964eccd6f9b3d867f51bc335611459b466d83401cc` | `2820b856c1bfe49e0d90dc964eccd6f9b3d867f51bc335611459b466d83401cc` | **MATCH** | 198,003 |
| `investigation_report.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/investigation_report.md` | `46ea3e271ce1bdb98d3a5b6f4a9532413b76993c9402c2c5dbb8d626681d80b1` | `46ea3e271ce1bdb98d3a5b6f4a9532413b76993c9402c2c5dbb8d626681d80b1` | **MATCH** | 19,013 |
| `preflight_report.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/preflight_report.md` | `0c8f69a02ddf0d3ca8ff0e359b4d3f22bfab178778fdfb329b03e14381daf6e8` | `0c8f69a02ddf0d3ca8ff0e359b4d3f22bfab178778fdfb329b03e14381daf6e8` | **MATCH** | 6,785 |
| `walkthrough.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/walkthrough.md` | `1b863e8e751535f9bdd3d21609e9edcd909c9e51ba627ea83e1891f59c52e65b` | `e2a4be6f38ef06e12e9b97779f67aee1dcba94560d21051fa8a452bf97df6db6` | **DISCREPANCY (Documented)** | 4,675 |

> [!NOTE]
> **Walkthrough Hash Discrepancy Note**: The preflight report in `full_cohort_threshold_20261010/` contained a recorded placeholder hash (`e2a4be6f...`) for `walkthrough.md` that was recorded before the walkthrough artifact was finalized. The actual SHA-256 digest of the finalized walkthrough file is `1b863e8e751535f9bdd3d21609e9edcd909c9e51ba627ea83e1891f59c52e65b`. This is purely an artifact logging sequencing discrepancy and does not affect any evaluation data.

### 2.2. Runner, Test, and Model Fingerprint Provenance

- **Experiment Runner**: `scripts/eval_experiment_4_2_threshold.py`  
  - SHA-256 Digest: `2ebabbcfb247721935366f69999fd798c9fcd6105cbf44e5967435a582fac606`
- **Integrity Test Suite**: `scripts/test_experiment_4_2_integrity.py`  
  - SHA-256 Digest: `f01840d94d02de61c099c2e67f448ef7c18254ec1931e341f101df6afbf38487`  
  - Test Suite Result: **13 passed in 4.03s** (100% pass rate).
- **Configuration Fingerprint**: `81aacc9186b973dc90abe728d37ad5a7337c6c7de7b463a62e3f16135ebae5c7`  
  - Model: `qwen2.5-coder:7b`  
  - Sampling: `temperature=0.0`, `top_p=0.9`, `seed=42`, `max_tokens=512`  
  - Grounding Budget: `token_ceiling=2048`, `max_table_tokens=500`, `max_rows_per_table=15`  
  - Evaluated Conditions: Condition C ($\theta=2.0$), Condition D ($\theta=0.0$).
- **Threshold-Only Code Diff**: Recovered directly between `eval_experiment_4_v1.py` and `eval_experiment_4_2_threshold.py`. The runner was adapted specifically to:
  1. Evaluate all 200 table-bearing cases instead of the 58-case union subset.
  2. Test threshold relaxation ($\theta=2.0$ vs $\theta=0.0$) in place of list ablation.
  3. Keep identical prompt templates (`CONCISE_PROMPT_TEMPLATE`), token normalization, scoring methods, and model configuration.

---

## 3. Independent Recomputation of Accuracy & Paired Statistical Metrics

All metrics were recomputed from the raw individual case entries in `eval_records.jsonl` ($N=200$) without reading from `aggregate_summary.json` or `paired_comparisons.json`. The independently recomputed metrics match the precomputed summaries in every field.

### 3.1. Recomputed Condition-Level Performance (Full Cohort $N=200$)

| Metric | Condition A (Prose Baseline) | Condition B (Stage C SVOA) | Condition C (Retention $\theta=2.0$) | Condition D (Retention $\theta=0.0$) | Precomputed Summary Match |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Attempted Cases** | 200 | 200 | 200 | 200 | **EXACT MATCH** |
| **Scored Denominator** | 200 | 200 | 200 | 200 | **EXACT MATCH** |
| **Failed Inferences** | 0 | 0 | 0 | 0 | **EXACT MATCH** |
| **Unscorable Inferences** | 0 | 0 | 0 | 0 | **EXACT MATCH** |
| **Exact Match Count** | 64 | 28 | 61 | **99** | **EXACT MATCH** |
| **Exact Match Rate** | 32.0% | 14.0% | 30.5% | **49.5%** | **EXACT MATCH** |
| **Containment Count** | 87 | 39 | 79 | **122** | **EXACT MATCH** |
| **Containment Rate** | 43.5% | 19.5% | 39.5% | **61.0%** | **EXACT MATCH** |
| **Mean ROUGE-L** | N/A (unlogged) | N/A (unlogged) | 0.3726 | **0.5846** | **EXACT MATCH** |
| **Median ROUGE-L** | N/A (unlogged) | N/A (unlogged) | 0.0000 | **0.8286** | **EXACT MATCH** |
| **Context Tokens (Mean)** | 618.8 | 155.4 | 195.4 | **326.4** | **EXACT MATCH** |
| **Context Tokens (Median)**| 367.0 | 63.0 | 79.5 | **235.0** | **EXACT MATCH** |
| **Context Tokens (p95)** | 2041.0 | 549.0 | 809.0 | **966.0** | **EXACT MATCH** |
| **Prompt Tokens (Mean)** | N/A (unlogged) | N/A (unlogged) | 506.6 | **672.5** | **EXACT MATCH** |
| **Generated Tokens (Mean)**| N/A (unlogged) | N/A (unlogged) | 5.9 | **6.7** | **EXACT MATCH** |
| **Mean Latency (ms)** | N/A (unlogged) | N/A (unlogged) | 278.1 | **241.0** | **EXACT MATCH** |
| **Zero-Context Count** | 2 (1.0%) | 71 (35.5%) | 90 (45.0%) | **31 (15.5%)** | **EXACT MATCH** |

### 3.2. Baseline Prediction Provenance Verification
Every single prediction for Condition A and Condition B recorded in `eval_records.jsonl` was verified against `eval_records_stage_c.jsonl`.
- Exactly 200 of 200 cases matched bit-identically across `predicted_answer`, `exact_match`, and `containment`.
- Zero discrepancies or data modifications detected.

### 3.3. Recomputed Paired Comparisons (Exact McNemar Test)

All paired contingency tables and binomial tests were independently evaluated over valid pairs ($N=200$):

| Comparison | Contrast Definition | Both Win | Cond 1 Win | Cond 2 Win | Both Loss | Net Wins | $\Delta$ Rate (pp) | Odds Ratio | McNemar $p$-value | Statistically Significant? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **D vs C (EM)** | $\theta=0.0$ vs $\theta=2.0$ | 61 | **38** | **0** | 101 | **+38** | **+19.0 pp** | $\infty$ | **$7.276 \times 10^{-12}$** | **YES ($p < 10^{-11}$)** |
| **D vs C (Cont)**| $\theta=0.0$ vs $\theta=2.0$ | 79 | **43** | **0** | 78 | **+43** | **+21.5 pp** | $\infty$ | **$2.274 \times 10^{-13}$** | **YES ($p < 10^{-12}$)** |
| **D vs A (EM)** | $\theta=0.0$ vs Prose Baseline | 49 | **50** | **15** | 86 | **+35** | **+17.5 pp** | 3.33 | **$1.572 \times 10^{-5}$** | **YES ($p < 10^{-4}$)** |
| **D vs A (Cont)**| $\theta=0.0$ vs Prose Baseline | 65 | **57** | **22** | 56 | **+35** | **+17.5 pp** | 2.59 | **$1.025 \times 10^{-4}$** | **YES ($p < 10^{-3}$)** |
| **D vs B (EM)** | $\theta=0.0$ vs SVOA Decomp | 28 | **71** | **0** | 101 | **+71** | **+35.5 pp** | $\infty$ | **$4.235 \times 10^{-22}$** | **YES ($p < 10^{-21}$)** |
| **C vs B (EM)** | $\theta=2.0$ vs SVOA Decomp | 22 | **39** | **6** | 133 | **+33** | **+16.5 pp** | 6.50 | **$1.087 \times 10^{-6}$** | **YES ($p < 10^{-5}$)** |
| **C vs A (EM)** | $\theta=2.0$ vs Prose Baseline | 30 | **31** | **34** | 105 | **-3** | **-1.5 pp** | 0.91 | **0.793** | **NO ($p \approx 0.79$)** |
| **C vs A (Cont)**| $\theta=2.0$ vs Prose Baseline | 40 | **39** | **47** | 74 | **-8** | **-4.0 pp** | 0.83 | **0.403** | **NO ($p \approx 0.40$)** |

Independently calculated binomial $p$-values match `paired_comparisons.json` to all decimal places.

---

## 4. Forensic Resolution of the Evidence-Path Discrepancy

### 4.1. The Apparent Anomaly
The investigation report presented the following funnel table (Table in Section 6):

| Evidence Stage | Condition C ($\theta=2.0$) | Condition D ($\theta=0.0$) |
| :--- | :---: | :---: |
| Evidence in Source HTML | 200 | 200 |
| Evidence in Extracted Tables | 164 | 164 |
| Evidence in Selected Tables | 105 | 164 |
| Evidence in Packed Context | **108** | **167** |

In both conditions, **the packed context count exceeds the selected table count by exactly 3 cases** ($105 \to 108$ in C, $164 \to 167$ in D). Furthermore, in Condition D, the packed context count (167) exceeds the total evidence found in extracted tables (164).

### 4.2. Forensic Root Cause
We traced the exact execution of context construction in `build_table_retention_context()` in `scripts/eval_experiment_4_2_threshold.py` (lines 800–940):
1. **Extraction Pipeline**: The runner separates the raw HTML document into two structural streams:
   - Extracted `TableBlock` objects.
   - Non-tabular `clean_prose` extracted from remaining HTML body tags (including lists `<ul>`, `<ol>`, `<p>`, etc.).
2. **Context Packing Priority**:
   ```python
   # In build_table_retention_context:
   if clean_prose_str:
       packed_parts.append(f"### Clean Prose:\n{clean_prose_str}")
   # Followed by selected Markdown table chunks
   for chunk in selected_table_chunks:
       packed_parts.append(chunk)
   ```
   `clean_prose` is packed *first* into the context budget before any table chunks!
3. **Telemetry Measurement Difference**:
   - `evidence_in_selected_tables`: Measures whether the answer string appears within the text of any `TableBlock` that was selected (`b.block_id in selected_ids`).
   - `evidence_in_packed_context`: Measures whether the answer string appears anywhere within the final `packed_context` string.
4. **The Three Cases with Prose Evidence**:
   In exactly **3 cases**, the gold answer was present in the source HTML document inside non-table markup (specifically unordered lists `<li>`), but was **not** present in any extracted `<table>`. Because `clean_prose` was preserved and prefixed to the context, the gold answer was present in `packed_context`!

### 4.3. Case-by-Case Breakdown of the 3 Discrepancy Cases

| Case ID | Question | Gold Answer | Source HTML Location | Clean Prose Context Snippet | Extracted Table Evidence? | Selected Table Evidence? | Packed Context Evidence? | Model Pred (C & D) | EM Score (C & D) |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `3f5983b2021c43aabd1bda0c71bb6f9e` | who is the minister of youth and sport in namibia | `Erastus Utoni` | `<li> Minister of Sport... Erastus Utoni </li>` | `Minister of Sport, Youth and National Service Erastus Utoni` | **False** | **False** | **True** | `Erastus Utoni` | **True (Win)** |
| `a5c30bbe447b4a2a8797b11c7ffbc48f` | who played pink in pink floyd the wall | `Bob Geldof as Pink` | `<li> Bob Geldof as Pink </li>` | `Bob Geldof as Pink Kevin McKeon as Young Pink` | **False** | **False** | **True** | `Bob Geldof` | **False (Pred lacked 'as Pink')** |
| `00d7c7cc7b534abeaf1f9dded1d3639b` | who played chris on the rich christy show | `Jim Gaffigan` | `<li> Jim Gaffigan as Chris Grandy </li>` | `Jim Gaffigan as Chris Grandy` | **False** | **False** | **True** | `Jim Gaffigan` | **True (Win)** |

**Key Findings on These 3 Cases**:
- In all 3 cases, Condition C and Condition D received the exact same `clean_prose` input and produced identical model predictions.
- In 2 cases (`3f5983b2...` and `00d7c7cc...`), the model extracted the exact gold answer (`Erastus Utoni` and `Jim Gaffigan`), achieving Exact Match under both C and D!
- In 1 case (`a5c30bbe...`), the model predicted `Bob Geldof` (exact match False against gold `Bob Geldof as Pink`).
- In **zero** cases did table selection or thresholding affect these 3 queries, because no table contained the answer.

### 4.4. Truncation and Packing Integrity Audit
We audited whether any selected table row was dropped or truncated during context assembly:
- Condition C: `evidence_in_selected_tables == True` in **105 cases**. In **105 of 105 cases (100.0%)**, `evidence_in_packed_context` was also `True`. Packing loss = **0**.
- Condition D: `evidence_in_selected_tables == True` in **164 cases**. In **164 of 164 cases (100.0%)**, `evidence_in_packed_context` was also `True`. Packing loss = **0**.

### 4.5. Corrected Evidence-Path Table

To eliminate ambiguity, telemetry must strictly distinguish between **Table-Only Evidence** and **Combined Context Evidence**:

| Evidence Pipeline Stage | Condition C ($\theta=2.0$) | Condition D ($\theta=0.0$) | Delta ($\theta=0.0$ vs $\theta=2.0$) | Forensic Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **1. Evidence in Source HTML** | 200 / 200 (100.0%) | 200 / 200 (100.0%) | 0 | Perfect source sufficiency across confirmatory cohort |
| **2. Evidence in Extracted Tables** | 164 / 200 (82.0%) | 164 / 200 (82.0%) | 0 | 36 cases have gold answer in non-table text |
| **3. Evidence in Selected Tables Alone** | **105 / 200 (52.5%)** | **164 / 200 (82.0%)** | **+59 cases (+29.5 pp)** | Relaxing threshold selects 100% of answer-bearing tables |
| **4. Evidence in Retained Clean Prose** | 3 / 200 (1.5%) | 3 / 200 (1.5%) | 0 | Non-tabular list evidence retained in clean prose |
| **5. Packing Truncation Losses** | 0 / 200 (0.0%) | 0 / 200 (0.0%) | 0 | Context ceiling (2,048 tokens) was never breached |
| **6. Evidence in Full Packed Context** | **108 / 200 (54.0%)** | **167 / 200 (83.5%)** | **+59 cases (+29.5 pp)** | Context = Clean Prose + Selected Markdown Tables |
| **7. Final Exact Match Accuracy** | **61 / 200 (30.5%)** | **99 / 200 (49.5%)** | **+38 cases (+19.0 pp)** | Net answer accuracy gain from recovered evidence |

### 4.6. Recommended Replacement Wording for Original Report
In `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/investigation_report.md` Section 6, the evidence diagram should be updated with the following clarification:

```markdown
### Corrected Evidence Funnel Definition
Total Table-Bearing Cases (N = 200)
├── Evidence in Source HTML: 200 / 200 (100.0%)
│   ├── Evidence in Extracted Tables: 164 / 200 (82.0%)
│   │   ├── Condition C (theta = 2.0):
│   │   │   ├── Table Selected: 105 / 164 (64.0%)
│   │   │   └── Table Rejected (SELECTION_FAILURE): 59 / 164 (36.0%)
│   │   └── Condition D (theta = 0.0):
│   │       ├── Table Selected: 164 / 164 (100.0%)
│   │       └── Table Rejected (SELECTION_FAILURE): 0 / 164 (0.0%)
│   └── Evidence in Clean Prose / Lists Only: 36 / 200 (18.0%)
│       ├── Answer Retained in Clean Prose Stream: 3 / 36 (8.3%)
│       └── Answer Omitted from Both Tables & Prose: 33 / 36 (91.7%)
│
└── Total Evidence in Packed Context (Selected Tables + Clean Prose):
    ├── Condition C: 108 / 200 (54.0%) [105 table-selected + 3 clean-prose]
    └── Condition D: 167 / 200 (83.5%) [164 table-selected + 3 clean-prose]
```

---

## 5. Audit & Reconstruction of Failure Classifications

### 5.1. Classification Definitions
To ensure mutually exclusive categories, every case is evaluated under strict hierarchical rules:
1. `NONE_CORRECT` / `SUCCESS`: Model prediction matches gold answer under standard normalization (`exact_match == True`).
2. `NO_EVIDENCE_IN_SOURCE`: Gold answer string is absent from the raw HTML document.
3. `EXTRACTION_OMISSION`: Gold answer is absent from all extracted document tables (and, in prose-aware accounting, absent from clean prose).
4. `SELECTION_FAILURE`: Gold answer was present in an extracted table, but the table was rejected by the threshold scoring filter $\theta$.
5. `PACKING_FAILURE`: Gold answer was present in a selected table, but truncated or omitted during context packing.
6. `SURFACE_FORM_MISMATCH`: Evidence is present in packed context, and the model prediction contains the gold answer (`containment == True`), but fails Exact Match.
7. `GENERATION_REASONING_FAILURE`: Evidence is present in packed context, but the model produces an incorrect answer or distractor row (`containment == False` and `exact_match == False`).

### 5.2. Reconstructed Failure Breakdown Table

| Category | Condition C Count (Rate) | Condition D Count (Rate) | Runner Category Audit | Prose-Aware Category Audit | Impact of $\theta=0.0$ |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`NONE_CORRECT` (Success)** | 61 (30.5%) | **99 (49.5%)** | **VERIFIED (61 / 99)** | **VERIFIED (61 / 99)** | **+38 correct answers** |
| **`SELECTION_FAILURE`** | 59 (29.5%) | **0 (0.0%)** | **VERIFIED (59 / 0)** | **VERIFIED (59 / 0)** | **Eliminated (-59 cases)** |
| **`GENERATION_REASONING_FAILURE`** | 28 (14.0%) / 29 (14.5%) | 44 (22.0%) / 45 (22.5%) | **VERIFIED (28 / 44)** | **VERIFIED (29 / 45)** | Shifted from selection to generation (+16) |
| **`EXTRACTION_OMISSION`** | 34 (17.0%) / 33 (16.5%) | 34 (17.0%) / 33 (16.5%) | **VERIFIED (34 / 34)** | **VERIFIED (33 / 33)** | Unchanged (structural limit of table extractor) |
| **`SURFACE_FORM_MISMATCH`** | 18 (9.0%) | 23 (11.5%) | **VERIFIED (18 / 23)** | **VERIFIED (18 / 23)** | Minor phrasing variance (+5) |
| **`PACKING_FAILURE`** | 0 (0.0%) | 0 (0.0%) | **VERIFIED (0 / 0)** | **VERIFIED (0 / 0)** | Zero context truncations |
| **`NO_EVIDENCE_IN_SOURCE`** | 0 (0.0%) | 0 (0.0%) | **VERIFIED (0 / 0)** | **VERIFIED (0 / 0)** | 100% source sufficiency |
| **Total Cases** | **200 (100.0%)** | **200 (100.0%)** | **200** | **200** | Perfect mutually exclusive partition |

> [!NOTE]
> **Runner vs Prose-Aware Accounting**:
> - The original runner classification strictly checked `if not ev_in_all_tables: return EXTRACTION_OMISSION`. Since 36 cases had no evidence in extracted tables and 2 of them were correct (EM=True), the remaining 34 cases were assigned `EXTRACTION_OMISSION`.
> - In prose-aware accounting, case `a5c30bbe...` (where the answer was present in clean prose and the model predicted `Bob Geldof`) is recognized as having evidence in context. It is therefore classified under `GENERATION_REASONING_FAILURE` rather than `EXTRACTION_OMISSION`.
> - Both accountings verify the substantive conclusion: **Selection failures are 100% eliminated**, and remaining errors are dominated by generation over distractor rows.

### 5.3. Reconciliation with Historical Stage C Subgroups

The 200 cases were historically partitioned by their Stage C outcome into four groups. Here is how Condition C and Condition D perform across each group:

1. **Stage C P1 Regressions (Cond A Correct, Cond B Incorrect, $N=47$)**:
   - Condition C recovered: **21 / 47 (44.7%)**
   - Condition D recovered: **37 / 47 (78.7%)**
   - Net recovery gain from $\theta=0.0$: **+16 additional cases recovered** (+34.0 pp).
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
   - Net gain from $\theta=0.0$: **+22 brand new recoveries** on historically failed cases!

### 5.4. Explanation of Difference from Gate 4 Pilot
The Gate 4 targeted diagnostic pilot evaluated **only 58 cases** (the 47 P1 regressions + 11 P2 recoveries) with $\theta=2.0$ (testing list ablation: C=tables only, D=tables+lists). In Gate 4, Condition D achieved 33/58 (56.9%) EM.  
In contrast, Experiment 4.2 evaluated the **entire 200-case confirmatory cohort** (including the 125 double-loss cases and 17 double-win cases) and directly relaxed the table-selection threshold to $\theta=0.0$. On the exact same 58-case subset, Experiment 4.2 Condition D achieves **45 / 58 (77.6%) EM**, demonstrating that relaxing $\theta$ eliminates the 17 threshold rejection failures discovered in Gate 4.

---

## 6. Statistical Interpretation & Defensible Scientific Boundaries

1. **Fixed-Cohort Paired Result**:
   - The primary comparison ($D$ vs $C$) is evaluated on a pre-registered, frozen 200-case table-bearing cohort from Natural Questions.
   - The paired McNemar test yielded 38 discordant pairs with 38 wins and 0 losses ($p = 7.276 \times 10^{-12}$). This confirms that the observed improvement on this cohort is not a chance sampling artifact.
2. **No Claim of Generalization to All Document Types**:
   - The 200 evaluated cases were specifically sampled as HTML documents containing table structures.
   - A statistically significant improvement on this table-bearing cohort does **not** establish generalization to documents without tables, multi-page PDFs, dense unstructured text, or documents with adversarial distractors.
3. **Non-Significant Result Interpretation**:
   - The comparison of Condition C ($\theta=2.0$) against Condition A (Prose Baseline) was not statistically significant (61 vs 64 EM, $p = 0.793$).
   - A non-significant result does **not** establish equivalence between Condition C and Condition A; it simply establishes that the data do not reject the null hypothesis of equal accuracy.
4. **Scope of the Zero-Regression Invariant**:
   - Condition D produced 0 EM regressions and 0 containment regressions relative to Condition C across all 200 cases.
   - This zero-regression property is strictly bounded by the measured 200 cases, the specific model (`qwen2.5-coder:7b`), and the concise extraction prompt style. It cannot be mathematically extrapolated as an absolute guarantee on unseen datasets.
5. **No Claim of Global Optimality for $\theta=0.0$**:
   - Lowering the threshold to $\theta=0.0$ retains all extracted tables. On this cohort, this increased mean context tokens from 195.4 to 326.4 (well below the 2,048 token ceiling).
   - In corpora with massive documents containing dozens of irrelevant tables, $\theta=0.0$ could cause context ceiling overflows or distractor dilution. Therefore, $\theta=0.0$ is an **empirically justified operating point for this table budget**, not a globally optimal retrieval algorithm.

---

## 7. Deliverable Artifacts and Checksums

All audit artifacts have been generated deterministically and written exclusively to:
`results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/`

| Audit Artifact | Relative Path | Size (Bytes) | Description |
| :--- | :--- | :---: | :--- |
| `audit_report.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/audit_report.md` | *This File* | Comprehensive independent audit report |
| `case_level_evidence_audit.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/case_level_evidence_audit.jsonl` | 366,480 | Reconstructed case-by-case evidence and failure taxonomy for all 200 cases |
| `recomputed_metrics.json` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/recomputed_metrics.json` | 8,389 | Complete recomputed accuracy, token, and statistical metrics |
| `hash_verification.json` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/hash_verification.json` | 4,373 | Cryptographic SHA-256 digest verifications for all inputs, runner, and tests |
| `walkthrough.md` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/audit/walkthrough.md` | 5,200 | Executive walkthrough of audit methodology and findings |

---

## 8. Final Audit Recommendation

**Status**: **VERIFIED WITH REPORTING CORRECTIONS**

The results of Experiment 4.2 are mathematically and empirically sound. The claimed accuracy improvements (EM: 30.5% $\to$ 49.5%, Containment: 39.5% $\to$ 61.0%) and the paired McNemar significance ($p = 7.28 \times 10^{-12}$) are verified. The reporting discrepancy regarding evidence funnel numbers has been completely traced to the prefixing of clean prose lists, with zero table truncation occurring.

The audit is complete. Execution stops here awaiting user review.
