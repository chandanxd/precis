# Feature Flag and Disabled-Mode Compatibility Audit

**Experiment 4.5.3 Independent Audit**  
**Date**: 2026-10-10  
**Status**: VERIFIED (Pass with Zero Drift)

---

## 1. Feature Flag Defaults and Semantics

The feature flag `PRECIS_ENABLE_LIST_EXTRACTION` governs structural table and list extraction across Précis. Code inspection of `backend/src/precis/pipeline/structural.py` (`parse_feature_flag()` and `is_list_extraction_enabled()`) establishes:

1. **Default State**:
   - When the environment variable is unset, `os.getenv(FLAG_NAME)` returns `None`.
   - `parse_feature_flag(None)` explicitly returns `False`.
   - Deterministic test `TestAuditFeatureFlagAndDisabledMode.test_flag_defaults_to_disabled` passes.
2. **Boolean and Truthy Parsing**:
   - Truthy values: `True`, `1`, `"1"`, `"true"`, `"TRUE"`, `"yes"`, `"YES"`, `"on"`, `"ON"`.
   - Falsy values: `False`, `0`, `"0"`, `"false"`, `"FALSE"`, `"no"`, `"NO"`, `"off"`, `"OFF"`, `""`.
   - Invalid values (`"maybe"`, `"enabled"`, `2`, `-1`, `None` with bad types) strictly raise `ValueError` with clear messages, preventing silent fallback to unintended modes.

---

## 2. Override Isolation and Concurrency Safety

A critical risk in flag-controlled pipelines is global state leakage (e.g. an API request with an override mutating `os.environ` or a global module variable, impacting subsequent requests).

Audit inspection and test `test_explicit_override_does_not_mutate_global_env` verified:
- The parameter `override: bool | None` is evaluated locally within `is_list_extraction_enabled(override=...)`.
- If `override is not None`, it returns `parse_feature_flag(override)` without touching `os.environ`.
- Ingestion and query invocations with `enable_list_extraction=True` do not mutate `os.environ[FLAG_NAME]`.
- Subsequent queries without explicit overrides strictly read the underlying environment variable.

---

## 3. Byte-Level Identity Verification (Legacy Parity)

To verify that disabled mode produces 100% byte-for-byte identical output to the legacy SVOA pipeline, we evaluated `assemble_query_context()` against legacy `pack_context()` + `render_context()`:

### Test Scenario
- **Document**: Marie Curie Nobel Prize biographical prose.
- **Query**: "Who won the Nobel Prize in Physics?"
- **Ceiling**: 2048 tokens.

### Results
```python
assembled_disabled = assemble_query_context(query, store, token_ceiling, enable_list_extraction=False)
pure_pack = pack_context(query, store, token_ceiling)
legacy_context = render_context(pure_pack.packed_facts)

assert assembled_disabled.context == legacy_context  # True (Exact byte-for-byte match)
assert assembled_disabled.use_structural is False    # True
assert assembled_disabled.tokens_used == pure_pack.tokens_used  # True
```

The resulting prompt strings are identical:
- Selected facts: Identical order and formatting (`Fact 1: ...`).
- Modality tagging: Preserved identically (`[asserted]`, etc.).
- Telemetry: Zero divergence in compression rate or token accounting.

---

## 4. Operational Bypass Verification

Audit test `test_disabled_mode_skips_structural_operations` confirms that when disabled:
1. Ingestion of HTML containing lists (`<ul><li>Alpha</li><li>Beta</li></ul>`) skips all structural extraction.
2. `store.count_structural_evidence()` returns `0`.
3. Zero vectors are added to `{collection_name}_structural`.
4. At query time, `store.has_structural_evidence()` returns `False` and no structural similarity queries are dispatched.
5. Ingestion and query latencies incur zero structural vector calculation overhead.
