# Experiment 4.5.7: REST Structural Evidence Delivery Audit

**Audit Date**: 2026-10-10  
**Target Subsystem**: REST Handlers (`POST /api/ingest`, `POST /api/query`), Persistence, and Context Packing  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Execution Environment**: Python 3.12.3, Linux x86_64, Isolated In-Memory FactStore, Mocked LLM Generation  
**Test Node ID**: `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_rest_passes_structural_context_to_generator`  
**Result**: **PASSED**

---

## 1. Executive Summary & Defect Remediation

In the initial Gate 5 preflight review (Experiment 4.5.6 Phase 1), lifecycle probes demonstrated that the REST API delivered structural context to the generator. However, the assertions were identified as having test-quality gaps:
- The context check asserted string length (`len(ctx) > 0`) and markdown formatting characters rather than unique, unmistakable sentinel content.
- Negative controls were absent, leaving open the risk of false positives or indiscriminate context leakage across documents.
- Provenance was inferred from high-level execution rather than directly asserting `source_doc` metadata on the retrieved structural evidence.

**Test A** (`test_rest_passes_structural_context_to_generator`) remediates these gaps completely with deterministic sentinel values, store-level persistence verification, query parameter inspection, negative control isolation, and direct candidate provenance assertions.

---

## 2. Test Architecture & Lifecycle Execution Flow

The test executes the full production path through FastAPI's `TestClient`, exercising real storage in ChromaDB without bypassing ingestion or query layers:

```
[Target HTML Document]
         │
         ▼ (POST /api/ingest)
[FastAPI Ingestion Handler] ─────────► [FactStore: secondary ChromaDB collection]
         │                                       │
[Distractor HTML Document]                       │ (Persisted records: 2 docs,
         │                                       │  distinct source_doc metadata)
         ▼ (POST /api/ingest)                   │
[FastAPI Ingestion Handler] ─────────► ──────────┘
                                                 │
[User Query: "What is target latency..."]       │
         │                                       │
         ▼ (POST /api/query)                     │
[FastAPI Query Handler]                          │
         │                                       ▼
         ├──────────────────────────────► [assemble_query_context()]
         │                                       │
         │                                       ▼ (Vector Similarity & Blended Ranking)
         │                                [Structural Evidence Filtered:
         │                                  - Target sentinel selected
         │                                  - Distractor sentinel excluded]
         ▼                                       │
[mock_generate_answer(query, context)] ◄─────────┘
         │
         ▼
[Captured Context Assertions:
  - "17.3 ms" IN context
  - "Gate 5 Sentinel Project" IN context
  - "99.9 tons" NOT IN context
  - "Building Gamma HVAC" NOT IN context]
```

---

## 3. Detailed Step-by-Step Verification Record

### Step 1: Target Document Ingestion & Sentinel Definition
A deterministic document with an unmistakable numerical sentinel and project name was ingested via `POST /api/ingest`:
```html
<p>Gate 5 Production Benchmark Specification</p>
<ul>
    <li>Gate 5 Sentinel Project — target latency: 17.3 ms</li>
    <li>Throughput requirement: 850 qps</li>
</ul>
```
- **Assigned Document Identifier**: `target_sentinel_doc.html`
- **HTTP Status Code**: `200 OK`

### Step 2: Negative Control (Distractor) Document Ingestion
A semantically disjoint document representing facilities infrastructure was ingested via `POST /api/ingest`:
```html
<p>Corporate Facilities Infrastructure</p>
<ul>
    <li>Building Gamma HVAC — cooling capacity: 99.9 tons</li>
</ul>
```
- **Assigned Document Identifier**: `distractor_sentinel_doc.html`
- **HTTP Status Code**: `200 OK`

### Step 3: Direct FactStore Persistence Assertions
Before issuing queries, the underlying secondary ChromaDB collection was queried directly:
- `active_store.count_structural_evidence("target_sentinel_doc.html") == 1` (**PASSED**)
- `active_store.count_structural_evidence("distractor_sentinel_doc.html") == 1` (**PASSED**)
- `stored_items = active_store.get_structural_evidence_by_document("target_sentinel_doc.html")`
- Explicit assertion: `any("17.3 ms" in item.content and item.source_doc == "target_sentinel_doc.html" for item in stored_items)` (**PASSED**)

### Step 4: REST Query Execution
Query issued to `POST /api/query`:
```json
{
  "question": "What is the target latency for Gate 5 Sentinel Project?"
}
```
- **HTTP Status Code**: `200 OK`
- **Generator Called**: `mock_generate_answer.called == True`

### Step 5: Exact Generator Kwargs & Context Inspection
The exact keyword arguments passed to `generate_answer` were inspected:
- **`query` argument**: Exactly matched `target_question` (`"What is the target latency for Gate 5 Sentinel Project?"`).
- **`context` argument captured**:
  ```markdown
  ### Structured List:
  * Gate 5 Sentinel Project — target latency: 17.3 ms
  * Throughput requirement: 850 qps
  ```

### Step 6: Distinctive Sentinel Assertions
- `assert "Gate 5 Sentinel Project" in ctx` (**PASSED**)
- `assert "17.3 ms" in ctx` (**PASSED**)

### Step 7: Negative Control (Distractor Exclusion) Assertions
- `assert "99.9 tons" not in ctx` (**PASSED**)
- `assert "Building Gamma HVAC" not in ctx` (**PASSED**)

### Step 8: Direct Retrieval Provenance Assertion
The retrieval subsystem was probed directly with `target_question`:
```python
retrieved = active_store.query_similar_structural(target_question, n_results=5)
top_evidence, score = retrieved[0]
assert top_evidence.source_doc == "target_sentinel_doc.html"
```
- **Observed `top_evidence.source_doc`**: `"target_sentinel_doc.html"` (**PASSED**)
- **Observed `score`**: Cosine similarity $\approx 0.72$ (top-ranked candidate).

---

## 4. Audit Conclusion

The REST structural evidence delivery path meets all required verification standards:
1. Proof of delivery is rooted in exact sentinel strings, not general length or formatting.
2. Negative controls prove that irrelevant documents are excluded from context.
3. Provenance is verified at the record level (`source_doc` metadata in ChromaDB).
4. Zero application code modifications were made.
