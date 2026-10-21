# Experiment 4.7.0.2: Final Acceptance-Test Determinism Check Walkthrough

## 1. Overview and Executive Summary

Experiment 4.7.0.2 completes the final audit gate for **Intervention 1: Guarded Structural-Priority Context Packing**. Building directly upon the findings of Experiment 4.7.0 and Experiment 4.7.0.1, this audit resolved all remaining determinism and assertion rigor gaps without modifying any production code or executing any model inference.

### Key Outcomes
- **Production Code Modified**: None (`backend/src/precis/pipeline/structural.py` remained untouched).
- **Test File Hardened**: `backend/tests/test_structural_priority_packing.py`.
- **Acceptance Tests Passing**: 14 of 14 passed deterministically.
- **Existing Regression Tests Passing**: 77 of 77 passed with zero regressions.
- **Fault-Injection Verification**: All 5 output-level fault injections triggered deterministic assertion failures.
- **Feature Flag Default**: Confirmed `PRECIS_ENABLE_LIST_EXTRACTION` defaults to `False`.
- **Gate Verdict**: **READY FOR INFERENCE AUTHORIZATION**.

---

## 2. Hardening and Determinism Audit of ATP Cases

### ATP-02: Deterministic Relevance-Rejection Fallback
- **Previous Gap**: Test relied on natural embedding distance between `"revenue and profit details"` and `"completely unrelated query about astronomy"`. While this worked on standard embedding checkpoints, it was vulnerable to embedding model drift or low-variance embedding spaces.
- **Hardening Applied**: Replaced natural embedding reliance with a controlled fixture mock on `store.query_similar_structural` that deterministically returns candidate structural chunks with a similarity score of `0.10` (strictly below the production threshold `0.25`) and zero keyword overlap.
- **Verified Invariants**:
  1. The production fallback path (`packer.pack_facts_into_context`) is deterministically exercised.
  2. SVOA facts from the document are present in `result.context` and `result.facts_used`.
  3. No Markdown table structures (`|` or structural headers) leak into `result.context`.
  4. Token ceiling is strictly respected (`result.tokens_used <= 100`).
  5. Assertion sensitivity: If fallback returned an empty context, `assert result.context.strip()` and fact assertions deterministically fail (verified via Fault Injection 1).

### ATP-08: Structural Rejection Fact Survival
- **Previous Gap**: Relied on natural query divergence to ensure structural rejection.
- **Hardening Applied**: Mocked `store.query_similar_structural` to deterministically return `[]`.
- **Verified Invariants**:
  1. SVOA facts for `"DocFallback Corp"` (`"DocFallback Corp acquired TargetCo in 2022"`) survive into `result.context` and `result.facts_used`.
  2. No table structures appear in `result.context`.
  3. Assertion sensitivity: An empty fallback context deterministically fails assertions (verified via Fault Injection 2).

### ATP-09: Unconditional Context Budget Accounting Across Scales
- **Previous Gap**: The assertion for `estimate_text_tokens(result.context) <= ceiling` was guarded behind `if structural_packed:`, omitting enforcement during SVOA fallback.
- **Hardening Applied**:
  - Expanded test fixture with a multi-row table (`10 rows`, ~78 tokens) and evaluated across ceilings: `[40, 100, 250, 500, 1000, 2048]`.
  - Asserted **unconditionally** across all scales:
    ```python
    assert result.tokens_used <= ceiling
    assert estimate_text_tokens(result.context) <= ceiling
    ```
- **Token Accounting Reconciliation**:
  - For structural packing, `tokens_used` is set to `telemetry["total_context_estimated_tokens"]`, which is computed as `estimate_text_tokens(context)`. Hence, `result.tokens_used == estimate_text_tokens(result.context)`.
  - For SVOA fallback, `packer.py` calculates budget by summing `estimate_fact_tokens(f)`. In our fixture across all supported ceilings, both metrics strictly and unconditionally satisfy `<= ceiling`.
  - Assertion sensitivity: If `result.tokens_used` overflows ceiling (`ceiling + 1`), the test deterministically fails (verified via Fault Injection 3).

### ATP-10: Bidirectional Deduplication Assertions
- **Previous Gap**: Did not explicitly assert that same-subject distinct facts from other documents are preserved (preventing over-suppression).
- **Hardening Applied**:
  - `doc_a` contains a table with `AlphaCorp | BetaLLC | 2021`.
  - `doc_b` contains two distinct facts:
    1. Duplicate SVOA fact: `"AlphaCorp acquired BetaLLC in 2021."`
    2. Distinct SVOA fact with different subject: `"ZetaCorp launched OmegaApp in 2023."`
    3. Distinct SVOA fact sharing the same subject: `"AlphaCorp acquired GammaCorp in Berlin."`
  - Assertions verify:
    - `AlphaCorp acquired BetaLLC in 2021` is **absent** from both `result.context` and `result.facts_used`.
    - Both `ZetaCorp launched OmegaApp in 2023` and `AlphaCorp acquired GammaCorp in Berlin` are **present** in both `result.context` and `result.facts_used`.
- **Production Deduplication Logic Verified**:
  - In `assemble_structural_query_context`:
    ```python
    is_dupe = (
        fact.subject.lower() in struct_combined_content and
        fact.object.lower() in struct_combined_content
    )
    ```
  - Since `"gammacorp"` is not present in the structural table, the fact sharing subject `AlphaCorp` is preserved, proving no indiscriminate subject-level suppression occurs.
  - Assertion sensitivity: Leaking the duplicate fact or over-suppressing the same-subject fact triggers deterministic test failure (verified via Fault Injections 4 and 5).

---

## 3. Fault-Injection Audit

To establish that the acceptance tests are sensitive to regressions, 5 output-level fault injections were executed:

| ID | Target Test | Injected Defect / Mutation | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| **FI 1** | ATP-02 | Fallback context forced to empty string `""` | `AssertionError` | Caught by `assert result.context.strip()` | **PASS** |
| **FI 2** | ATP-08 | Fallback context forced to empty string `""` | `AssertionError` | Caught by `assert "targetco" in result.context.lower()` | **PASS** |
| **FI 3** | ATP-09 | `tokens_used` artificially set to `ceiling + 1` | `AssertionError` | Caught by `assert result.tokens_used <= ceiling` | **PASS** |
| **FI 4** | ATP-10 | Duplicate fact forced into `result.context` | `AssertionError` | Caught by `assert not (subj in ctx and obj in ctx)` | **PASS** |
| **FI 5** | ATP-10 | Same-subject distinct fact suppressed | `AssertionError` | Caught by `assert "gammacorp" in result.context.lower()` | **PASS** |

*All 5 fault injections deterministically failed the test suite, confirming assertion rigor.*

---

## 4. Verification and Regression Testing

### 1. Acceptance Test Suite Execution
```bash
backend/venv/bin/pytest backend/tests/test_structural_priority_packing.py
```
- **Result**: `14 passed in 54.06s`

### 2. Regression Test Suites Execution
```bash
backend/venv/bin/pytest backend/tests/test_production_wiring.py backend/tests/test_structural_persistence.py backend/tests/test_structural_integration.py
```
- **Result**: `77 passed in 102.87s`

### 3. Feature Flag Verification
```bash
backend/venv/bin/python3 -c "from precis.pipeline.structural import is_list_extraction_enabled; import os; os.environ.pop('PRECIS_ENABLE_LIST_EXTRACTION', None); print('Default enabled:', is_list_extraction_enabled())"
```
- **Result**: `Default enabled: False`

### 4. Working Tree Integrity & File Checksums
- `backend/src/precis/pipeline/structural.py`: `10f16ce3f08fc00693d723c0a6e3e03e1a46a585b47d41e2feb110f6b9fb1ee4` (Unchanged)
- `backend/tests/test_structural_priority_packing.py`: `0286142841dbfb133d4770701def61334886531c8872166ee18852e9e285d9d8` (Hardened)
- Git status verified that no unrelated changes were altered or discarded.

---

## 5. Final Gate Verdict

All acceptance tests ATP-01 through ATP-10 now exhibit deterministic execution, strict budget accounting, bidirectional deduplication verification, and verified failure sensitivity. All 77 existing regression tests continue to pass with zero regressions.

**Final Decision**: **READY FOR INFERENCE AUTHORIZATION**
