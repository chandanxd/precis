# Précis Experiment 3: Isolated Structural Document Decompilation (Frozen Plan)

This document establishes the frozen experimental protocol for Précis Experiment 3.

## 1. Safety & Isolation Invariants
- Zero modifications to production code under backend/src/precis/.
- Zero modifications to production prompts, configurations, or frozen benchmark outputs.
- Zero modifications to Git history, branches, or pre-existing working-tree modifications.
- All code resides in scripts/eval_structural_decompilation_v3.py.
- All outputs reside in results/diagnostic_structural_decompilation_v3/.
- Model: qwen2.5-coder:7b via local Ollama (http://127.0.0.1:11434), greedy decoding (T=0.0, top-p 0.9, seed 42), max tokens 512, context ceiling 2048, CONCISE_PROMPT_TEMPLATE.

## 2. Experimental Conditions
- **Condition A (Baseline)**: Unsanitized raw document HTML -> Coref -> Prose SVOA.
- **Condition B (Isolated Structural Decompilation)**: StructuralDocumentParser decomposes HTML into clean prose stream and StructuredBlock stream. Clean prose -> Coref -> Prose SVOA. StructuredBlock stream -> StructuredBlockAdapter -> query-aware extractor. Conservative deduplication before store insertion.
- **Condition C (Decompilation + Sortable-Name Normalization)**: Condition B + Pattern 1 only sortable-name normalization (Barry , Gareth Gareth Barry -> Gareth Barry). Ordinary Last, First is preserved without normalization.

## 3. Staged Execution Protocol
- **Stage A**: Fully deterministic unit and forensic test suite (15 tests). Zero LLM inference.
  - `Test A1`: Forensic `bad74caad5` Great Lakes leakage prevention and positive preservation of non-Great Lakes (`Great Salt Lake`, `Lake of the Woods`).
  - `Test A2`: Multi-row and multi-header table structural integrity.
  - `Test A3`: Table caption and header extraction.
  - `Test A4`: Ordered and unordered lists nested in prose.
  - `Test A5`: Adversarial surrounding prose preservation without tag leakage.
  - `Test A6`: Abbreviations and date parsing within cells.
  - `Test A7`: Multiple disjoint tables within a single document.
  - `Test A8`: Deterministic prose-only document invariance.
  - `Test A9`: Malformed / unclosed HTML table EOF recovery without losing trailing text.
  - `Test A10`: Conservative cross-path deduplication semantics across all 8 conflict/match scenarios (`temporal`, `location`, `manner`, `role`, `qualifier`, missing qualifier, matching qualifier, and modality mismatch).
  - `Test A11`: Wikipedia sortable-name normalization (Pattern 1 only; ordinary `Last, First` strictly preserved).
  - `Test A12`: End-to-end source provenance (`prose`, `table_row`, `list_item`), source block ID tracking, zero table/list leakage into prose SVOA, and deterministic ordering across repeated runs.
  - `Test A13`: Structured content query-aware availability and synthesis.
  - `Test A14`: Legitimate prose mentioning table entities preserved in prose extraction path.
  - `Test A15`: Nested blocks inside table cells (introduced to test nested structures within table cells and verify parser recovery and containment without corrupting trailing prose).
- **Stage B**: Historical diagnostic replay (59 unique cases: 50 Cohort B, 4 explicit forensic cases, 6 Exp 1 failure clusters). Diagnostic and non-confirmatory.
- **Stage C**: Confirmatory dual-stratum evaluation (N=300: N=200 Table-Bearing, N=100 Prose-Only) programmatically verified disjoint from all 600 historical IDs.

## 4. Primary & Secondary Metrics
- **Primary Metric**: Exact Match (EM) on Stratum 1 (Table-Bearing, N=200).
- **Primary Comparisons**: Condition B vs A; Condition C vs A. Multiplicity-adjusted with Holm-Bonferroni (alpha=0.05).
- **Efficiency Guardrail**: Mean context token growth on Stratum 1 <= +10.0% vs Baseline A. Stratum 2 (Prose-Only) reported independently.
- **Equivalence Prohibition**: Nonsignificant results (p > 0.05) will not be interpreted as evidence of equivalence.
