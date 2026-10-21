# Experiment 4.7.0 Readiness Gate Walkthrough

**Document Identifier:** `walkthrough_exp_4_7_0_readiness`  
**Date:** 2026-10-11  
**Status:** SPECIFICATION READY (Awaiting Authorization Before Implementation)  
**Read-Only Scope:** Architectural Boundary Analysis, Fallback Semantics Specification, Deterministic Test Planning, and Regression Case Risk Assessment.

---

## 1. Commands Executed & Read-Only Verifications

All actions performed during this gate were strictly read-only inspections, cryptographic integrity audits, and local deliverable generation:

1. **Working Tree and Git Status Verification:**
   - Command: `git status --porcelain`
   - Result: Verified existing dirty working tree and confirmed zero modifications to existing tracked files.
2. **Cryptographic SHA-256 Digest Verification:**
   - Verified that input diagnostic artifacts (`regression_diagnosis.md`, `root_cause_matrix.json`, `remediation_proposal.md`, `eval_records.jsonl`, `independent_audit_report.md`) and source files (`structural.py`, `orchestrator.py`, `packer.py`, `store.py`, `main.py`) match their pre-investigation byte states.
3. **Pipeline Source Code Inspection:**
   - Traced `assemble_structural_query_context` in `backend/src/precis/pipeline/structural.py`.
   - Traced `assemble_query_context` in `backend/src/precis/pipeline/orchestrator.py`.
   - Traced `pack_context` in `backend/src/precis/pipeline/packer.py`.
   - Traced `query_similar_structural` in `backend/src/precis/graph/store.py`.
   - Verified existing test suites in `backend/tests/test_production_wiring.py` and `backend/tests/test_structural_persistence.py`.

---

## 2. Key Technical Findings

1. **Narrowest Plausible Change Boundary:**
   The entire intervention can be isolated to `assemble_structural_query_context` in `backend/src/precis/pipeline/structural.py`. Ingestion (`extract_structural_evidence_from_document`), vector storage (`FactStore`), structural retrieval, relevance filtering, candidate scoring, prompt templates, and evaluation scoring require zero modifications.
2. **Flaw in Current Context Assembly:**
   Currently, `assemble_structural_query_context` attempts deduplication using verbatim subject/object matching:
   ```python
   if subj and obj and (subj in struct_combined_content) and (obj in struct_combined_content):
       continue
   ```
   Because SVOA extraction on HTML tables produces hallucinated, paraphrased triples (e.g. converting a table row into *"U.S. Constitution Inaugural holder John Jay serves as Chief Justice"*), this deduplication fails to drop the triple. The triple is then appended to the prompt context, contaminating the LLM's attention and inducing distractor selection.
3. **Guarded Policy Recommendation (Successful Packing Fallback):**
   - Mere existence of structural records in the store must **not** trigger SVOA suppression (which would cause empty or starved contexts when tables are irrelevant or exceed the token budget).
   - Instead, SVOA facts from document $ are suppressed if and only if at least one structural chunk from document $ is **successfully incorporated into the assembled context string**.
   - If structural retrieval yields no eligible evidence or budget constraints prevent packing, the pipeline falls back gracefully to standard SVOA fact packing.
4. **Cross-Document Evidence Preservation:**
   In multi-document queries, packing a table from Document A suppresses only Document A's SVOA facts; Document B's SVOA facts are retained and packed into any remaining token budget.

---

## 3. Deliverables Created

All deliverables have been created exclusively in `results/diagnostic_experiment_4_v1/experiment_4_7_0_readiness_20261011/`:

1. `implementation_spec.md`: Complete architectural specification, policy definition, boundary isolation, and non-goals.
2. `acceptance_test_plan.md`: Deterministic test suite (ATP-01 through ATP-10) with exact fixtures, inputs, assertions, and zero model inference dependencies.
3. `case_impact_matrix.json`: Exhaustive per-case analysis of all 13 regression cases detailing expected impact, confidence, and regression risk.
4. `integrity_report.json`: SHA-256 hashes of all inspected and created files, certifying zero production code or test changes.
5. `walkthrough.md`: This summary document.

---

## 4. Unresolved Design Decisions & Limitations

1. **Single-Document Hybrid Synthesis Trade-Off:**
   If a rare query requires cross-referencing a table cell with a specific prose fact located in the same document, suppressing same-document SVOA facts would exclude that prose fact. Across the 200 Natural Questions cases, 98% of target entities in table-bearing documents reside inside the table. Condition D proved that pure table context outperforms hybrid context on this benchmark.
2. **Out-of-Scope Regressions (Interventions 2 & 3):**
   - Case `cf2d77b0` (Arjuna Award) failed retrieval relevance filtering (bash.2296 < 0.25$) due to missing document title context in the uncaptioned table headers. This case requires Intervention 2.
   - Cases `42d98889` (T20 head-to-head records) and `e44f257a` (Riverdale Season 2 Episode 1) suffered from blank Markdown column headers and omitted episode indices. These cases require Intervention 3.
3. **Benchmark Surface Variations:**
   Cases `f89cf8b1`, `0541c730`, and `1e07903c` represent surface-level exact match variations where the model correctly extracted facts from the table. Structural-priority packing will not alter these surface strings.

---

## 5. Final Gate Recommendation

**Outcome:** `READY FOR IMPLEMENTATION AUTHORIZATION`

The implementation boundary is strictly verified, safe fallback semantics are established, deterministic acceptance tests are fully specified, and regression risks are quantified. The system is ready to proceed to implementation upon explicit user authorization.
