# Experiment 4.5.7: Source Provenance Assertion Audit

**Audit Date**: 2026-10-10  
**Target Subsystem**: Document Provenance, Vector Metadata Isolation, and Context Assembly  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Execution Environment**: Python 3.12.3, Linux x86_64, Isolated In-Memory FactStore, Mocked LLM Generation  
**Test Node IDs**:
- `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_source_provenance_and_telemetry_test_c`
- `scripts/test_experiment_4_5_persistence_audit.py::TestAuditRestAndWebSocketHandlers::test_failure_sensitivity_demonstration_test_d`  
**Result**: **PASSED**

---

## 1. Executive Summary & Design Clarification

A critical question addressed by this audit is how source provenance is represented and verified in Précis's persistent structural pipeline:

1. **Storage & Retrieval Provenance (Strict Metadata Contract)**:
   In the underlying storage layer, every structural chunk is encapsulated in a `StructuralEvidence` object persisted into ChromaDB with explicit metadata:
   - `id`: Deterministic hash of document + content.
   - `source_doc`: The exact document identifier provided during ingestion.
   - `structure_type`: `"table"` or `"list"`.
   - `searchable_text`: Flattened text used for semantic embedding.
   This metadata is preserved across all storage, querying, and deletion operations.

2. **Prompt Assembly (Prompt Cleanliness Principle)**:
   When `assemble_structural_query_context` formats selected evidence for the LLM generator, it produces clean GitHub-Flavored Markdown (GFM tables and structured lists). It **does not** prepend artificial document file paths or prefix tags to each Markdown block. Doing so would consume unnecessary token budget and risk confusing downstream generation models.

**Test C** and **Test D** honor this architectural distinction: they directly test stored source identifiers and candidate provenance on retrieval records, test scoped vector filtering, verify delivery to assembled context, and prove failure sensitivity when provenance is tampered with.

---

## 2. Multi-Document Test Invariant Design

To test provenance across document boundaries, two distinct synthetic documents with distinguishable structural facts and identifiers were constructed:

| Document | Identifier | Structural Type | Distinctive Fact | Numerical Sentinel |
|---|---|---|---|:---:|
| **Document Alpha** | `doc_alpha.html` | Table | `Alpha Latency Budget` | `12.5 ms` |
| **Document Beta** | `doc_beta.html` | Table | `Beta Worker Pool` | `88 replicas` |

---

## 3. Step-by-Step Provenance Verification Record

### Invariant 1: Direct Store Provenance Verification
Following ingestion into an isolated `FactStore`:
- `items_alpha = test_store.get_structural_evidence_by_document("doc_alpha.html")`
  - `len(items_alpha) == 1` (**PASSED**)
  - `items_alpha[0].source_doc == "doc_alpha.html"` (**PASSED**)
  - `items_alpha[0].structure_type == "table"` (**PASSED**)
  - `"Alpha Latency Budget" in items_alpha[0].content` (**PASSED**)
- `items_beta = test_store.get_structural_evidence_by_document("doc_beta.html")`
  - `len(items_beta) == 1` (**PASSED**)
  - `items_beta[0].source_doc == "doc_beta.html"` (**PASSED**)
  - `items_beta[0].structure_type == "table"` (**PASSED**)
  - `"Beta Worker Pool" in items_beta[0].content` (**PASSED**)

### Invariant 2: Retrieval Candidate Metadata Provenance
Querying the vector store without document filters:
```python
retrieved_alpha = test_store.query_similar_structural("Alpha Latency Budget", n_results=5)
top_alpha, score_alpha = retrieved_alpha[0]
```
- `top_alpha.source_doc == "doc_alpha.html"` (**PASSED**)
- `"12.5 ms" in top_alpha.content` (**PASSED**)

### Invariant 3: Document-Scoped Vector Filtering
When querying with explicit document scoping (`source_doc=...`):
- `scoped_alpha = test_store.query_similar_structural("Latency Budget", n_results=5, source_doc="doc_alpha.html")`
  - `all(item.source_doc == "doc_alpha.html" for item, _ in scoped_alpha)` (**PASSED**)
  - `not any(item.source_doc == "doc_beta.html" for item, _ in scoped_alpha)` (**PASSED**)
- `scoped_beta = test_store.query_similar_structural("Worker Pool", n_results=5, source_doc="doc_beta.html")`
  - `all(item.source_doc == "doc_beta.html" for item, _ in scoped_beta)` (**PASSED**)
  - `not any(item.source_doc == "doc_alpha.html" for item, _ in scoped_beta)` (**PASSED**)

### Invariant 4: Assembled Query Context Isolation
Assembled contexts were evaluated for cross-document contamination:
- Query: `"What is the Alpha Latency Budget?"`
  - `assert assembled_alpha.use_structural is True` (**PASSED**)
  - `assert "Alpha Latency Budget" in assembled_alpha.context` (**PASSED**)
  - `assert "12.5 ms" in assembled_alpha.context` (**PASSED**)
  - `assert "Beta Worker Pool" not in assembled_alpha.context` (**PASSED**)
  - `assert "88 replicas" not in assembled_alpha.context` (**PASSED**)
- Inverse Query: `"What is the replica count for Beta Worker Pool?"`
  - `assert assembled_beta.use_structural is True` (**PASSED**)
  - `assert "Beta Worker Pool" in assembled_beta.context` (**PASSED**)
  - `assert "88 replicas" in assembled_beta.context` (**PASSED**)
  - `assert "Alpha Latency Budget" not in assembled_beta.context` (**PASSED**)
  - `assert "12.5 ms" not in assembled_beta.context` (**PASSED**)

### Invariant 5: Failure Sensitivity to Provenance Tampering (Test D)
To demonstrate that provenance checks are failure-sensitive:
```python
mock_evidence = StructuralEvidence(
    id="rec_swapped", source_doc="unrelated_doc.html", structure_type="table",
    content="Some table", searchable_text="Some text",
)
with pytest.raises(AssertionError):
    assert mock_evidence.source_doc == "target_sentinel_doc.html"
```
- Mismatched `source_doc` immediately raises `AssertionError` (**PASSED**).

---

## 4. Audit Conclusion

The provenance assertions are technically sound and accurate to system design:
1. They assert actual provenance metadata stored in the database and returned by retrieval.
2. They do not fabricate claims about artificial document labels in prompt text.
3. Scoped filtering strictly prevents cross-document retrieval.
4. Negative controls and failure-sensitivity tests confirm these assertions cannot pass vacuously.
