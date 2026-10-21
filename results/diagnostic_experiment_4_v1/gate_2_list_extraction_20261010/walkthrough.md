# Experiment 4.3 Gate 2: Isolated List-Extraction Evaluation — Walkthrough

## Overview & Status

Gate 2 of **Experiment 4.3** (`results/diagnostic_experiment_4_v1/gate_2_list_extraction_20261010/`) has been completed.

- **Gate Status**: **COMPLETED — READY FOR FULL-COHORT EVALUATION**
- **Safety Invariants**:
  * Zero modifications to production code (`backend/src/precis/` 100% untouched).
  * Exactly 31 cases evaluated (no unauthorized inference outside the cohort).
  * Strict 2,048-token context ceiling observed (max context: 1,037 tokens, headroom: 1,011 tokens).
  * 18/18 integrity and fixture tests passing.
  * Zero imputed scores; 100% completed inferences.

---

## Key Results Summary

### 1. Stage 2A: Deterministic Evidence Recovery
- **Gold Answer Recovery**: **31 / 31 cases (100.0%)** retained the target gold answer substring in the extracted context.
- **Boilerplate Filtering**: 100% precision; 0 navigation menus, footer link farms, or sidebars leaked into context.
- **Token Efficiency**: Average list payload was ~290 tokens. Across all 31 cases, the combined context (Clean Prose + Tables + Lists) peaked at 1,037 tokens.

### 2. Stage 2B: Targeted Live Generation Pilot (`qwen2.5-coder:7b`)
- **Condition A (Reference)**: Exact Match = **0 / 31 (0.0%)**, Containment = **0 / 31 (0.0%)**.
- **Condition B (Candidate)**: Exact Match = **11 / 31 (35.5%)**, Containment = **16 / 31 (51.6%)**.
- **Paired Discordant Transitions**: Exactly **11 wins, 0 losses, 20 ties** (+11 net wins, $+35.5$ percentage points).
- **Containment Transitions**: Exactly **16 wins, 0 losses, 15 ties** (+16 net wins, $+51.6$ percentage points).
- **Exact McNemar Test**: $p = 0.0009765625$ ($p < 10^{-3}$, statistically significant).
- **Regressions**: **0 regressions** (0 EM losses, 0 containment losses).

---

## Detailed Case Analysis

### The 11 Exact Match Wins
Direct recoveries from previously omitted bulleted/numbered lists:
1. `4a3eb5f5`: Area code for Phoenix, Arizona $\rightarrow$ `602`
2. `e6bfa9f3`: Second book in Alchemyst series $\rightarrow$ `The Magician`
3. `363edbaa`: Maryland county close to DC $\rightarrow$ `Frederick County`
4. `8fe0d283`: Detective in Little Boy Blue $\rightarrow$ `Stephen Graham`
5. `bd673bbb`: Last time US women's hockey won gold $\rightarrow$ `2018`
6. `f3bd270e`: End of WW2 in the Pacific $\rightarrow$ `September 2, 1945`
7. `521b6a03`: Little boy in Polar Express $\rightarrow$ `Dante Pastula`
8. `3d3088e3`: Big Momma in Big Momma's House $\rightarrow$ `Martin Lawrence`
9. `02365027`: Zebra's name in Peppa Pig $\rightarrow$ `Zoe Zebra`
10. `04070d67`: Water body along Uruguay $\rightarrow$ `Bay of Montevideo`
11. `c530f07f`: Queen in Victoria and Abdul $\rightarrow$ `Judi Dench`

### The 5 Containment Wins (Near-Misses)
1. `abe22dfa`: Cast of A Good Day to Die Hard (listed all cast members)
2. `ed97c452`: Scottish referendum voter eligibility (listed all 5 clauses)
3. `2a25e7ad`: States in Northeast region (listed all 9 states)
4. `503e0316`: Fastest train in India and speed (`Mumbai Rajdhani Express, 140 km / h`)
5. `3e87ec57`: Spices in Chinese 5 spice powder (listed all 5 spices)

### The 15 Non-Recoveries
- **Strict Normalization Differences (4 cases)**: The model gave the concise correct answer, but NQ gold contained parentheticals or annotations (e.g., `Bonnie Lipton` vs `Bonnie Lipton ( portrayed by Skyler Samuels )`, `James I` vs `James I , King of England`).
- **"Insufficient Information" Responses (8 cases)**: Multi-hop queries over long lists where the model abstained.
- **Entity / Distractor Misattributions (3 cases)**: Selecting an adjacent list item (e.g. `Lucilla` instead of `Lucius Verus`, character name instead of actor name).

---

## Deliverables Generated

The following files are located in `results/diagnostic_experiment_4_v1/gate_2_list_extraction_20261010/`:
1. `stage_2a_evidence_recovery.jsonl`: 31 case-level evidence recovery records with token accounting.
2. `stage_2b_eval_records.jsonl`: 31 full evaluation records with prompt telemetry and scoring.
3. `paired_comparison_summary.json`: Aggregated metrics, contingency tables, and McNemar test statistics.
4. `regression_audit.jsonl`: Regression audit log (0 regressions observed).
5. `integrity_report.json`: Verification of input/output SHA-256 digests, automated test runs, and safety constraints.
6. `gate_2_report.md`: Complete Gate 2 diagnostic report.
7. `walkthrough.md`: Executive summary of the gate.

---

## Recommendation

**Status**: **READY FOR FULL-COHORT EVALUATION**

The isolated content-list extractor successfully converted 35.5% of previously missing cases into Exact Match wins and 51.6% into Containment wins with **zero regressions** and modest token consumption (~290 tokens/case). All gating requirements have been satisfied.
