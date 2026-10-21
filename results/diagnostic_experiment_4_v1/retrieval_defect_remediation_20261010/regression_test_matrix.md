# Regression Test Matrix

**Experiment 4.5.4 Remediation Verification**  
**Date**: 2026-10-10  
**Test Suite**: `scripts/test_experiment_4_5_persistence_audit.py` & `backend/tests/`

---

## 1. Defect Remediation Test Suite (Tests A through G)

| Test Identifier | Name / Function | Target Defect | Setup / Probe Conditions | Expected Behavior | Observed Result | Status |
|---|---|---|---|---|---|---|
| **Test A** | `test_top_doc_defect_vulnerability_demonstration` | DEFECT-01 | Doc A (`energy_summit.html`) has query-matching prose + weak table (`Frank Miller`). Doc B (`awards_data.html`) has minimal prose + exact winner table (`Dr. Elena Rostova`). | Elena Rostova ($sim=0.58$) selected in context; old logic demonstrated to have selected only Frank Miller. | Elena Rostova selected and ranked #1; old logic failure proved. | **PASSED** |
| **Test B** | `test_candidate_starvation_remediation_test_b` | DEFECT-03 | Doc A has SVOA facts + weak table candidate. Doc B has 0 SVOA facts + strong table candidate ($sim=0.65 \ge 0.40$). | Strong candidate from Doc B selected; not starved by nonempty `matched_items`. | Benchmark latency measurement (0.42 ms) present in context. | **PASSED** |
| **Test C** | `test_multiple_relevant_documents_deterministic_selection_test_c` | General Ranking | 4 server metric documents + 1 grocery distractor document ($sim=0.20$). | Context identical across 3 repeated runs; chunk count $\le 3$; distractor excluded. | 100% deterministic across 3 runs; at most 3 tables; "Apples" excluded. | **PASSED** |
| **Test D** | `test_rest_pure_structural_query_test_d` | DEFECT-02 | Ingest pure table document (`store.count() == 0`, `store.count_structural_evidence() > 0`). Query via `POST /api/query`. | Returns HTTP 200 (not 400); table evidence reaches mocked generator context. | HTTP 200 OK; "MaxConcurrentConnections" & "10000" in generator context. | **PASSED** |
| **Test E** | `test_websocket_pure_structural_query_test_e` | DEFECT-02 | Ingest pure table document. Query via WebSocket stream `/ws`. | No "No documents ingested" error; tokens streamed; table evidence in generator context. | Completed with `pipeline:done`; streamed tokens confirmed evidence present. | **PASSED** |
| **Test F** | `test_truly_empty_store_rejection_test_f` | Empty-Store Guard | Store has 0 SVOA facts and 0 structural evidence. Query via REST and WebSocket. | REST returns HTTP 400 Bad Request; WebSocket emits error "No documents ingested". | REST HTTP 400 with detail; WebSocket error emitted as expected. | **PASSED** |
| **Test G** | `test_feature_disabled_pure_structural_compatibility_test_g` | Compatibility | `PRECIS_ENABLE_LIST_EXTRACTION=false`. Ingest pure table document. | Zero structural records persisted; query rejected as empty store. | 0 structural writes; REST returns HTTP 400; legacy behavior preserved. | **PASSED** |

---

## 2. Historical Regression Fixtures

| Fixture ID | Domain / Failure Mode | Target Query | Structural Evidence | Context Presence | Status |
|---|---|---|---|---|---|
| `3f5983b2` | Namibian Cabinet: Minister vs. Deputy Minister | "who is the minister of youth in namibia" | Hierarchical list: Erastus Utoni vs. Deputy Agnes Tjongarero | Both Erastus Utoni and Agnes Tjongarero present in context | **PASSED** |
| `ef634417` | Scorpions Song: Songwriters vs. Band | "who sings the song rock you like a hurricane" | Table with "Single by Scorpions" and redundant list of songwriters | "Single by Scorpions" present; redundant list suppressed | **PASSED** |
| `8f1f9bd9` | Thomas Definition: Short Answer | "what is the definition of the name thomas" | Table with Word="Aramaic", Meaning="twin" | Both "twin" and "Aramaic" present in context | **PASSED** |
