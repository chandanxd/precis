# Test Quality & Regression Assertion Matrix

**Experiment 4.5.5 Independent Audit**  
**Date**: 2026-10-10  
**Target Suite**: `scripts/test_experiment_4_5_persistence_audit.py` and `backend/tests/`

---

## 1. Deep Scrutiny of Tests A through G

Each test in `scripts/test_experiment_4_5_persistence_audit.py` was audited against 6 strict criteria:
1. **Assertion Strength**: Does it assert invariants using explicit `assert` statements or merely log/print?
2. **Defect Sensitivity**: Would the assertion fail under the original pre-remediation code?
3. **Execution Path Realism**: Does it exercise real production handlers or simplified synthetic mocks?
4. **Score Control**: Are vector similarities evaluated via actual embedding or controlled models?
5. **Context Verification**: Does it inspect the final `context` string delivered to generation?
6. **Negative Case Coverage**: Does it verify that distractors or errors are properly excluded/raised?

---

### Detailed Test-by-Test Audit

| Test ID | Function Name | Assertion vs Print | Fails on Pre-Remediation Code? | Real Production Path? | Generator Context Inspected? | Negative Cases Checked? | Quality Rating |
|---|---|---|---|---|---|---|---|
| **Test A** | `test_top_doc_defect_vulnerability_demonstration` | **Strict Assertions** (`assert has_correct`, plus assertions proving old selection function would choose Frank Miller). Diagnostic prints retained for logging. | **YES (Empirically verified)**. Under old code, failed with `AssertionError: PROVED: Old code discards Elena Rostova!`. | **YES**. Ingests through `ingest_document()`, computes real 384-d cosine embeddings, executes `assemble_query_context()`. | **YES**. Context string inspected for `Dr. Elena Rostova`. | **YES**. Demonstrates Frank Miller was selected under old logic. | **EXCELLENT** |
| **Test B** | `test_candidate_starvation_remediation_test_b` | **Strict Assertions** (`assert "0.42 milliseconds" in assembled.context`). | **YES**. Under old code, `matched_items` took precedence, starving `other_items`. | **YES**. Full ingestion and context assembly through real pipeline. | **YES**. Context string verified. | **YES**. Evaluates weak candidate from `fact_docs` vs. strong candidate outside `fact_docs`. | **HIGH** |
| **Test C** | `test_multiple_relevant_documents_deterministic_selection_test_c` | **Strict Assertions** (Determinism, chunk limit $\le 3$, distractor exclusion, server provenance). | **YES** (on distractor exclusion & determinism). | **YES**. Ingests 5 separate documents with tables. | **YES**. Assembled context verified. | **YES**. Asserts `assert "Apples" not in runs[0]` (distractor table rejected). | **EXCELLENT** |
| **Test D** | `test_rest_pure_structural_query_test_d` | **Strict Assertions** (`assert resp.status_code == 200`, `assert "MaxConcurrentConnections" in ctx`). | **YES (Empirically verified)**. Pre-remediation returned HTTP 400 Bad Request ("No documents ingested"). | **YES**. Real FastAPI `TestClient` invoking `POST /api/query` through middleware. | **YES**. Mock generator inspects `call_args[1]["context"]`. | **YES**. Checks store state `store.count() == 0` prior to query. | **EXCELLENT** |
| **Test E** | `test_websocket_pure_structural_query_test_e` | **Strict Assertions** (`assert "STREAMED_PURE_STRUCTURAL_EVIDENCE" in full_ans`). | **YES (Empirically verified)**. Pre-remediation emitted `type: "error"` ("No documents ingested"). | **YES**. Real WebSocket client `/ws?token=...` handling stage events and token frames. | **YES**. Generator mock conditionally streams only when evidence is found in context. | **YES**. Fails if unexpected error frame emitted. | **EXCELLENT** |
| **Test F** | `test_truly_empty_store_rejection_test_f` | **Strict Assertions** (REST HTTP 400 with detail; WS error with detail). | **YES** (preserves existing guard). | **YES**. Real REST and WebSocket handlers tested against empty store. | N/A (generation is blocked). | **YES**. Truly empty store explicitly tested. | **HIGH** |
| **Test G** | `test_feature_disabled_pure_structural_compatibility_test_g` | **Strict Assertions** (0 structural writes, REST HTTP 400 on empty SVOA store). | **YES**. | **YES**. Real REST ingestion and query with flag false. | N/A (generation is blocked). | **YES**. Negative feature-disabled path verified. | **HIGH** |

---

## 2. Gaps and Limitations Identified

### Audit Finding [TEST-01: Low-to-Medium Severity]: Synthetic Score Control in Integration Tests
- **Observation**: Tests A, B, and C rely on actual sentence-transformer embeddings (`all-MiniLM-L6-v2`) generated from carefully crafted text snippets rather than injecting synthetic mocks of `query_similar_structural()`.
- **Strength**: This proves real-world compatibility with the ChromaDB embedding pipeline.
- **Limitation**: Sentence-transformer cosine scores can shift slightly if the underlying embedding model weights or tokenizers change in future updates. For pure unit-level regression protection, an additional unit test using strictly mocked score tuples `[(item1, 0.45), (item2, 0.55)]` would guarantee immunity against embedding model updates.
