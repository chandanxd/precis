# Disabled-Mode Compatibility and Parity Audit

**Experiment 4.5.2**  
**Date**: 2026-10-10  
**Status**: Verified with Byte-Level Parity

---

## 1. Feature Flag Semantics and Defaults

To prevent unintended regressions in existing evaluations or production environments, list extraction and persistence is strictly disabled by default:

```python
FLAG_NAME = "PRECIS_ENABLE_LIST_EXTRACTION"

def is_list_extraction_enabled(override: bool | None = None) -> bool:
    if override is not None:
        return bool(override)
    val = os.getenv(FLAG_NAME, "").strip().lower()
    return val in ("1", "true", "yes", "on")
```

### Precedence Matrix

| Environment Variable (`PRECIS_ENABLE_LIST_EXTRACTION`) | Explicit Argument (`enable_list_extraction`) | Effective State | Ingestion Action | Query Action |
|---|---|---|---|---|
| Unset | `None` | **Disabled** | Pure SVOA facts stored; 0 structural chunks | Pure SVOA context packing |
| `""` or `"false"` or `"0"` | `None` | **Disabled** | Pure SVOA facts stored; 0 structural chunks | Pure SVOA context packing |
| `"true"` or `"1"` | `None` | **Enabled** | Tables & lists extracted and persisted | Structural vector search & assembly |
| `"true"` | `False` | **Disabled** (Override wins) | Pure SVOA facts stored; 0 structural chunks | Pure SVOA context packing |
| `"false"` | `True` | **Enabled** (Override wins) | Tables & lists extracted and persisted | Structural vector search & assembly |

---

## 2. Zero-Overhead Guarantee

When disabled:
1. **Ingestion Overhead**:
   - `extract_structural_evidence_from_document()` is completely bypassed.
   - Zero additional regex passes, HTML tree parsing, or list tokenization.
   - Zero embedding computations or vector writes to `{collection_name}_structural`.
2. **Query Overhead**:
   - `has_structural_evidence()` and `query_similar_structural()` are never called.
   - Stage 4 packing delegates directly to `pack_context()` and `render_context()`.
   - Latency, token count, and compression rate are 100% identical to the legacy pipeline.

---

## 3. Byte-Level Compatibility Verification

In `backend/tests/test_structural_integration.py` (`TestDisabledModeCompatibility`), disabled mode output was verified against historical reference implementations across multiple document modalities:

1. **Pure Prose Documents**:
   - Input: Prose paragraphs without HTML lists or tables.
   - Result: Exact byte-for-byte identical output between enabled and disabled modes.
2. **Table-Only Documents**:
   - Input: HTML tables without lists.
   - Result: Exact byte-for-byte identity to historical Condition D table retention (`build_table_retention_context`).
3. **Mixed Documents**:
   - Input: HTML documents containing prose, tables, and lists.
   - When disabled: List items are ignored, while tables and prose are preserved with 100% parity to Condition D baseline.

All tests passed with zero drift.
