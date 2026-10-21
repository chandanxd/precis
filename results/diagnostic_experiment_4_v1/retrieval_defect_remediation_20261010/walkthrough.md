# Experiment 4.5.4: Structural Retrieval Defect Remediation Walkthrough

## Summary of Accomplishments

During Experiment 4.5.4, we resolved all three retrieval defects identified in the Experiment 4.5.3 audit:

1. **Remediated DEFECT-01 (`top_doc` bias)**:
   - Refactored `assemble_structural_query_context()` in `backend/src/precis/pipeline/structural.py`.
   - Replaced the hard document-level short-circuit with a similarity-dominant blended ranking policy:
     $$\text{score}(s) = \text{sim}(s, q) \times (1.0 + 0.15 \times \mathbb{I}_{s \in \text{fact\_docs}} + 0.10 \times \mathbb{I}_{s = \text{top\_doc}})$$
   - Deterministic tie-breaking: `(-round(score, 6), -round(sim, 6), item.id)`.
   - In Test A, `awards_data.html` ($sim=0.58$) is now retained and ranked #1, defeating `Frank Miller` from `energy_summit.html` ($sim=0.32$).

2. **Remediated DEFECT-02 (Pure-structural store rejection)**:
   - Updated empty-store guards in `query()` (REST) and `_handle_ws_query()` (WebSocket) in `backend/main.py`.
   - Both handlers now verify `has_svoa = active_store.count() > 0` and `has_struct = is_list_extraction_enabled() and active_store.has_structural_evidence()`.
   - In Tests D and E, pure-structural documents now successfully execute through REST (HTTP 200) and WebSocket streaming, delivering table context to the LLM generator.
   - In Test F, truly empty stores continue to return the expected HTTP 400 Bad Request and WebSocket error.
   - In Test G, disabled mode preserves exact legacy failure behavior.

3. **Remediated DEFECT-03 (Candidate starvation)**:
   - Candidates across document groups are pooled and evaluated together instead of excluding uncorroborated documents when `matched_items` is nonempty.
   - In Test B, a strong structural candidate from an uncorroborated document ($sim=0.65$) is selected over a weak candidate ($sim=0.28$) from a document in `fact_docs`.

---

## Test Verification Summary

- **Full Backend Test Suite**: 418 passed in 203.48s (0 failed, 0 skipped).
- **Persistence Audit Suite**: 25 passed in 86.27s (0 failed, 0 skipped).
- **Diagnostic Scripts (4.2, 4.3, 4.4)**: 33 passed in 3.93s (0 failed, 0 skipped).
- **Total Unique Non-Overlapping Tests**: 476 passed (100% pass rate).
- **Zero Live Inference**: All LLM generation was deterministic and offline.
- **Zero Accidental File Modifications**: Only `structural.py`, `main.py`, and `test_experiment_4_5_persistence_audit.py` were edited.
