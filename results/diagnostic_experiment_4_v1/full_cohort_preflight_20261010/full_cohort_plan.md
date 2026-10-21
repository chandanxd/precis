# Précis Full-Cohort Evaluation Plan: Structural Table Retention & Content-List Extraction

**Document Version**: 1.0 (Pre-Registered Plan)  
**Date**: October 10, 2026  
**Status**: Pre-Flight Proposal (Awaiting Explicit Execution Approval)  
**Cohort**: Frozen 200-Case Table-Bearing Confirmatory Cohort  
**Target Runner**: `scripts/eval_experiment_4_4_full_cohort.py` (Candidate Name)  
**Output Directory Target**: `results/diagnostic_experiment_4_v1/full_cohort_evaluation_20261010/`  

---

## 1. Objective and Scientific Scope

The objective of this full-cohort evaluation is to determine whether augmenting the structural table-retention pipeline ($\theta=0.0$) with an isolated HTML content-list extractor (`<ul>` and `<ol>`) improves end-to-end question answering accuracy on the **frozen 200-case table-bearing confirmatory cohort** without causing regressions on baseline-success cases.

### Core Scientific Questions
1. **Confirmatory Accuracy**: Does adding extracted content lists to retained tables improve Exact Match (EM) over the table-only condition ($\theta=0.0$) on the complete, unbiased 200-case table-bearing cohort?
2. **Regression Safety**: Does the presence of extracted lists introduce distractor interference, context competition, or attention dilution that regresses cases previously answered correctly by the prose baseline (Condition A) or the table-retention condition (Condition D)?
3. **Net System Competitiveness**: Does Condition E finally outperform the clean prose baseline (Condition A) on the 200-case table-bearing cohort, reversing the net regression observed in Stage C?

---

## 2. Experimental Conditions

The evaluation will compare five strictly controlled conditions across all 200 cases:

| Condition | Name | Description | Provenance / Source | Inference Needed |
| :---: | :--- | :--- | :--- | :---: |
| **A** | `cond_a_prose_baseline` | Raw HTML with Coref + Clean Prose SVOA | Reused from Stage C records | 0 (Frozen) |
| **B** | `cond_b_stage_c_decomp` | Decompiled prose with structured adapter | Reused from Stage C records | 0 (Frozen) |
| **C** | `cond_c_retention_theta2` | Structural table retention at $\theta=2.0$ | Reused from Exp 4.2 records | 0 (Frozen) |
| **D** | `cond_d_retention_theta0` | Structural table retention at $\theta=0.0$ | Reused from Exp 4.2 records | 0 (Frozen) |
| **E** | `cond_e_tables_and_lists` | Retention at $\theta=0.0$ + Content-List Extractor | 31 reused from Gate 2; 169 new | **169 calls** |

---

## 3. Prediction Reuse & Inference Budget

To preserve compute resources, guarantee bit-for-bit reproducibility, and eliminate rerun variance:

1. **Conditions A, B, C, D (100% Frozen)**:
   - All 200 predictions for Conditions A, B, and C will be loaded directly from `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl`.
   - All 200 predictions for Condition D will be loaded directly from `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl`.
   - Zero model inference will be executed for Conditions A–D.

2. **Condition E (Targeted Execution)**:
   - Exactly **31 cases** were already evaluated under this exact condition, code, prompt, and model configuration during Gate 2 (`stage_2b_eval_records.jsonl`). These 31 records will be verified and reused bit-identically.
   - Exactly **169 cases** remain to be evaluated under Condition E.
   - **Total Generation Budget**: Exactly **169 model inferences**.

---

## 4. Controlled Experimental Invariants

The evaluation harness will enforce strict invariance across all dimensions:

1. **Model & Daemon**:
   - Model: `qwen2.5-coder:7b` via local Ollama daemon.
   - Context window: 4,096 tokens (Ollama parameter: `num_ctx: 4096`).
2. **Decoding Parameters**:
   - `temperature`: 0.0 (greedy decoding).
   - `top_p`: 0.9.
   - `seed`: 42.
   - `max_tokens`: 512.
3. **Prompt Template**:
   - Concise Natural Questions prompt (`CONCISE_PROMPT_TEMPLATE`), invariant across all conditions:
     ```
     Answer the following question based on the provided context.
     Be concise and extract the exact answer directly from the context.
     If the answer cannot be found in the context, output "Insufficient information".

     Context:
     {context}

     Question: {question}
     Answer:
     ```
4. **Context Construction & Ceiling**:
   - Clean prose is prepended.
   - Candidate tables scored at $\theta=0.0$ are appended.
   - Non-boilerplate content lists (`<ul>`/`<ol>`) extracted via `diagnostic_list_extractor.py` are appended as Markdown lists.
   - Strict hard ceiling: **2,048 estimated tokens**. If total context exceeds 2,048 tokens, subsequent blocks are omitted with explicit telemetry logging.
5. **Scoring Invariants**:
   - Strict Exact Match (`check_exact_match_v2`): lowercase, punctuation strip, article strip, whitespace normalization.
   - Containment (`check_containment_v2`): normalized gold substring presence in normalized prediction.
   - ROUGE-L.

---

## 5. Pre-Registered Endpoints and Statistical Methodology

### 5.1 Primary Endpoint
- **Exact Match (EM)** accuracy across all 200 cases under Condition E compared to Condition D.

### 5.2 Secondary Endpoints
- **Containment** accuracy across all 200 cases.
- **Net Discordant Transitions** against Condition A (Prose Baseline) and Condition D (Table-Only).
- **Regression Count on Baseline Successes**:
  $$\text{Regressions}_{E < D} = \sum_{i=1}^{200} \mathbf{1}(\text{EM}_D(i) = \text{True} \land \text{EM}_E(i) = \text{False})$$
  $$\text{Regressions}_{E < A} = \sum_{i=1}^{200} \mathbf{1}(\text{EM}_A(i) = \text{True} \land \text{EM}_E(i) = \text{False})$$

### 5.3 Hypothesis Testing & Significance
- **Statistical Test**: Exact two-tailed McNemar test on paired discordant binary outcomes ($b = \text{wins}$, $c = \text{losses}$):
  $$p = 2 \times \sum_{k=b}^{b+c} \binom{b+c}{k} 0.5^{b+c} \quad (\text{for } b > c)$$
- **Confidence Intervals**: Exact Binomial 95% confidence interval on discordant difference $(b - c) / N$.
- **Significance Level**: $\alpha = 0.05$.

---

## 6. Pre-Registered Diagnostic Subgroup Analysis

To maintain historical continuity and understand where performance gains or losses originate, results will be stratified into three mutually exclusive subgroups:

1. **Stratum 1: Original Stage C Regressions ($N=47$)**:
   Cases where Condition A was correct and Condition B was incorrect in Stage C. (Measures recovery of P1 regressions).
2. **Stratum 2: Original Stage C Recoveries ($N=11$)**:
   Cases where Condition A was incorrect and Condition B was correct in Stage C. (Measures preservation of P2 recoveries).
3. **Stratum 3: Remaining Table-Bearing Cases ($N=142$)**:
   - `both_loss` ($N=125$): Both A and B were incorrect in Stage C.
   - `both_win` ($N=17$): Both A and B were correct in Stage C.
4. **Diagnostic Focus Subset ($N=31$)**:
   The 31 Gate 2 verified list-omission cases will be tracked separately to ensure that the 11 wins observed in the targeted pilot are replicated without drift.

> [!NOTE]
> All subgroup analyses are pre-declared as exploratory/diagnostic. The primary decision criterion remains the aggregate 200-case performance.

---

## 7. Context & Generation Telemetry Accounting

The runner will record complete case-level telemetry for all 200 cases:

1. **Context Components (Estimated Tokens)**:
   - `clean_prose_tokens`: Tokens from clean prose.
   - `table_tokens`: Tokens from table chunks.
   - `list_tokens`: Tokens from extracted list blocks.
   - `total_context_tokens`: Sum of context tokens.
   - `ceiling_violated`: Boolean flag indicating if 2,048 token limit was reached.
2. **Extractor Mechanics**:
   - `content_list_blocks_found`: Total HTML list blocks detected.
   - `boilerplate_lists_filtered`: Navigation and footer link farms excluded.
   - `list_blocks_packed`: Non-boilerplate lists packed into prompt.
   - `list_items_packed`: Total `<li>` elements formatted.
3. **Model Telemetry**:
   - `full_prompt_model_tokens`: Exact token count returned by model tokenizer.
   - `generated_tokens`: Tokens generated by model.
   - `latency_ms`: Response latency in milliseconds.

---

## 8. Failure-Handling and Robustness Rules

To prevent data corruption, partial runs, or biased imputation:

1. **Explicit Inference Statuses**:
   Every case must be assigned one of three statuses:
   - `success`: Model generated a valid text response.
   - `failed`: HTTP connection error, daemon timeout, or process failure.
   - `unscorable`: Empty response or malformed payload.
2. **Strict Non-Imputation Rule**:
   - Failed or unscorable cases are **never imputed as False** in the accuracy score.
   - Failed cases remain in the denominator, and the aggregate report will publish:
     * Strict Completion Denominator ($N=200$)
     * Scorable Denominator ($N_{\text{scorable}} = 200 - N_{\text{failed}}$)
     * If $N_{\text{failed}} > 0$, the run is flagged as incomplete.
3. **Idempotent Checkpointing**:
   - The runner must record completed case JSONL records immediately to disk.
   - If the run is interrupted, re-invoking the runner will detect existing completed records and skip them, only generating the remaining uncompleted cases.
4. **Preflight Verification**:
   - Before executing inference, the runner will verify SHA-256 hashes of all input files.
   - The runner will verify that Ollama is online, has the correct model loaded, and responds to a dummy probe.

---

## 9. Pre-Registered Production Promotion Criteria

Following the execution of the 200-case evaluation, the candidate system (Condition E) will be evaluated against the following strict decision thresholds:

| Decision | Criteria |
| :---: | :--- |
| **PROCEED TO PRODUCTION INTEGRATION** | 1. Condition E achieves statistically significant EM improvement over Condition D ($p < 0.05$).<br>2. Net Exact Match on Condition E is $\ge$ Condition A (prose baseline) across the full 200 cases.<br>3. Regressions on Condition D successes ($\text{Losses}_{E < D}$) are outnumbered by gains ($\text{Wins}_{E > D} \ge 2 \times \text{Losses}_{E < D}$).<br>4. Zero token ceiling violations across all 200 cases. |
| **REFINE EXTRACTOR / PACKING** | 1. Condition E achieves positive net EM, but misses statistical significance ($p \ge 0.05$).<br>2. OR regressions on table-heavy queries indicate context competition that can be resolved via priority ranking. |
| **REJECT CANDIDATE** | 1. Condition E causes net negative accuracy relative to Condition D or Condition A.<br>2. OR list distractor interference causes substantial regressions on baseline successes. |

---

## 10. Execution Safeguards

- **Zero Modifications to Production Code**: `backend/src/precis/` will not be altered during this evaluation.
- **Execution Confinement**: Inference is restricted strictly to the 169 remaining cases.
- **Review Requirement**: This plan is pre-registered and halted. Execution will begin only upon explicit user authorization.
