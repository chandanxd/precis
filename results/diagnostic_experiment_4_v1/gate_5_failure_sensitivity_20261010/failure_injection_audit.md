# Experiment 4.5.8: Controlled Failure-Injection Audit

**Audit Date**: 2026-10-10  
**Target Subsystems**: REST Query Endpoint, WebSocket Protocol Handler, Vector Metadata Provenance, Scoped Retrieval Filtering  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Execution Environment**: Python 3.12.3, Linux x86_64, Isolated In-Memory FactStore, Mocked LLM Generation  
**Verdict**: **`READY FOR GATE 5 AUTHORIZATION`**

---

## 1. Executive Summary & Defect Characterization

In Experiment 4.5.7, preflight test assertions were hardened with unique sentinels and negative controls. However, a critical methodological critique was raised:
> *"Verify that the actual hardened REST and WebSocket evidence-delivery tests detect realistic regressions, rather than merely demonstrating that Python assertions raise AssertionError on local dummy variables."*

Specifically, testing `assert "17.3 ms" in ""` or asserting a dummy property on a local mock proves Python's `assert` statement works, but does not prove that the test harness and production pipeline detect regressions under realistic runtime conditions.

**Experiment 4.5.8 resolves this critique completely.** Tautological negative assertions have been replaced by four controlled failure-injection tests exercising the actual production REST and WebSocket handlers. Each test verifies that:
1. The surrounding execution infrastructure (HTTP routing, status codes, WebSocket framing, stage transitions, generator invocation) succeeds completely.
2. The assertion fails **strictly and exclusively** because the injected regression occurred.
3. Unrelated failures (HTTP 500, exceptions, mock configuration errors, protocol timeouts) are not conflated with assertion success.

---

## 2. Shared Assertion Helper Architecture

To ensure consistent validation contracts across both positive tests and failure-injection probes, four shared assertion helpers were implemented in [`scripts/test_experiment_4_5_persistence_audit.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_5_persistence_audit.py):

| Helper Function | Target Scope | Verification Invariants |
|---|---|---|
| **`assert_rest_structural_delivery`** | REST Query (`POST /api/query`) | 1. `mock_gen.called == True`<br>2. `call_kwargs["query"] == target_question`<br>3. Expected sentinels present in `context`<br>4. Negative control sentinels absent from `context` |
| **`assert_websocket_structural_delivery`** | WebSocket Streaming (`/ws`) | 1. Stage 4 (`re-rank & pack`) completed<br>2. Stage 5 (`inference`) completed<br>3. `pipeline:done` event received<br>4. Exactly 1 generator call with `target_question`<br>5. Expected sentinels present, negative controls absent |
| **`assert_retrieval_candidate_provenance`** | Vector Candidate Metadata | 1. Candidate list non-empty<br>2. `top_candidate.source_doc == expected_doc_id` |
| **`assert_scoped_retrieval_isolation`** | Scoped Vector Filtering | 1. All returned items originate from `allowed_doc_id`<br>2. Zero items originate from `prohibited_doc_ids` |

---

## 3. Failure-Injection Probe Breakdown & Empirical Findings

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Controlled Failure Injections                   │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Probe D1 (REST Drop)     │ Exercised real POST /api/query              │
│                          │ HTTP 200 OK; generator called               │
│                          │ assert_rest_structural_delivery FAILS:      │
│                          │ "sentinel missing from generator context"   │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Probe D2 (WS Drop)       │ Exercised real /ws streaming connection     │
│                          │ Stages 4, 5, tokens, done payload emitted   │
│                          │ assert_websocket_structural_delivery FAILS: │
│                          │ "sentinel missing from WS generator context"│
├──────────────────────────┼─────────────────────────────────────────────┤
│ Probe D3 (Provenance)    │ Corrupted candidate source_doc metadata     │
│                          │ assert_retrieval_candidate_provenance FAILS:│
│                          │ "Candidate provenance mismatch"             │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Probe D4 (Scoped Leak)   │ Leaked doc_beta items into doc_alpha scope  │
│                          │ assert_scoped_retrieval_isolation FAILS:    │
│                          │ "Prohibited document 'doc_beta.html' leaked"│
└──────────────────────────┴─────────────────────────────────────────────┘
```

---

### 3.1 Probe D1: REST Structural Drop
- **Node ID**: `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_failure_injection_rest_structural_drop_test_d1`
- **Simulated Regression**: A retrieval defect where structural evidence candidates are dropped (`store.query_similar_structural` returns `[]`), causing context assembly to fall back to prose SVOA facts.
- **Production Execution Trace**:
  - `POST /api/ingest` ingests `target_sentinel_doc.html` (`HTTP 200 OK`).
  - Store confirms persistence: `count_structural_evidence() > 0`.
  - Failure injected via monkeypatch on `active_store.query_similar_structural`.
  - Actual REST query issued: `client.post("/api/query", json={"question": target_question})`.
- **Observed Behavior**:
  - `resp.status_code == 200` (**Verified HTTP layer did not fail**).
  - `mock_gen.called == True` (**Verified generator pipeline was executed**).
  - `assert_rest_structural_delivery` was evaluated inside `with pytest.raises(AssertionError) as exc_info:`.
  - Error message: `"Distinctive sentinel 'Gate 5 Sentinel Project' missing from generator context"`.
- **Verdict**: **PASSED**. Proves the assertion specifically detects context-level evidence loss during normal REST execution.

---

### 3.2 Probe D2: WebSocket Structural Drop
- **Node ID**: `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_failure_injection_websocket_structural_drop_test_d2`
- **Simulated Regression**: A retrieval defect during WebSocket query streaming where structural candidates are dropped, causing streaming context to omit structural sentinels.
- **Production Execution Trace**:
  - Real WebSocket connection established: `client.websocket_connect(f"/ws?token={token}")`.
  - Document ingested via WebSocket `type="ingest"` (`ingest:done` received).
  - Failure injected on `active_store.query_similar_structural`.
  - Query issued via `type="query"`.
  - Protocol loop executed:
    - `pipeline:stage` (Stage 4: Re-rank & pack) status=`complete` received.
    - `pipeline:stage` (Stage 5: Inference) status=`complete` received.
    - `pipeline:token` streamed tokens received.
    - `pipeline:done` event received with execution telemetry.
    - Zero WebSocket error events emitted.
- **Observed Behavior**:
  - Protocol lifecycle ran to completion without timeouts or disconnections.
  - Streaming generator was called with `target_question`.
  - `assert_websocket_structural_delivery` was evaluated inside `with pytest.raises(AssertionError) as exc_info:`.
  - Error message: `"Distinctive sentinel 'Gate 5 Sentinel Project' missing from WS generator context"`.
- **Verdict**: **PASSED**. Proves the assertion detects missing evidence without being confounded by protocol or network failures.

---

### 3.3 Probe D3: Provenance Metadata Corruption
- **Node ID**: `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_failure_injection_provenance_metadata_mismatch_test_d3`
- **Simulated Regression**: Ingestion or vector store corruption where extracted content is preserved, but the `source_doc` metadata is misattributed to another document (`corrupted_or_wrong_source.html`).
- **Observed Behavior**:
  - Retrieval returns candidate item.
  - `assert_retrieval_candidate_provenance` evaluated inside `with pytest.raises(AssertionError) as exc_info:`.
  - Error message: `"Candidate provenance mismatch: expected 'doc_alpha.html', got 'corrupted_or_wrong_source.html'"`.
- **Verdict**: **PASSED**. Proves provenance validation strictly checks metadata identity.

---

### 3.4 Probe D4: Scoped Retrieval Cross-Document Leakage
- **Node ID**: `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_failure_injection_provenance_scoped_leakage_test_d4`
- **Simulated Regression**: Vector filtering failure where a query explicitly scoped to `doc_alpha.html` (`source_doc="doc_alpha.html"`) returns records originating from `doc_beta.html`.
- **Observed Behavior**:
  - Scoped candidates contain items from `doc_beta.html`.
  - `assert_scoped_retrieval_isolation` evaluated inside `with pytest.raises(AssertionError) as exc_info:`.
  - Error message: `"Prohibited document 'doc_beta.html' leaked into scoped results"`.
- **Verdict**: **PASSED**. Proves document-scoped isolation assertions detect cross-document leakage.

---

## 4. Audit Conclusion

All four controlled failure-injection tests demonstrate that:
1. Hardened assertions are sensitive to realistic regressions in evidence extraction, retrieval, and metadata binding.
2. Positive and negative tests exercise the genuine production REST and WebSocket handlers.
3. Test failures are strictly attributable to missing evidence or corrupted metadata, not infrastructural or protocol faults.
