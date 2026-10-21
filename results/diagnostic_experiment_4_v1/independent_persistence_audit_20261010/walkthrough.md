# Experiment 4.5.3 Walkthrough: Independent Structural Persistence Integration Audit

**Date**: 2026-10-10  
**Status**: Audit Complete | Verdict: PASS WITH LIMITATIONS  
**Output Directory**: `results/diagnostic_experiment_4_v1/independent_persistence_audit_20261010/`

---

## 1. Audit Overview & Rules of Engagement

Experiment 4.5.3 performed an exhaustive independent audit of the persistent structural evidence implementation completed in Experiment 4.5.2.

Strict adherence to non-negotiable constraints was maintained:
- **Zero Production Modifications**: No files under `backend/src/precis/` or `backend/main.py` were edited or altered.
- **Hash Verified**: All 8 target implementation files match their pre-audit SHA-256 hashes exactly.
- **Frozen Cohorts Untouched**: No Experiment 4.2, 4.3, or 4.4 files were touched or overwritten.
- **Zero Live Calls**: Zero live model inferences, network requests, or external APIs were executed.

---

## 2. Executive Findings Summary

| Identifier | Severity | Title | Affected File & Lines |
|---|---|---|---|
| **DEFECT-01** | **HIGH** | Hidden SVOA dependency in multi-document structural selection (`top_doc` bias) | `backend/src/precis/pipeline/structural.py:1320-1323` |
| **DEFECT-02** | **HIGH** | Rejection of pure-structural knowledge bases by REST & WebSocket query handlers | `backend/main.py:272,550` |
| **DEFECT-03** | **MEDIUM** | Starvation of non-`fact_docs` candidate documents by `matched_items` | `backend/src/precis/pipeline/structural.py:1327` |
| **DEFECT-04** | **MEDIUM** | Double-counted test metrics in Experiment 4.5.2 report (528 reported vs 451 actual) | `results/.../implementation_report.md` |

---

## 3. Verified Capabilities

1. **Flag Defaults and Safe Precedence**:
   - `PRECIS_ENABLE_LIST_EXTRACTION` defaults to `False` when unset.
   - Parameter overrides execute safely in request scope without mutating global environment variables.
2. **Disabled-Mode Byte-Level Parity**:
   - Pure prose, table-only, and mixed documents produce exact byte-identical context to legacy SVOA fact packing.
   - Zero structural parsing, vector writes, or vector searches occur when disabled.
3. **Dual-Collection ChromaDB Persistence**:
   - Reuses `SentenceTransformer("all-MiniLM-L6-v2")` with 384 dimensions and cosine metric.
   - Content-addressed SHA-256 IDs prevent duplicates.
   - Re-ingestion safely deletes obsolete structural chunks.
   - `delete_document` and `clear` purge both collections synchronously.
4. **REST and WebSocket Production Integration**:
   - Both `POST /api/query` and WebSocket `/ws` query streams successfully deliver persistent structural context to the LLM generator without requiring `raw_document` in the request payload.
5. **Context Budget Enforcement**:
   - Strictly enforces ceilings across 100, 250, 500, 1000, and 2048 token budgets with header reservations.
6. **Regression Failure Safeguards**:
   - Cases `3f5983b2`, `ef634417`, and `8f1f9bd9` have valid context representations that prevent historical failure modes at the prompt level.

---

## 4. Test Accounting Reconciliation

- Total Unique Tests in Repository: **470 passed** (0 failed, 0 skipped).
  - `backend/tests/`: **418** unique tests.
  - `scripts/`: **52** unique tests (33 diagnostic + 19 audit probes).
- The previously reported 528 count resulted from summing subsets of `backend/tests/` with the total suite.

---

## 5. Deliverable Audit Reports

All 11 audit documents have been generated in `results/diagnostic_experiment_4_v1/independent_persistence_audit_20261010/`:
1. `audit_report.md` (Main report, verdict, findings, reproduction steps, proposed fixes)
2. `test_results.json` (Structured JSON test accounting and defect matrix)
3. `feature_flag_audit.md` (Detailed flag semantics and byte parity audit)
4. `persistence_lifecycle_audit.md` (Extraction, hashing, lifecycle, embedding verification)
5. `retrieval_isolation_audit.md` (Trace of retrieval, `top_doc` vulnerability analysis)
6. `rest_websocket_audit.md` (REST & WebSocket handler execution, pure-structural bug)
7. `context_budget_audit.md` (Multi-scale token ceiling and deduplication evaluation)
8. `regression_fixture_audit.md` (Detailed trace of historical failure cases)
9. `test_accounting.md` (Reconciliation of the 528 vs 451/470 overlap discrepancy)
10. `integrity_report.json` (Pre- and post-audit file hash verification)
11. `walkthrough.md` (Audit process and summary walkthrough)
