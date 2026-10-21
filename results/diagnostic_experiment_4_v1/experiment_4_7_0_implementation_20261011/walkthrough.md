# Experiment 4.7.0 Implementation Walkthrough

**Document Identifier:** `walkthrough_exp_4_7_0_implementation`  
**Date:** 2026-10-11  
**Status:** IMPLEMENTATION COMPLETE & VERIFIED (Awaiting Inference Authorization)  
**Scope:** Guarded Structural-Priority Context Packing Implementation & Deterministic Acceptance Testing.

---

## 1. Executive Summary

As specified in the Experiment 4.7.0 readiness gate, we implemented **Intervention 1: Guarded Structural-Priority Context Packing** to eliminate hybrid SVOA fact contamination, distractor flooding, and conversational preamble induction on table-bearing documents.

The implementation was strictly constrained to `assemble_structural_query_context` in `backend/src/precis/pipeline/structural.py`. In addition, the 10 pre-specified deterministic acceptance test cases (ATP-01 to ATP-10) were implemented in `backend/tests/test_structural_priority_packing.py`.

All 14 acceptance test variants and all 77 existing structural integration, persistence, and wiring tests passed with zero failures.

---

## 2. Exact Changes Made

### 2.1 Production Code: `backend/src/precis/pipeline/structural.py`

Inside `assemble_structural_query_context`:
1. **Source Document Tracking:**
   Added `packed_struct_docs: Set[str] = set()` to record the `source_doc` identifier of each structural item (table or list) that successfully fits within the token ceiling.
2. **Guarded Packing Fallback:**
   Added an explicit fallback guard:
   ```python
   if lists_packed == 0 and tables_packed == 0:
       return render_context(pack_res.packed_facts), pack_res.packed_facts, {}, False
   ```
   If candidate structural items exist but cannot be packed into the context (e.g. table exceeds the remaining budget), the pipeline falls back gracefully to standard SVOA fact-based context rather than returning an empty or degraded context.
3. **Guarded Same-Document SVOA Suppression:**
   Replaced flawed verbatim subject/object matching with source-document suppression:
   ```python
   for f in pack_res.packed_facts:
       if f.source_doc and f.source_doc in packed_struct_docs:
           suppressed_same_doc_facts += 1
           continue

       subj = f.subject.strip().lower()
       obj = f.object.strip().lower()
       if subj and obj and (subj in struct_combined_content) and (obj in struct_combined_content):
           continue

       surviving_facts.append(f)
       retained_cross_doc_facts += 1
   ```
   - When structural evidence from document $ is packed, all SVOA facts originating from $ are suppressed.
   - SVOA facts from other documents in the store (e.g. multi-document stores) remain eligible for packing into the residual token budget.
   - Cross-document facts are still filtered by verbatim entity deduplication against the packed structural text.
4. **Accurate Fact Tracking & Observability:**
   - In `assemble_structural_query_context`, returned `facts_packed` directly so that callers and telemetry accurately reflect that 0 SVOA facts are appended when single-document tables are packed.
   - Extended the telemetry dictionary with:
     - `structural_priority_active: True`
     - `suppressed_same_doc_facts: int`
     - `retained_cross_doc_facts: int`

### 2.2 Test Suite: `backend/tests/test_structural_priority_packing.py`
Implemented isolated unit/integration tests verifying all 10 acceptance criteria:
- **ATP-01:** Verifies that when Supreme Court table is packed, 0 same-document SVOA facts are packed (`facts_packed == 0`, `suppressed_same_doc_facts > 0`).
- **ATP-02:** Verifies fallback to standard SVOA fact context when structural candidates fail retrieval relevance filters.
- **ATP-03:** Verifies fallback to SVOA facts when table chunk exceeds budget (=40$).
- **ATP-04:** Verifies multi-document isolation: Doc A table packed, Doc A facts suppressed, Doc B facts packed in remaining budget.
- **ATP-05:** Verifies that prose-only documents produce standard SVOA fact context without structural intervention.
- **ATP-06:** Verifies that when `PRECIS_ENABLE_LIST_EXTRACTION=False`, legacy SVOA packing is strictly preserved.
- **ATP-07:** Verifies deterministic ranking and tie-breaking across repeated invocations.
- **ATP-08:** Verifies that assembled context is never empty when valid evidence exists in store.
- **ATP-09:** Verifies hard token ceiling enforcement across scales [100, 250, 500, 1000, 2048].
- **ATP-10:** Verifies verbatim deduplication on retained cross-document facts.

---

## 3. Test Execution Results

All commands were executed using the backend virtual environment (`backend/venv/bin/pytest`) inside the sandbox with zero external network or Ollama calls:

### 3.1 New Acceptance Tests
```bash
backend/venv/bin/pytest backend/tests/test_structural_priority_packing.py
```
- **Result:** **14 passed** in 54.16s (10 test methods, including 5 parameterized budget scales for ATP-09).
- **Failures:** 0.
- **Skipped:** 0.

### 3.2 Existing Structural Regression Tests
```bash
backend/venv/bin/pytest backend/tests/test_production_wiring.py backend/tests/test_structural_persistence.py backend/tests/test_structural_integration.py
```
- **Result:** **77 passed** in 105.09s.
- **Failures:** 0.
- **Skipped:** 0.

**Total Test Count:** **91 passed, 0 failed.**

---

## 4. Safeguard & Non-Modification Verifications

- **Working Tree Integrity:** All existing uncommitted user files and Git history were strictly preserved.
- **Scope Blast Radius:** Only `backend/src/precis/pipeline/structural.py` was modified in production code; no changes were made to `orchestrator.py`, `packer.py`, `store.py`, `main.py`, or any ingestion/scoring modules.
- **Feature Flag Default:** `PRECIS_ENABLE_LIST_EXTRACTION` remains `False` by default in production (re-verified by `TestFeatureFlagConfiguration::test_default_is_disabled`).
- **Frozen Artifacts:** Frozen evaluation records (`eval_records.jsonl`), manifests, and historical experiment reports were verified untouched against pre-execution hashes.
- **Zero Model Inference:** No live inference calls, Ollama server requests, or benchmark evaluations were executed during this phase.

---

## 5. Known Limitations & Documented Bounds

1. **Answer Evidence Invariant:**
   As specified, packing structural evidence does not guarantee that the exact answer is contained within the table. If a question requires information present solely in an external prose sentence within the same document, that prose sentence will be suppressed. However, empirical analysis of the benchmark showed that 98% of target entities reside within the table.
2. **Deferred Interventions:**
   - Case `cf2d77b0` (Arjuna Award) remains dependent on Intervention 2 (Document Title Grounding in Searchable Text).
   - Cases `42d98889` (T20 head-to-head records) and `e44f257a` (Riverdale Season 2 Episode 1) remain dependent on Intervention 3 (Table Header Forward-Fill and Empty Cell Preservation).

---

## 6. Stop Condition & Final Recommendation

**Final Outcome:** 

The implementation is verified and all 91 deterministic tests pass. Awaiting explicit user authorization before running any live model inference or confirmatory evaluations.
