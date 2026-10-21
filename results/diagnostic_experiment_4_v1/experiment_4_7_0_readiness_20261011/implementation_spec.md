# Experiment 4.7.0: Structural-Priority Context Packing Implementation Specification

**Specification Identifier:** `spec_exp_4_7_0_structural_priority_packing`  
**Date:** 2026-10-11  
**Status:** SPECIFICATION READY (Awaiting Authorization Before Implementation)  
**Target Milestone:** Experiment 4.7.0 Implementation Gate  
**Direct Predecessors:**
- `results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/regression_diagnosis.md`
- `results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/remediation_proposal.md`
- `results/diagnostic_experiment_4_v1/gate_5_independent_audit_20261011/independent_audit_report.md`

---

## 1. Executive Summary & Objective

Experiment 4.6 diagnosed all 13 Condition F vs Condition D Exact-Match regressions from Gate 5 Phase 2. The forensic trace proved that **hybrid SVOA fact contamination and distractor flooding** was the dominant failure driver in 8 of the 13 regressions (`93078684`, `8b41e651`, `b786366c`, `44408e37`, `d84f0eaa`, `ef634417`, `5868443c`, `42d98889`).

In the current production context assembler (`assemble_structural_query_context`), when relevant structural evidence (Markdown tables or structured lists) is retrieved and packed, the orchestrator backfills the remaining token budget under the 2,048 token ceiling with SVOA facts from the vector store. Because SVOA extraction on HTML tables produces hallucinated, scrambled triples (such as converting historical table entries into present-tense assertions), appending SVOA facts directly contaminated the model prompt context, causing entity-role confusion, distractor entity flooding, and conversational preamble induction.

The objective of this specification is to establish the **exact behavioral policy, narrow architectural boundary, deterministic fallback semantics, and non-goals** for the first ranked remediation proposed by Experiment 4.6: **Structural-Priority Context Packing**.

---

## 2. Scope & Non-Goals

### 2.1 In Scope
- Context composition policy inside `assemble_structural_query_context` (`backend/src/precis/pipeline/structural.py`).
- Selective suppression of same-document SVOA facts when relevant structural evidence from that document is successfully packed into the prompt context.
- Cross-document isolation semantics when structural evidence and SVOA facts originate from different documents.
- Safe, deterministic fallback to standard SVOA fact context when no eligible structural evidence is retrieved or packed.
- Budget accounting and hard token ceiling enforcement under structural-priority packing.
- Telemetry extensions recording suppression decisions and packed evidence composition.

### 2.2 Explicit Non-Goals (Out of Scope for Intervention 1)
- **No Document Title Grounding Modifications:** Title injection into `searchable_text` or Markdown headers (`Intervention 2`) is strictly deferred. Case `cf2d77b0` retrieval false negatives will not be solved by this intervention.
- **No HTML Table Parser Modifications:** Multi-row header forward-fill, column header repair, and empty cell preservation (`Intervention 3`) are strictly deferred. Cases `42d98889` (blank headers) and `e44f257a` (omitted season index) header degradation will not be solved by this intervention.
- **No Ingestion, Storage, or Schema Edits:** No changes to `FactStore`, ChromaDB schema, `StructuralEvidence` dataclass, or embedding models.
- **No Prompt Template or Scoring Edits:** No changes to system prompts, few-shot examples, post-processing rules, or evaluation metrics (`check_exact_match`, `check_containment`).
- **No Alteration of Default Feature Flag:** `PRECIS_ENABLE_LIST_EXTRACTION` remains `False` by default in production.

---

## 3. Current Implementation vs. Proposed Policy

### 3.1 Current Implementation Analysis

In `backend/src/precis/pipeline/structural.py` (lines 1269–1446):
1. `pack_context` is executed first to retrieve top-k SVOA facts (`pack_res.packed_facts`).
2. `store.query_similar_structural` retrieves up to 10 structural candidates.
3. Relevance filtering requires cosine similarity $\ge 0.25$, or keyword match with similarity $\ge 0.15$.
4. Multi-document isolation filters structural candidates based on `fact_docs` or high structural similarity ($\ge 0.40$).
5. Top-3 structural candidates are selected by blended score.
6. **Flawed Deduplication:** `struct_combined_content` is computed. SVOA facts are dropped *only if* both `fact.subject` and `fact.object` appear verbatim in `struct_combined_content`. If subject or object undergoes slight rephrasing, or if a hallucinated role triple is extracted (e.g. `John Jay serves as Chief Justice`), the triple survives.
7. **Greedy Backfill:** Structural candidates are packed first. Then, all surviving SVOA facts are greedily packed into whatever token budget remains.

### 3.2 Proposed Policy: Guarded Structural-Priority Packing

Under the proposed policy:
1. **Pre-conditions for Structural Priority:**
   - Structural candidates must pass the existing retrieval relevance filter (similarity $\ge 0.25$ or keyword match with similarity $\ge 0.15$).
   - At least one structural item must be **successfully packed** into the context within the token budget.
2. **Same-Document SVOA Suppression:**
   - Let $\mathcal{D}_{\text{struct}}$ be the set of `source_doc` identifiers for all structural items *successfully packed* into the context.
   - For all candidate SVOA facts where `fact.source_doc` $\in \mathcal{D}_{\text{struct}}$, those facts are **strictly suppressed** from context assembly.
3. **Cross-Document Fact Retention:**
   - For any candidate SVOA fact where `fact.source_doc` $\notin \mathcal{D}_{\text{struct}}$ (i.e. originating from a document with no packed structural evidence in context), the fact remains eligible for packing in the residual budget.
   - Cross-document facts are still filtered by verbatim entity deduplication against the packed structural text.
4. **Single-Document Table-Bearing Invariant:**
   - In single-document QA (such as Natural Questions or standard single-document RAG), if a relevant table or list is successfully packed, **zero SVOA facts are appended** (`facts_packed == 0`). The model receives clean, uncorrupted structural Markdown.

---

## 4. Phase 1 Boundary Analysis

The narrowest plausible function boundary is isolated entirely to `assemble_structural_query_context` in `backend/src/precis/pipeline/structural.py`:

```
+-----------------------------------------------------------------------------------------+
| Pipeline Boundary Isolation                                                             |
|                                                                                         |
| [Ingestion]              -> extract_structural_evidence_from_document [UNTOUCHED]       |
| [Embedding & Storage]    -> FactStore & ChromaDB collections           [UNTOUCHED]       |
| [Vector Retrieval]       -> store.query_similar_structural             [UNTOUCHED]       |
| [Relevance Filter]       -> sim >= 0.25 or (kw_match and sim >= 0.15)  [UNTOUCHED]       |
| [Candidate Ranking]      -> _candidate_rank_key (top 3)                [UNTOUCHED]       |
|                                                                                         |
| >>> NARROW CHANGE BOUNDARY <<<                                                          |
| [assemble_structural_query_context] -> Context Composition & SVOA Suppression Policy    |
|                                                                                         |
| [Prompt Rendering]       -> render_context / prompt template            [UNTOUCHED]       |
| [Inference Generation]   -> generate_answer / Ollama LLM                [UNTOUCHED]       |
| [Output Scoring]         -> check_exact_match / check_containment       [UNTOUCHED]       |
+-----------------------------------------------------------------------------------------+
```

No callers in `backend/src/precis/pipeline/orchestrator.py`, `backend/main.py`, or downstream evaluation harnesses require signature or interface changes.

---

## 5. Phase 2 Safe Fallback Semantics

We evaluated 8 distinct operational scenarios to ensure no silent failures, empty contexts, or regressions:

| Scenario | System State | Structural Priority Behavior | Delivered Context | Fallback Safety Justification |
| :--- | :--- | :--- | :--- | :--- |
| **1. Relevant Structural Evidence Packed** | Single document has a relevant table that fits in budget. | Structural item packed. Same-doc SVOA facts suppressed. | Pure Markdown table. 0 SVOA facts. | Proven by Condition D: eliminates distractor triples and preamble induction. |
| **2. Structural Records Exist, None Pass Relevance Filter** | Store has tables (e.g. Case `cf2d77b0`), but query similarity $< 0.25$ and no keyword match. | `relevant_struct` is empty. | Standard SVOA fact context (`render_context(pack_res.packed_facts)`). | Preserves legacy behavior. Avoids returning empty context when tables are irrelevant to the query. |
| **3. Structural Evidence Exceeds Budget** | Table is larger than `token_ceiling` (e.g. 100-token budget, 500-token table) and cannot be packed; no lists to truncate. | No structural items successfully packed (`len(packed_parts) == 0`). | Fallback to standard SVOA fact context (`render_context(pack_res.packed_facts)`). | Prevents empty context when a table is too large to fit the strict budget constraint. |
| **4. Structural Evidence Packed but Insufficient** | Table packed, but target answer is in an omitted row or external text. | Structural item packed. SVOA facts from that document suppressed. | Structural Markdown context. | Suppressing noisy table-derived SVOA triples does not worsen answers; SVOA triples on the same table were already scrambled and misleading. |
| **5. Prose-Only Document** | Document has no tables or lists (`has_structural_evidence() is False`). | `assemble_structural_query_context` is never invoked, or returns standard fact context. | Standard SVOA fact context. | Bit-for-bit identical to legacy SVOA pipeline. Zero regression risk on prose-only queries. |
| **6. Multi-Document Store** | Doc A has a relevant table; Doc B has relevant SVOA facts. | Doc A table packed. Doc A SVOA facts suppressed. Doc B SVOA facts packed into remaining budget. | Doc A Markdown table + Doc B SVOA facts (`Fact 1: ...`). | Preserves multi-document recall. Evidence from Doc A does not suppress useful evidence from Doc B. |
| **7. Structural Collection Empty** | FactStore has no `_structural_collection` or count is 0. | Early exit on `hasattr` or `count == 0`. | Standard SVOA fact context. | Deterministic fallback to SVOA fact packing. |
| **8. Structural Evidence with Distractors** | Table contains multiple entity rows (e.g. Supreme Court Chief Justices). | Table packed cleanly. SVOA facts suppressed. | Pure Markdown table. | Eliminates hallucinated present-tense triples (e.g. "John Jay serves as Chief Justice") that biased model. |

### 5.1 Fallback Policy Recommendation

We explicitly recommend **Policy B: Successful Packing Fallback**:

- **Why Not Policy A (Mere Storage Existence)?** If tables exist in storage but are irrelevant or cannot fit within the token ceiling, suppressing SVOA facts would result in an empty context or severe information starvation.
- **Why Not Policy C (Semantic Answer-Evidence Criterion)?** Assessing whether structural evidence contains the "complete answer" requires an auxiliary LLM judge or brittle heuristics at retrieval time, violating our latency and deterministic execution invariants.
- **Policy B (Successful Packing):** SVOA facts from document $ are suppressed if and only if at least one structural chunk from document $ is **successfully incorporated into the assembled context string**. If structural retrieval fails or budget constraints prevent packing, the pipeline falls back gracefully to standard SVOA fact packing.

---

## 6. Telemetry & Observability Extensions

To maintain complete auditability, `assemble_structural_query_context` telemetry dictionary will be extended with the following deterministic metrics:

- `structural_priority_active`: `bool` — `True` when structural-priority suppression is enabled and executed.
- `suppressed_same_doc_facts`: `int` — Count of SVOA facts suppressed because their source document had structural evidence packed.
- `retained_cross_doc_facts`: `int` — Count of SVOA facts retained because they originated from non-structural documents.
- `facts_packed`: `int` — Final number of SVOA facts included in prompt context (0 in single-doc table queries).

---

## 7. Verification Invariants

Before code implementation is authorized, any implementation must guarantee:

1. **Deterministic Execution:** Zero randomness, seed dependencies, or stochastic ordering.
2. **Budget Strictness:** Assembled context token estimation must never exceed `token_ceiling`.
3. **No Empty Context:** If either relevant structural evidence or candidate SVOA facts exist, context must never be empty unless the budget is zero.
4. **Feature Flag Neutrality:** When `PRECIS_ENABLE_LIST_EXTRACTION` is disabled, behavior remains byte-identical to current production.
