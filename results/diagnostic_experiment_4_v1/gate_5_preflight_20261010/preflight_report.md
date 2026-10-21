# Experiment 4.5.6: Gate 5 Production-Path Confirmatory Preflight Report

**Evaluation Date**: 2026-10-10  
**Phase**: Phase 1 Preflight (Read-Only Inspection & Deterministic Verification)  
**Evaluator**: Independent Evaluation Agent (Antigravity AI)  
**Directory**: `results/diagnostic_experiment_4_v1/gate_5_preflight_20261010/`  

---

## 1. Executive Preflight Verdict

**FINAL VERDICT**: **`READY FOR EXPLICIT AUTHORIZATION`**

### Summary
Phase 1 deterministic preflight has completed with zero defects and zero regressions:
- The persistent production path implemented across `backend/src/precis/pipeline/structural.py`, `backend/src/precis/pipeline/orchestrator.py`, `backend/src/precis/graph/store.py`, and `backend/main.py` is technically sound, robust, and verified.
- The 200-case table-bearing cohort, gold answers, and canonical frozen reference predictions (Conditions A through E) are verified bit-identically against frozen manifests with zero discrepancies.
- Real application handlers (`POST /api/ingest`, `POST /api/query`, and WebSocket `/ws`) were tested with mocked generation: all 11 persistent lifecycle invariants passed deterministically.
- Disabled-mode compatibility (`PRECIS_ENABLE_LIST_EXTRACTION=false`) was verified: byte-for-byte context parity (118 bytes) with the legacy SVOA pipeline is preserved, and zero structural evidence is persisted when disabled.
- The test suite of **476 unique, non-overlapping tests** passed with a **100% pass rate**.
- **Phase 2 live inference has NOT been run.** Execution is stopped at the authorization gate awaiting user approval.

---

## 2. Mandatory Preflight Checkpoints

| # | Checkpoint Dimension | Preflight Finding & Evidence | Status |
|:---:|:---|:---|:---:|
| **1** | **Technical Readiness of Candidate Path** | Ingestion-side structural extraction, ChromaDB persistence, similarity-dominant ranking, and context packing function properly across both REST and WebSocket paths. | **READY** |
| **2** | **200-Case Cohort & Frozen References** | Exactly 200 unique cases in manifest. Predictions for A, B, C, D, E match canonical records 100%. Recomputed scores match stored scores exactly. Belichick case analysis verified. | **VERIFIED** |
| **3** | **REST & WebSocket Context Delivery** | Tested with mocked generator fixtures. REST `POST /api/query` and WebSocket `/ws` successfully deliver structural evidence from store without requiring `raw_document` at query time. | **VERIFIED** |
| **4** | **Disabled-Mode Compatibility** | Tested with `PRECIS_ENABLE_LIST_EXTRACTION=false`. Empty store rejection preserved. Context byte-for-byte identical to baseline SVOA pipeline. 0 structural chunks stored. | **VERIFIED** |
| **5** | **Unresolved Defects** | Zero critical or high-severity defects. DEFECT-01, DEFECT-02, DEFECT-03 verified resolved. One medium-severity architectural limitation characterized (ARCH-01: cross-document table deduplication). | **BOUNDED** |
| **6** | **Candidate Condition & Comparators** | **Candidate Condition F**: Persistent Production Structural Retrieval (`PRECIS_ENABLE_LIST_EXTRACTION=true` in isolated runner). **Primary Comparators**: Frozen Condition D ($\theta=0.0$) and Frozen Condition E (in-memory tables + lists). **Contextual Baseline**: Frozen Condition A. | **DEFINED** |
| **7** | **Inference-Call Accounting** | Exactly **200 inference calls** will be executed in Phase 2 (one call per case for Condition F). 1,000 historical predictions (A–E) will be reused directly from frozen records. 0 historical calls will be rerun. | **PLANNED** |
| **8** | **Known Limitations Characterized** | 1. ARCH-01: Cross-document table deduplication absent (non-confounding for single-document queries in NQ). 2. Subword token estimator heuristic (`estimate_text_tokens`) used for ceiling enforcement. | **CHARACTERIZED** |
| **9** | **Integrity & Test Results** | 476/476 collected tests passed across 5 disjoint suites. Zero duplicate test node IDs. Working tree preserved untouched. Frozen artifact hashes 100% intact. | **PASSED** |
| **10** | **Authorization Boundary** | **Phase 1 is complete. Zero live model inferences, network requests, or benchmark runs were performed. The pipeline is stopped and awaiting explicit user authorization.** | **ENFORCED** |

---

## 3. Reference Benchmark Comparison Baseline ($N=200$)

| Condition | Description | Exact Match (EM) | Containment | Net EM vs. A | Net EM vs. D |
|:---:|:---|:---:|:---:|:---:|:---:|
| **A** | Prose Baseline (Coref + Prose SVOA) | 64 / 200 (32.0%) | 87 / 200 (43.5%) | Baseline (0.0 pp) | -17.5 pp |
| **B** | Stage C Decompiled Prose | 28 / 200 (14.0%) | 39 / 200 (19.5%) | -18.0 pp | -35.5 pp |
| **C** | Table Retention ($\theta=2.0$) | 61 / 200 (30.5%) | 79 / 200 (39.5%) | -1.5 pp | -19.0 pp |
| **D** | Table Retention ($\theta=0.0$) | 99 / 200 (49.5%) | 122 / 200 (61.0%) | +17.5 pp | Baseline (0.0 pp) |
| **E** | Prototype Tables ($\theta=0.0$) + Lists | 108 / 200 (54.0%) | 137 / 200 (68.5%) | +22.0 pp ($p < 10^{-8}$) | +4.5 pp ($p = 0.035$) |
| **F** | **Persistent Production Structural Pipeline** | *(To be evaluated in Phase 2)* | *(To be evaluated in Phase 2)* | *(Pending)* | *(Pending)* |

---

## 4. Architectural Distinctions: Condition E vs. Condition F

Understanding the architectural relationship between Condition E (the prototype) and Condition F (the persistent production path) is essential for interpreting the upcoming Phase 2 evaluation:

| Dimension | Condition E (Experiment 4.4 Prototype) | Condition F (Experiment 4.5.6 Production Candidate) |
|---|---|---|
| **Storage & Persistence** | In-memory only; parsed on the fly per question from `raw_document`. | Ingestion-time persistence in ChromaDB secondary collection (`structural_evidence`). |
| **Vector Search** | None; all tables at $\theta=0$ and all content lists considered. | Semantic vector search over structural chunks using `all-MiniLM-L6-v2` (384 dimensions). |
| **Candidate Selection** | Hard inclusion of all extracted structural elements up to ceiling. | Similarity-dominant blended ranking with document affinity boost and relevance filters (Filters 1 & 2). |
| **Structural Chunk Budget** | Unlimited chunk count (bounded only by 2,048 token ceiling). | Sliced to top 3 structural chunks to preserve budget for corroborating SVOA facts. |
| **SVOA Fact Integration** | Zero SVOA facts included (pure structural tables + lists). | Blends surviving top SVOA facts into any remaining token budget after structural packing. |
| **Application Handlers** | Bypasses `orchestrator.py` and `main.py`. | Fully routed through `orchestrator.py`, `assemble_query_context`, and API endpoints. |

---

## 5. Scope & Safety Constraint Compliance

- [x] Application source code under `backend/src/precis/` and `backend/main.py` remained untouched.
- [x] Zero Git commits, resets, stashes, or branch changes were made.
- [x] Zero live model inference was executed (Ollama was not called).
- [x] Zero network requests were made.
- [x] Zero benchmark evaluations were run.
- [x] Default feature flag `PRECIS_ENABLE_LIST_EXTRACTION` remains `false`.
- [x] All 7 frozen benchmark input digests were verified bit-identically.
- [x] All Phase 1 deliverables are strictly contained in `results/diagnostic_experiment_4_v1/gate_5_preflight_20261010/`.

---

## 6. Stop Condition & Next Action

**Execution is stopped.** Phase 1 is fully complete.

To initiate the live evaluation:
- The user must provide explicit authorization to execute Phase 2.
- Upon authorization, the runner will execute exactly 200 inference calls for Condition F, compute paired McNemar tests against frozen D and E, and generate the final confirmatory evaluation report.
