# Experiment 4.5.6 Phase 2: Gated Live Confirmatory Evaluation Plan

**Plan Date**: 2026-10-10  
**Status**: **DRAFT / PENDING EXPLICIT USER AUTHORIZATION**  
**Execution Boundary**: **Phase 2 live inference will NOT run until authorized by the user.**

---

## 1. Objective and Hypothesis

The objective of Phase 2 is to determine whether the persistent structural-evidence subsystem (implemented in Experiments 4.5.2–4.5.4) successfully reproduces the end-to-end question answering gains of Experiment 4.4 when evaluated through the actual application path.

### Evaluation Hypothesis
- **Hypothesis $H_1$**: The persistent production path (**Condition F**) will significantly outperform Table Retention alone (**Condition D**, 49.5% EM) and match or closely approach the prototype in-memory list retention benchmark (**Condition E**, 54.0% EM).
- **Primary Statistical Test**: Exact two-sided McNemar test for paired binary outcomes between Condition F and Condition D ($N=200$).
- **Success Criteria**: Statistically significant net win count over Condition D ($p < 0.05$) and non-inferiority compared to Condition E.

---

## 2. Experimental Conditions and Inference Budget

| Condition ID | Pipeline Implementation | Feature Flag | Inference Calls Required | Data Source |
|:---:|:---|:---:|:---:|:---|
| **A** | Prose Baseline (Coref + Prose SVOA) | N/A | **0** | Reused from `eval_records_stage_c.jsonl` (200 records) |
| **B** | Stage C Decompiled Baseline | N/A | **0** | Reused from `eval_records_stage_c.jsonl` (200 records) |
| **C** | Table Retention at $\theta=2.0$ | N/A | **0** | Reused from Exp 4.2 `eval_records.jsonl` (200 records) |
| **D** | Table Retention at $\theta=0.0$ | N/A | **0** | Reused from Exp 4.2 `eval_records.jsonl` (200 records) |
| **E** | Prototype Tables + Content Lists | N/A | **0** | Reused from Exp 4.4 `eval_records.jsonl` (200 records) |
| **F** | **Persistent Production Structural Pipeline** | `true` (isolated) | **200** | **Newly generated live inferences in Phase 2** |

### Total Inference Budget
- Total Cohort Size: $N=200$ cases.
- Reused Frozen Predictions: $5 \times 200 = 1,000$ predictions.
- **New Live Model Inference Calls**: **Exactly 200 calls** (for Condition F only).
- Rerun of Historical Conditions: **Strictly 0 calls**.

---

## 3. Canonical Model & Inference Configuration

To ensure valid comparison against frozen Conditions A through E, Condition F will execute under the identical inference configuration:

- **LLM Engine**: Ollama daemon (`http://localhost:11434`)
- **Model Identifier**: `qwen2.5-coder:7b`
- **Sampling Temperature**: `0.0` (greedy decoding for reproducibility)
- **Top-p Nucleus Sampling**: `0.9`
- **Random Seed**: `42`
- **Maximum Output Tokens**: `512`
- **Context Ceiling**: `2,048` tokens
- **Prompt Template**: Canonical concise prompt:
  ```
  Answer the question directly and concisely based ONLY on the provided context. If the context does not contain sufficient information to answer the question, respond with "Insufficient information".

  Context:
  {context}

  Question: {question}

  Answer:
  ```

---

## 4. Execution Workflow for Condition F

For each of the 200 cases in `sample_manifest.jsonl`:

1. **Storage Setup**: Initialize an isolated temporary `FactStore` (in-memory ChromaDB instance).
2. **Ingestion**:
   - Ingest the raw document HTML using `orchestrator.ingest_document(text=clean_text, source_doc=case_id, store=store, raw_document=raw_html, enable_list_extraction=True)`.
   - Both SVOA facts and structural blocks (tables and lists) are persisted into their respective ChromaDB collections.
3. **Query Retrieval & Context Assembly**:
   - Call `orchestrator.assemble_query_context(query=question, store=store, token_ceiling=2,048, enable_list_extraction=True)`.
   - The query retrieves top SVOA facts and vector-searches `structural_evidence`.
   - `assemble_structural_query_context` performs similarity-dominant blended ranking, document affinity boosting, deterministic tie-breaking, and packs up to 3 chunks within the 2,048-token budget.
4. **Context Archival**: The exact assembled context string passed to Ollama is saved directly into the evaluation record for auditability.
5. **Generation**:
   - Query Ollama `POST /api/generate` with the canonical prompt and parameters.
   - Record response text, prompt tokens, completion tokens, and latency.
6. **Scoring**:
   - Evaluate exact match (`check_exact_match(pred, gold, alts)`).
   - Evaluate containment (`check_containment(pred, gold, alts)`).
   - Evaluate ROUGE-L (`check_rouge_l(pred, gold, alts)`).
7. **Cleanup**: Clear and close the isolated store instance.

---

## 5. Statistical Analysis and Evaluation Plan

### 5.1 Primary Paired Comparisons
- **Contrast 1 (Condition F vs. Condition D)**: Assesses the net incremental gain of persistent structural lists over table retention alone.
- **Contrast 2 (Condition F vs. Condition E)**: Assesses whether the persistent vector-retrieval pipeline reproduces the performance of the prototype in-memory extractor.
- **Contrast 3 (Condition F vs. Condition A)**: Assesses the overall improvement over the baseline clean prose system.

### 5.2 Metrics & Tests
- **Exact Match (EM)** and **Containment** accuracy percentages.
- **Contingency Tables**: Cell counts ($a, b, c, d$) for paired binary outcomes.
- **Exact Two-Sided McNemar Test**: Exact binomial calculation on discordant pairs ($b$ vs $c$):
  $$p = 2 \times \sum_{k=\max(b, c)}^{b+c} \binom{b+c}{k} 0.5^{b+c}$$
- **95% Confidence Intervals**: Wald / Wilson score confidence intervals for net percentage point differences.

### 5.3 Context Cost & Telemetry Distributions
- Token consumption: mean, median, standard deviation, percentiles (p25, p75, p90), minimum, maximum.
- Zero-context rate: percentage of cases where no context was packed.
- Ceiling violations: count of cases where context exceeded 2,048 tokens (invariant: must be 0).
- Duplicate structural chunk rate: tracking instances where multiple chunks from the same table/list entered context.

### 5.4 Strata Breakdown
Performance will be broken down by:
- **Stratum 1 (Stage C Regressions, $N=47$)**: Target recovery rate $\ge 80\%$.
- **Stratum 2 (Stage C Recoveries, $N=11$)**.
- **Stratum 3 (Remaining Concordant Cases, $N=142$)**.
- **Gate 2 List Subset ($N=31$)** and **Non-Gate-2 Subset ($N=169$)**.

### 5.5 Sensitivity Analysis ($N=199$)
A parallel sensitivity analysis excluding ambiguous case `895b5134173847ff8837c187a367cde0` (Bill Belichick premise) will be computed to confirm that findings do not depend on gold-label ambiguities.

### 5.6 Discordant Case Error Analysis
All discordant pairs between Condition F and Condition D (F wins and F losses) will be logged into `regression_audit.jsonl` and manually reviewed for failure patterns (e.g. retrieval truncation, distractor interference, answer extraction failure).

---

## 6. Pre-Registered Safety Guardrails

- **Zero In-Flight Tuning**: No adjustments to prompts, ranking multipliers, thresholds, or chunk limits during or after the run.
- **Zero Imputation**: If an inference fails or times out, it is recorded as unscorable; no optimistic imputation.
- **Zero Historical Overwrites**: Frozen results A through E will not be modified or re-generated.
- **Resumption & Idempotence**: The runner will support JSONL checkpointing to ensure safe resumption without re-evaluating completed cases.

---

## 7. Execution Gate Boundary

**Current Status**: **STOPPED. Phase 1 Preflight is complete. Phase 2 live inference will not be initiated until the user provides explicit authorization.**
