# Feature Flag Documentation: PRECIS_ENABLE_LIST_EXTRACTION

## Overview

The feature flag `PRECIS_ENABLE_LIST_EXTRACTION` controls the runtime activation of structural list retention in Précis. It governs whether structured HTML list blocks (`<ul>`, `<ol>`, nested item hierarchies, key-value definitions) are extracted, deduplicated against selected tables, and packed into prompt contexts alongside structural table retention.

## Invariant Safety Guarantee

- **Default State**: Strictly **disabled** (`False`).
- **Default Behavior**: When the flag is unset or set to `0`/`false`, the pipeline executes the existing production table-retention path (`Condition D` at `theta=0.0`) with 100% byte-for-byte fidelity.
- **Fail-Safe Validation**: Malformed string values or invalid types raise a fail-fast `ValueError` rather than silently defaulting or misconfiguring the pipeline.

## Configuration & Value Matrix

| Raw Value (String or Type) | Parsed Result | Operational Behavior |
| :--- | :---: | :--- |
| `None` (Unset) | `False` | **Default**: Table retention only (Condition D). |
| `""` (Empty string) | `False` | Disabled: Table retention only. |
| `"0"`, `"false"`, `"False"`, `"FALSE"` | `False` | Explicitly disabled. |
| `"no"`, `"NO"`, `"off"`, `"OFF"` | `False` | Explicitly disabled. |
| `False` (Boolean literal) | `False` | Explicitly disabled. |
| `0` (Integer literal) | `False` | Explicitly disabled. |
| `"1"`, `"true"`, `"True"`, `"TRUE"` | `True` | **Enabled**: Full structural list retention active. |
| `"yes"`, `"YES"`, `"on"`, `"ON"` | `True` | Enabled. |
| `True` (Boolean literal) | `True` | Enabled. |
| `1` (Integer literal) | `True` | Enabled. |
| `"maybe"`, `"enabled"`, `"disabled"`, `"2"`, `"-1"`, `"null"` | `ValueError` | **Rejection**: Fail-fast error to prevent misconfiguration. |
| `dict`, `list`, complex objects | `ValueError` | Rejection. |

## Precedence Order

When resolving flag status within `is_list_extraction_enabled(override=...)`:

1. **Explicit Function Argument**: If `override` is not `None`, its boolean value takes highest precedence.
2. **Environment Variable**: `os.getenv("PRECIS_ENABLE_LIST_EXTRACTION")` is parsed via `parse_feature_flag`.
3. **Fallback Default**: `False`.

## Operational Commands

### Check Current Status in Python
```python
from precis.pipeline.structural import is_list_extraction_enabled

if is_list_extraction_enabled():
    print("Structural list extraction is active.")
else:
    print("Baseline table-retention mode (Condition D) is active.")
```

### Enable for Canary / Evaluation
```bash
export PRECIS_ENABLE_LIST_EXTRACTION=1
```

### Emergency Rollback (Instant Reversion)
```bash
unset PRECIS_ENABLE_LIST_EXTRACTION
# Or explicitly:
export PRECIS_ENABLE_LIST_EXTRACTION=0
```

Zero process restart is required if callers query `is_list_extraction_enabled()` dynamically per request.
