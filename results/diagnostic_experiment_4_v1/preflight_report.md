# Experiment 4: Controlled End-to-End Generation Pilot — Preflight Report (Gate 1)

**Experiment Identifier**: `diagnostic_experiment_4_v1`  
**Evaluation Scope**: Gate 1 Mandatory Preflight Inspection  
**Date**: 2026-10-10  
**Status**: Completed — **Awaiting Explicit Review & Approval**  
**Execution Constraints**: Zero Code Modifications, Zero LLM Inference Executed  

---

## 1. Executive Summary & Preflight Verdict

### Gate 1 Verdict: `GO (CONDITIONAL ON REVIEW & OLLAMA ACTIVATION)`

```
+---------------------------------------------------------------------------------------------------------+
|                                      PREFLIGHT VERDICT: GO                                              |
|                                                                                                         |
|  All 7 mandatory preflight verification checks PASSED:                                                  |
|  1. Frozen 200-case table/list confirmatory cohort is 100% identical across all manifests and records.  |
|  2. Canonical model, prompt, decoding hyperparameters, normalization, and scoring rules are verified.   |
|  3. Exact case sets reconstructed: 47 Stage C regressions and 11 Stage C recoveries are strictly        |
|     disjoint (intersection = 0); targeted pilot cohort = exactly 58 unique cases.                      |
|  4. Original Condition A and Condition B predictions in Stage C records are 100% complete and verified  |
|     for direct reuse without re-running model inference.                                                |
|  5. D.2 outputs cleanly separate conversion, selection, row retention, chunking, and packing.           |
|  6. Established interfaces (`generate_answer`, `check_exact_match`, etc.) are recoverable and reusable.  |
|  7. Destination directory `results/diagnostic_experiment_4_v1/` is isolated with zero overwrite risk.   |
|                                                                                                         |
|  OPERATIONAL NOTE:                                                                                      |
|  Local Ollama model weights for `qwen2.5-coder:7b` are verified present on the host filesystem.         |
|  The Ollama HTTP daemon (port 11434) is currently offline and must be started prior to Gates 3 and 4.   |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Input Provenance & Cryptographic Hashes

All source inputs from Experiment 3 Stage C, Diagnostic Probe D.1, Diagnostic Probe D.2, and the benchmark dataset were cryptographically verified against preflight checksums:

| File Artifact | Repository Path | SHA-256 Checksum | Verification Status |
| :--- | :--- | :--- | :--- |
| **Sample Manifest** | `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** |
| **Stage C Eval Records** | `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** |
| **Stage D.1 Evidence Audit** | `results/diagnostic_structural_decompilation_v3/stage_d1_evidence_audit.jsonl` | `916d9ae633fba042c464ad7739f619ce38be733ef6c79b828b88a74ab5c673b7` | **MATCH** |
| **Stage D.1 Sweep Results** | `results/diagnostic_structural_decompilation_v3/stage_d1_retrieval_sweep.jsonl` | `9885b3a5b9fdf2466aba6609e9f940d4046a32fe091ddd05f42abf36f865b2b5` | **MATCH** |
| **Stage D.1 Summary** | `results/diagnostic_structural_decompilation_v3/stage_d1_summary.json` | `c312cb9aaac80e6ea56f6d90410a9e521dfedc18015f64c51b532c0d63b0e73b` | **MATCH** |
| **Stage D.2 Case Audit** | `results/diagnostic_structural_decompilation_v3/stage_d2_case_audit.jsonl` | `2e13ccec907f7e5db2d0e5c229dbc283db00c2cc2c68e85e6a793858c03af470` | **MATCH** |
| **Stage D.2 Table Audit** | `results/diagnostic_structural_decompilation_v3/stage_d2_table_conversion_audit.jsonl` | `05414212fa8b7a571512a1282a9530de32b7bdf9a5e59cfbf022ecf84341d430` | **MATCH** |
| **Stage D.2 Summary** | `results/diagnostic_structural_decompilation_v3/stage_d2_summary.json` | `00b97c858c346691282bb29c482deb1a13461b80ebfb43f95fd002a872fea6a8` | **MATCH** |
| **Stage C Eval Harness** | `scripts/eval_structural_decompilation_v3.py` | `ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4` | **MATCH** |
| **Evaluation Benchmark** | `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** |

---

## 3. Cohort Verification & Case Set Reconstruction

### Population Breakdown (200-Case Frozen Confirmatory Stratum)
The confirmatory cohort consists of exactly the 200 cases labeled `stratum: "table_bearing"` in `sample_manifest.jsonl`.
Analysis of paired records in `eval_records_stage_c.jsonl` shows the exact distribution:

```
Total Confirmatory Cohort Cases: 200
├── Condition A Correct (Exact Match):  64 / 200 (32.0%)
└── Condition B Correct (Exact Match):  28 / 200 (14.0%)

Paired EM Quadrants:
├── Quadrant 1: Regressions (A=True,  B=False): 47 cases (23.5%)
├── Quadrant 2: Recoveries  (A=False, B=True):  11 cases  (5.5%)
├── Quadrant 3: Concordant  (A=True,  B=True):  17 cases  (8.5%)
└── Quadrant 4: Concordant  (A=False, B=False): 125 cases (62.5%)
```

### Targeted Pilot Cohort Reconciliation (Section 3 of Experiment 4 Protocol)
- **Stage C EM Regressions ($N_1$)**: 47 unique cases
- **Stage C EM Recoveries ($N_2$)**: 11 unique cases
- **Intersection ($N_1 \cap N_2$)**: **0 cases** (strictly disjoint; binary EM prevents simultaneous win and loss)
- **Targeted Unique Union ($N_1 \cup N_2$)**: **58 unique cases**
- **Completeness**: All 58 cases exist in `sample_manifest.jsonl`, `eval_records_stage_c.jsonl`, and `stage_d2_case_audit.jsonl`. Zero cases are duplicated, missing, or unscorable.

### Secondary Containment Accounting across Cohort
- Condition A Containment: 87 / 200 (43.5%)
- Condition B Containment: 39 / 200 (19.5%)
- Containment Regressions ($Cont_A=1, Cont_B=0$): 60 cases
- Containment Recoveries ($Cont_A=0, Cont_B=1$): 12 cases
- Both Containment Correct: 27 cases; Both Incorrect: 101 cases.

---

## 4. Reusability of Condition A & Condition B Predictions

The paired evaluation records in `eval_records_stage_c.jsonl` contain complete inference outputs and evaluation scores for every case:

- **Condition A (Reference Naive RAG)**:
  - `predicted_answer`: Extracted string prediction from Ollama.
  - `exact_match`: Boolean ground truth comparison.
  - `containment`: Boolean substring comparison.
  - `context_tokens`: Measured subword token count.
  - `status`: `"success"` for all 58 targeted cases (0 failures).
- **Condition B (Stage C Structural Decompilation Baseline)**:
  - `predicted_answer`: Extracted string prediction from Ollama.
  - `exact_match`: Boolean ground truth comparison.
  - `containment`: Boolean substring comparison.
  - `context_tokens`: Measured subword token count.
  - `struct_facts`: Structured propositions count.
  - `status`: `"success"` for all 58 targeted cases (0 failures).

**Provenance Determination**: Because Condition A and Condition B are frozen reference baselines with deterministic temperature 0.0 outputs preserved in `eval_records_stage_c.jsonl`, their predictions will be reused directly in Experiment 4 without re-running model inference.

---

## 5. D.2 Intermediate Representation Traceability

The Stage D.2 audit records (`stage_d2_case_audit.jsonl` and `stage_d2_table_conversion_audit.jsonl`) provide complete, verified intermediate data for the proposed interventions:

1. **Source Table Conversion**:
   - 164 source tables evaluated across the 200 cases.
   - Conversion success rate: 100.0% (164/164).
   - Row preservation: 2,830 / 2,830 rows (100.0% preservation; zero lost rows).
   - Headers: 63 explicit column headers preserved, 99 title banners mapped to table captions, 2 generated defaults.
2. **Table Selection Threshold ($\theta=2.0$)**:
   - Condition C strictly uses the **same** table selection policy as Condition B (`score_and_select_tables` with threshold $\ge 2.0$).
   - Distinguishes tables that passed the threshold from those rejected.
3. **Contiguous Row Chunking**:
   - Tables exceeding the 500-token per-table cap are chunked contiguously with repeated headers.
   - Every chunk specifies `[Rows start-end]` and maps rendered rows to 0-indexed source rows.
4. **Context Packing**:
   - Enforces the 2048-token context ceiling. Zero ceiling violations observed in D.2 (max tokens = 1,215).

---

## 6. Model, Prompt, and Harness Interface Verification

### Canonical Benchmark Parameters
From `scripts/eval_structural_decompilation_v3.py` and `eval_records_stage_c.jsonl`:

| Hyperparameter | Frozen Value | Source Location |
| :--- | :--- | :--- |
| **Model** | `qwen2.5-coder:7b` | `eval_structural_decompilation_v3.py:75` |
| **Temperature** | `0.0` | `eval_structural_decompilation_v3.py:76` |
| **Top-P** | `0.9` | `eval_structural_decompilation_v3.py:77` |
| **Max Tokens** | `512` | `eval_structural_decompilation_v3.py:78` |
| **Seed** | `42` | `eval_structural_decompilation_v3.py:79` |
| **Token Ceiling** | `2048` | `eval_structural_decompilation_v3.py:80` |
| **Prompt Style** | `"concise"` | `eval_structural_decompilation_v3.py:1030` |
| **Prompt Template** | `CONCISE_PROMPT_TEMPLATE` | `precis.pipeline.inference:50-69` |

### Scoring & Normalization Implementations
- **Exact Match**: `check_exact_match()` from `eval_table_selection_v2.py`, calling `compute_exact_match()` and `normalize_answer()` in `precis.evaluation.metrics`.
- **Containment**: `check_containment()` from `eval_table_selection_v2.py`, calling `contains_answer()`.
- **ROUGE-L**: `check_rouge_l()` from `eval_table_selection_v2.py`, calling `compute_rouge_l()` in `precis.evaluation.metrics`.

### Interface Reuse Plan
To eliminate implementation drift, Experiment 4 will import and reuse:
1. `generate_answer()` from `precis.pipeline.inference` for Ollama dispatch.
2. `build_prompt()` with `prompt_style="concise"` from `precis.pipeline.inference`.
3. `check_exact_match`, `check_containment`, and `check_rouge_l` from `eval_table_selection_v2`.
4. `render_gfm_table` and `render_list_items` verified during Diagnostic Probe D.2.

---

## 7. Operational Status & Environment Inspection

1. **Ollama Executable**: Installed and verified at `/usr/local/bin/ollama`.
2. **Local Model Weights**: Verified present at `/usr/share/ollama/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5-coder/7b`.
3. **Ollama Daemon Status**: Currently **OFFLINE** (port 11434 unreachable).
   - *Requirement for Gate 3/4*: The daemon must be launched (`ollama serve &`) prior to running smoke tests or generation pilots.
4. **Output Directory Isolation**: `results/diagnostic_experiment_4_v1/` has been created as a new, isolated directory. No pre-existing files will be overwritten.
5. **Working Tree Safety**: Zero files under `backend/src/precis/` or tracked benchmark files were modified.

---

## 8. Definition of Experimental Conditions for Experiment 4

All conditions will be evaluated over the identical 58 cases in the targeted union:

- **Condition A (Reference Naive RAG)**: Reused directly from `eval_records_stage_c.jsonl`.
- **Condition B (Stage C Baseline Decompilation)**: Reused directly from `eval_records_stage_c.jsonl`.
- **Condition C (D.2 Structural Retention — Table-Only)**:
  - Table selection threshold: $\theta = 2.0$ (identical to Condition B).
  - Table representation: Compact GFM Markdown tables with 500-token per-table cap and contiguous row chunking.
  - Lists: Excised from context.
  - Clean prose: Preserved if present.
  - Context packing: Up to 2048 tokens.
  - Inference: New model dispatch via `generate_answer()`.
- **Condition D (D.2 Structural Retention + Raw Lists)**:
  - Table selection threshold: $\theta = 2.0$.
  - Table representation: GFM Markdown tables (500-token cap).
  - Lists: Preserved as raw formatted list items (`- [Item N]: text`).
  - Clean prose: Preserved if present.
  - Context packing: Up to 2048 tokens.
  - Inference: New model dispatch via `generate_answer()`.

---

## 9. Sequential Execution Gate Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GATE 1: PREFLIGHT INSPECTION                                                │
│ Status: COMPLETED. Awaiting user review and explicit approval.             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Upon Approval)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ GATE 2: HARNESS & INTEGRITY TESTS                                           │
│ Action: Implement isolated runner script `scripts/eval_experiment_4_v1.py`  │
│         Validate output schemas, paired records, failure handling, tests.   │
│         ZERO inference executed. Deliver Gate 2 report. Stop for review.   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Upon Approval)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ GATE 3: SMOKE TEST (5 Explicit Cases)                                       │
│ Action: Start Ollama daemon. Run 5 explicitly identified test cases         │
│         across Conditions C and D. Validate end-to-end inference and logs.  │
│         Deliver Gate 3 report. Stop for review.                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Upon Approval)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ GATE 4: TARGETED GENERATION PILOT (58 Unique Union Cases)                   │
│ Action: Execute Conditions C and D across all 58 targeted pilot cases.      │
│         Pair with verified A and B predictions.                             │
│         Calculate McNemar's exact tests, EM, Containment, ROUGE-L, tokens.  │
│         Document all newly introduced regressions. Stop for review.         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Upon Approval)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ GATE 5: FULL-COHORT GENERATION (200 Cases)                                  │
│ Action: Evaluate complete confirmatory cohort only if Gate 4 is approved.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Unresolved Questions & Clarifications for Reviewer

Before proceeding to Gate 2, please confirm:
1. **Targeted Pilot Cohort**: Do you confirm the 58-case unique union ($47 \text{ regressions} + 11 \text{ recoveries}$) as the pilot scope for Gate 4?
2. **Ollama Execution Mode**: For Gates 3 and 4, do you approve starting the local Ollama daemon via `ollama serve` in the background?
3. **Statistical Significance Testing**: Do you approve McNemar's exact test (paired binary test of wins vs. losses) as the primary significance test for paired EM and Containment comparisons?

---

*Preflight report completed. Antigravity has stopped execution and will make no file modifications or run any model inference until this Gate 1 Preflight Report is reviewed and approved.*
