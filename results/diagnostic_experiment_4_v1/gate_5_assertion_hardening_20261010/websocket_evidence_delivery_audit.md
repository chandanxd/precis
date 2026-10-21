# Experiment 4.5.7: WebSocket Structural Evidence Delivery Audit

**Audit Date**: 2026-10-10  
**Target Subsystem**: WebSocket Streaming Protocol (`/ws`), Streaming Generator, and Context Packing  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Execution Environment**: Python 3.12.3, Linux x86_64, Isolated In-Memory FactStore, Mocked Streaming Generator  
**Test Node ID**: `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_websocket_passes_structural_context_to_generator`  
**Result**: **PASSED**

---

## 1. Executive Summary & Defect Remediation

In the initial Gate 5 preflight review (Experiment 4.5.6 Phase 1), the WebSocket handler test verified that connection was established and tokens were received. However, it had several assertion quality gaps:
- It did not assert that the generator received the exact question string.
- It did not assert specific numerical and textual sentinel strings inside the streaming generator's `context` argument.
- It lacked negative control assertions confirming that unrelated documents ingested in the same session were excluded from the query context.
- It did not verify the complete progression through required protocol stages (Stage 4: Re-rank & pack, Stage 5: Inference, and `pipeline:done`).

**Test B** (`test_websocket_passes_structural_context_to_generator`) remediates all of these gaps through strict event lifecycle checks, question verification, context sentinel validation, and negative control exclusion.

---

## 2. WebSocket Protocol Architecture & Event Sequence

The WebSocket test communicates with `/ws?token=<jwt>` using FastAPI's `TestClient.websocket_connect`. The protocol interaction spans two ingestion cycles followed by an interactive query stream:

```
Client                                      Server (/ws)
  │                                              │
  ├────── {"type": "ingest", ...target...} ─────►│ Ingest Target HTML into FactStore
  │◄───── {"type": "ingest:done"} ──────────────┤
  │                                              │
  ├────── {"type": "ingest", ...distractor...} ─►│ Ingest Distractor HTML into FactStore
  │◄───── {"type": "ingest:done"} ──────────────┤
  │                                              │
  ├────── {"type": "query", "question": ...} ───►│ Stage 0: Query Sanitization & Check
  │                                              │ Stage 1: Vector Search
  │                                              │ Stage 2: SVOA Matching
  │                                              │ Stage 3: Coreference
  │                                              │ Stage 4: Re-rank & Context Packing
  │◄───── {"type": "pipeline:stage", stage: 4} ──┤ (Status: complete)
  │                                              │
  │                                              │ Call generate_answer(stream=True)
  │                                              │ Stage 5: Inference Execution
  │◄───── {"type": "pipeline:stage", stage: 5} ──┤ (Status: complete)
  │◄───── {"type": "pipeline:token", ...} ───────┤ Streamed Tokens ("STREAMED_SENTINEL_TOKEN")
  │◄───── {"type": "pipeline:done", ...} ────────┤ Done Payload (latency, tokens, metadata)
  │                                              │
```

---

## 3. Step-by-Step Verification Record

### Step 1: WebSocket Document Ingestion (`target_sentinel_doc.html`)
The target document containing the numerical sentinel was streamed via the WebSocket ingestion protocol:
```json
{
  "type": "ingest",
  "text": "<p>Gate 5 Production Benchmark Specification</p><ul><li>Gate 5 Sentinel Project — target latency: 17.3 ms</li></ul>",
  "document_name": "ws_target_doc.html"
}
```
- **Observed Response**: `{"type": "ingest:done", "facts_extracted": ..., "entities": ...}`.
- Zero errors emitted.

### Step 2: Negative Control Document Ingestion (`ws_distractor_doc.html`)
A semantically unrelated facilities document was streamed via the WebSocket ingestion protocol:
```json
{
  "type": "ingest",
  "text": "<p>Corporate Facilities Infrastructure</p><ul><li>Building Gamma HVAC — cooling capacity: 99.9 tons</li></ul>",
  "document_name": "ws_distractor_doc.html"
}
```
- **Observed Response**: `{"type": "ingest:done", ...}`.

### Step 3: Persistence Assertion in Active Store
- `active_store.count_structural_evidence("ws_target_doc.html") == 1` (**PASSED**)
- `active_store.count_structural_evidence("ws_distractor_doc.html") == 1` (**PASSED**)

### Step 4: Streaming Query Execution
The query message was dispatched:
```json
{
  "type": "query",
  "question": "What is the target latency for Gate 5 Sentinel Project?"
}
```

### Step 5: Protocol Stage Progression & Token Assembly
The event loop collected and asserted all protocol events:
1. **Stage 4 Completion**:
   - `payload["stage"] == 4` and `payload["status"] == "complete"` (**PASSED**)
2. **Stage 5 Completion**:
   - `payload["stage"] == 5` and `payload["status"] == "complete"` (**PASSED**)
3. **Token Streaming**:
   - Assembled streamed characters: `"".join(tokens) == "STREAMED_SENTINEL_TOKEN"` (**PASSED**)
4. **Done Payload**:
   - Received `pipeline:done` message with valid performance telemetry (**PASSED**).

### Step 6: Generator Question Argument Assertion
Captured streaming generator kwargs:
- `len(captured_kwargs) == 1` (**PASSED**)
- `captured_kwargs[0]["query"] == "What is the target latency for Gate 5 Sentinel Project?"` (**PASSED**)

### Step 7: Distinctive Sentinel Context Delivery
The `context` string passed to the streaming generator was inspected:
- `assert "Gate 5 Sentinel Project" in ctx` (**PASSED**)
- `assert "17.3 ms" in ctx` (**PASSED**)

### Step 8: Negative Control Isolation
Unrelated evidence was asserted strictly absent:
- `assert "99.9 tons" not in ctx` (**PASSED**)
- `assert "Building Gamma HVAC" not in ctx` (**PASSED**)

---

## 4. Audit Conclusion

The WebSocket structural evidence delivery path satisfies all hardened verification invariants:
1. Real WebSocket framing, message handling, and stage progression were exercised.
2. The generator receives the verified question and exact sentinel context.
3. Negative controls prove that un-queried documents do not leak into the context.
4. All assertions are deterministic and failure-sensitive.
