# Comprehensive Test-Report Accounting and Overlap Reconciliation

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Status**: RECONCILED AND VERIFIED

---

## 1. The 528 vs. 451 Overlap Discrepancy

In the Experiment 4.5.2 implementation report (`results/diagnostic_experiment_4_v1/production_persistence_20261010/implementation_report.md`), the summary table reported a grand total of **528 passed tests**:

```
Full Backend Regression Suite:        418
Persistent Structural Suite:            21
Production Wiring Suite:                 9
Structural Integration Suite:           47
Diagnostic Cohort Integrity:            13
Diagnostic Fixtures:                     5
Diagnostic Extractor Audit:             15
------------------------------------------
Reported Total:                        528
```

### Audit Finding (DEFECT-04)
The audit identified that the three specialized suites:
1. `backend/tests/test_structural_persistence.py` (21 tests)
2. `backend/tests/test_production_wiring.py` (9 tests)
3. `backend/tests/test_structural_integration.py` (47 tests)

are all located directly within the `backend/tests/` directory. When running `./backend/venv/bin/pytest backend/tests/`, pytest collects and executes all 77 of these tests as part of the 418 total backend tests.

Summing the full suite total (418) with the subsets (21 + 9 + 47 = 77) resulted in **double-counting 77 tests**.

### Corrected Baseline (Pre-Experiment 4.5.3)
- Unique Backend Tests: **418**
- Unique Diagnostic Script Tests: 13 + 5 + 15 = **33**
- **Actual Unique Tests Prior to 4.5.3**: **451** (not 528).

---

## 2. Current Unique Test Accounting (Experiment 4.5.3)

With the addition of the independent audit suite in `scripts/test_experiment_4_5_persistence_audit.py` (19 tests), the total unique test inventory is:

```
Unique Backend Tests:                  418
Unique Scripts Tests:                   52 (33 diagnostic + 19 audit)
------------------------------------------
True Unique Test Total:                470
```

---

## 3. Detailed Non-Overlapping Test Breakdown

### A. Backend Test Suite (`backend/tests/`)
Command: `./backend/venv/bin/pytest backend/tests/`  
Total Collected: **418** | Passed: **418** | Failed: **0** | Duration: **195.22s** | Exit Code: **0**

| Test Module | Test Count | Focus Area |
|---|---|---|
| `test_api.py` | 19 | REST API authentication, ingestion, query, and WebSocket basics |
| `test_coref.py` | 24 | FCoref neural coreference resolution |
| `test_evaluation.py` | 39 | Evaluation harness and ablation metrics |
| `test_failure_analysis.py` | 17 | Historical failure taxonomy tracking |
| `test_hardware.py` | 20 | Edge hardware detection and token ceiling calibration |
| `test_inference.py` | 27 | Ollama local inference and prompt templates |
| `test_packer.py` | 26 | Stage 4 SVOA fact packing and modality filtering |
| `test_production_wiring.py` | 9 | Orchestrator wiring of structural context |
| `test_sdh.py` | 25 | Semantic Density Heuristic 4-term scoring |
| `test_security.py` | 20 | JWT tokens and prompt injection sanitization |
| `test_store.py` | 17 | FactStore ChromaDB dual-collection operations |
| `test_structural_integration.py` | 47 | Feature flag parsing, HTML parser, and budget accounting |
| `test_structural_persistence.py` | 21 | Persistence lifecycle and end-to-end integration |
| `test_svoa.py` | 107 | SVOA dependency extraction, negation, and copular structures |
| **Subtotal (Backend)** | **418** | **All tests verified passing** |

### B. Isolated Scripts & Diagnostic Suite (`scripts/`)
Command: `./backend/venv/bin/pytest scripts/test_*.py`  
Total Collected: **52** | Passed: **52** | Failed: **0** | Duration: **58.31s** | Exit Code: **0**

| Test Module | Test Count | Focus Area |
|---|---|---|
| `scripts/test_experiment_4_2_integrity.py` | 13 | Cohort hashing, threshold isolation, paired McNemar stats |
| `scripts/test_experiment_4_3_fixtures.py` | 5 | Deterministic HTML list and table fixtures |
| `scripts/test_experiment_4_4_audit_extractor.py` | 15 | HTML decompiler and GFM table chunker audit |
| `scripts/test_experiment_4_5_persistence_audit.py` | 19 | Experiment 4.5.3 independent persistence & retrieval audit |
| **Subtotal (Scripts)** | **52** | **All tests verified passing** |

---

## 4. Execution Summary

| Scope | Files | Unique Tests | Passed | Failed | Exit Code | Real Duration |
|---|---|---|---|---|---|---|
| Full Backend | 14 files | 418 | 418 | 0 | 0 | 195.22s |
| Scripts Diagnostics & Audit | 4 files | 52 | 52 | 0 | 0 | 58.31s |
| **Total Non-Overlapping** | **18 files** | **470** | **470** | **0** | **0** | **253.53s** |

Zero tests timed out, zero tests failed, and zero tests were skipped.
