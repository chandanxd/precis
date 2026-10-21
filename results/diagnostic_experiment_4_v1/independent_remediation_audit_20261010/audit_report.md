# Experiment 4.5.5: Independent Audit of Structural Retrieval Remediation

**Date**: 2026-10-10  
**Environment**: Linux x86_64, Python 3.12.3  
**Auditor**: Independent Pipeline Audit Subagent (Antigravity AI)  
**Target Under Audit**: Experiment 4.5.4 Remediation (Fixes for DEFECT-01, DEFECT-02, and DEFECT-03)

---

## 1. Executive Verdict

**EXECUTIVE VERDICT**: **`PASS WITH LIMITATIONS`**

### Summary
The Experiment 4.5.4 remediation successfully resolves the three functional defects identified in Experiment 4.5.3:
1. **DEFECT-01 (Hard `top_doc` bias)** is removed from `backend/src/precis/pipeline/structural.py`. Structural candidates compete in a similarity-dominant blended ranking with a bounded document affinity boost (+25% max) and deterministic tie-breaking.
2. **DEFECT-02 (Rejection of pure-structural stores)** is resolved in `backend/main.py` across both REST (`query()`) and WebSocket (`_handle_ws_query()`) endpoints, enabling stores with 0 SVOA facts and $>0$ structural records to be queried normally when enabled.
3. **DEFECT-03 (Candidate starvation)** is eliminated by pooling all eligible candidates across document groups rather than taking `matched_items` exclusively.

Disabled-mode byte parity with the legacy SVOA pipeline is verified. The test suite of **476 distinct test functions** passes with a 100% pass rate. All frozen artifacts from Experiments 4.2, 4.3, and 4.4 remain unmodified.

An unconditional `PASS` is tempered to **`PASS WITH LIMITATIONS`** due to one medium architectural limitation (absence of cross-document table-to-table deduplication) and two low-severity items (documentation descriptive compression and reliance on real embeddings rather than synthetic score tuples in integration ranking tests).

---

## 2. Separate Component Verdicts

| Subsystem / Audit Dimension | Verdict | Summary of Findings |
|---|---|---|
| **Implementation Correctness** | **`PASS`** | All 3 defects correctly remediated in actual production paths (`structural.py`, `main.py`). Zero secondary guards or early returns remain. |
| **Test Quality & Assertion Rigor** | **`PASS WITH LIMITATIONS`** | Tests A through G employ strict assertions and fail under the old code. However, ranking tests rely on sentence-transformer embeddings rather than synthetic score tuples. |
| **Compatibility & Feature Flags** | **`PASS`** | Disabled mode is 100% byte-for-byte identical to the legacy pipeline. Default is `False`. Zero structural writes when disabled. |
| **Integrity & Preservation** | **`PASS`** | Zero Git commits, resets, or stashes. Frozen Experiment 4.2/4.3/4.4 hashes 100% intact. Zero live inference or benchmarks run. |
| **Gate 5 Justification** | **`JUSTIFIED TO PROCEED`** | Subsystem is architecturally stable and deterministic. Ready for confirmatory accuracy benchmark upon user authorization. |

---

## 3. Findings Ranked by Severity

### Finding ARCH-01 [MEDIUM SEVERITY]: Absence of Cross-Document Structural Chunk Deduplication
- **Location**: `backend/src/precis/pipeline/structural.py`, lines 1346–1360.
- **Description**: While intra-document table-list overlap is deduplicated during ingestion, and SVOA facts are deduplicated against selected structural evidence, there is **no cross-document table deduplication**.
- **Impact**: If multiple ingested documents contain identical or mirrored tables (e.g., duplicated company disclosures across two press releases), both tables will enter `ranked_struct` with identical high scores and can consume up to 2 or 3 of the limited top-3 structural slots.
- **Recommendation**: In a future optimization pass, introduce a Jaccard/header-similarity deduplication step among `ranked_struct` candidates before slicing to top 3. For current Single-Document / Clean Multi-Document benchmarks, this risk is bounded.

### Finding TEST-01 [LOW SEVERITY]: Synthetic Score Control Gap in Integration Ranking Tests
- **Location**: `scripts/test_experiment_4_5_persistence_audit.py`, Tests A, B, and C.
- **Description**: Tests A, B, and C rely on natural embedding scores produced by `all-MiniLM-L6-v2` from designed HTML text rather than injecting mocked score tuples into `query_similar_structural()`.
- **Impact**: The tests successfully execute the full production ChromaDB pipeline, but their assertions could be sensitive to future changes in the underlying sentence-transformer embedding weights.
- **Recommendation**: Retain existing integration tests and add a pure unit test with explicit mock tuples `[(item1, 0.45), (item2, 0.55)]` in a future test refinement.

### Finding DOC-01 [LOW SEVERITY]: Descriptive Compression in `implementation_report.md`
- **Location**: `results/diagnostic_experiment_4_v1/retrieval_defect_remediation_20261010/implementation_report.md`, Section 4.
- **Description**: The report described candidate eligibility as a single combined condition rather than explicitly illustrating the two-phase pipeline where Filter 2 operates downstream of Filter 1.
- **Impact**: `ranking_strategy.md` provides the complete two-phase architectural breakdown, resolving the discrepancy.

---

## 4. Remediation Verification Summary

| Defect ID | Defect Description | Pre-Remediation Behavior | Post-Remediation Verification | Audit Status |
|---|---|---|---|---|
| **DEFECT-01** | Hard `top_doc` bias discards relevant structural evidence from other documents | `energy_summit.html` produced top SVOA fact; `Frank Miller` ($sim=0.32$) monopolized context; `Dr. Elena Rostova` ($sim=0.58$) dropped. | Similarity-dominant ranking evaluates all candidates. `Dr. Elena Rostova` ranked #1 and retained in context. | **VERIFIED FIXED** |
| **DEFECT-02** | REST and WebSocket reject stores with structural evidence but zero SVOA facts | Query on pure-table document returned `HTTP 400 Bad Request` ("No documents ingested"). WebSocket emitted error frame. | Both handlers check both collections. Pure-table query returns `HTTP 200 OK` and streams tokens. | **VERIFIED FIXED** |
| **DEFECT-03** | `(matched_items if matched_items else other_items)` starves non-`fact_docs` candidates | Weak candidate in `matched_items` ($sim=0.28$) excluded strong candidate in `other_items` ($sim=0.65$). | Candidates pooled across groups. Strong candidate ($0.42\text{ ms}$) selected over weak candidate. | **VERIFIED FIXED** |

---

## 5. Test Accounting Summary

The claimed **476 unique non-overlapping tests** was independently audited:
- Backend test suite (`backend/tests/`): **418** collected.
- Persistence audit suite (`scripts/test_experiment_4_5_persistence_audit.py`): **25** collected.
- Diagnostic integrity suite (`scripts/test_experiment_4_2_integrity.py`): **13** collected.
- Diagnostic fixtures suite (`scripts/test_experiment_4_3_fixtures.py`): **5** collected.
- Diagnostic extractor suite (`scripts/test_experiment_4_4_audit_extractor.py`): **15** collected.
- **Total collected across listed suites**: **476**.
- **Audit Verification**: All 5 test suites execute on disjoint files in disjoint directories. Zero duplicate test node IDs exist across the suites. All 476 tests pass.

---

## 6. Gate 5 Readiness Verdict

**Verdict**: **`GATE 5 PROCEED JUSTIFIED`**

The persistent structural retrieval subsystem is deterministically verified, structurally isolated, compatible with legacy pipelines, and free of the three identified retrieval defects. The identified limitations are bounded and do not block the Gate 5 confirmatory benchmark.

**Next Step**: Await explicit user authorization before initiating the Gate 5 accuracy evaluation.
