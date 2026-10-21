# Empty Store Behavior & Multi-Collection Guard Specification

**Experiment 4.5.4 Remediation Design**  
**Date**: 2026-10-10  
**Target**: `backend/main.py` (`POST /api/query`, `_handle_ws_query`) and `backend/src/precis/pipeline/packer.py`

---

## 1. Problem Description (DEFECT-02)

In Experiment 4.5.2, `FactStore` maintained two collections in ChromaDB:
1. Atomic SVOA facts: `{collection_name}` (accessed via `store.count()`, `store.collection`)
2. Structural evidence chunks: `{collection_name}_structural` (accessed via `store.count_structural_evidence()`, `store.has_structural_evidence()`)

However, the production API guards in `backend/main.py` checked only the SVOA collection:
```python
if active_store.count() == 0:
    raise HTTPException(status_code=400, detail="No documents ingested. Upload a document first.")
```
And in WebSocket `_handle_ws_query`:
```python
if active_store.count() == 0:
    await ws.send_json({"type": "error", "detail": "No documents ingested"})
    return
```

### Consequence
When an ingested document consisted entirely of tables or lists (e.g. data catalogs, financial tables, key-value specifications), spaCy SVOA extraction extracted 0 atomic prose facts (`store.count() == 0`).
Even though `store.count_structural_evidence() > 0` and `store.has_structural_evidence()` was True, queries were rejected immediately with HTTP 400 Bad Request, preventing pure-structural documents from ever being queried.

---

## 2. Corrected Multi-Collection Guard Logic

The unified empty-store definition across REST and WebSocket handlers now checks both collections:

```python
has_svoa = active_store.count() > 0
has_struct = (
    is_list_extraction_enabled()
    and hasattr(active_store, "has_structural_evidence")
    and active_store.has_structural_evidence()
)
if not has_svoa and not has_struct:
    raise HTTPException(
        status_code=400,
        detail="No documents ingested. Upload a document first.",
    )
```

And in WebSocket `_handle_ws_query`:
```python
has_svoa = active_store.count() > 0
has_struct = (
    is_list_extraction_enabled()
    and hasattr(active_store, "has_structural_evidence")
    and active_store.has_structural_evidence()
)
if not has_svoa and not has_struct:
    await ws.send_json(
        {
            "type": "error",
            "detail": "No documents ingested",
        }
    )
    return
```

---

## 3. Four-Quadrant State Matrix

| State | SVOA Facts Count | Structural Evidence Count | Flag Status (`PRECIS_ENABLE_LIST_EXTRACTION`) | System Behavior | HTTP Status / WS Event |
|---|---|---|---|---|---|
| **1. Dual Knowledge Base** | $> 0$ | $> 0$ | Enabled (`true`) | Query executes; combines SVOA facts and structural tables/lists in budget. | HTTP 200 / Stream tokens |
| **2. Pure Prose Document** | $> 0$ | $0$ | Any (`true` / `false`) | Query executes; standard SVOA fact packing. | HTTP 200 / Stream tokens |
| **3. Pure Structural Document** | $0$ | $> 0$ | Enabled (`true`) | Query executes; structural evidence retrieved, formatted, and passed to LLM context. | HTTP 200 / Stream tokens |
| **4. Pure Structural (Disabled)** | $0$ | $> 0$ (or $0$) | Disabled (`false`) | Guard evaluates `has_struct = False`; rejected as empty knowledge base. Preserves 100% legacy parity. | HTTP 400 Bad Request / WS error |
| **5. Truly Empty Store** | $0$ | $0$ | Any | Both collections empty; rejected with explicit diagnostic error. | HTTP 400 Bad Request / WS error |

---

## 4. Downstream Packer Safety

`pack_context()` in `backend/src/precis/pipeline/packer.py`:
- `if not query or not query.strip() or store.count() == 0 or token_ceiling <= 0: return _empty_pack_result()`
- When `store.count() == 0`, `pack_context()` cleanly returns `_empty_pack_result()` (`packed_facts = []`, `tokens_used = 0`).
- In `orchestrator.py::assemble_query_context()`:
  - If `store.has_structural_evidence()` is True and list extraction is enabled, `assemble_structural_query_context()` is invoked.
  - `assemble_structural_query_context()` receives `pack_res.packed_facts == []`, sets `fact_docs = set()`, retrieves candidate chunks from `{collection_name}_structural`, and packs them up to `token_ceiling`.
  - The assembled context contains the structural tables/lists and is passed directly to `generate_answer()`.
