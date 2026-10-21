# Experiment 4 Gate 3: Audit and Reconciliation Report

**Experiment Identifier**: `diagnostic_experiment_4_v1`  
**Document**: Gate 3 Audit and Reconciliation Report  
**Date**: 2026-10-10  
**Status**: Completed — **Awaiting Explicit Approval Before Proceeding to Gate 4**  
**Execution Constraints Enforced**: Zero Additional LLM / Embedding Inference, Ollama Daemon Unaltered, Production Code Untouched, Original Gate 3 Artifacts Preserved Intact  

---

## 1. Executive Summary & Gate 4 Recommendation

### Gate 4 Recommendation: `GO FOR GATE 4 (TARGETED DIAGNOSTIC PILOT ONLY)`

```
+---------------------------------------------------------------------------------------------------------+
|                                    GATE 4 RECOMMENDATION: GO                                            |
|                                                                                                         |
|  1. Smoke-Test Cohort Reconciled:                                                                       |
|     - All 5 smoke-test cases derived directly against frozen Stage C records:                          |
|       * Case 1 (2c62d7eb): Both incorrect in Stage C (Cond A=False, Cond B=False).                      |
|       * Case 2 (a16cca39): Both incorrect in Stage C (Cond A=False, Cond B=False).                      |
|       * Case 3 (3f0497f4): Stage C EM regression (Cond A=True, Cond B=False).                           |
|       * Case 4 (16caa32e): Stage C EM recovery (Cond A=False, Cond B=True).                             |
|       * Case 5 (00d7c7cc): Stage C EM recovery (Cond A=False, Cond B=True).                             |
|     - Cases 1 & 2 are confirmed OUTSIDE the 58-case targeted union. They served as operational smoke    |
|       probes (originating from Diagnostic Probes D.1/D.2), NOT members of the targeted pilot cohort.   |
|     - Mislabeling in gate_2_report.md and gate_3_report.md prose corrected in this audit report.       |
|  2. Artifact Revalidation:                                                                              |
|     - All 5 case records and summary metrics recomputed from disk and 100% verified.                   |
|     - Zero schema violations; zero discrepancies in token, latency, EM, containment, or McNemar stats. |
|     - Cryptographic hashes for frozen inputs and Gate 3 artifacts verified bit-identical.              |
|  3. Interpretive Guardrails:                                                                            |
|     - Individual successes (Cases 1, 3, 5) are case-level observations consistent with the structural-  |
|       retention hypothesis, NOT definitive causal confirmations.                                        |
|     - Case 4 (wool producer) is documented as an explicit unresolved failure in Condition C & D.       |
|  4. Scope & Generalization Disclaimer:                                                                  |
|     - The 58-case cohort (47 regressions + 11 recoveries) is an outcome-selected diagnostic pilot,      |
|       NOT an unbiased population-level confirmatory benchmark.                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Audit of the Five Smoke-Test Cases

### 2.1. Frozen Baseline Classification Derivation

The 5 smoke-test cases were evaluated against the frozen benchmark inputs (`sample_manifest.jsonl` and `eval_records_stage_c.jsonl`). Their canonical classifications are derived strictly from their Stage C performance:

| # | Case ID | Question | Gold Answer | Stage C Cond A (Prose) | Stage C Cond B (Decomp) | Derived Canonical Classification | In 58-Case Union? |
| :-: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **1** | `2c62d7eb04924071959544f85e978b8b` | *who is the secretary of state for northern ireland* | Karen Bradley | `False` (EM=0, Cont=0) | `False` (EM=0, Cont=0) | **Both incorrect** | **NO** |
| **2** | `a16cca39f27e4d78a64de2d8285bc4bf` | *when will the next episode of my next guest needs no introduction* | May 31 , 2018 | `False` (EM=0, Cont=0) | `False` (EM=0, Cont=0) | **Both incorrect** | **NO** |
| **3** | `3f0497f4a228459c8b2201e7f871a520` | *where was gunsmoke to the last man filmed* | Tucson , Arizona | `True` (EM=1, Cont=1) | `False` (EM=0, Cont=0) | **Stage C EM regression** (Cond A win, Cond B loss) | **YES** |
| **4** | `16caa32e50d342878340cacefe5a417a` | *who is the leading african producer of wool* | South Africa | `False` (EM=0, Cont=0) | `True` (EM=1, Cont=1) | **Stage C EM recovery** (Cond A loss, Cond B win) | **YES** |
| **5** | `00d7c7cc7b534abeaf1f9dded1d3639b` | *who plays chris grandy in 13 going on 30* | Jim Gaffigan | `False` (EM=0, Cont=0) | `True` (EM=1, Cont=1) | **Stage C EM recovery** (Cond A loss, Cond B win) | **YES** |

### 2.2. Reconciliation with Prior Reports (`gate_2_report.md` & `gate_3_report.md`)

1. **Reconciliation of Case 1 (`2c62d7eb`)**:
   - *Previous Label in Report Prose*: Labeled as "P1 Regression — Secretary of State for Northern Ireland".
   - *Audit Finding*: This label was **factually inaccurate**. In the frozen Stage C records, Condition A generated *"Northern Ireland Secretary"* (`exact_match: False`), and Condition B generated *"The Right Honourable Northern Ireland Secretary"* (`exact_match: False`). Both conditions failed exact match.
   - *Record-Level Integrity*: In `eval_records_experiment_4.jsonl`, line 2, the runner correctly calculated `priority_cohort: "other"`. The runner's programmatic logic was correct; the discrepancy existed solely in the descriptive text of the reports.
   - *Provenance & Purpose*: Case 1 was chosen during Gate 2 because it was the flagship infobox table case in Diagnostic Probes D.1 and D.2 demonstrating header preservation (`TITLE_BANNER_TO_CAPTION`). It was included in the smoke test to verify table rendering, not as a regression-cohort sample. It is **not** a member of the 58-case union.

2. **Reconciliation of Case 2 (`a16cca39`)**:
   - *Previous Label in Report Prose*: Labeled as "P1 Regression — Next Guest Needs No Introduction".
   - *Audit Finding*: This label was **factually inaccurate**. In Stage C, both Condition A and Condition B emitted *"Insufficient information"* (`exact_match: False`).
   - *Record-Level Integrity*: In `eval_records_experiment_4.jsonl`, line 3, the runner correctly assigned `priority_cohort: "other"`.
   - *Provenance & Purpose*: Case 2 originated as a representative multi-row tabular episode list from Diagnostic Probe D.1. It is **not** a member of the 58-case union.

3. **Reconciliation of Cases 3, 4, 5**:
   - Case 3 (`3f0497f4`): Correctly confirmed as a **Stage C EM regression** ($A=1, B=0$). Member of the 47-case regression cohort.
   - Case 4 (`16caa32e`): Correctly confirmed as a **Stage C EM recovery** ($A=0, B=1$). Member of the 11-case recovery cohort.
   - Case 5 (`00d7c7cc`): Correctly confirmed as a **Stage C EM recovery** ($A=0, B=1$). Member of the 11-case recovery cohort.

---

## 3. Revalidation of Gate 3 Artifacts

An automated revalidation was conducted directly against `eval_records_experiment_4.jsonl` and `experiment_4_summary.json` without invoking model inference:

### 3.1. Record Count & Case Ordering
- **Total Case Records**: Exactly 5 case records (lines 2 through 6).
- **Header Line**: Line 1 contains `{"type": "run_header", "experiment_id": "diagnostic_experiment_4_v1", "dry_run": false, "total_cases": 5, ...}`.
- **Case Ordering**: 100% matched the authorized sequence:
  1. `2c62d7eb04924071959544f85e978b8b`
  2. `a16cca39f27e4d78a64de2d8285bc4bf`
  3. `3f0497f4a228459c8b2201e7f871a520`
  4. `16caa32e50d342878340cacefe5a417a`
  5. `00d7c7cc7b534abeaf1f9dded1d3639b`

### 3.2. Condition Statuses & Score Validity
Across all 5 cases and all 4 conditions ($5 	imes 4 = 20$ condition results):
- All 20 condition blocks report `status: "success"` with `error_message: null`.
- All 20 condition blocks have valid boolean `exact_match` and `containment` fields (`True` or `False`).
- All 20 condition blocks have valid float `rouge_l` fields ($0.0$ or $1.0$).
- Conditions C and D contain valid integers for `full_prompt_model_tokens` (> 0), `generated_tokens` (> 0), and `latency_ms` (> 0).

### 3.3. Reconciliation of Aggregate Metrics
Recomputing condition-level aggregates from the 5 case records exactly replicates `experiment_4_summary.json`:

| Metric | Cond A (Recalculated / Logged) | Cond B (Recalculated / Logged) | Cond C (Recalculated / Logged) | Cond D (Recalculated / Logged) | Discrepancy |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Exact Match Count** | 1 / 1 | 2 / 2 | 3 / 3 | 3 / 3 | None (0) |
| **Exact Match Rate** | 20.0% / 20.0% | 40.0% / 40.0% | 60.0% / 60.0% | 60.0% / 60.0% | None (0) |
| **Containment Count** | 1 / 1 | 2 / 2 | 3 / 3 | 3 / 3 | None (0) |
| **Containment Rate** | 20.0% / 20.0% | 40.0% / 40.0% | 60.0% / 60.0% | 60.0% / 60.0% | None (0) |
| **Mean ROUGE-L** | 0.200 / 0.200 | 0.400 / 0.400 | 0.600 / 0.600 | 0.600 / 0.600 | None (0) |
| **Mean Context Est Tokens** | 278.6 / 278.6 | 167.4 / 167.4 | 184.4 / 184.4 | 212.4 / 212.4 | None (0) |
| **Mean Full Prompt Tokens** | N/A | N/A | 454.6 / 454.6 | 489.0 / 489.0 | None (0) |
| **Mean Generated Tokens** | 0.0 / 0.0 | 0.0 / 0.0 | 4.2 / 4.2 | 4.2 / 4.2 | None (0) |

### 3.4. Reconstruction of McNemar Paired Tables
Reconstructing the paired $2 	imes 2$ contingency tables and exact two-sided binomial tests directly from per-case boolean arrays yields exact agreement with the summary file:

- **Cond C vs Cond A**:
  - Contingency: $a=1$ (both win), $b=2$ (C win, A loss: `2c62d7eb`, `00d7c7cc`), $c=0$ (C loss, A win), $d=2$ (both loss).
  - Discordant pairs: $n_{	ext{disc}} = 2$. Two-sided binomial test $p = 0.5000$. Matches summary: **YES**.
- **Cond C vs Cond B**:
  - Contingency: $a=1$ (both win), $b=2$ (C win, B loss: `2c62d7eb`, `3f0497f4`), $c=1$ (C loss, B win: `16caa32e`), $d=1$ (both loss).
  - Discordant pairs: $n_{	ext{disc}} = 3$. Two-sided binomial test $p = 1.0000$. Matches summary: **YES**.
- **Cond D vs Cond A**:
  - Identical to C vs A ($a=1, b=2, c=0, d=2, p=0.5000$). Matches summary: **YES**.
- **Cond D vs Cond B**:
  - Identical to C vs B ($a=1, b=2, c=1, d=1, p=1.0000$). Matches summary: **YES**.
- **Cond D vs Cond C**:
  - Contingency: $a=3, b=0, c=0, d=2$. Zero discordant pairs. Two-sided binomial test $p = 1.0000$. Matches summary: **YES**.

---

## 4. Corrected Interpretations & Observed Weaknesses

### 4.1. Avoidance of Over-Claiming on Smoke Test Cases
The 5-case smoke test was conducted to verify operational harness stability, GPU memory allocation, telemetry tracking, and non-null failure guards. Case-level outcomes must be interpreted cautiously:
- **Case 1 (`2c62d7eb` — Karen Bradley)**: The model correctly extracted "Karen Bradley" under Conditions C and D. This is an empirical observation consistent with the hypothesis that compact GFM table retention preserves structural facts better than SVOA decomposition, but it is **not** population-level proof.
- **Case 3 (`3f0497f4` — Tucson, Arizona)**: The recovery of the correct filming location aligns with the observation that decompilation in Condition B aggressively stripped context (down to 33 tokens), whereas Condition C retained the full infobox (250 tokens).

### 4.2. Explicit Documentation of Unresolved Weakness (Case 4)
In Case 4 (`16caa32e50d342878340cacefe5a417a` — *leading African producer of wool*):
- **Gold Answer**: `"South Africa"`.
- **Condition B (Decompilation)**: Succeeded (`exact_match: True`, 281 tokens) because its heuristic rule parsed the bulleted list into relational facts.
- **Condition C (Table-Only Retention)**: Failed (`exact_match: False`). Because the source document contained no HTML table matching the threshold, 0 tables were selected, resulting in an empty context (0 tokens) and an answer of *"Insufficient information"*.
- **Condition D (Table + List Retention)**: Failed (`exact_match: False`). Although 11 raw list items were packed into the context (126 tokens), the model still emitted *"Insufficient information"*.
- **Diagnostic Conclusion**: This case documents an explicit unresolved weakness: raw list item preservation is not a guaranteed remedy for list-based queries, and heuristic decompilation can occasionally outperform raw list retention when queries depend on synthesized list attributes.

---

## 5. Gate 4 Targeted Pilot Scope & Methodological Invariants

### 5.1. Exact Reconstruction of the 58-Case Union
The 58-case targeted diagnostic pilot cohort was independently validated against the frozen benchmark inputs:
- Total table-bearing confirmatory stratum: **200 cases**.
- Condition A successes / Condition B failures (P1 Regressions): **exactly 47 cases**.
- Condition A failures / Condition B successes (P2 Recoveries): **exactly 11 cases**.
- Intersection between regressions and recoveries: **exactly 0 cases** (strictly disjoint).
- Targeted unique union ($47 + 11$): **exactly 58 unique cases**.
- Dataset document presence: **58 / 58 present** in `backend/data/nq_subset/nq_dev.jsonl`.
- Zero missing, unexpected, or duplicate case IDs.

### 5.2. Methodological Clarification on Pilot vs Benchmark
It is essential to clarify the statistical nature of Gate 4:
> [!IMPORTANT]
> **DIAGNOSTIC PILOT DISCLAIMER**:
> The 58-case cohort is an **outcome-selected targeted cohort** constructed specifically from the discordant cases of Stage C (47 regressions where Condition B degraded accuracy, and 11 recoveries where Condition B improved accuracy).
> 
> Because this cohort is conditioned on past model discordance, it is **NOT an independent or unbiased confirmatory benchmark**, and its accuracy percentages cannot be interpreted as an unbiased estimate of general system performance over the broader population.
> 
> Paired statistical metrics (McNemar exact tests, discordant win/loss counts, risk differences, and odds ratios) will be computed to measure the directional treatment effect on this targeted stratum. However, these metrics describe only whether the proposed retention architecture reverses past regressions and preserves past recoveries within this specific diagnostic subset.

---

## 6. File Inventory & Cryptographic Checksums

All benchmark files, harness scripts, and output artifacts with exact file sizes and SHA-256 digests:

| Artifact | Repository Path | Size (Bytes) | SHA-256 Checksum | Purpose / Status |
| :--- | :--- | :---: | :--- | :--- |
| **Audit Report** | [`gate_3_reconciliation_audit_report.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_3_reconciliation_audit_report.md) | *(Post-write)* | *(Post-write)* | Current reconciliation audit document |
| **Gate 3 Report** | [`gate_3_report.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_3_report.md) | 17,592 | `c4d52be68b24436b7a70d3ba6af3104dbd411ac60bad427aa9aa6110cc5d4c69` | Original Gate 3 report (preserved untouched) |
| **Smoke Records** | [`gate_3_smoke_test/eval_records_experiment_4.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_3_smoke_test/eval_records_experiment_4.jsonl) | 22,981 | `eeba8c2ae944b5bec72a59871ed8b8186ed40549c0589a0cc1674401550cab21` | Frozen Gate 3 records (verified intact) |
| **Smoke Summary** | [`gate_3_smoke_test/experiment_4_summary.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_3_smoke_test/experiment_4_summary.json) | 15,365 | `1ac32db78a6d7aa065e3181dea090b6907bd2cea12558844bb620170317c0745` | Frozen Gate 3 summary (verified intact) |
| **Runner Harness**| [`eval_experiment_4_v1.py`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py) | 66,271 | `f228e41eb3d724380e20f2f84046f451f9a3862f57d49702ff4b4b6c9ac041dc` | Runner harness script |
| **Integrity Suite**| [`test_experiment_4_integrity.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_integrity.py) | 45,412 | `f27a0d5f5788b297f48845513975c6b1df1419e3c8280ed726390aae56b5d01d` | 21 passing integrity unit tests |
| **Manifest** | [`sample_manifest.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl) | 87,419 | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | Frozen benchmark manifest (bit-identical) |
| **Stage C Records**| [`eval_records_stage_c.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl) | 441,836 | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | Frozen Stage C predictions (bit-identical) |
| **Dataset** | [`nq_dev.jsonl`](file:///home/chandan/Projects/major-project/precis/backend/data/nq_subset/nq_dev.jsonl) | 1,481,215 | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | Canonical evaluation dataset (bit-identical) |

---

## 7. Safety Invariants & Stop Condition

1. **Zero Additional Inference**: No model inference has been initiated during this audit.
2. **Daemon Unchanged**: Ollama daemon was neither restarted nor modified.
3. **Production Isolation**: Zero modifications to `backend/src/precis/`.
4. **Original Files Untouched**: `gate_3_report.md` and all files under `gate_3_smoke_test/` remain byte-for-byte identical.
5. **Full Regression Test Suite**: 38/38 tests passing (`test_stage_c_safety_hardening.py` + `test_experiment_4_integrity.py`).

**Antigravity has stopped execution.** No further actions will be taken until explicit user approval is granted to proceed with Gate 4.
