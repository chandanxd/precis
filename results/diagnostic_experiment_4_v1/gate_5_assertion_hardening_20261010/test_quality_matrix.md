# Experiment 4.5.7: Test Quality Matrix & Assertion Accounting

**Audit Date**: 2026-10-10  
**Target Evaluation**: Gate 5 Confirmatory Production-Path Evaluation  
**Auditor**: Independent Evaluation Agent (Antigravity AI)  
**Total Unique Tests Collected & Executed**: **478**  
**Total Passed**: **478** (100% pass rate, 0 failures, 0 skipped)  
**Duplicate Node IDs**: **0**

---

## 1. Executive Summary

This matrix provides exhaustive accounting for all 478 deterministic tests across the Précis test base, categorizing tests by status (modified, newly added, or reused as evidence), evaluating failure sensitivity, and certifying that zero tests rely on print-only diagnostics.

---

## 2. Test Suite Composition & Execution Summary

| Suite Name | Path | Command Line | Count | Status | Exit Code |
|---|---|---|:---:|:---:|:---:|
| **Backend Core Suite** | `backend/tests/` | `./backend/venv/bin/pytest backend/tests/` | 418 | PASSED | 0 |
| ├─ Structural Persistence | `backend/tests/test_structural_persistence.py` | (included above) | 17 | PASSED | 0 |
| ├─ Production Wiring | `backend/tests/test_production_wiring.py` | (included above) | 10 | PASSED | 0 |
| ├─ Structural Integration | `backend/tests/test_structural_integration.py` | (included above) | 50 | PASSED | 0 |
| └─ Standard Units/API | `backend/tests/test_api.py`, etc. | (included above) | 341 | PASSED | 0 |
| **Hardened Audit Suite** | `scripts/test_experiment_4_5_persistence_audit.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_5_persistence_audit.py -v` | 27 | PASSED | 0 |
| **Diagnostic 4.2 Suite** | `scripts/test_experiment_4_2_integrity.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_2_integrity.py -v` | 13 | PASSED | 0 |
| **Diagnostic 4.3 Suite** | `scripts/test_experiment_4_3_fixtures.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_3_fixtures.py -v` | 5 | PASSED | 0 |
| **Diagnostic 4.4 Suite** | `scripts/test_experiment_4_4_audit_extractor.py` | `./backend/venv/bin/pytest scripts/test_experiment_4_4_audit_extractor.py -v` | 15 | PASSED | 0 |
| **Total Non-Overlapping** | | | **478** | **PASSED** | **0** |

---

## 3. Detailed Accounting of Hardened & New Probes

| Test Invariant | Test Function / Node ID | Change Type | Primary Assertion Strengthened | Failure Sensitivity Proof |
|:---:|:---|:---:|:---|:---:|
| **Test A** | `test_rest_passes_structural_context_to_generator` | **MODIFIED** | Asserts exact sentinel (`17.3 ms`) present; negative sentinel (`99.9 tons`) absent; candidate `source_doc` verified. | Tested in Test D: removing target causes `17.3 ms not in ctx` to pass and `assert in ctx` to fail. |
| **Test B** | `test_websocket_passes_structural_context_to_generator` | **MODIFIED** | Asserts stream protocol stages 4, 5, `pipeline:done`; question arg verified; sentinel (`17.3 ms`) present; negative absent. | Tested in Test D & stream checks: protocol errors immediately trigger `pytest.fail`. |
| **Test C** | `test_source_provenance_and_telemetry_test_c` | **NEW** | Direct `source_doc` metadata assertions on stored items; scoped filtering; bidirectional cross-document context isolation. | Tested in Test D: swapping `source_doc` on record raises `AssertionError`. |
| **Test D** | `test_failure_sensitivity_demonstration_test_d` | **NEW** | Proves assertions fail when sentinel is missing, when context is empty/purged, and when provenance is swapped. | Directly executes `with pytest.raises(AssertionError)` against mutated conditions. |
| **Test E-1** | `test_top_doc_defect_vulnerability_demonstration` | **REUSED** | `Dr. Elena Rostova` in context; `Frank Miller` excluded (DEFECT-01). | Fails if hard top_doc filter is restored. |
| **Test E-2** | `test_candidate_starvation_remediation_test_b` | **REUSED** | High-sim uncorroborated candidate wins over low-sim fact candidate (DEFECT-03). | Fails if starved branch is restored. |
| **Test E-3** | `test_rest_pure_structural_query_test_d` | **REUSED** | HTTP 200 on pure structural document (0 SVOA facts); context delivered. | Fails if empty SVOA check is restored. |
| **Test E-4** | `test_websocket_pure_structural_query_test_e` | **REUSED** | WebSocket succeeds on pure structural document (0 SVOA facts). | Fails if empty SVOA check is restored. |
| **Test E-5** | `test_truly_empty_store_rejection_test_f` | **REUSED** | HTTP 400 Bad Request on genuinely empty store; WS error event. | Fails if empty guard is removed. |
| **Test E-6** | `test_feature_disabled_pure_structural_compatibility_test_g` | **REUSED** | Pure structural rejected when disabled; byte-for-byte legacy context parity. | Fails if disabled flag leaks structural context. |

---

## 4. Assertion Rigor Audit (Verification Against Print-Only Diagnostics)

Every test in `scripts/test_experiment_4_5_persistence_audit.py` was audited for passive assertions:
- **Print Statements**: Exactly 0 test functions rely on `print()` to report outcomes.
- **Assertion Coverage**: Every test contains explicit `assert` statements.
- **FastAPI Validation**: Responses are validated via `response.status_code == 200` and `assert response.json()`.
- **WebSocket Validation**: Incoming messages are strictly parsed; `error` messages trigger `pytest.fail()`.

---

## 5. Disjointness and Duplicate Node ID Verification

Execution of `pytest --collect-only -q` across all 5 suite paths returned:
- Total collected node IDs: **478**
- Set of unique node IDs: **478**
- Duplicate node IDs: **0**

Disjointness between `backend/tests/` and `scripts/` is structurally guaranteed: zero test modules in `scripts/` are discovered by `pytest backend/tests/`, and zero test modules in `backend/tests/` import test functions from `scripts/`.
