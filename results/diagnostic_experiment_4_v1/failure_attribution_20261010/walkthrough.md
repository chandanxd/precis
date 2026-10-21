# Experiment 4.3 Gate 1: Walkthrough

## Overview

This walkthrough documents the completion of **Gate 1: Failure Attribution and Targeted Diagnostic Preparation** for **Experiment 4.3** (`results/diagnostic_experiment_4_v1/failure_attribution_20261010/`).

Gate 1 investigated the remaining 101 failure cases under Condition D ($\theta=0.0$) from the Experiment 4.2 full-cohort evaluation ($N=200$). The objective was to audit the root causes of failure, verify the extraction-omission cases individually, separate evidence presence from semantic answerability, create minimal reproducible extraction fixtures, and prepare for isolated targeted diagnostics.

---

## Accomplishments in Gate 1

### 1. Individual Verification of the 34 Extraction Omissions
- Every single extraction omission case was traced to its raw HTML markup, parsed block index, block type, row index, and text snippet.
- **Result**: Exactly **33 of 34 cases** reside strictly within HTML list blocks (`<ul>` or `<ol>`) that were excluded by `include_lists = False` to isolate table thresholding.
- Exactly **1 case** (`a5c30bbe...`, Bob Geldof) had list evidence retained in clean prose.
- Exactly **0 cases** had evidence residing in tables or unparsed deep HTML.

### 2. Separation of Evidence Presence from Semantic Answerability
- Substring presence was evaluated independently from semantic answerability:
  - **31 cases (91.2%)**: Clearly and directly supported by the list text.
  - **2 cases (5.9%)**: Annotator errors where the gold string is on the page but contradicts or does not support the query:
    * `2b464be1...`: Query asks for the dad in A Christmas Story; gold answer is `Ian Petrella` (who played the brother Randy Parker; Darren McGavin played the dad).
    * `f2438373...`: Query asks for the Nobel laureate who began career as an accountant; gold answer is `Amartya Sen` (list only enumerates laureates; C.V. Raman was the accountant).
  - **1 case (2.9%)**: Ambiguous / false-premise query (`895b5134...`, Belichick as player).

### 3. Comprehensive Taxonomy of All 101 Condition D Failures
- **Genuine Extraction Omissions (31 cases)**: 30 unordered lists, 1 ordered list.
- **Generation & Reasoning Failures (44 cases)**:
  - 14 attention / context-length failures (model output `"Insufficient information"` despite table in context).
  - 30 distractor row / entity misattributions (model extracted an adjacent cell, wrong year, or wrong season).
- **Surface-Form / Scoring Mismatches (24 cases)**:
  - 14 multi-entity over-complete answers (model provided all valid entities requested; benchmark only labeled a single entity).
  - 7 unit or category specifiers (e.g. `Stone bridge` vs `Stone`).
  - 2 parenthetical additions (e.g. `$205,700 annually (Executive Schedule I)`).
  - 1 incomplete entity (`Bob Geldof` vs `Bob Geldof as Pink`).
- **Dataset / Annotator Errors (2 cases)**: Irrecoverable under current gold metrics.

### 4. Minimal Reproducible Extraction Fixtures & Isolated Extractor
- Created 5 minimal HTML fixtures in `extraction_fixtures/`:
  1. `fixture_01_key_value_list.html`: Entity-role binding and qualifiers.
  2. `fixture_02_nested_list.html`: Nested division hierarchies and parent prefixes.
  3. `fixture_03_ordered_list.html`: Ranked numerical sequence preservation.
  4. `fixture_04_malformed_list.html`: Robust recovery from unclosed `<li>` tags.
  5. `fixture_05_negative_distractor_list.html`: Filtering navigation boilerplate.
- Implemented isolated diagnostic list extractor in `scripts/diagnostic_list_extractor.py` (outside `backend/src/precis/`).
- Test suite executed via `pytest scripts/test_experiment_4_3_fixtures.py`: **5 passed in 0.02s** (100% pass rate).
- Prior integrity suite executed via `pytest scripts/test_experiment_4_2_integrity.py`: **13 passed in 4.02s** (100% pass rate).

---

## Deliverables Generated

All Gate 1 artifacts are stored strictly in `results/diagnostic_experiment_4_v1/failure_attribution_20261010/`:
1. `failure_inventory.jsonl`: Auditable case-by-case records for all 101 failures.
2. `failure_taxonomy_summary.json`: Detailed aggregation of failure categories, structural elements, and answerability judgments.
3. `extraction_fixtures/`: 5 minimal reproducible HTML test fixtures.
4. `gate_1_report.md`: Comprehensive Gate 1 evaluation report.
5. `walkthrough.md`: This executive walkthrough.
6. `integrity_report.json`: Cryptographic verification of all inputs, test results, and safety invariants.

---

## Gate 1 Recommendation

**Status**: `READY FOR TARGETED DIAGNOSTICS`  
The architectural root cause of the 31 extraction omissions is verified. The next step is evaluating the candidate list extractor on the 31-case diagnostic subset before proposing any full-cohort generation run.
