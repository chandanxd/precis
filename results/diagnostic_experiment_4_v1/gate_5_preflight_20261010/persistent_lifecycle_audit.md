# Experiment 4.5.6: Persistent Lifecycle Audit

**Audit Date**: 2026-10-10  
**Target Evaluation**: Gate 5 Confirmatory Production-Path Evaluation  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Execution Environment**: Python 3.12.3, Linux x86_64, Isolated In-Memory FactStore, Mocked LLM Generation

---

## 1. Executive Summary

This audit validates the full persistent structural-evidence lifecycle through actual application handlers (`POST /api/ingest`, `POST /api/query`, and WebSocket `/ws`), exercising real storage operations against canonical frozen documents from Natural Questions (`nq_dev.jsonl`).

All 11 mandatory lifecycle invariants were deterministically executed and verified. Zero live model inference or network calls were made.

---

## 2. Test Execution Environment & Test Setup

- **Server Handlers Tested**:
  - REST Ingestion: `POST /api/ingest` via FastAPI `TestClient`
  - REST Query: `POST /api/query` via FastAPI `TestClient`
  - WebSocket Streaming: `/ws` protocol connection handling `type="ingest"` and `type="query"`
- **Storage Subsystem**: Isolated in-memory `FactStore` with dual ChromaDB collections:
  - Primary collection: SVOA facts (`all-MiniLM-L6-v2`, 384 dimensions, cosine distance)
  - Secondary collection: `structural_evidence` (`all-MiniLM-L6-v2`, 384 dimensions, cosine distance)
- **Generator Isolation**: `generate_answer` mocked via `unittest.mock.patch` with deterministic `InferenceResult` fixtures.
- **Frozen Documents Tested**:
  - `3f5983b2`: Namibian Cabinet list document (`<Li> Minister of Sport , Youth and National Service : Jerry Ekandjo...`)
  - `ef634417`: Scorpions band discography document
  - `8f1f9bd9`: Thomas definition document

---

## 3. Step-by-Step Lifecycle Invariant Audit

| Step | Lifecycle Invariant | Test Method | Observed Output | Verdict |
|:---:|:---|:---|:---|:---:|
| **1** | Supported Ingestion Path | `client.post("/api/ingest")` with frozen HTML docs | HTTP 200 OK across all 3 documents. Ingestion pipeline extracts both structural blocks and prose SVOA facts. | **PASSED** |
| **2** | Secondary Collection Persistence | `store.count_structural_evidence(doc_id)` | Structural evidence persisted into secondary ChromaDB collection: Namibia: 1 record, Scorpions: 1 record, Thomas: 1 record. | **PASSED** |
| **3** | REST Query Execution | `client.post("/api/query")` without `raw_document` | HTTP 200 OK. Queries retrieve persistent structural records directly from vector store. | **PASSED** |
| **4** | WebSocket Query Execution | WebSocket `/ws` connection with `type="query"` | `pipeline:stage` events emitted for Stages 0, 4, 5. Tokens successfully streamed. Done payload confirms completion. | **PASSED** |
| **5** | Context Capture to Generator | `mock_generate.call_args[1]["context"]` | Exact delivered context captured: Namibia context: 1,914 chars; Scorpions: 2,562 chars; Thomas: 2,170 chars. | **PASSED** |
| **6** | Provenance & Structural Preservation | Inspection of captured context string | Preserves markdown list (`- `) and table (`\|`) syntax. Contains target entities (`Erastus Utoni`, `Scorpions`). | **PASSED** |
| **7** | Pure-Structural Query (0 SVOA facts) | Document with pure table and 0 SVOA facts | `store.count() == 0`, `store.count_structural_evidence() > 0`. REST and WebSocket return HTTP 200 OK. Target evidence delivered to generator. | **PASSED** |
| **8** | Truly Empty Store Rejection | Query against empty store (0 facts, 0 structural) | HTTP 400 Bad Request returned with `"No documents ingested. Upload a document first."` WebSocket emits error event. | **PASSED** |
| **9** | Document Deletion & Store Clear | `store.delete_document("docA")` and `store.clear()` | Deletion removes docA structural records while preserving docB. Store clear flushes both collections completely. | **PASSED** |
| **10** | Multi-Document Isolation | Scoped query on `doc_alpha` with `doc_beta` present | Document filter strictly bounds vector retrieval; zero cross-document contamination. | **PASSED** |
| **11** | Disabled-Mode Parity (`PRECIS_ENABLE_LIST_EXTRACTION=false`) | Ingestion and query with feature flag disabled | Exactly 118 bytes generated; identical byte-for-byte to legacy SVOA context; 0 structural records persisted. | **PASSED** |

---

## 4. Verification Details for Critical Edge Cases

### Pure-Structural Document Query (DEFECT-02 Remediation Verification)
A synthetic document containing a single table (`<table><tr><th>Metric</th><th>Target</th></tr><tr><td>Latency</td><td>15ms</td></tr></table>`) was ingested:
- **SVOA Fact Count**: Exactly 0.
- **Structural Evidence Count**: Exactly 1.
- **REST Response**: HTTP 200 OK (`answer` generated, latency 10ms).
- **Context Delivered**: Contains `"| Metric | Target |"` and `"| Latency | 15ms |"`.
- **Finding**: Resolves DEFECT-02 completely in production endpoints.

### Genuinely Empty Store Guard
When neither collection contains data (`store.count() == 0` and `store.count_structural_evidence() == 0`):
- **REST Endpoint**: Returns `HTTP 400 Bad Request` with `{"detail": "No documents ingested. Upload a document first."}`.
- **WebSocket Endpoint**: Emits `{"type": "error", "detail": "No documents ingested"}` and closes.
- **Finding**: Guard preserves original safety contract for uninitialized stores.

### Disabled-Mode Zero-Overhead Verification
With `PRECIS_ENABLE_LIST_EXTRACTION=false`:
- Document containing mixed prose and lists was ingested.
- `store.count_structural_evidence()` was asserted to be exactly 0.
- Query context was compared against the output of the unmodified legacy `pack_context` + `render_context` pipeline:
  $$\text{context}_{\text{assembled}} \equiv \text{context}_{\text{legacy}} \quad (\text{exact match, } 118 \text{ bytes})$$
- `use_structural` telemetry flag evaluated to `False`.

---

## 5. Audit Conclusion

The persistent lifecycle implementation is technically sound, robust against empty/pure-structural edge cases, and completely non-interfering when disabled. All application-level integration points for Gate 5 are fully verified.
