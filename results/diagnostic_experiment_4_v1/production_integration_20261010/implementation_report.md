# Experiment 4.5: Controlled Production Integration Report

## 1. Executive Summary

Experiment 4.5 integrates the validated diagnostic list-extraction approach from Experiments 4.3 and 4.4 into Précis as an isolated, feature-flagged module under `backend/src/precis/pipeline/structural.py`.

The integration satisfies all five constraints established by the user review:
1. **Disabled by Default**: `PRECIS_ENABLE_LIST_EXTRACTION` defaults strictly to `False`.
2. **Byte-Level Disabled Parity**: When disabled, the context builder produces output byte-for-byte identical to Condition D.
3. **Context-Budget Accounting Defect Resolved**: Section headers (`### Structured List:
`) and delimiters (`

`) are deducted prior to allocating line budgets, with a hard post-assembly ceiling clamp.
4. **Conservative Table-List Deduplication**: List sections whose items duplicate ($\ge 80\%$) selected table cells are suppressed to mitigate distractor regressions (e.g. Scorpions songwriters).
5. **Permanent Regression Safeguards**: Dedicated evidence-level test cases guard against regressions on `3f5983b2`, `ef634417`, and `8f1f9bd9`.

## 2. Integrated Architecture

```
HTML Input Document
         │
         ▼
StructuralDocumentParser ───► Clean Prose Stream (excised tables/lists)
         │
         ├───► Table Blocks ───► score_and_select_tables (theta=0.0) ───► GFM Chunks
         │
         ▼ (Enabled Path Only)
extract_lists_from_html ───► RobustListParser (hierarchies, bindings)
         │
         ▼
deduplicate_table_list_overlap (suppress >=80% table overlap)
         │
         ▼
Exact Budget Accounting (deduct headers, delimiters, enforce hard ceiling)
         │
         ▼
Unified Context Assembly
```

## 3. Test Suite Verification Summary

| Test Suite | Total Tests | Passed | Failed | Duration | Coverage Highlights |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `backend/tests/test_structural_integration.py` | 47 | 47 | 0 | 3.87s | Feature flag, disabled parity, budget ceilings, deduplication, safeguards, HTML edge cases |
| `backend/tests/` (Full Backend Suite) | 388 | 388 | 0 | 97.25s | Entire backend regression test suite |
| `scripts/` (Diagnostic Suite) | 33 | 33 | 0 | 3.99s | Experiment 4.2 integrity, 4.3 fixtures, 4.4 audit extractor |
| **Total** | **468** | **468** | **0** | **~105s** | **100% Pass Rate** |

## 4. Git Working Tree & Safety Invariants

- **No Pre-existing User Changes Modified**: Pre-existing modifications in `backend/` and `frontend/` were recorded prior to editing and strictly preserved.
- **Zero Git Commits / Resets**: No git branches, commits, stashes, or resets were created.
- **Zero Model Inference Calls**: Validation relied purely on deterministic unit and integration tests.
- **Zero Network Calls**: Executed completely offline in standard sandbox mode.

## 5. Final Verdict

**`IMPLEMENTATION READY FOR DISABLED-MODE REVIEW`**
