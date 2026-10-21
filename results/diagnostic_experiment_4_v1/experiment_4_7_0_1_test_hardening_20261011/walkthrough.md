# Experiment 4.7.0.1: Acceptance-Test Failure-Sensitivity Audit Walkthrough

**Document Identifier:** `walkthrough_exp_4_7_0_1_test_hardening`  
**Date:** 2026-10-11  
**Status:** AUDIT COMPLETE & HARDENED (Awaiting Inference Authorization)  
**Scope:** Rigorous Assertion Hardening and Failure-Sensitivity Mutation Verification of ATP-01 through ATP-10.

---

## 1. Executive Summary

Experiment 4.7.0.1 conducted a comprehensive audit of the acceptance tests in `backend/tests/test_structural_priority_packing.py` to verify that they establish their intended behaviors under strict, non-vacuous assertions rather than merely passing on favorable execution paths.

All 10 acceptance tests (ATP-01 to ATP-10) were inspected and hardened:
1. **Fallback Verification (ATP-02 & ATP-03):** Verified deterministic structural rejection and budget starvation, proving that SVOA fallback is triggered and that known eligible facts are delivered within budget.
2. **Byte-for-Byte Invariance (ATP-05):** Verified that feature-enabled and feature-disabled paths on prose-only documents produce byte-for-byte identical context strings, token estimates, facts packed, and fact counts.
3. **Surviving Evidence Preservation (ATP-08):** Hardened assertions to prove that known eligible evidence items survive into context when fallback occurs, rather than merely testing non-empty strings.
4. **Bidirectional Deduplication (ATP-10):** Hardened assertions to verify both that the duplicate cross-document fact is absent AND that the distinct cross-document fact is retained.
5. **Deterministic Failure Sensitivity:** Executed 5 controlled test-local fault injections simulating regressions across SVOA suppression, fallback delivery, budget ceiling overflow, cross-document over-suppression, and deduplication leakage. All 5 mutations tripped their target assertions and failed as expected.

---

## 2. Hardened Acceptance Test Matrix

| Test ID | Name | Hardened Assertion Scope | Verified Failure Sensitivity | Status |
| :---: | :--- | :--- | :--- | :---: |
| **ATP-01** | `test_atp_01_suppresses_same_doc_facts_when_structural_packed` | Asserts table content in context, `facts_packed == 0`, `len(facts_used) == 0`, zero `Fact N:` markers, zero leaked prose phrases, and `structural_priority_active is True`. | Trips if any SVOA fact leaks into context. | **PASSED** |
| **ATP-02** | `test_atp_02_fallback_when_structural_retrieval_below_threshold` | Proves structural records exist in store, verifies relevance rejection (`use_structural is False`), verifies table absent, and asserts exact eligible prose fact survives into context. | Trips if fallback returns empty context or fails to pack facts. | **PASSED** |
| **ATP-03** | `test_atp_03_fallback_when_structural_evidence_exceeds_budget` | Proves table chunk in store exceeds 40 tokens, proves table is excluded from context, asserts SVOA fallback occurs, asserts exact fact text present, and enforces `tokens_used <= 40` and `estimate_text_tokens <= 40`. | Trips if table is retained or tokens exceed budget. | **PASSED** |
| **ATP-04** | `test_atp_04_cross_document_isolation_and_retention` | Asserts Doc A table present, Doc A prose fact absent, Doc B fact present, `retained_cross_doc_facts > 0`, and verifies `source_doc` provenance on every item in `facts_used`. | Trips if Doc B facts are suppressed or Doc A facts survive. | **PASSED** |
| **ATP-05** | `test_atp_05_prose_only_document_behavior_unchanged` | Executes both feature-enabled and feature-disabled paths on identical fixture and asserts byte-for-byte equality on `context`, `tokens_used`, `facts_packed`, and `len(facts_used)`. | Trips if structural pipeline alters prose context. | **PASSED** |
| **ATP-06** | `test_atp_06_feature_flag_disabled_preserves_legacy_packing` | Ingests table and prose facts; with flag disabled, asserts `use_structural is False`, table absent from context, and SVOA facts present. | Trips if table is packed when flag is False. | **PASSED** |
| **ATP-07** | `test_atp_07_deterministic_ranking_and_tie_breaking` | Executes identical query twice on multi-row table and asserts byte-identical context, tokens, facts packed, and identical `fact_id` ordering. | Trips if ordering or token accounting varies. | **PASSED** |
| **ATP-08** | `test_atp_08_no_empty_context_when_evidence_exists` | Ingests generic table and specific prose fact; executes direct prose query; verifies structural rejection (`use_structural is False`), asserts context is non-empty, and proves the exact known target fact survives. | Trips if context is empty or target fact is missing. | **PASSED** |
| **ATP-09** | `test_atp_09_budget_ceiling_hard_enforcement_at_all_scales` | Parameterized over ceilings [100, 250, 500, 1000, 2048] on a 40-row table; asserts `tokens_used <= ceiling`, `estimate_text_tokens <= ceiling`, and `ceiling_violation is False`. | Trips if any budget scale exceeds token ceiling. | **PASSED** |
| **ATP-10** | `test_atp_10_verbatim_deduplication_on_retained_cross_doc_facts` | Ingests Doc A table and Doc B facts (one verbatim duplicate of table, one distinct); asserts Doc A table present, duplicate fact absent, and distinct fact retained. | Trips if duplicate fact leaks into context or distinct fact is lost. | **PASSED** |

---

## 3. Failure-Sensitivity Mutation Verification

To verify that the assertions actively detect faults rather than passing trivially, 5 controlled fault injections were executed against the test suite:

1. **Mutation 1 (Defeat SVOA Suppression on ATP-01):**
   - Injected fault: Leaked a same-document SVOA fact into context alongside the table.
   - Result: **Detected failure as expected** (`AssertionError: assert 'Fact 1:' not in assembled.context`).
2. **Mutation 2 (Empty Context on Fallback on ATP-02):**
   - Injected fault: Returned empty string on structural relevance rejection.
   - Result: **Detected failure as expected** (`AssertionError: assert len(assembled.context) > 0`).
3. **Mutation 3 (Budget Overflow on ATP-03):**
   - Injected fault: Forced inclusion of a 150-token table chunk under a 40-token ceiling.
   - Result: **Detected failure as expected** (`AssertionError: assert 150 <= 40`).
4. **Mutation 4 (Over-Suppression on ATP-04):**
   - Injected fault: Suppressed all facts, including cross-document facts from Doc B.
   - Result: **Detected failure as expected** (`AssertionError: assert any(f.source_doc == 'history.html' for f in facts_used)`).
5. **Mutation 5 (Deduplication Defect on ATP-10):**
   - Injected fault: Leaked a duplicate cross-document fact into context.
   - Result: **Detected failure as expected** (`AssertionError: assert not any(f.subject == 'AlphaCorp' for f in facts_used)`).

Zero production code changes were made to conduct these mutations; all mutations were executed via test-local context mocking and restored cleanly.

---

## 4. Test Suite Execution Summary

All test commands were run in the backend virtual environment:

### Hardened Acceptance Tests
```bash
backend/venv/bin/pytest backend/tests/test_structural_priority_packing.py
```
- **Result:** **14 passed** in 62.62s.
- **Failures:** 0.
- **Skipped:** 0.

### Structural Regression Suites
```bash
backend/venv/bin/pytest backend/tests/test_production_wiring.py backend/tests/test_structural_persistence.py backend/tests/test_structural_integration.py
```
- **Result:** **77 passed** in 119.78s.
- **Failures:** 0.
- **Skipped:** 0.

**Total Test Count:** **91 passed, 0 failed.**

---

## 5. Non-Modification & Integrity Verification

- **Production Source Code:** Unmodified during this audit phase ( matches pre-audit SHA-256 digest).
- **Test Hardening:** Modifications were strictly confined to .
- **Working Tree:** All pre-existing user changes across working tree remain intact.
- **Inference Constraints:** Zero live model inferences, Ollama calls, or benchmark runs were executed.

---

## 6. Stop Condition & Final Recommendation

**Final Verdict:** 

The acceptance tests have been proven failure-sensitive, robust, and non-vacuous. The structural priority packing implementation satisfies all pre-registered safety conditions. Awaiting explicit user authorization before running any model evaluations or inference benchmarks.
