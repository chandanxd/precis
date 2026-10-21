# Experiment 4.5.1: Production Wiring Walkthrough

## Summary of Completed Changes

### 1. Production Pipeline Wiring (`backend/src/precis/pipeline/orchestrator.py`)
- Imported `build_structural_context` and `is_list_extraction_enabled` from `precis.pipeline.structural`.
- Extended `query_pipeline()` overloads and implementation with optional parameters `raw_document: str | None = None` and `enable_list_extraction: bool | None = None`.
- Implemented minimal safe context routing:
  - If `enable_list_extraction` is enabled AND `raw_document` contains content lists, `build_structural_context()` is executed and the structural context (containing clean prose, GFM tables, and structured lists) is passed to `generate_answer()`.
  - When disabled (the default), `pack_context()` and `render_context()` are executed verbatim with zero overhead and zero structural changes.
  - When enabled on a document without content lists, the pipeline safely falls back to the original fact-based context, ensuring parity.
- Extended `process_query()` to forward `raw_document=document_text` and `enable_list_extraction=enable_list_extraction` to `query_pipeline()`.

### 2. Comprehensive Production Wiring Test Suite (`backend/tests/test_production_wiring.py`)
- 8 new deterministic unit/integration tests covering all 6 prompt requirements:
  - `test_disabled_mode_preserves_original_fact_based_behavior`
  - `test_enabled_mode_calls_structural_extraction_with_retained_lists`
  - `test_retained_list_items_improve_answer_evidence_for_list_answer`
  - `test_document_without_lists_produces_same_result_regardless_of_feature_flag`
  - `test_feature_flag_validation_prevents_invalid_configurations`
  - `test_hardware_token_ceiling_respected_across_full_production_path`
  - `test_streaming_pipeline_with_list_extraction_enabled`
  - `test_omitted_raw_document_gracefully_falls_back_to_facts`

## Verification Commands
To reproduce all tests:
```bash
# Run new production wiring tests
pytest backend/tests/test_production_wiring.py -v

# Run structural integration tests
pytest backend/tests/test_structural_integration.py -v

# Run inference tests
pytest backend/tests/test_inference.py -v
```
