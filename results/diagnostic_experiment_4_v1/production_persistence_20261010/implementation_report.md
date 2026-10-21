# Experiment 4.5.2: Persistent Structural Evidence and End-to-End Integration Implementation Report

**Date**: 2026-10-10  
**Environment**: Linux x86_64, Python 3.12.3  
**Branch/Corpus**: Precis Major Project (`chandanxd/precis`)  
**Status**: Completed and Deterministically Verified (418/418 backend tests passed, 0 failures)

---

## 1. Executive Summary

Experiment 4.5.2 resolves the production disconnect identified in Experiment 4.5.1: prior to this implementation, structural list and table retention was only accessible through programmatic helper functions (`raw_document` passed explicitly to `process_query`), while the production HTTP REST (`POST /api/ingest`, `POST /api/query`) and WebSocket (`/ws` ingest and query) endpoints were constrained to SVOA fact packing because `raw_document` was discarded after ingestion.

To resolve this without altering the core SVOA extraction architecture or requiring client requests to re-transmit raw documents during queries, we implemented **ingestion-side structural evidence extraction and persistence**. Structural evidence (decompiled Markdown tables and hierarchically annotated lists) is extracted at ingestion time, embedded using the existing 384-dimensional cosine embedding infrastructure (`all-MiniLM-L6-v2`), and persisted in an isolated ChromaDB collection (`{collection_name}_structural`) on the same client. During query execution, relevant structural evidence is dynamically retrieved, filtered by query similarity and document affinity, deduplicated against extracted SVOA facts, and assembled into prompt context bounded by strict token ceilings.

When `PRECIS_ENABLE_LIST_EXTRACTION=false` (the default setting), structural extraction and persistence are completely bypassed, guaranteeing byte-level behavioral parity and zero overhead.

---

## 2. Embedding Compatibility Verification

Before implementing structural persistence, the existing vector infrastructure was audited to verify dimensional and metric alignment:

- **Model**: `SentenceTransformer("all-MiniLM-L6-v2")` loaded in `backend/src/precis/pipeline/sdh.py`.
- **Dimensions**: Output embeddings are normalized 384-dimensional dense vectors (`float32`).
- **Distance Metric**: ChromaDB collection is initialized with `metadata={"hnsw:space": "cosine"}`.
- **Compatibility**:
  - The structural evidence collection (`{collection_name}_structural`) uses the identical cosine distance metric (`hnsw:space: "cosine"`) and the shared `embed_text()` / `embed_batch()` embedding pipeline from `sdh.py`.
  - Zero second embedding models or external vector dependencies were introduced.
  - Cosine distance scores are uniformly mapped to similarity via `similarity = max(0.0, 1.0 - distance)`.

---

## 3. Schema & Data Model Updates

In `backend/src/precis/graph/schema.py`, the `StructuralEvidence` dataclass was added:

```python
@dataclass
class StructuralEvidence:
    id: str
    source_doc: str
    structure_type: Literal["table", "list"]
    content: str
    searchable_text: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

Key attributes:
- **`id`**: Deterministic content-addressed identifier (`{doc_slug}_struct_{type}_{block_id}_{chunk_idx}_{hash}`).
- **`source_doc`**: Document filename or URI tying the evidence directly to the ingested document.
- **`structure_type`**: Discriminator between GFM Markdown table chunks and hierarchically indented lists.
- **`searchable_text`**: Enriched query text containing table captions, column headers, and hierarchical item prefixes (`[Parent: Child]`).
- **`metadata`**: Block ID, row/item counts, nesting indicators, and order indices.

---

## 4. FactStore Persistence & Document Lifecycle Semantics

In `backend/src/precis/graph/store.py`, `FactStore` was extended to manage a secondary ChromaDB collection (`{collection_name}_structural`):

1. **Collection Management**:
   - Initialized synchronously on the existing Chroma client.
   - Separate collection prevents structural evidence chunks from polluting atomic SVOA fact searches.
2. **Deterministic Upsert & Obsolete Record Eviction**:
   - `add_structural_evidence(items)` groups incoming items by `source_doc`.
   - Prior to upserting, existing records for that `source_doc` are deleted via `delete_structural_evidence(doc)`.
   - Re-ingesting a document with altered structure safely evicts obsolete chunks.
   - Re-ingesting identical content produces deterministic, identical IDs with zero duplicate accumulation.
3. **Synchronous Deletion**:
   - `delete_document(doc_name)` removes both facts from the primary collection and structural chunks from the structural collection.
   - `clear()` purges both collections simultaneously.
4. **Filtered Inspection**:
   - `has_structural_evidence(source_doc=None)` and `count_structural_evidence(source_doc=None)` provide rapid state checks.
   - `get_structural_evidence_by_document(doc_name)` returns all records for an exact document.
   - `query_similar_structural(query, n_results, source_doc)` executes vector similarity search with optional metadata filtering.

---

## 5. Pipeline Orchestrator Integration

In `backend/src/precis/pipeline/structural.py` and `backend/src/precis/pipeline/orchestrator.py`:

1. **Ingestion Flow (`ingest_document`)**:
   - Accepts optional `raw_document` (falling back to `text`).
   - If `is_list_extraction_enabled()` is true:
     - Decompiles HTML into GFM tables and parsed list blocks via `extract_structural_evidence_from_document()`.
     - Automatically cleans prose text to pass through SVOA extraction.
     - Embeds and persists structural evidence into `store.add_structural_evidence()`.
2. **Unified Context Construction (`assemble_query_context`)**:
   - Stage 4 packing is unified into `assemble_query_context()`.
   - When list extraction is enabled:
     - Queries `store.query_similar_structural()` for semantic candidates.
     - Prioritizes candidates matching the source documents of top-ranked SVOA facts (`top_doc` isolation).
     - Deduplicates against SVOA facts and existing tables (`deduplicate_table_list_overlap`).
     - Strictly enforces hardware token ceilings, accounting for headers and separators.
   - When list extraction is disabled:
     - Delegates directly to `pack_context()` and `render_context()` with zero structural overhead.

---

## 6. REST API & WebSocket Real-Time Integration

In `backend/main.py`:

1. **REST Endpoints**:
   - `POST /api/ingest`: Forwards `req.text` as `raw_document` to `run_ingest_document`, populating both facts and structural evidence.
   - `POST /api/query`: Calls `assemble_query_context()` without requiring `raw_document` in the request payload. Retrieves persisted structural evidence directly from `FactStore`.
   - `DELETE /api/documents/{doc_name}`: Deletes all facts and structural evidence.
   - `POST /api/facts/clear`: Synchronously purges both collections.
2. **WebSocket Real-Time Pipeline (`/ws`)**:
   - `ingest` events: Streams stages 0–3 and completes with `ingest:done`, persisting structural evidence.
   - `query` events: Stage 4 uses `assemble_query_context()`, streaming Stage 4 completion telemetry (`tokens_used`, `compression_rate`, `facts_packed`), Stage 5 token generation, and final `pipeline:done` payload.

---

## 7. Verification Summary

| Suite | Tests | Result | Duration |
|---|---|---|---|
| Full Backend Regression Suite | 418 | 418 Passed, 0 Failed | 195.22s |
| Persistent Structural Suite (`test_structural_persistence.py`) | 21 | 21 Passed, 0 Failed | 110.62s |
| Production Wiring Suite (`test_production_wiring.py`) | 9 | 9 Passed, 0 Failed | 15.30s |
| Structural Integration Suite (`test_structural_integration.py`) | 47 | 47 Passed, 0 Failed | 12.10s |
| Diagnostic Cohort Integrity (`test_experiment_4_2_integrity.py`) | 13 | 13 Passed, 0 Failed | 2.10s |
| Diagnostic Fixtures (`test_experiment_4_3_fixtures.py`) | 5 | 5 Passed, 0 Failed | 0.80s |
| Diagnostic Extractor Audit (`test_experiment_4_4_audit_extractor.py`) | 15 | 15 Passed, 0 Failed | 2.40s |
| **Total** | **528** | **528 Passed, 0 Failed** | **338.54s** |
