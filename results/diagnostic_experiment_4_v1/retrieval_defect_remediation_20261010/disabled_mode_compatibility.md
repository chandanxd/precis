# Disabled Mode Compatibility and Byte-Parity Audit

**Experiment 4.5.4 Remediation Verification**  
**Date**: 2026-10-10  
**Feature Flag**: `PRECIS_ENABLE_LIST_EXTRACTION` (Default: `false`)

---

## 1. Zero-Regression Design Principles

1. **Disabled by Default**: When `PRECIS_ENABLE_LIST_EXTRACTION` is unset or set to `0`, `false`, `no`, `off`, or `""`, the system behaves as the classical SVOA pipeline.
2. **Byte-for-Byte Identical Context**: Under disabled mode, `assemble_query_context()` calls `pack_context()` and `render_context()` directly, producing string output byte-for-byte identical to the legacy pipeline.
3. **Zero Structural Persistence Overhead**: During document ingestion with the flag disabled, table and list extraction is completely skipped; zero embeddings are computed for structural blocks, and zero records are inserted into `{collection_name}_structural`.
4. **Clean Override Isolation**: In-memory function parameter overrides (`enable_list_extraction=True`) never mutate `os.environ` or persist across requests.

---

## 2. Deterministic Verification Evidence

### Test Evidence from `scripts/test_experiment_4_5_persistence_audit.py`

#### A. Byte-Identical Context (`test_disabled_mode_byte_identical_context`)
- Document: `<p>Marie Curie was awarded the Nobel Prize in Physics in 1903.</p>`
- Query: `"Who won the Nobel Prize in Physics?"`
- Assembled disabled-mode context vs. pure legacy `pack_context` + `render_context`:
  ```python
  assert assembled_disabled.context == legacy_context
  assert assembled_disabled.use_structural is False
  assert assembled_disabled.tokens_used == pure_pack.tokens_used
  ```
- **Result**: `PASSED` (Exact byte-for-byte equality verified).

#### B. Zero Structural Writes (`test_disabled_mode_skips_structural_operations`)
- Ingested HTML containing nested `<ul>` lists with `enable_list_extraction=False`.
- `assert mem_store.count_structural_evidence() == 0`
- **Result**: `PASSED` (ChromaDB structural collection remains completely untouched).

#### C. Empty-Store Parity Under Disabled Mode (`test_feature_disabled_pure_structural_compatibility_test_g`)
- Ingested pure table document with `PRECIS_ENABLE_LIST_EXTRACTION=false`.
- Ingestion stored 0 SVOA facts and 0 structural records.
- Query through `POST /api/query` returned `HTTP 400 Bad Request` (`"detail": "No documents ingested. Upload a document first."`).
- Query through WebSocket emitted `{"type": "error", "detail": "No documents ingested"}`.
- **Result**: `PASSED` (Legacy failure modes exactly preserved when feature is inactive).

#### D. Full Production Wiring Parity (`test_production_wiring.py`)
- `test_disabled_mode_preserves_original_fact_based_behavior`: `PASSED`
- `test_document_without_lists_produces_same_result_regardless_of_feature_flag`: `PASSED`
