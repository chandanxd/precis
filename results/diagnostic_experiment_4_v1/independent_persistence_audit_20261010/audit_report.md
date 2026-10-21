# Experiment 4.5.3: Independent Structural Persistence Integration Audit Report

**Date**: 2026-10-10  
**Environment**: Linux x86_64, Python 3.12.3  
**Auditor**: Independent Pipeline Audit Subagent (Antigravity AI)  
**Target Under Audit**: Experiment 4.5.2 Implementation (Dual-Collection Persistence & Production Wiring)

---

## 1. Executive Verdict

**EXECUTIVE VERDICT**: **`PASS WITH LIMITATIONS`**

### Summary
The core objectives of Experiment 4.5.2—extracting structural tables and lists during ingestion, persisting them into ChromaDB using the existing 384-dimensional cosine embedding infrastructure, assembling them into context, and wiring them into the REST and WebSocket query endpoints without requiring `raw_document` in request payloads—are **verified and functional**. Disabled-mode byte parity with the legacy SVOA pipeline is verified.

However, an unconditional `PASS` cannot be granted due to **two critical/high architectural defects** and **two medium defects** identified during this independent audit:
1. **DEFECT-01 (High Severity)**: The multi-document `top_doc` selection logic creates a hidden dependency on SVOA fact ranking. If an irrelevant document produces the top SVOA fact due to lexical prose overlap, its structural chunks monopolize the context, silently discarding higher-similarity structural answers from the correct document.
2. **DEFECT-02 (High Severity)**: If an ingested document consists purely of tables or lists (producing 0 SVOA facts), `active_store.count() == 0`. The REST API (`POST /api/query`) and WebSocket handlers immediately reject queries with HTTP 400 Bad Request ("No documents ingested. Upload a document first"), rendering pure-structural knowledge bases completely unqueryable.
3. **DEFECT-03 (Medium Severity)**: The candidate selection expression `(matched_items if matched_items else other_items)` completely starves non-`fact_docs` structural records if any item in `matched_items` exists, regardless of similarity differences.
4. **DEFECT-04 (Medium Severity)**: The Experiment 4.5.2 implementation report reported 528 tests by double-counting 77 tests in `backend/tests/`. The true unique test baseline is 451 tests (expanded to 470 with this audit).

---

## 2. Verified Behavior vs. Unverified Claims

| Feature / Claim | Claim in 4.5.2 Report | Actual Audit Status | Audit Evidence & Notes |
|---|---|---|---|
| **Flag Default** | Disabled by default | **VERIFIED** | `is_list_extraction_enabled()` defaults to `False` when unset. |
| **Override Safety** | Overrides do not leak | **VERIFIED** | Function overrides do not mutate `os.environ` or global state. |
| **Disabled-Mode Parity** | 100% byte-for-byte identical | **VERIFIED** | Verified exact string equality with legacy SVOA packing. |
| **Zero Overhead When Disabled** | No structural writes/queries | **VERIFIED** | Structural extraction, ChromaDB writes, and vector searches skipped. |
| **Dual-Collection Persistence** | Shared client, 384-d cosine | **VERIFIED** | Model is `all-MiniLM-L6-v2`, 384-d, `hnsw:space: "cosine"`. |
| **Deterministic Upsert** | Re-ingest replaces records | **VERIFIED** | Obsolete records deleted before re-inserting; IDs are SHA-256 addressed. |
| **Deletion & Clear** | Both collections purged | **VERIFIED** | Synchronously cleans `{collection_name}` and `{collection_name}_structural`. |
| **REST Wire Delivery** | Structural context to LLM | **VERIFIED** | `POST /api/query` passes structural context to generator without `raw_document`. |
| **WebSocket Delivery** | Stream context with structure | **VERIFIED** | Stage 4 and Stage 5 streaming utilize persistent structural context. |
| **Multi-Doc Isolation** | No cross-doc leakage | **VERIFIED WITH LIMITATIONS** | Works when SVOA facts identify the correct document; **fails if SVOA top fact belongs to wrong document** (DEFECT-01). |
| **Pure-Structural Ingestion** | Full support for tables/lists | **UNVERIFIED / FAILS** | Ingestion succeeds, but query fails with HTTP 400 "No documents ingested" (DEFECT-02). |
| **Token Budget Ceilings** | Strictly obeys token ceiling | **VERIFIED** | Verified across 100, 250, 500, 1000, and 2048 token budgets. |
| **Historical Regressions** | 3f5983b2, ef634417, 8f1f9bd9 | **VERIFIED AT CONTEXT LEVEL** | Evidence preserved in context. (Semantic answerability depends on LLM inference). |
| **Test Accounting Total** | 528 unique passing tests | **DISPROVEN (Overlapping)** | 77 tests were double-counted. Correct total was 451; now 470 with audit suite. |

---

## 3. Findings Ranked by Severity

### Finding 1 [HIGH SEVERITY]: Hidden SVOA Dependency (`top_doc` Bias)
- **Location**: `backend/src/precis/pipeline/structural.py`, lines 1320–1323 (`assemble_structural_query_context`)
- **Code Snippet**:
  ```python
  if fact_docs:
      top_doc = pack_res.packed_facts[0].source_doc if pack_res.packed_facts else None
      top_items = [it for it in relevant_struct if it[0].source_doc == top_doc]
      if top_items:
          selected_struct = top_items[:3]
  ```
- **Description**: If Document A contains prose with high keyword overlap with the query, it produces the #1 SVOA fact. Even if Document B has the true answer in a table with high similarity (e.g. 0.75), if Document A has *any* structural chunk with similarity >= 0.25, `top_items` selects Document A's chunk and completely discards Document B's answer.
- **Impact**: Undermines structural retrieval in multi-document corpora specifically when SVOA facts point to the wrong document.

### Finding 2 [HIGH SEVERITY]: Rejection of Pure-Structural Knowledge Bases
- **Location**: `backend/main.py`, lines 272–276 (`query` endpoint) and lines 550–557 (`_handle_ws_query`)
- **Code Snippet**:
  ```python
  if active_store.count() == 0:
      raise HTTPException(
          status_code=400,
          detail="No documents ingested. Upload a document first.",
      )
  ```
- **Description**: `active_store.count()` only counts SVOA facts. For documents with only tables or lists (e.g. data catalogs, financial tables), `active_store.count() == 0`. The server rejects queries with HTTP 400 Bad Request, even though `active_store.count_structural_evidence() > 0`.
- **Impact**: Completely prevents querying pure tabular or list documents through production APIs.

### Finding 3 [MEDIUM SEVERITY]: Starvation of Non-`fact_docs` Candidates
- **Location**: `backend/src/precis/pipeline/structural.py`, line 1327
- **Code Snippet**:
  ```python
  selected_struct = (matched_items if matched_items else other_items)[:3]
  ```
- **Description**: When `top_items` is empty, if `matched_items` contains any item from secondary documents in `fact_docs`, `other_items` is never consulted. Highly relevant structural chunks from documents outside `fact_docs` are starved.
- **Impact**: Drops relevant structural evidence when top SVOA facts span several documents that contain weakly related tables.

### Finding 4 [MEDIUM SEVERITY]: Inflated Test Count Accounting
- **Location**: `results/diagnostic_experiment_4_v1/production_persistence_20261010/implementation_report.md`
- **Description**: The previous report summed 418 (full backend) with 21 + 9 + 47 (subsets in `backend/tests/`), double-counting 77 tests.
- **Impact**: Misleading test metric in project records.

---

## 4. Non-Overlapping Test Accounting

```
Backend Tests (backend/tests/):        418 passed (0 failed, 0 skipped, 195.22s)
Diagnostic Scripts (scripts/):          33 passed (0 failed, 0 skipped, 3.87s)
Independent Audit Suite (scripts/):     19 passed (0 failed, 0 skipped, 54.44s)
---------------------------------------------------------------------------------
Total Unique Non-Overlapping Tests:    470 passed (0 failed, 0 skipped, 253.53s)
```

Every test file and its unique count:
- `test_svoa.py`: 107
- `test_structural_integration.py`: 47
- `test_evaluation.py`: 39
- `test_inference.py`: 27
- `test_packer.py`: 26
- `test_sdh.py`: 25
- `test_coref.py`: 24
- `test_structural_persistence.py`: 21
- `test_hardware.py`: 20
- `test_security.py`: 20
- `test_api.py`: 19
- `test_failure_analysis.py`: 17
- `test_store.py`: 17
- `test_production_wiring.py`: 9
- `test_experiment_4_5_persistence_audit.py`: 19
- `test_experiment_4_4_audit_extractor.py`: 15
- `test_experiment_4_2_integrity.py`: 13
- `test_experiment_4_3_fixtures.py`: 5

---

## 5. Exact Reproduction Steps for Identified Defects

### Reproduction 1: DEFECT-01 (`top_doc` Bias)
Execute:
```bash
./backend/venv/bin/pytest scripts/test_experiment_4_5_persistence_audit.py -k test_top_doc_defect_vulnerability_demonstration -s
```
**Observed Behavior**:
- Document A has SVOA prose about an energy summit and an irrelevant nominee table (`Frank Miller`).
- Document B has the true winner in an award table (`Dr. Elena Rostova`).
- Query: `"Who won the renewable energy innovation award at the energy summit?"`
- Assembled context retains `Frank Miller` and **drops `Dr. Elena Rostova`**.

### Reproduction 2: DEFECT-02 (Pure-Structural Rejection)
Execute:
```bash
./backend/venv/bin/pytest scripts/test_experiment_4_5_persistence_audit.py -k test_zero_svoa_facts_store_rejection -s
```
**Observed Behavior**:
- Ingest pure table document (`pure_table.html`).
- `store.count() == 0`, `store.count_structural_evidence() == 1`.
- `POST /api/query` returns `HTTP 400: {"detail": "No documents ingested. Upload a document first."}`.

---

## 6. Proposed Fixes (Pending Explicit Approval)

### Proposed Fix for DEFECT-01: Similarity-Dominant Blended Ranking
In `backend/src/precis/pipeline/structural.py`:
Replace the hard `top_doc` filter with a soft document affinity score:
```python
def score_candidate(item_tuple):
    item, sim = item_tuple
    doc = item.source_doc
    boost = 1.0
    if doc in fact_docs:
        boost += 0.20
    if doc == top_doc:
        boost += 0.15
    return sim * boost

selected_struct = sorted(relevant_struct, key=score_candidate, reverse=True)[:3]
```
This preserves document isolation for low-similarity distractor chunks while allowing a high-confidence structural chunk (sim >= 0.70) from another document to surface when SVOA retrieval misidentifies the primary document.

### Proposed Fix for DEFECT-02: Unified Ingestion Guard
In `backend/main.py`:
- In line 272 (`query` endpoint):
  ```python
  if active_store.count() == 0 and not active_store.has_structural_evidence():
      raise HTTPException(
          status_code=400,
          detail="No documents ingested. Upload a document first.",
      )
  ```
- In line 550 (`_handle_ws_query`):
  ```python
  if active_store.count() == 0 and not active_store.has_structural_evidence():
      await ws.send_json(
          {
              "type": "error",
              "detail": "No documents ingested",
          }
      )
      return
  ```
- In `backend/src/precis/pipeline/packer.py` line 218:
  Do not early-return `_empty_pack_result()` if the store contains structural evidence.
