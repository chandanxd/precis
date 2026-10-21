# Experiment 4.7.0: Deterministic Acceptance Test Plan

**Document Identifier:** `acceptance_test_plan_exp_4_7_0`  
**Date:** 2026-10-11  
**Status:** SPECIFICATION READY (Awaiting Authorization Before Implementation)  
**Target Milestone:** Experiment 4.7.0 Implementation & Gate Verification  
**Scope:** Specification of deterministic unit and integration tests verifying structural-priority context packing without model inference.

---

## 1. Principles & Objectives

This test plan defines a deterministic test suite to verify the structural-priority context packing policy specified in `implementation_spec.md`.

### Core Testing Invariants:
1. **Zero Model Inference:** Tests must execute purely at the prompt context assembly level (`assemble_structural_query_context` and `assemble_query_context`). Model generation is never used as an oracle.
2. **Deterministic Evaluation:** All assertions test explicit string presence/absence, telemetry counters, token ceiling boundaries, and deterministic sorting orders.
3. **Isolation:** Tests use isolated in-memory `FactStore` instances with ChromaDB client fixtures.
4. **Distinguishability:** Every test must produce a demonstrable behavioral difference between legacy hybrid packing and structural-priority packing.

---

## 2. Test Matrix

| Test ID | Name | Target Condition | Fixture Type | Expected Behavior | Failure Condition |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **ATP-01** | `test_structural_priority_suppresses_same_doc_facts` | Relevant table selected and packed | In-memory store (single doc: Supreme Court) | Context contains Markdown table; exactly 0 `Fact N:` markers; `facts_packed == 0`; `suppressed_same_doc_facts > 0`. | Any `Fact N:` marker appears from same doc; `facts_packed > 0`. |
| **ATP-02** | `test_fallback_when_structural_retrieval_below_threshold` | Table exists, similarity $< 0.25$ and no KW match | In-memory store (single doc: uncaptioned table with mismatched query) | Context contains standard SVOA facts; `use_structural == False`; `facts_packed > 0`; zero table content. | Empty context or silence when eligible facts exist. |
| **ATP-03** | `test_fallback_when_structural_evidence_exceeds_budget` | Table exceeds `token_ceiling`; cannot fit | In-memory store (single doc: large table, tiny budget =50$) | Table cannot fit; pipeline falls back to SVOA facts that fit in budget; context is non-empty; tokens $\le 50$. | Empty context returned or token ceiling violation ($> 50$). |
| **ATP-04** | `test_cross_document_isolation_and_retention` | Doc A has table; Doc B has relevant prose facts | In-memory store (multi-doc: Doc A table + Doc B SVOA) | Doc A table packed; Doc A facts suppressed; Doc B facts packed in remaining budget; `retained_cross_doc_facts > 0`. | Doc B facts suppressed; or Doc A facts not suppressed. |
| **ATP-05** | `test_prose_only_document_behavior_unchanged` | Document contains no tables or lists | In-memory store (single doc: pure prose) | Context is standard SVOA facts; `use_structural == False`; telemetry byte-identical to legacy. | Structural priority interferes with prose-only pipeline. |
| **ATP-06** | `test_feature_flag_disabled_preserves_legacy_packing` | `PRECIS_ENABLE_LIST_EXTRACTION=False` | In-memory store (single doc: table + facts) | Context contains standard SVOA facts; `use_structural == False`; zero structural chunks. | Context contains structural chunks when flag is disabled. |
| **ATP-07** | `test_deterministic_ranking_and_tie_breaking` | Multiple structural candidates with identical similarities | In-memory store (multiple synthetic chunks) | Ordering is 100% deterministic across repeated calls using blended score and ID tie-breaking. | Order changes across invocations. |
| **ATP-08** | `test_no_empty_context_when_evidence_exists` | Edge case: structural items rejected | In-memory store (facts exist, structural items fail) | `len(assembled.context) > 0`; `facts_packed > 0`. | Output context is empty string (""). |
| **ATP-09** | `test_budget_ceiling_hard_enforcement_at_all_scales` | Large tables and facts across budgets [100, 250, 500, 1000, 2048] | In-memory store (dense table + 50 facts) | `estimate_text_tokens(context) <= budget` for all budgets. `ceiling_violation == False`. | Any budget produces estimated tokens $> budget$. |
| **ATP-10** | `test_verbatim_deduplication_on_retained_cross_doc_facts` | Doc A table; Doc B fact shares subject/object with table | In-memory store (Doc A table + Doc B identical triple) | Doc B fact is deduplicated against Doc A table content and excluded from residual budget. | Redundant fact from Doc B is packed despite verbatim overlap. |

---

## 3. Detailed Test Specifications

### ATP-01: `test_structural_priority_suppresses_same_doc_facts`
- **Goal:** Distinguish proposed behavior from legacy behavior on table-bearing documents.
- **Fixture:**
  - Ingest HTML document `supreme_court.html`: contains infobox table with John Roberts and John Jay, plus prose sentences generating 5 SVOA facts (including Fact 1: `U.S. Constitution Inaugural holder John Jay serves as Chief Justice`).
- **Input:** `query = "who is the supreme justice of the supreme court"`, `token_ceiling = 2048`.
- **Expected Context Properties:**
  - `assembled.context` contains `| Incumbent John Roberts since September 29 , 2005 |`.
  - `assembled.context` does NOT contain `Fact 1:` or `serves as Chief Justice`.
  - `assembled.facts_packed == 0`.
  - `assembled.telemetry["tables_packed"] >= 1`.
  - `assembled.telemetry["structural_priority_active"] is True`.
  - `assembled.telemetry["suppressed_same_doc_facts"] >= 1`.
- **Failure Condition:** Any `Fact 1:` marker appears in context or `facts_packed > 0`.

### ATP-02: `test_fallback_when_structural_retrieval_below_threshold`
- **Goal:** Verify safe fallback when structural evidence fails relevance filtering.
- **Fixture:**
  - Ingest document `arjuna.html` with generic headers `['S.No .', 'Year', 'Name']` and facts.
- **Input:** `query = "who got the first arjun award in athletics"`, `token_ceiling = 2048`.
- **Condition:** Cosine similarity $< 0.25$, no keyword match.
- **Expected Context Properties:**
  - `assembled.use_structural is False`.
  - `assembled.context` contains standard `Fact 1:` ... `Fact N:`.
  - `assembled.facts_packed > 0`.
  - Context is non-empty.
- **Failure Condition:** Context is empty or pipeline errors.

### ATP-03: `test_fallback_when_structural_evidence_exceeds_budget`
- **Goal:** Verify that when a table cannot fit within a tiny token budget, the pipeline falls back to SVOA facts rather than emitting an empty context.
- **Fixture:**
  - Table chunk requiring ~120 tokens; SVOA facts requiring ~15 tokens each.
- **Input:** `query = "test query"`, `token_ceiling = 50`.
- **Expected Context Properties:**
  - Table cannot fit (20 > 50$).
  - Pipeline falls back to packing SVOA facts that fit within 50 tokens.
  - `estimate_text_tokens(assembled.context) <= 50`.
  - `assembled.context` is not empty.
- **Failure Condition:** Empty context or token ceiling violation.

### ATP-04: `test_cross_document_isolation_and_retention`
- **Goal:** Verify that evidence from Document A suppresses only Document A facts, while Document B facts remain eligible.
- **Fixture:**
  - `doc_a.html`: Table with team roster (Alice, Bob, Charlie).
  - `doc_b.html`: Prose facts about company founding (Dave founded Acme in 2010).
- **Input:** `query = "Who is on the team and who founded Acme?"`, `token_ceiling = 2048`.
- **Expected Context Properties:**
  - `doc_a.html` table is packed.
  - Any SVOA facts from `doc_a.html` are suppressed.
  - SVOA facts from `doc_b.html` are packed as `Fact 1: ...`.
  - `assembled.telemetry["tables_packed"] >= 1`.
  - `assembled.telemetry["retained_cross_doc_facts"] >= 1`.
- **Failure Condition:** `doc_b.html` facts suppressed, or `doc_a.html` facts included.

### ATP-05: `test_prose_only_document_behavior_unchanged`
- **Goal:** Ensure zero regression or divergence on prose-only documents.
- **Fixture:** Pure prose document without HTML tables or lists.
- **Input:** Standard query.
- **Expected Context Properties:**
  - `assembled.context` is identical between legacy and proposed implementation.
  - `assembled.use_structural is False`.
- **Failure Condition:** Any deviation in context text or fact packing.

---

## 4. Execution Protocol & Verification Criteria

1. Tests will be added to `backend/tests/test_structural_priority_packing.py` only after implementation authorization.
2. All tests must run under standard pytest inside sandbox (`pytest backend/tests/test_structural_priority_packing.py`).
3. 100% of ATP tests must pass before authorization for any model evaluation.
