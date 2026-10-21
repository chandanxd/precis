# Précis Research Evaluation: Representation Loss Summary & Scientific Interpretation

**Document Status**: Authoritative Representation Audit Synthesis  
**Evaluation Benchmark**: Natural Questions MRQA (200 deterministic samples, v3 Frozen Benchmark)  
**System Evaluated**: Précis Full (6-Stage Pipeline) vs. Naive RAG (512-word chunk baseline)  
**Associated Artifacts**:
- `paper/tables/representation_loss_audit_v3.json` (Machine-readable 23-case audit)
- `paper/tables/representation_loss_audit_v3.md` (Detailed case-by-case extraction failure audit)
- `paper/tables/naive_only_representation_reaudit_v3.md` (Independent re-audit of the 29 Naive-only bottleneck cases)
- `paper/tables/authoritative_results_ledger.md` (Numerical source of truth)

---

## 1. Executive Summary: The Structural Loss Landscape

The Précis evaluation integrity audit established that Précis Full achieves **70.5% (141/200)** containment correctness and **19.0% (38/200)** Exact Match on the Natural Questions benchmark, trailing conventional passage-based Naive RAG (**79.5%** containment, **28.5%** Exact Match).

To make this negative benchmark outcome scientifically informative, this audit traces the exact failure mechanics across:
1. **The 23 Complete Extraction Failures**: Questions where the raw Wikipedia passage contains the gold answer, but Stage 2 SVOA extraction failed to materialize any answer-bearing proposition.
2. **The 29 Naive-Only Bottleneck Cases**: Questions where Naive RAG answered correctly under containment evaluation, but Précis Full failed.

The central finding is that **72.4% (21/29)** of Précis losses are caused by **upstream representational limits** (unextracted HTML tables/lists and truncated predicates), while only **24.1% (7/29)** represent downstream local LLM reasoning failures, and **0.0% (0/29)** are caused by vector retrieval or context packing.

---

## 2. Taxonomy of the 23 Complete Extraction Failures

Every complete extraction failure was independently analyzed with spaCy dependency parses and categorized under a strict taxonomy:

| Failure Category | Count | % of 23 Failures | Epistemic Classification | Fix Classification | Primary Mechanism |
| :--- | :---: | :---: | :--- | :--- | :--- |
| **NON_SENTENTIAL_STRUCTURE** | **12** | **52.2%** | Source-Format Mismatch | `ARCHITECTURAL_CHANGE` | HTML table cells (`<td>`), bullet lists (`<li>`), and standing grids lacking finite matrix verbs. |
| **MULTI_CLAUSE_REPRESENTATION_LIMIT** | **3** | **13.0%** | Representation Limitation | `NOT_FIXABLE_WITH_CURRENT_REPRESENTATION` | 21-to-42-word narrative definitions spanning multiple subordinate clauses, appositives, and discourse relations. |
| **DOMAIN_SPECIFIC_STRUCTURE** | **3** | **13.0%** | Representation Limitation | `DOMAIN_SPECIFIC_HEURISTIC` | Formal legal reporter citations (`2 U.S. 419 (1793)`) appended to case names. |
| **IMPLEMENTATION_DEFECT** | **2** | **8.7%** | Implementation Defect | `SAFE_GENERIC_FIX` / `GENERALIZATION_REQUIRED` | Intransitive verbs with prepositional objects (`refers to X`) and copular prepositional complements (`is from X`). |
| **QUALIFIER_OR_ARGUMENT_LOSS** | **2** | **8.7%** | Implementation Defect | `SAFE_GENERIC_FIX` | Adjunct spans truncated at punctuation/hyphens (`71 --` vs `71 -- 74 °C`) and compound prepositions (`along with`). |
| **EVALUATION_OR_ANNOTATION_ARTIFACT** | **1** | **4.3%** | Evaluation Artifact | `NOT_FIXABLE_WITH_CURRENT_REPRESENTATION` | Correct anatomical location (`sperm's midpiece`) extracted, but annotation required parenthetical explanation. |
| **Total** | **23** | **100.0%** | | | |

### Epistemic Distribution of Extraction Losses:
- **Source-Format Mismatch (Non-Sentential Content)**: 12 / 23 (**52.2%**)
- **Inherent Representation Limits (Multi-Clause & Domain)**: 6 / 23 (**26.1%**)
- **Addressable Engineering / Implementation Defects**: 4 / 23 (**17.4%**)
- **Evaluation / Annotation Artifacts**: 1 / 23 (**4.3%**)

---

## 3. Taxonomy of the 29 Naive-Only Bottleneck Cases

Cross-referencing the 29 questions where Naive RAG succeeded but Précis Full failed under containment correctness:

| Failure Category | Count | % of 29 Cases | Primary Pipeline Stage | Generalizable Fix? |
| :--- | :---: | :---: | :--- | :--- |
| **Complete SVOA Extraction Failure** | **15** | **51.7%** | Stage 2 (SVOA Extraction) | **No**: HTML tables, non-sentential lists, legal citations. |
| **Incomplete / Distorted Representation** | **6** | **20.7%** | Stage 2 / Stage 3 (Factual Representation) | **Partial (3/6)**: Passive complement propagation and negation misattachment. |
| **Downstream LLM Generation / Reasoning Failure** | **7** | **24.1%** | Stage 5 (Local LLM Inference) | **No**: Inherent to 7B parameter local model synthesis and entity disambiguation. |
| **Evaluation / Annotation Artifact** | **1** | **3.4%** | Stage 6 (String Containment) | **N/A**: Strict string containment failed on equivalent year (`in 1980` vs `The 1980 Summer Olympics`). |
| **Retrieval / Ranking Issue** | **0** | **0.0%** | Stage 3 (ChromaDB Retrieval) | **N/A**: 100% retrieval retention. |
| **Context Packing Issue** | **0** | **0.0%** | Stage 4 (Knapsack Packing) | **N/A**: 100% packing retention under 2048 token ceiling. |
| **Modality Filter Issue** | **0** | **0.0%** | Stage 4 (Epistemic Filtering) | **N/A**: Zero answer-bearing facts were dropped by modality filtering. |
| **Total** | **29** | **100.0%** | | |

---

## 4. Most Common Failure Mechanisms

The empirical audit reveals three primary failure mechanisms that account for over 90% of all Précis losses:

### Mechanism 1: Non-Sentential Web Structure (12 extraction cases, 52.2%)
Natural Questions source documents are derived from Wikipedia dumps containing raw HTML tags (`<Table>`, `<Td>`, `<Ul>`, `<Li>`).
- SVOA extraction is fundamentally predicated on sentential dependency grammar (requiring a finite verb or auxiliary root).
- Isolated table cells (e.g., `<td>Daisuke Ohata</td>`, `<td>51,331</td>`) and bullet lists (e.g., `<Li>Hathi Jr. -</Li>`) possess no subject-verb-object syntax.
- Naive RAG trivially preserves these entities because it indexes raw character/word chunks without requiring linguistic structure.

### Mechanism 2: Multi-Clause & Argument Truncation (5 extraction cases, 21.7%)
When information spans multiple subordinate clauses, appositives, or complex prepositional chains:
- Atomic SVOA extraction intentionally decomposes the sentence into discrete propositions.
- In doing so, it drops connective discourse ties (e.g., decomposing a 42-word metaphor into 7 separate facts, or dropping secondary disjuncts in `until he or she resigns, is dismissed, or dies`).
- The benchmark evaluator requires contiguous string containment of the entire reference span, causing fragmented atomic facts to register as complete extraction failures.

### Mechanism 3: Local LLM Synthesis & Entity Competition (7 cases in 29 bottleneck, 24.1%)
Even when answer-bearing facts are cleanly extracted, retrieved, and packed into the prompt:
- The local 7B generator (`qwen2.5-coder:7b`) exhibits reasoning errors:
  - **Granularity Confusion**: Selecting a street address (`Russell Road`) instead of the city/state (`Paradise, Nevada`) when both are present in packed facts (3 identical samples).
  - **Entity Confusion**: Selecting `dual mono signal` when the context explicitly defines `Panning` (2 identical samples).
  - **Phrasing Sensitivity**: Refusing to answer when the context says "released the series on April 13, 2018" because the prompt asked when the "new season" was released (1 sample).

---

## 5. Implementation Defects vs. Representation Limitations

To maintain scientific integrity, the audit strictly separates genuine engineering defects from fundamental representational limits:

### A. Genuine Implementation Defects (Addressable in Software)
1. **Punctuation Truncation in Adjuncts**:
   - In `b98f6e8089e2` (Crock pot temperature), the temperature span `71 -- 74 ° C` was truncated at the double hyphen `--`, yielding `71 --`. This is an engineering defect in regex/punctuation token slicing.
2. **Compound Preposition Truncation**:
   - In `3425eab641a5` (True Grit cast), the compound preposition `along with X, Y, Z` was truncated to `manner: along`. This is an engineering defect in prepositional phrase expansion.
3. **Copular Prepositional Complements**:
   - In `4309a135fbc4` (Comanche name origin), `X is from Y` failed to extract because the copular handler only looks for `attr` or `acomp`, dropping `prep` (`from`).
4. **Passive Predicate Complement Propagation**:
   - In `35d3ce1b8ae8` (Sakshi Malik ambassador), `was made brand ambassador` dropped `brand ambassador`, extracting only `was made 26 August 2016`.

### B. Fundamental Representation Limitations (Inherent to Atomic SVOA)
1. **Non-Sentential Tabular Records**:
   - Tables represent tabular relational schemas (rows, columns, headers), not natural language Subject-Verb-Object propositions. Representing table cells as SVOA facts requires dedicated tabular parsers, not dependency rules.
2. **Multi-Clause Discourse Semantics**:
   - Propositional logic cannot represent extended 42-word explanations without decomposing them. Once decomposed, string containment against long reference spans fails by definition.
3. **Legal Citation Notations**:
   - Legal reporter citations (`Volume Reporter Page (Year)`) are formal bibliographic metadata, not grammatical adjuncts.

---

## 6. General Fixability Assessment & Code Intervention Decision

### Audit Question:
*"Is there one small, general, deterministic implementation fix that addresses a meaningful class of the remaining failures without introducing benchmark-specific heuristics or architectural changes?"*

### Evaluation:
1. **The 4 Implementation Defects**:
   - Fixing copular `is from`, compound `along with`, and double-hyphen `--` spans would fix **at most 3 of the 23 extraction failures** (13.0%) and **at most 2 of the 29 Naive-only bottleneck cases** (6.9%).
   - These 4 defects represent isolated, disparate linguistic edge cases across different parts of `svoa.py` (copula handler, adjunct regex, passive complements), rather than a single unified root cause.
2. **The Dominant Failure Class (52.2%)**:
   - Over half of all remaining failures (12/23) are HTML tables and bullet lists.
   - Addressing them cannot be achieved via a "small deterministic fix" in `svoa.py`; it requires an **architectural redesign** to introduce a dedicated HTML DOM / table parsing stage prior to linguistic analysis.
3. **Regression Risk**:
   - Expanding dependency rules in `svoa.py` risks introducing false-positive relations and clutter across the 177 currently successful questions, potentially degrading downstream precision and latency.

### Formal Recommendation:
**DO NOT MODIFY PRODUCTION CODE. FREEZE THE V3 BENCHMARK.**

- The v3 pipeline represents a stable, clean, and fully characterized research artifact.
- Attempting ad-hoc patches to capture 2 or 3 edge cases would amount to benchmark-specific decoration without altering the overarching scientific outcome (Naive RAG would still statistically significantly outperform Précis).
- The scientifically defensible path is to present these representation losses as **rigorously quantified architectural trade-offs** in the paper.

---

## 7. Scientific Interpretation

### 1. What does SVOA represent well?
The audited results show that SVOA represents **asserted sentential relations in natural prose with high fidelity**:
- 88.5% (177/200) of all questions retain verified answer-bearing facts in structured SVOA form.
- In clean narrative text, SVOA successfully decouples semantic entities, attributes, and adjuncts.
- This decoupling provides **11 clear precision wins over Naive RAG**, where isolating clean propositions eliminated confusing narrative distractors that led Naive RAG into hallucinations.

### 2. What does it systematically fail to represent?
The audited cases indicate that the current atomic SVOA framework systematically fails on two fronts:
1. **Non-sentential web layouts**: HTML tables, cast lists, and statistical infoboxes that lack verbal predicates.
2. **Cross-clausal discourse structures**: Long definitions and explanations where the semantic content depends on the logical relation between multiple clauses rather than an individual proposition.

### 3. Which failures are engineering defects vs. inherent limitations?
- **Engineering Defects (17.4% of extraction failures)**: Minor syntactic edge cases (copular PPs, compound prepositions, punctuation slicing in numbers).
- **Inherent Limitations (78.3% of extraction failures)**: Semi-structured HTML content (52.2%) and multi-clause discourse boundaries (26.1%).

### 4. What does this imply for future retrieval architectures?
These observations suggest that real-world knowledge extraction cannot rely solely on sentence-level dependency parsing:
- **Hybrid Ingestion**: Future architectures must incorporate dedicated multimodal / DOM-aware parsers that convert HTML tables and key-value lists into structured tuples before linguistic processing.
- **Clausal Graphs**: Instead of flat atomic proposition sets, complex knowledge representations should support hierarchical clausal graphs that preserve parenthetical, causal, and conditional dependencies across propositions.
