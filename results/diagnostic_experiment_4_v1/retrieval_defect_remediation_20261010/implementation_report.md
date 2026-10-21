# Experiment 4.5.4: Structural Retrieval Defect Remediation Report

**Date**: 2026-10-10  
**Environment**: Linux x86_64, Python 3.12.3  
**Target**: Retrieval Defect Remediation for Experiment 4.5.3 Audit Findings

---

## 1. Executive Summary

Experiment 4.5.4 successfully remediates the three retrieval defects identified during the independent audit of Experiment 4.5.3:
1. **DEFECT-01**: Hard `top_doc` bias in `assemble_structural_query_context()` that previously monopolized structural context with chunks from the top SVOA fact's document.
2. **DEFECT-02**: REST and WebSocket queries rejecting stores containing structural evidence but zero SVOA facts with HTTP 400 Bad Request.
3. **DEFECT-03**: Starvation of non-`fact_docs` structural candidates by the `(matched_items if matched_items else other_items)` fallback expression.

All remediations were implemented minimally, cleanly, and deterministically. The full test suite of **476 unique non-overlapping tests passed with a 100% pass rate**. Zero live model inference was executed, zero external network calls were made, and zero accuracy benchmark evaluations were run.

---

## 2. Defects Remediated & Root Causes

### DEFECT-01: Hard `top_doc` Bias
- **Location**: `backend/src/precis/pipeline/structural.py`, lines 1317–1324.
- **Root Cause**: The logic selected `top_doc` as the `source_doc` of the first SVOA fact. If `top_items = [it for it in relevant_struct if it[0].source_doc == top_doc]` contained any candidates, it set `selected_struct = top_items[:3]`. This unconditionally discarded high-similarity structural records from other documents (e.g. $sim = 0.58$ in `awards_data.html` vs $0.32$ in `energy_summit.html`).
- **Remediation**: Replaced hard `top_doc` filtering with a similarity-dominant blended ranking policy where document affinity provides a modest multiplier ($+25\%$ for `top_doc`, $+15\%$ for other `fact_docs`), allowing high-similarity structural chunks from other documents to win decisively.

### DEFECT-02: Rejection of Pure-Structural Stores
- **Location**: `backend/main.py`, lines 272 and 550.
- **Root Cause**: `active_store.count()` counts only atomic SVOA facts. When documents consist purely of tables or lists, `active_store.count() == 0`, prompting the REST API and WebSocket handlers to reject incoming queries with HTTP 400 Bad Request ("No documents ingested. Upload a document first.").
- **Remediation**: Updated both handlers to inspect both SVOA and usable structural evidence:
  ```python
  has_svoa = active_store.count() > 0
  has_struct = (
      is_list_extraction_enabled()
      and hasattr(active_store, "has_structural_evidence")
      and active_store.has_structural_evidence()
  )
  if not has_svoa and not has_struct:
      raise HTTPException(400, "No documents ingested. Upload a document first.")
  ```

### DEFECT-03: Starvation of Non-`fact_docs` Candidates
- **Location**: `backend/src/precis/pipeline/structural.py`, lines 1325–1327.
- **Root Cause**: In the secondary branch, `(matched_items if matched_items else other_items)` selected `matched_items` whenever nonempty, completely ignoring `other_items` even if `other_items` contained a substantially stronger candidate.
- **Remediation**: Pooled all eligible candidates across document groups and ranked them together under the similarity-dominant policy, eliminating group starvation.

---

## 3. Files and Functions Modified

1. **`backend/src/precis/pipeline/structural.py`**:
   - `assemble_structural_query_context()`: Refactored lines 1317–1348 to implement the similarity-dominant scoring function, candidate eligibility criteria, and deterministic tie-breaking.
2. **`backend/main.py`**:
   - Imported `is_list_extraction_enabled` from `precis.pipeline.structural`.
   - `query()`: Updated empty-store guard to check both SVOA facts and usable structural evidence.
   - `_handle_ws_query()`: Updated WebSocket empty-store guard to check both SVOA facts and usable structural evidence.
3. **`scripts/test_experiment_4_5_persistence_audit.py`**:
   - Strengthened Section 3 and Section 4 with rigorous assertions for Tests A through G.

---

## 4. The New Ranking Policy & Deterministic Tie-Breaking

### Formulation
- **Candidate Eligibility**:
  - If `fact_docs` is empty: all items in `relevant_struct` are eligible.
  - If `fact_docs` is nonempty: items with `item.source_doc in fact_docs` are eligible ($sim \ge 0.25$ or $kw$ match with $sim \ge 0.15$); items with `item.source_doc not in fact_docs` are eligible when $sim \ge 0.40$.
- **Blended Score**:
  $$\text{score}(s) = \text{sim}(s, q) \times (1.0 + 0.15 \times \mathbb{I}_{s \in \text{fact\_docs}} + 0.10 \times \mathbb{I}_{s = \text{top\_doc}})$$
- **Tie-Breaking Key**:
  $$\text{key}(s) = (-\text{round}(\text{score}, 6), -\text{round}(\text{sim}, 6), s.\text{item}.\text{id})$$
- **Chunk Limit**: Sliced to top 3 candidates before token-budget packing.

---

## 5. Multi-Collection Empty Store Definition

The updated guard recognizes five distinct knowledge-base states:
1. **Dual Knowledge Base** ($SVOA > 0, Struct > 0$): Query proceeds with unified packing.
2. **Pure Prose Store** ($SVOA > 0, Struct = 0$): Query proceeds with standard fact packing.
3. **Pure Structural Store** ($SVOA = 0, Struct > 0$): Query proceeds with structural context packing when enabled.
4. **Disabled-Mode Pure Structural Store** ($SVOA = 0$, Flag disabled): `has_struct = False`; query rejected with HTTP 400 Bad Request (preserving exact legacy parity).
5. **Truly Empty Store** ($SVOA = 0, Struct = 0$): Query rejected with HTTP 400 Bad Request / WebSocket error.

---

## 6. Before-and-After Behavior Across Regression Fixtures

### Test A: `test_top_doc_defect_vulnerability_demonstration`
- **Before**: Document A (`energy_summit.html`) monopolized context with `Frank Miller`. `Dr. Elena Rostova` was discarded.
- **After**: `Dr. Elena Rostova` ($sim=0.58$) is ranked #1 and retained in context. Test confirms old logic fails and new logic succeeds.

### Test B: `test_candidate_starvation_remediation_test_b`
- **Before**: `matched_items` with weak candidate ($sim=0.28$) excluded `other_items` with strong candidate ($sim=0.65$).
- **After**: Strong candidate ($0.42\text{ milliseconds}$) from `other_items` is selected and packed into context.

### Test C: `test_multiple_relevant_documents_deterministic_selection_test_c`
- **Behavior**: Deterministic across 3 runs; at most 3 tables; distractor grocery table ($sim=0.20$) rejected.

### Test D & E: REST & WebSocket Pure-Structural Queries
- **Before**: HTTP 400 Bad Request ("No documents ingested. Upload a document first.") / WS error.
- **After**: HTTP 200 OK / WebSocket stream tokens; structural table evidence reaches generator context.

### Historical Regression Fixtures (`3f5983b2`, `ef634417`, `8f1f9bd9`)
- `3f5983b2`: Namibian youth minister (`Erastus Utoni`) and deputy (`Agnes Tjongarero`) preserved in context.
- `ef634417`: Scorpions song evidence preserved; redundant list suppressed.
- `8f1f9bd9`: Thomas definition (`twin`, `Aramaic`) preserved.

---

## 7. Disabled-Mode Compatibility Evidence

- Feature flag `PRECIS_ENABLE_LIST_EXTRACTION` defaults to `False`.
- In disabled mode, `assemble_query_context()` invokes standard SVOA fact packing and returns byte-for-byte identical output to legacy pipeline (`test_disabled_mode_byte_identical_context`).
- Zero structural embeddings or collection writes occur during ingestion when disabled.

---

## 8. Non-Overlapping Test Accounting

```
Full Backend Test Suite (backend/tests/):               418 passed (0 failed, 0 skipped, 203.48s)
Persistence Audit Suite (scripts/):                      25 passed (0 failed, 0 skipped, 86.27s)
Diagnostic Integrity Suite (scripts/4.2):                13 passed (0 failed, 0 skipped, 0.58s)
Diagnostic Fixtures Suite (scripts/4.3):                  5 passed (0 failed, 0 skipped, 0.32s)
Diagnostic Extractor Audit Suite (scripts/4.4):          15 passed (0 failed, 0 skipped, 3.03s)
-------------------------------------------------------------------------------------------------
Total Unique Non-Overlapping Tests:                     476 passed (0 failed, 0 skipped, 293.68s)
```
Zero double counting. All 476 tests passed.

---

## 9. Remaining Limitations and Unresolved Risks

1. **Semantic Answering vs. LLM Capabilities**: As demonstrated in earlier diagnostics, placing correct structural evidence into the prompt context does not guarantee the 7B model will output the gold exact answer string without model instruction tuning or few-shot exemplars.
2. **Chunk Limit Fixed at 3**: Very wide questions requiring tables from $\ge 4$ distinct documents will only receive the top 3 tables due to the chunk ceiling.
3. **Hardware Token Ceiling**: Strict ceiling truncation remains enforced; if a single table exceeds the remaining hardware budget, it will be excluded or truncated.

---

## 10. Confirmation of Zero Live Inference / Benchmark Run

It is confirmed that:
- Zero live model inference was executed.
- Zero external network requests were made.
- Zero accuracy benchmark evaluations were run.
- Zero Git commits, resets, or branch switches occurred.
