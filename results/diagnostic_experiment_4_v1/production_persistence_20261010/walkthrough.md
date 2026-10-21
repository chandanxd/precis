# Experiment 4.5.2 Walkthrough: Persistent Structural Evidence and End-to-End Integration

**Date**: 2026-10-10  
**Status**: All Changes Implemented and Verified (418/418 backend tests passed)

---

## 1. Summary of Changes

In Experiment 4.5.2, we transitioned structural list and table retention from an in-memory helper feature into a persistent, production-ready pipeline capability:

1. **Embedding Compatibility Verified**:
   - Reused `SentenceTransformer("all-MiniLM-L6-v2")` producing normalized 384-dimensional cosine embeddings, matching ChromaDB distance space `cosine`.
2. **Schema & Model Updates**:
   - Added `StructuralEvidence` dataclass to `backend/src/precis/graph/schema.py`.
3. **FactStore Persistence Layer**:
   - Added secondary ChromaDB collection `{collection_name}_structural` in `backend/src/precis/graph/store.py`.
   - Implemented `add_structural_evidence`, `get_structural_evidence_by_document`, `query_similar_structural`, `has_structural_evidence`, `count_structural_evidence`, and `delete_structural_evidence`.
   - Wired `delete_document` and `clear` to clean both facts and structural evidence synchronously.
4. **Pipeline Orchestrator & Context Assembly**:
   - Added `extract_structural_evidence_from_document` and `assemble_structural_query_context` in `backend/src/precis/pipeline/structural.py`.
   - Updated `ingest_document` in `backend/src/precis/pipeline/orchestrator.py` to extract and persist structural evidence during ingestion when enabled.
   - Implemented `assemble_query_context` as a unified context constructor used across non-streaming, streaming, and WebSocket query flows.
5. **REST API & WebSocket Wiring**:
   - Updated `POST /api/ingest` and `_handle_ws_ingest` in `backend/main.py` to pass `raw_document` to ingestion.
   - Updated `_handle_ws_query` to construct context via `assemble_query_context`, enabling structural retrieval during WebSocket queries.
6. **Comprehensive Test Suite**:
   - Created `backend/tests/test_structural_persistence.py` covering all 17 mandatory verification items.

---

## 2. Verification and Reproduction

To reproduce all test results deterministically:

### A. Run Focused Structural Persistence Suite
```bash
./backend/venv/bin/pytest backend/tests/test_structural_persistence.py backend/tests/test_production_wiring.py backend/tests/test_structural_integration.py -v
```
**Outcome**: 77 passed in ~100s.

### B. Run Diagnostic Cohort and Extractor Suites
```bash
./backend/venv/bin/pytest scripts/test_experiment_4_2_integrity.py scripts/test_experiment_4_3_fixtures.py scripts/test_experiment_4_4_audit_extractor.py -v
```
**Outcome**: 33 passed in ~5s.

### C. Run Full Backend Regression Suite
```bash
./backend/venv/bin/pytest backend/tests/
```
**Outcome**: 418 passed in ~195s.

---

## 3. Key Guarantees Enforced

- **Zero Breaking Changes**: When `PRECIS_ENABLE_LIST_EXTRACTION=false`, behavior is 100% bit-for-bit identical to legacy SVOA fact packing with 0 overhead.
- **Cross-Document Isolation**: Structural records from document A never leak into queries targeting document B.
- **Hardware Token Clamp**: Token ceilings (100 to 2048) are strictly respected across all queries.
- **Zero External Dependencies**: All vector stores, embeddings, and mocks operate offline and deterministically.
