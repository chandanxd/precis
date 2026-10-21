# REST API and WebSocket Integration Audit

**Experiment 4.5.2**  
**Date**: 2026-10-10  
**Status**: Verified End-to-End

---

## 1. REST Endpoint Audit

### `POST /api/ingest`
- **Request Payload**: `{"text": "<HTML or raw text>", "document_name": "example.html"}`
- **Behavior**:
  - Sanitizes document and screens for prompt injection.
  - Passes `raw_document=req.text` to `run_ingest_document()`.
  - When list extraction is enabled, extracts and embeds table and list chunks into `{collection_name}_structural`.
  - Concurrently extracts SVOA facts and indexes them into `{collection_name}`.
- **Verification**: `test_rest_ingestion_and_query_end_to_end` confirms `count_structural_evidence("acme_board.html") > 0` after ingestion.

### `POST /api/query`
- **Request Payload**: `{"question": "Who are the board members?"}` (Notice: **zero `raw_document` field required!**)
- **Behavior**:
  - Calls `assemble_query_context(clean_question, store, hardware.token_ceiling)`.
  - Retrieves persisted structural evidence directly from `store.query_similar_structural()`.
  - Binds prompt context with structural chunks and SVOA facts.
  - Executes local inference with full structural awareness.
- **Verification**: Verified that mocked LLM receives context containing table/list items ingested in prior requests.

### `DELETE /api/documents/{doc_name}`
- **Behavior**: Deletes all atomic facts and all structural evidence for the specified `source_doc`.
- **Verification**: Confirmed `count_structural_evidence(doc_name) == 0` while retaining other documents.

### `POST /api/facts/clear`
- **Behavior**: Purges both facts and structural collections in ChromaDB simultaneously.

---

## 2. WebSocket Real-Time Pipeline Audit (`/ws`)

### WebSocket Ingestion Flow
1. Client connects with JWT token (`/ws?token=<token>`).
2. Client sends: `{"type": "ingest", "text": "...", "document_name": "..."}`.
3. Server streams stages:
   - `stage 0`: Hardware detection
   - `stage 1`: Coreference resolution
   - `stage 2`: SVOA extraction
   - `stage 3`: SDH scoring & storage (persists facts + structural evidence)
4. Server completes with `ingest:done` containing `facts_extracted`, `facts_stored`, and `latency_ms`.

### WebSocket Query Streaming Flow
1. Client sends: `{"type": "query", "question": "..."}`.
2. Server emits `stage 4`: Re-rank + pack running.
3. Server invokes `assemble_query_context` via `asyncio.to_thread()`, retrieving persisted structural evidence.
4. Server emits `stage 4`: Re-rank + pack complete with `tokens_used`, `compression_rate`, and `facts_packed`.
5. Server emits `stage 5`: LLM inference running, streaming individual character tokens via `pipeline:token`.
6. Server emits `pipeline:done` containing full answer, `facts_used`, `tokens_used`, and execution telemetry.
- **Verification**: `test_websocket_ingestion_and_query_end_to_end` successfully tests the full duplex cycle without timeouts or errors.
