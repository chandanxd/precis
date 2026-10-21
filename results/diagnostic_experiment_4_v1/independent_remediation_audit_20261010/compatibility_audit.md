# Independent Feature-Flag and Compatibility Audit

**Experiment 4.5.5 Independent Audit**  
**Date**: 2026-10-10  
**Feature Flag Under Audit**: `PRECIS_ENABLE_LIST_EXTRACTION` (Default: `false`)

---

## 1. Feature Flag Semantics & Default Safety

### A. Environment Variable Default
- **Target Function**: `is_list_extraction_enabled()` in `backend/src/precis/pipeline/structural.py`.
- **Implementation**:
  ```python
  def is_list_extraction_enabled(override: bool | None = None) -> bool:
      if override is not None:
          return bool(override)
      return parse_feature_flag(os.getenv(FLAG_NAME, "false"))
  ```
- **Audit Verification**:
  - Unsetting `PRECIS_ENABLE_LIST_EXTRACTION` returns `False`.
  - Setting invalid strings like `"maybe"`, `"enabled"`, `""` defaults safely to `False`.
  - Valid truthy strings: `"true"`, `"1"`, `"yes"`, `"on"` return `True`.
  - Valid falsy strings: `"false"`, `"0"`, `"no"`, `"off"` return `False`.

### B. Import-Time Isolation
- **Verification**: Importing `backend/main.py`, `precis.pipeline.orchestrator`, or `precis.pipeline.structural` in a clean Python process performs zero mutations on `os.environ`.
- **Finding**: Zero ambient activation side effects.

### C. Function Override Non-Leakage
- **Verification**: Calling `is_list_extraction_enabled(override=True)` returns `True` for that specific call, but leaves `os.getenv(FLAG_NAME)` unchanged (`test_explicit_override_does_not_mutate_global_env`).

---

## 2. Ingestion & Storage Compatibility

### A. Disabled Mode (`PRECIS_ENABLE_LIST_EXTRACTION=false`)
- **Code Path**: In `run_ingest_document()`, when `enable_list_extraction=False`:
  - `extract_structural_evidence_from_document()` is completely skipped.
  - `store.add_structural_evidence()` is never invoked.
  - Zero structural embeddings are computed.
  - `{collection_name}_structural` collection remains empty.
- **Verification**: Directly asserted in `test_disabled_mode_skips_structural_operations`.

### B. Enabled Mode (`PRECIS_ENABLE_LIST_EXTRACTION=true`)
- Tables and lists are parsed, embedded (384-d cosine), and stored in `{collection_name}_structural`.
- SVOA extraction on prose continues uninterrupted in `{collection_name}`.

---

## 3. Query Path & Context Byte-Parity Audit

### A. Disabled Mode Context Parity
- **Target Function**: `assemble_query_context()` in `backend/src/precis/pipeline/orchestrator.py`.
- **Code Path**:
  ```python
  if list_enabled:
      ...
  return AssembledQueryContext(
      context=render_context(pack_res.packed_facts),
      facts_used=pack_res.packed_facts,
      tokens_used=pack_res.tokens_used,
      ...
  )
  ```
- **Verification**: Directly asserted in `test_disabled_mode_byte_identical_context`:
  `assert assembled_disabled.context == legacy_context` (where `legacy_context = render_context(pure_pack.packed_facts)`).
- **Result**: **100% byte-for-byte identical output**.

### B. REST and WebSocket Handlers
- When the flag is disabled:
  - If a store has SVOA facts: Query executes using the classical fact-packing path.
  - If a store has pure-structural evidence (0 SVOA facts): `has_struct` evaluates to `False`. The server returns HTTP 400 Bad Request ("No documents ingested. Upload a document first.") and WebSocket error ("No documents ingested").
  - This preserves exact legacy behavior.
- When the flag is enabled:
  - If a store has pure-structural evidence: `has_struct` evaluates to `True`. Query executes, retrieves structural context, and delivers it to the generator.

---

## 4. Directly Verified Behavior vs. Report-Only Claims

| Compatibility Dimension | Reported Claim | Audit Verification Method | Verdict |
|---|---|---|---|
| **Default Inactive** | Flag is disabled by default | Evaluated in clean subshell with unset environment | **VERIFIED** |
| **No Import Side Effects** | Clean imports don't mutate state | Python subshell inspection | **VERIFIED** |
| **Zero Ingestion Overhead** | No structural writes when disabled | Verified Chroma collection count == 0 | **VERIFIED** |
| **Byte Parity** | Exact string match with legacy context | Direct string equality assert in test suite | **VERIFIED** |
| **REST Parity** | Disabled REST rejects pure structural | `TestClient` query returns HTTP 400 | **VERIFIED** |
| **WebSocket Parity** | Disabled WS rejects pure structural | WebSocket client receives error frame | **VERIFIED** |
| **Override Safety** | Function overrides do not leak | Asserted `os.getenv` remains unmodified | **VERIFIED** |
