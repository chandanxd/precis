# Experiment 4.5.6: Production-Path Test Matrix & Verification Accounting

**Audit Date**: 2026-10-10  
**Target Evaluation**: Gate 5 Confirmatory Production-Path Evaluation  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  

---

## 1. Executive Summary

This matrix documents the complete deterministic test execution results for the Gate 5 preflight evaluation. The test suite comprises **476 unique, non-overlapping tests** across 5 distinct test suites, plus 18 specialized Gate 5 deterministic lifecycle and ranking probes.

All tests passed with a **100% pass rate** (0 failures, 0 errors, 0 skipped tests).

---

## 2. Test Suite Execution Accounting

| Test Suite Description | Test File / Path | Command Line | Collected | Passed | Failed | Skipped | Duration | Exit Code |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Full Backend Application Suite** | `backend/tests/` | `./backend/venv/bin/pytest backend/tests/` | 418 | 418 | 0 | 0 | 203.48s | 0 |
| **Persistence & Remediation Audit** | `scripts/test_experiment_4_5_persistence_audit.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_5_persistence_audit.py -v` | 25 | 25 | 0 | 0 | 85.35s | 0 |
| **Diagnostic 4.2 Integrity Suite** | `scripts/test_experiment_4_2_integrity.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_2_integrity.py -v` | 13 | 13 | 0 | 0 | 3.99s | 0 |
| **Diagnostic 4.3 Fixtures Suite** | `scripts/test_experiment_4_3_fixtures.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_3_fixtures.py -v` | 5 | 5 | 0 | 0 | 0.02s | 0 |
| **Diagnostic 4.4 Extractor Suite** | `scripts/test_experiment_4_4_audit_extractor.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_4_audit_extractor.py -v` | 15 | 15 | 0 | 0 | 3.93s | 0 |
| **Total Non-Overlapping Suite** | | | **476** | **476** | **0** | **0** | **296.77s** | **0** |

---

## 3. Disjointness and Non-Overlap Verification

To verify that the reported aggregate count of 476 tests represents unique tests without double-counting:
1. **Pytest Node ID Inspection**:
   - `pytest --collect-only -q` was executed simultaneously across all 5 test directories and files.
   - Collected node IDs: exactly 476 distinct test identifiers.
   - Duplicate count: exactly 0.
2. **Directory Separation**:
   - `backend/tests/` contains only unit and integration tests for the core application (`test_api.py`, `test_svoa.py`, `test_structural_persistence.py`, `test_production_wiring.py`, `test_structural_integration.py`, etc.).
   - `scripts/` contains only standalone evaluation harness integrity tests. Zero test files in `scripts/` import or re-export test cases from `backend/tests/`.

---

## 4. Remediation Regression Test Matrix (Tests A through G)

| Test ID | Defect / Dimension Tested | File & Test Function | Primary Assertion | Result |
|:---:|:---|:---|:---|:---:|
| **Test A** | DEFECT-01: Hard `top_doc` bias removal | `test_experiment_4_5_persistence_audit.py::test_top_doc_defect_vulnerability_demonstration` | `assert "Dr. Elena Rostova" in context` and `assert "Frank Miller" not in context` | **PASSED** |
| **Test B** | DEFECT-03: Candidate starvation elimination | `test_experiment_4_5_persistence_audit.py::test_candidate_starvation_remediation_test_b` | `assert "0.42 ms" in context` (uncorroborated strong wins over fact weak) | **PASSED** |
| **Test C** | Multi-doc ranking, chunk limit, tie-breaking | `test_experiment_4_5_persistence_audit.py::test_multiple_relevant_documents_deterministic_selection_test_c` | Deterministic context across runs; chunk count $\le 3$; distractor exclusion | **PASSED** |
| **Test D** | DEFECT-02: REST pure-structural query | `test_experiment_4_5_persistence_audit.py::test_rest_pure_structural_query_test_d` | `resp.status_code == 200`; evidence reaches generator context | **PASSED** |
| **Test E** | DEFECT-02: WebSocket pure-structural query | `test_experiment_4_5_persistence_audit.py::test_websocket_pure_structural_query_test_e` | Streams tokens without error; evidence reaches generator context | **PASSED** |
| **Test F** | Empty store safety contract | `test_experiment_4_5_persistence_audit.py::test_truly_empty_store_rejection_test_f` | `resp.status_code == 400`; WebSocket sends `"error"` event | **PASSED** |
| **Test G** | Disabled-mode legacy parity | `test_experiment_4_5_persistence_audit.py::test_feature_disabled_pure_structural_compatibility_test_g` | Pure-structural rejected when disabled; byte-for-byte legacy context | **PASSED** |

---

## 5. Gate 5 Preflight Deterministic Verification Probes

### 5.1 Persistent Lifecycle Probes (11 Invariants Tested)
1. REST ingestion with frozen HTML docs (`3f5983b2`, `ef634417`, `8f1f9bd9`): **PASSED**
2. Secondary collection persistence (`count_structural_evidence > 0`): **PASSED**
3. REST query without raw document: **PASSED** (HTTP 200 OK)
4. WebSocket query stream: **PASSED** (all pipeline events emitted)
5. Context capture to generator: **PASSED** (table/list syntax verified)
6. Provenance & structural integrity: **PASSED**
7. Pure-structural query (0 SVOA facts): **PASSED** (HTTP 200 OK)
8. Genuinely empty store rejection: **PASSED** (HTTP 400 Bad Request)
9. Document deletion & store clearing: **PASSED** (records removed)
10. Multi-document isolation: **PASSED** (no cross-contamination)
11. Disabled-mode byte-for-byte legacy parity: **PASSED** (118 bytes exact match)

### 5.2 Retrieval & Budget Safety Probes (7 Invariants Tested)
1. Cross-doc structural competition (sim 0.58 vs 0.32): **PASSED**
2. Candidate starvation elimination (sim 0.65 vs 0.28): **PASSED**
3. Determinism and tie-breaking across 5 runs: **PASSED**
4. Maximum chunk limit (exactly 3 selected from 10): **PASSED**
5. Low-relevance candidate exclusion (Filters 1 & 2): **PASSED**
6. Cross-document table deduplication characterization (ARCH-01): **PASSED**
7. Context token ceiling enforcement (2,048 tokens): **PASSED**

---

## 6. Audit Conclusion

All 476 tests in the test suite and all 18 dedicated Gate 5 preflight probes pass deterministically. The production path has demonstrated comprehensive test coverage and regression protection.
