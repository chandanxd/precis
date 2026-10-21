# Experiment 4.6: Regression Diagnosis & Remediation Design Walkthrough

## Summary of Executed Work

This walkthrough summarizes the diagnostic investigation and engineering remediation design performed under **Experiment 4.6: Structural Retrieval Regression Diagnosis and Remediation Design**.

The entire investigation was conducted under strict read-only constraints:
- Zero live model inference calls, Ollama daemon invocations, or benchmark runs.
- Zero modifications to production source code (`backend/src/precis/`, `backend/main.py`), test suites, prompts, or configuration.
- Zero modifications to frozen historical datasets, Gate 5 evaluation records, or independent audit reports.
- Preservation of all existing working-tree state and uncommitted changes.

---

## Deliverables Generated

All deliverables have been created in:
`results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/`

1. **[`regression_diagnosis.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/regression_diagnosis.md)**:
   Comprehensive case-by-case forensic analysis of all 13 Condition F vs Condition D regressions. Details questions, gold answers, Condition D & F predictions, context compositions (character and token counts), evidence presence, semantic binding integrity, earliest failure points, audit hypothesis verification, and confidence ratings.
2. **[`root_cause_matrix.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/root_cause_matrix.json)**:
   Machine-readable JSON mapping each of the 13 cases to verified primary and secondary failure mechanisms.
3. **[`remediation_proposal.md`](file:///file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/remediation_proposal.md)**:
   Three strictly ranked engineering interventions:
   - Rank 1: *Structural-Priority Pure Context Packing* (eliminates SVOA fact distractor noise in 8 cases).
   - Rank 2: *Document Title & Section Grounding in Structural Chunks* (eliminates false-negative retrieval rejection in Case `cf2d77b0`).
   - Rank 3: *Multi-Row Header Forward-Fill & Empty-Cell Preservation* (resolves blank headers in Case `42d98889` and `e44f257a`).
4. **[`confirmatory_experiment_plan.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/confirmatory_experiment_plan.md)**:
   Pre-registered evaluation protocol for future implementation, featuring a 50-case development cohort and an untouched 200-case confirmatory cohort (150 table-bearing + 50 prose-only negative controls), strict stop rules, and feature flag safeguards.
5. **[`integrity_report.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/integrity_report.json)**:
   Cryptographic SHA-256 integrity report verifying all 8 input files and certifying zero modifications to production or historical assets.
6. **[`walkthrough.md`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/experiment_4_6_regression_diagnosis_20261011/walkthrough.md)**:
   This document.

---

## Key Diagnostic Findings

### 1. Hybrid SVOA Fact Contamination is the Primary Regression Cause
In 8 of the 13 regression cases (`8b41e651`, `5868443c`, `b786366c`, `44408e37`, `ef634417`, `93078684`, `d84f0eaa`, `42d98889`), the failure was driven by `assemble_structural_query_context` appending surviving SVOA facts after the structural table chunks:
- SVOA extraction on HTML tables produced corrupted, hallucinated present-tense assertions (e.g. asserting that inaugural 1789 Chief Justice John Jay *"serves as Chief Justice"* in Facts 1 and 2, causing Cases `8b41e651` and `5868443c` to predict John Jay over incumbent John Roberts).
- SVOA extraction repeated distractor entities 7 to 10 times (e.g. repeating *"47 Kansas 31"* across 7 facts, prompting the model in `b786366c` to explicitly declare *"Based on the information provided in the facts, Kansas has the most appearances with 31"*).
- Enumerating 20+ SVOA facts primed conversational introductory preambles (e.g. Case `44408e37` generating *"Based on the data provided in the facts, the 3rd largest state in the USA is California"*).

### 2. Retrieval Relevance Filter False Negative Identified
In Case `cf2d77b0` (*Gurbachan Singh Randhawa*), the table chunk was extracted into ChromaDB during ingestion. However, because the Wikipedia table lacked an explicit caption and had generic headers (`S.No . | Year | Name`), its query embedding similarity to *"who got the first arjun award in athletics"* was $0.2296 < 0.25$, and no keyword matched. The retriever discarded the table, fell back to 46 scrambled SVOA facts, and caused an *"Insufficient information"* prediction.

### 3. HTML-to-Markdown Parser Degradation
- In Case `42d98889`, columns 2-5 headers were rendered blank (`| Opponent | | | | | ... |`), making it difficult to distinguish Won from Lost.
- In Case `e44f257a`, the season episode number cell was rendered blank (`| 14 | | Chapter Fourteen... |`), and the table lacked a "Season 2" section header.

---

## Limitations and Boundaries

1. **No Production Modifications:** None of the proposed remediations have been implemented in production code. Production code and defaults remain completely unchanged.
2. **Feature Flag Status:** `PRECIS_ENABLE_LIST_EXTRACTION` remains disabled by default (`False`).
3. **No Inference Executed:** All findings were derived deterministically from raw evaluation records, HTML source parsing, and vector similarity mathematics. Zero GPU/LLM compute was consumed.
