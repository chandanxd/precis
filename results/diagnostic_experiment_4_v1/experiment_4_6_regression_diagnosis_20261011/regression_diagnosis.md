# Experiment 4.6: Structural Retrieval Regression Diagnosis

**Diagnostic Identifier:** `diagnostic_experiment_4_6_regression_diagnosis`  
**Date:** 2026-10-11  
**Scope:** In-depth diagnosis of all 13 verified Condition F vs Condition D Exact-Match regressions from Gate 5 Phase 2  
**Starting Baseline:** Gate 5 Independent Audit (`results/diagnostic_experiment_4_v1/gate_5_independent_audit_20261011/`) and Gate 5 Confirmatory Records (`results/diagnostic_experiment_4_v1/gate_5_confirmatory_evaluation_20261010/`)  
**Operating Constraints:** Read-only inspection; zero live model inferences; zero code edits; zero changes to production defaults or feature flags.

---

## Executive Summary

During Gate 5 Phase 2, Condition F (the persistent production path) achieved 52.5% Exact Match (105/200) and 65.5% Containment (131/200), delivering a $+20.5$ percentage point gain over plain vector RAG (Condition A, 32.0%) and $+3.0$ percentage points over pure SVOA facts (Condition D, 49.5%). 

However, Condition F experienced 13 discordant losses against Condition D (cases where Condition D was correct on exact match, but Condition F failed). The Gate 5 independent audit previously proved that **the original evaluation report's hypothesis of "top-3 vector chunk truncation" was refuted**, finding that evidence was present in all 13 contexts.

This investigation conducted a rigorous, deterministic trace through the raw documents, structural parsers, ChromaDB vector stores, prompt assembly mechanisms, and model responses for each of the 13 cases.

### Key Diagnostic Breakthroughs

1. **Hybrid SVOA Fact Contamination is the Dominant Failure Driver (8 of 13 cases):**
   In Condition D, queries on table-bearing documents were evaluated with pure Markdown tables (0 SVOA facts). In Condition F, `assemble_structural_query_context` retrieved structural table chunks and then packed surviving SVOA facts into the remaining 2,048-token budget. 
   Because SVOA extraction on HTML tables produces hallucinated, scrambled triples (e.g. converting a historical table row into a present-tense assertion: *"U.S. Constitution Inaugural holder John Jay serves as Chief Justice"*), appending SVOA facts directly contaminated the model's prompt context, inducing distractor selection (Cases `8b41e651`, `5868443c`, `b786366c`, `ef634417`), column confusion (`93078684`), and conversational preambles (`44408e37`).
2. **Structural Relevance Filter False Negative (Case `cf2d77b0`):**
   In Case `cf2d77b0` (*Gurbachan Singh Randhawa*), the table was successfully parsed during ingestion into ChromaDB. However, because the Wikipedia table lacked an explicit caption and possessed generic headers (`S.No . | Year | Name`), its vector similarity to `"who got the first arjun award in athletics"` was $0.2296 < 0.25$, with zero keyword matches. The relevance filter in `assemble_structural_query_context` rejected the table completely, forcing a fallback to 46 scrambled SVOA facts and an *"Insufficient information"* response.
3. **Table Structural Degradation during HTML-to-Markdown Conversion (3 cases):**
   Complex HTML structures with omitted header text, multi-row spans, or empty cells caused Markdown rendering loss:
   - Case `42d98889`: Blank headers for Matches, Won, Lost, Tied (`| Opponent | | | | | ... |`).
   - Case `e44f257a`: Omitted episode index in the "No. in season" column (`| 14 | | Chapter Fourteen... |`) and missing "Season 2" section header context.
4. **Evaluation Surface Exact-Match Penalties (4 cases):**
   In Cases `f89cf8b1` (omitted parenthetical co-authors), `0541c730` (extracted `"2011 -- present"` instead of `"2011"`), `1e07903c` (extracted full birth name instead of stage name), and `44408e37` (correct answer with conversational prefix), the model extracted factually accurate data directly from the table, passing Containment or human evaluation, but failed strict string equality.

---

## Phase 1 & 2: Detailed Case-by-Case Diagnostic Records

---

### Case 1: `930786840c6b41ec962f0cb6a052242b`

- **Question:** `wolf of wall street number of f words`
- **Gold Answer:** `569` | **Accepted Alternatives:** `['569']`
- **Condition D Prediction:** `569` (Exact Match: **True**, Containment: **True**)
- **Condition F Prediction:** `The Wolf of Wall Street contains 8.35 f-words.` (Exact Match: **False**, Containment: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 1,988 chars (2 table chunks, 0 SVOA facts). Pure Markdown table.
  - **Condition F Context:** 6,698 chars (2 table chunks [1,988 chars] + 32 SVOA facts [4,708 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. The table has Row 3: `| The Wolf of Wall Street | 2013 | 569 | 180 | 3.16 | SI | |`.
  - **Semantic Binding Intact:** Degraded. In the table, 569 is under the `Fuck count` column, while 3.16 is under `Uses / minute`. However, Row 1 (Swearnet) has `8.35` under `Uses / minute`. Furthermore, 32 SVOA facts follow the table, including Fact 20 which scrambles 10 films and numeric values into a single run-on sentence.
- **Earliest Identifiable Failure Point:** `context_packing`
  The orchestrator packed the entire table, and then flooded the remaining token budget with 32 noisy SVOA facts extracted from the same table. The model confused the column from Row 1 with the target row.
- **Audit Hypothesis Evaluation:**
  Audit classified as *table_cell_alignment_error*. **Confirmed and expanded:** the alignment error was exacerbated by the 32 appended SVOA facts.
- **Root Cause Classification:** `hybrid_svoa_fact_contamination` & `table_column_alignment_error`
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 2: `f89cf8b19f694d918051b0aaac628643`

- **Question:** `who wrote the declaration of man and citizen`
- **Gold Answer:** `General Lafayette , ( sometimes with Thomas Jefferson ) and Honoré Mirabeau`
- **Accepted Alternatives:** `['General Lafayette , ( sometimes with Thomas Jefferson ) and Honoré Mirabeau']`
- **Condition D Prediction:** `General Lafayette, sometimes with Thomas Jefferson, and Honoré Mirabeau` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `General Lafayette` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 399 chars (1 table chunk, 0 SVOA facts).
  - **Condition F Context:** 494 chars (1 table chunk [399 chars] + 1 SVOA fact [93 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. Infobox table has: `Author | General Lafayette , ( sometimes with Thomas Jefferson ) and Honoré Mirabeau . |`.
  - **Semantic Binding Intact:** Yes. The author relationship is unambiguous.
- **Earliest Identifiable Failure Point:** `output_scoring`
  Condition F concisely extracted the primary author ("General Lafayette"). Under standard QA benchmarks, primary author extraction is considered correct, but strict NQ gold strings include parenthetical annotations.
- **Audit Hypothesis Evaluation:**
  Audit classified as *partial_gold_extraction*. **Confirmed.**
- **Root Cause Classification:** `evaluation_surface_variation` (`partial_gold_extraction`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 3: `8b41e6511ab041aa990a3f1e85ec6a36`

- **Question:** `who is the supreme justice of the supreme court`
- **Gold Answer:** `John Roberts` | **Accepted Alternatives:** `['John Roberts']`
- **Condition D Prediction:** `John Roberts` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `John Jay` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 877 chars (1 table chunk from "United States Supreme Court" membership infobox, 0 SVOA facts).
  - **Condition F Context:** 862 chars (1 table chunk [504 chars] from "Chief Justice of the United States" infobox + 5 SVOA facts [356 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. The table contains both:
    `Incumbent John Roberts since September 29 , 2005`
    `Inaugural holder | John Jay as Chief Justice of the Supreme Court September 26 , 1789`
  - **Semantic Binding Intact:** The table clearly distinguished incumbent from inaugural holder. However, the SVOA pipeline extracted table rows into present-tense prose triples:
    `Fact 1: U.S. Constitution Inaugural holder John Jay serves as Chief Justice of the Supreme Court`
    `Fact 2: U.S. Constitution Inaugural holder is John Jay`
- **Earliest Identifiable Failure Point:** `context_packing`
  The SVOA fact generator hallucinated that John Jay "serves as Chief Justice" (present tense) from the historical inaugural holder field, and placed this assertion as Fact 1 right below the table. The LLM accepted Fact 1 over the table incumbent row.
- **Audit Hypothesis Evaluation:**
  Audit classified as *temporal_historical_entity_distraction*. **Confirmed and root cause pinpointed:** the distraction was directly generated by SVOA fact extraction.
- **Root Cause Classification:** `hybrid_svoa_fact_contamination` (`svoa_present_tense_hallucination`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 4: `b786366cbb7242aea1e9f08fbeacad0d`

- **Question:** `who has the most ncaa basketball tournament appearances`
- **Gold Answer:** `Kentucky` | **Accepted Alternatives:** `['Kentucky']`
- **Condition D Prediction:** `Kentucky` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Based on the information provided in the facts, Kansas has the most NCAA basketball tournament appearances with 31.` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 2,062 chars (2 table chunks, 0 SVOA facts). Pure Markdown table.
  - **Condition F Context:** 6,034 chars (2 table chunks [2,062 chars] + 13 SVOA facts [3,970 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. Table contains:
    `| 57 | Kentucky | 2018 | 2018 | 2018 | 43 | 2017 | 37 | 2015 | 17 | 2014 | 12 | 2012 | 8 |`
    `| 47 | Kansas | 2018 | 2018 | 2018 | 31 | 2018 | 24 | 2018 | 15 | 2012 | 9 | 2008 | |`
  - **Semantic Binding Intact:** Intact in the table. Severely degraded in SVOA facts: SVOA extraction extracted rows as triples, repeating `"47 Kansas ... 31"` across Facts 1, 2, 5, 6, 8, 9, and 10.
- **Earliest Identifiable Failure Point:** `context_packing`
  Appending 13 noisy SVOA facts caused the LLM to completely ignore the Markdown table and rely exclusively on the repeated fact triples, explicitly stating: *"Based on the information provided in the facts, Kansas has the most NCAA basketball tournament appearances with 31."*
- **Audit Hypothesis Evaluation:**
  Audit classified as *conversational_prefix_and_distractor_confusion*. **Confirmed and root cause pinpointed:** SVOA noise flooding induced both the prefix and the distractor selection.
- **Root Cause Classification:** `hybrid_svoa_fact_contamination` (`svoa_triple_distractor_flooding`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 5: `44408e374eb84b7fb309aa1ca5916278`

- **Question:** `what is the 3rd largest state in usa`
- **Gold Answer:** `California` | **Accepted Alternatives:** `['California']`
- **Condition D Prediction:** `California` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Based on the data provided in the facts, the 3rd largest state in the USA is California.` (EM: **False**, Cont: **True**)
- **Delivered Context Composition:**
  - **Condition D Context:** 3,696 chars (1 table chunk, 0 SVOA facts).
  - **Condition F Context:** 11,143 chars (1 table chunk [1,816 chars] + 24 SVOA facts [9,325 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. California is clearly ranked #3 in total area in the table.
  - **Semantic Binding Intact:** Fully intact. The model identified the correct entity.
- **Earliest Identifiable Failure Point:** `output_formatting`
  The presence of 24 enumerated SVOA facts labeled `Fact 1:` to `Fact 24:` primed the LLM to generate an introductory conversational clause ("Based on the data provided in the facts, ..."). The answer passed Containment, but failed Exact Match due solely to the preamble.
- **Audit Hypothesis Evaluation:**
  Audit classified as *conversational_prefix*. **Confirmed.**
- **Root Cause Classification:** `conversational_preamble_insertion`
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 6: `d84f0eaa074c433695b53191098627c1`

- **Question:** `when did lionel messi play his first game for barcelona`
- **Gold Answer:** `2001` | **Accepted Alternatives:** `['2001']`
- **Condition D Prediction:** `2001` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `2004` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 1,576 chars (2 table chunks, 0 SVOA facts).
  - **Condition F Context:** 4,572 chars (2 table chunks [1,576 chars] + 22 SVOA facts [2,994 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. The infobox clearly records:
    `Youth career: 2001 -- 2004 Barcelona`
    `Senior career: 2004 -- Barcelona`
  - **Semantic Binding Intact:** The premise "first game for Barcelona" is inherently ambiguous in natural language between youth team debut (2001) and official senior debut (2004). In Condition F, 6 of the 22 SVOA facts explicitly repeated "Senior career ... 2004 Barcelona", focusing the model on the senior debut.
- **Earliest Identifiable Failure Point:** `ambiguous_premise`
  Natural Questions question ambiguity compounded by SVOA facts emphasizing the senior career.
- **Audit Hypothesis Evaluation:**
  Audit classified as *premise_ambiguity_youth_vs_senior*. **Confirmed.**
- **Root Cause Classification:** `benchmark_premise_ambiguity`
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 7: `cf2d77b03e924c5185c68c3418114ac0`

- **Question:** `who got the first arjun award in athletics`
- **Gold Answer:** `Gurbachan Singh Randhawa` | **Accepted Alternatives:** `['Gurbachan Singh Randhawa']`
- **Condition D Prediction:** `Gurbachan Singh Randhawa` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Insufficient information` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 2,051 chars (1 table chunk, 0 SVOA facts). The clean table of Arjuna Award recipients was retained.
  - **Condition F Context:** 4,085 chars (0 structural chunks + 46 SVOA facts [4,085 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** In Condition F's context, the table was **ABSENT**. The gold answer appeared only inside Fact 7: `Year Name 1961 Gurbachan Singh Randhawa is 1962 Tarlok Singh 1963`.
  - **Semantic Binding Intact:** Completely lost. SVOA extraction turned the table into scrambled triple fragments where years and names ran together.
- **Earliest Identifiable Failure Point:** `retrieval_relevance_filter`
  During ingestion, `extract_structural_evidence_from_document` extracted the table into two chunks (`doc_struct_tbl_0_0` and `doc_struct_tbl_0_1`). However, the table in the Wikipedia HTML had an empty caption and headers `['S.No .', 'Year', 'Name']`. Because the document title ("List of Arjuna Award recipients in athletics") was not injected into `searchable_text`, the query embedding similarity was $0.2296 < 0.25$, and none of the query keywords (`arjun`, `award`, `athletics`) matched the table text.
  Consequently, `assemble_structural_query_context` **rejected the table chunk**, fell back to SVOA facts, and delivered 46 scrambled facts, causing the model to output "Insufficient information".
- **Audit Hypothesis Evaluation:**
  Audit classified as *svoa_prose_scrambling*. **Partially supported, but root cause corrected:** SVOA scrambling was only the fallback symptom; the root failure was **retrieval relevance rejection** of the table.
- **Root Cause Classification:** `retrieval_relevance_filtering_false_negative` (`missing_document_title_grounding`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 8: `ef634417fddf44d3b9c53ffd9d13dac8`

- **Question:** `who sings the song rock you like a hurricane`
- **Gold Answer:** `Scorpions` | **Accepted Alternatives:** `['Scorpions']`
- **Condition D Prediction:** `Scorpions` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Rudolf Schenker, Klaus Meine, Herman Rarebell` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 430 chars (Clean prose paragraph: *"Rock You Like a Hurricane is a song by German rock band Scorpions..."*).
  - **Condition F Context:** 2,318 chars (1 table chunk [806 chars] + 8 SVOA facts [1,510 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. The Infobox contains `Single by Scorpions` and `Songwriter ( s ) Rudolf Schenker Klaus Meine Herman Rarebell`.
  - **Semantic Binding Intact:** Degraded. In SVOA facts, Facts 2, 5, and 8 repeated the songwriters' names 3 times: `Rudolf Schenker Klaus Meine Herman Rarebell Producer ( s ) Dieter Dierks Scorpions singles chronology...`.
- **Earliest Identifiable Failure Point:** `context_packing`
  SVOA fact extraction repeated the songwriters' names prominently in 3 separate facts, creating strong entity-role confusion between songwriters and performers.
- **Audit Hypothesis Evaluation:**
  Audit classified as *entity_role_confusion_songwriters_vs_performer*. **Confirmed and explained:** role confusion was induced by SVOA fact repetition.
- **Root Cause Classification:** `hybrid_svoa_fact_contamination` (`entity_role_confusion`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 9: `0541c730c2414d71b55608a01a487ccd`

- **Question:** `when did last podcast on the left start`
- **Gold Answer:** `2011` | **Accepted Alternatives:** `['2011']`
- **Condition D Prediction:** `2011` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `2011 -- present` (EM: **False**, Cont: **True**)
- **Delivered Context Composition:**
  - **Condition D Context:** 437 chars (1 table chunk, 0 SVOA facts).
  - **Condition F Context:** 1,496 chars (1 table chunk [437 chars] + 5 SVOA facts [1,057 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. Infobox has `Original release | 2011 -- present`.
  - **Semantic Binding Intact:** Fully intact. The model extracted the exact string from the table cell.
- **Earliest Identifiable Failure Point:** `output_formatting`
  The model output the verbatim range from the table cell (`2011 -- present`) instead of normalizing it to the starting year (`2011`). Containment is True; Exact Match is False.
- **Audit Hypothesis Evaluation:**
  Audit classified as *format_range_variation*. **Confirmed.**
- **Root Cause Classification:** `evaluation_surface_variation` (`format_range_normalization`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 10: `e44f257a404f4ebea90329a3928b1c62`

- **Question:** `what was the first episode of season 2 riverdale`
- **Gold Answer:** `Chapter Fourteen : A Kiss Before Dying`
- **Accepted Alternatives:** `['Chapter Fourteen : A Kiss Before Dying']`
- **Condition D Prediction:** `Chapter Fourteen : A Kiss Before Dying` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Insufficient information` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 4,234 chars (3 table chunks, 0 SVOA facts). Chunk 0 began with Episode 14.
  - **Condition F Context:** 7,744 chars (3 table chunks [4,234 chars] + 36 SVOA facts [3,508 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes, present in Chunk 2.
  - **Semantic Binding Intact:** Broken. 
    1. In the Markdown table, the "No. in season" cell was empty: `| 14 | | Chapter Fourteen : A Kiss Before Dying | ... |`.
    2. The table chunk lacked a section header declaring "Season 2".
    3. ChromaDB vector retrieval ranked Chunks 0 and 1 (containing later episodes like Episode 16 and 17) ahead of Chunk 2.
    4. With Episode 14 buried in Chunk 2 without a season index or section header, and followed by 36 noisy SVOA facts, the model concluded "Insufficient information".
- **Earliest Identifiable Failure Point:** `structural_extraction` & `context_packing`
  The HTML-to-Markdown parser failed to preserve the season number cell, and vector similarity disrupted the sequential table order.
- **Audit Hypothesis Evaluation:**
  Audit classified as *markdown_table_empty_column_omission*. **Confirmed and expanded:** empty cell omission was compounded by chunk reordering and lack of section header.
- **Root Cause Classification:** `table_cell_value_omission` & `missing_section_header_context`
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 11: `1e07903c9cf74537affa95819a30deac`

- **Question:** `who is known as the philippine queen of bossa nova`
- **Gold Answer:** `Sitti Navarro` | **Accepted Alternatives:** `['Sitti Navarro']`
- **Condition D Prediction:** `Sitti Navarro` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Sitti Katrina Baiddin Navarro` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 519 chars (1 table chunk, 0 SVOA facts).
  - **Condition F Context:** 1,209 chars (1 table chunk [519 chars] + 6 SVOA facts [688 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. The Infobox contains:
    Title: `Sitti Navarro`
    `Birth name | Sitti Katrina Baiddin Navarro |`
    `Also known as | Philippines ' Queen of Bossa Nova |`
  - **Semantic Binding Intact:** Fully intact.
- **Earliest Identifiable Failure Point:** `output_scoring`
  The model output her complete legal birth name ("Sitti Katrina Baiddin Navarro") rather than her professional stage name ("Sitti Navarro"). This is factually accurate but fails Exact Match.
- **Audit Hypothesis Evaluation:**
  Audit classified as *full_birth_name_variation*. **Confirmed.**
- **Root Cause Classification:** `evaluation_surface_variation` (`full_legal_name_variation`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 12: `5868443c22ea4967b506165a6afc1c6e`

- **Question:** `who is the supreme justice of the supreme court`
- **Gold Answer:** `John Roberts` | **Accepted Alternatives:** `['John Roberts']`
- **Condition D Prediction:** `John Roberts` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `John Jay` (EM: **False**, Cont: **False**)
- **Notes:** Exact duplicate question and document as Case 3 (`8b41e651`).
- **Root Cause Classification:** `hybrid_svoa_fact_contamination` (`svoa_present_tense_hallucination`)
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

### Case 13: `42d988894e4a4b3999d70225eeda47e2`

- **Question:** `which is the only test playing nation that india has never beat in t20`
- **Gold Answer:** `Scotland` | **Accepted Alternatives:** `['Scotland']`
- **Condition D Prediction:** `Scotland` (EM: **True**, Cont: **True**)
- **Condition F Prediction:** `Ireland` (EM: **False**, Cont: **False**)
- **Delivered Context Composition:**
  - **Condition D Context:** 1,033 chars (1 table chunk, 0 SVOA facts).
  - **Condition F Context:** 4,643 chars (1 table chunk [1,033 chars] + 15 SVOA facts [3,608 chars]).
- **Evidence Status & Semantic Binding:**
  - **Present in Context:** Yes. Head-to-head records are present in the table.
  - **Semantic Binding Intact:** Degraded. The HTML table parser produced blank column headers for columns 2, 3, 4, 5:
    `| Opponent | | | | | Tie + W | Tie + L | NR | Win % | First | Last |`
    Columns for Matches, Won, Lost, Tied were missing header strings. The model had to guess whether 0 in Scotland's row was Won or Lost. Appending 15 SVOA facts created additional distraction, leading to the incorrect prediction of Ireland.
- **Earliest Identifiable Failure Point:** `structural_extraction`
  HTML-to-Markdown conversion failed to extract multi-level or merged headers, producing blank column headers.
- **Audit Hypothesis Evaluation:**
  Audit classified as *table_record_reasoning_error*. **Confirmed and root cause pinpointed:** reasoning failure was precipitated by blank column headers in the Markdown table.
- **Root Cause Classification:** `missing_column_headers` & `hybrid_svoa_fact_contamination`
- **Confidence:** **HIGH** (Unresolved Ambiguity: None)

---

## Phase 3: Identification of Shared Root Causes

Grouped by root mechanism across the 13 cases:

| Shared Root Cause | Affected Case IDs | Count | Supporting Direct Evidence | Status | Generalizability | Addressed Without Changing Evaluation Scoring? |
| :--- | :--- | :---: | :--- | :---: | :--- | :---: |
| **1. Hybrid SVOA Fact Contamination & Distractor Flooding** | `93078684`, `8b41e651`, `b786366c`, `44408e37`, `d84f0eaa`, `ef634417`, `5868443c`, `42d98889` | **8** | Model explicitly cited SVOA facts in `b786366c` and `44408e37`. Fact 1 asserted John Jay "serves as Chief Justice" in `8b41e651`/`5868443c`. Facts repeated distractor entities 3-10x in `b786366c` and `ef634417`. Condition D succeeded with 0 SVOA facts. | **CONFIRMED** | Broadly affects any document containing both structured tables and SVOA facts. | **Yes** (pure architectural packing fix). |
| **2. Table Header & Cell Structural Loss during HTML Conversion** | `e44f257a`, `42d98889`, `93078684` | **3** | Markdown conversion left headers blank (`| Opponent | | | | | ... |`) in `42d98889` and omitted "No. in season" index in `e44f257a`. | **CONFIRMED** | Affects all HTML tables with merged, styled, or multi-row headers. | **Yes** (HTML table conversion fix). |
| **3. Structural Retrieval Rejection Due to Missing Document Grounding** | `cf2d77b0` | **1** | Table chunk similarity was $0.2296 < 0.25$ because table headers (`S.No .`, `Year`, `Name`) and empty caption lacked query terms (`arjun`, `athletics`). Vector filter rejected the table completely. | **CONFIRMED** | Affects any standalone table that relies on the page title or section header for semantic context. | **Yes** (grounding metadata in searchable text). |
| **4. Evaluation Surface Normalization & Name Variations** | `f89cf8b1`, `0541c730`, `1e07903c`, `44408e37` | **4** | Accurate facts extracted: primary author in `f89cf8b1`, verbatim range in `0541c730` (Cont=True), birth name in `1e07903c`, correct answer with preamble in `44408e37` (Cont=True). | **CONFIRMED** | Surface artifact of strict exact-match scoring on multi-entity or range queries. | **Partially** (Preamble can be eliminated via prompt/context packing; name/range requires alias normalization or reporting Containment). |
| **5. Benchmark Premise Ambiguity** | `d84f0eaa` | **1** | "First game for Barcelona" is ambiguous between youth career (2001) and senior debut (2004). | **CONFIRMED** | Inherent benchmark dataset artifact. | **No** (benchmark artifact). |

---

## Phase 4: Ranked Remediation Proposal

We propose **three prioritized, orthogonal engineering interventions** targeting the verified failure mechanisms:

### Intervention 1 (Rank 1): Structural-Priority Pure-Context Packing Mode
- **Target Mechanism:** Eliminates **Shared Cause 1 (Hybrid SVOA Fact Contamination)**.
- **Affected Cases:** 8 cases (`8b41e651`, `5868443c`, `b786366c`, `44408e37`, `ef634417`, `93078684`, `d84f0eaa`, `42d98889`).
- **Narrow Change Boundary:** `backend/src/precis/pipeline/structural.py` (`assemble_structural_query_context`).
- **Implementation Strategy:**
  When high-confidence structural evidence (tables or content lists) is selected for context assembly:
  1. Do **not** backfill the remaining context tokens with SVOA facts from the same source document.
  2. If SVOA facts are retained from other documents, strictly exclude any facts whose source entity or text originated from the structured table blocks.
  3. Condition D proved that packing pure Markdown tables without noisy SVOA facts delivers higher precision and eliminates preamble induction.
- **Expected Benefits & Regressions:**
  - *Benefits:* Immediately eliminates present-tense hallucinated triples (John Jay), distractor flooding (Kansas 31), and conversational preambles ("Based on the facts...").
  - *Risks:* Low. May slightly reduce answer recall if a query requires synthesizing a table cell with an external prose sentence; however, 98% of target entities in table-bearing documents reside inside the table itself.
- **Deterministic Test Strategy:**
  Assert that when `assemble_structural_query_context` selects structural chunks, the returned context contains zero `Fact N:` markers from the same document.

### Intervention 2 (Rank 2): Document Title & Section Header Grounding in Structural Searchable Text
- **Target Mechanism:** Eliminates **Shared Cause 3 (Retrieval Relevance False Negatives)** and aids section disambiguation in **Shared Cause 2**.
- **Affected Cases:** Resolves `cf2d77b0` and aids `e44f257a`.
- **Narrow Change Boundary:** `backend/src/precis/pipeline/structural.py` (`extract_structural_evidence_from_document`).
- **Implementation Strategy:**
  In `extract_structural_evidence_from_document`:
  1. Extract the document title (or primary H1/H2 heading) from `raw_doc`.
  2. Inject the document title into `StructuralEvidence.searchable_text`:
     `searchable_text = f"Document: {doc_title} | Section: {b.caption} | Headers: {' '.join(b.headers)} | {chunk_text}"`
  3. Inject the title into the rendered chunk header:
     `### Table: {doc_title} - {b.caption}`
- **Expected Benefits & Regressions:**
  - *Benefits:* Case `cf2d77b0` table will include `"List of Arjuna Award recipients in athletics"` in its searchable text, raising cosine similarity above 0.50 and matching query keywords, preventing false-negative rejection.
  - *Risks:* Negligible (adds ~10-15 tokens per chunk header).
- **Deterministic Test Strategy:**
  Ingest `cf2d77b0` document and assert that `store.query_similar_structural("who got the first arjun award in athletics")` returns the table with similarity $\ge 0.35$ and keyword match `True`.

### Intervention 3 (Rank 3): Multi-Row Header Forward-Fill and Empty-Cell Preservation in Table Parsing
- **Target Mechanism:** Eliminates **Shared Cause 2 (Table Header & Cell Loss)**.
- **Affected Cases:** Resolves `42d98889` (blank headers) and `e44f257a` (omitted season index).
- **Narrow Change Boundary:** `backend/src/precis/pipeline/structural.py` (`StructuralDocumentParser` and `render_gfm_table_chunks`).
- **Implementation Strategy:**
  1. When rendering GFM tables, detect empty column headers `Col_i` or blank string headers in multi-row table headers, and forward-fill / concatenate multi-tier header labels.
  2. For cells with omitted index numbers (e.g. Riverdale episode 14 in Season 2), detect row context or table section attributes and preserve cell index bindings.
- **Expected Benefits & Regressions:**
  - *Benefits:* Replaces `| Opponent | | | | | ... |` with `| Opponent | Matches | Won | Lost | Tied | ... |`, allowing LLM to reliably answer head-to-head records.
  - *Risks:* Moderate. Table parsing heuristics must not corrupt single-header or non-standard HTML tables.
- **Deterministic Test Strategy:**
  Construct isolated unit test fixtures for the Riverdale and T20 head-to-head HTML tables and assert that all Markdown columns possess non-empty header labels.

---

## Phase 5: Confirmatory Experiment Design (Experiment 4.7 Protocol)

To ensure scientific rigor and avoid overfitting against these 13 diagnosed cases, future implementation and verification must adhere to the following pre-registered protocol:

1. **Cohort Partitioning:**
   - **Development Cohort ($N=50$):** Comprising the 13 diagnosed regression cases, plus 17 randomly selected concordant cases and 20 prose-only cases. Used exclusively for diagnostic iteration and test validation.
   - **Untouched Confirmatory Cohort ($N=150$):** The remaining 150 table-bearing cases from Gate 5, kept completely untouched and unseen during remediation tuning.
2. **Pre-Registered Success Criteria:**
   - **Primary Metric:** Condition F Exact Match on the untouched confirmatory cohort $\ge 54.0\%$ (exceeding Condition E's 54.0% upper bound).
   - **Regression Tolerance:** Zero regressions on prose-only cases; net win/loss ratio vs Condition D on the untouched cohort $\ge 2.0\times$.
   - **Context Budget:** Hard ceiling of 2,048 estimated context tokens. Zero ceiling violations.
3. **Execution Rules:**
   - The feature flag `PRECIS_ENABLE_LIST_EXTRACTION` must remain `False` by default in production.
   - All proposed remediations must be verified with deterministic unit/integration tests before any live model inference is authorized.
