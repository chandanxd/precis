# REST API and WebSocket Production Integration Audit

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Status**: VERIFIED WITH LIMITATIONS (DEFECT-02 Identified)

---

## 1. Overview and Audit Scope

The primary goal of Experiment 4.5.2 was to ensure persistent table and list evidence functions through the actual production server endpoints (`POST /api/ingest`, `POST /api/query`, and WebSocket `/ws`), rather than solely through programmatic test helpers passing `raw_document`.

The audit evaluated:
1. End-to-end execution of FastAPI REST endpoints with mocked LLM generation.
2. End-to-end execution of WebSocket duplex streaming with mocked LLM generation.
3. Inspection of the exact `context` string passed into `generate_answer()`.
4. Identification of edge-case failure modes and limitations.

---

## 2. REST API Handler Audit

### Execution Path
1. **`POST /api/ingest`**:
   - Client sends JSON: `{"text": "<HTML>", "document_name": "awards.html"}`.
   - Handler sanitizes input and passes `raw_document=req.text` to `run_ingest_document()`.
   - When enabled, `extract_structural_evidence_from_document()` extracts and embeds chunks into `{collection_name}_structural`.
   - Facts are concurrently indexed into `{collection_name}`.
2. **`POST /api/query`**:
   - Client sends JSON: `{"question": "Who won excellence in physics?"}` (**Notice: zero `raw_document` parameter**).
   - Handler calls `query_pipeline()` with `stream=False`.
   - `query_pipeline()` calls `assemble_query_context()`.
   - Context is constructed from persisted ChromaDB structural evidence and passed to `generate_answer(context=...)`.

### Audit Test Verification
In `TestAuditRestAndWebSocketHandlers.test_rest_passes_structural_context_to_generator`:
- Mock generator intercepted the call.
- Evaluated `mock_gen.call_args[1]["context"]`.
- Confirmed: `"Professor X"` from the ingested `<ul>` list was present in the generator's context.
- When `PRECIS_ENABLE_LIST_EXTRACTION=false`, the structural block was completely absent from the generator's context.

---

## 3. WebSocket Real-Time Pipeline Audit

### Execution Path
1. **Connection & Authentication**:
   - Client connects via `/ws?token=<jwt_token>`.
2. **Ingestion Stream (`type: "ingest"`)**:
   - Emits pipeline stage events: `Hardware detection` (0), `Coreference resolution` (1), `SVOA extraction` (2), `SDH scoring & storage` (3).
   - Completes with `type: "ingest:done"`.
   - Confirmed: Structural evidence persisted into ChromaDB.
3. **Query Stream (`type: "query"`)**:
   - Emits `stage 4: Re-rank + pack running`.
   - Invokes `assemble_query_context()` via `asyncio.to_thread()`, retrieving persisted structural evidence.
   - Emits `stage 4 complete` with `tokens_used`, `compression_rate`, and `facts_packed`.
   - Emits `stage 5: LLM inference running`.
   - Streams character tokens via `type: "pipeline:token"`.
   - Emits `type: "pipeline:done"`.

### Audit Test Verification
In `TestAuditRestAndWebSocketHandlers.test_websocket_passes_structural_context_to_generator`:
- Ingested HTML containing `Target Item 99: Special Active Config`.
- Queried: `"What is Target Item 99?"`.
- Mock stream generator inspected the context and streamed `"VERIFIED_EVIDENCE_IN_CONTEXT"`.
- WebSocket client drained the stream and verified that `VERIFIED_EVIDENCE_IN_CONTEXT` was received.
- Confirmed that WebSocket queries successfully retrieve and utilize persistent structural evidence.

---

## 4. Programmatic API Consistency

Both `query_pipeline()` and `process_query()` support:
- `enable_list_extraction: bool | None`: Correctly overrides environment default.
- `raw_document: str | None`:
  - If supplied: Parses `raw_document` directly on the fly (Path A).
  - If omitted (`None`): Seamlessly queries persisted evidence from `store` (Path B).
  - If store has no evidence and no `raw_document`: Gracefully falls back to pure SVOA fact packing.

---

## 5. Identified Defect in REST & WebSocket Handlers (DEFECT-02)

### Rejection of Pure-Structural Knowledge Bases
During the audit, `test_zero_svoa_facts_store_rejection` revealed a critical bug in both handlers:

In `backend/main.py`:
- Line 272 (`query` endpoint):
  ```python
  if active_store.count() == 0:
      raise HTTPException(
          status_code=400,
          detail="No documents ingested. Upload a document first.",
      )
  ```
- Line 550 (`_handle_ws_query`):
  ```python
  if active_store.count() == 0:
      await ws.send_json(
          {
              "type": "error",
              "detail": "No documents ingested",
          }
      )
      return
  ```

`active_store.count()` only checks atomic SVOA facts. If a document contains purely tabular or list information (e.g. technical specifications, catalogs, or financial sheets with 0 prose sentences), `active_store.count()` returns 0.
Even though `active_store.count_structural_evidence() > 0`, the server blocks the query and returns `HTTP 400 "No documents ingested"`.

**Proposed Fix**:
Update the check to verify both collections:
```python
if active_store.count() == 0 and not active_store.has_structural_evidence():
```
