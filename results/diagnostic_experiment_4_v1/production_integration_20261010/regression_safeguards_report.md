# Evidence-Level Regression Safeguards Report

## Executive Summary

The Experiment 4.4 audit identified three specific cases where Condition E (tables + lists) produced an Exact Match regression relative to Condition D (table retention only). Rather than accepting regressions as inevitable noise, Experiment 4.5 implements permanent evidence-level regression safeguards.

All three cases are validated by dedicated regression tests in `backend/tests/test_structural_integration.py` (`TestRegressionSafeguards`).

---

## Detailed Case Analysis

### 1. Case `3f5983b2`: Namibian Minister of Finance

- **Query**: "Who was the first Minister of Finance in Namibia?"
- **Gold Answers**: `Saara Kuugongelwa`, `Callum`
- **Root Cause in Condition E**: The list parser extracted minister list items but lost key qualifiers (dates of tenure and title prefixes), causing confusion between incumbent and predecessor ministers.
- **Safeguard**: `extract_entity_binding()` and `RobustListParser` preserve full key-value bindings (`"Minister of Finance: Saara Kuugongelwa"`) and parent prefixes (`"Cabinet Ministers (2003-2015)"`), ensuring temporal and relational qualifiers remain bound to the proper entity.
- **Verification**: `test_regression_3f5983b2_namibian_minister_evidence` passes.

### 2. Case `ef634417`: Scorpions Songwriters

- **Query**: "Who wrote the song 'Still Loving You' by Scorpions?"
- **Gold Answers**: `Rudolf Schenker`, `Klaus Meine`
- **Root Cause in Condition E**: The input document contained a high-salience discography table identifying the songwriters, followed by a long, redundant personnel and track-listing bullet list. Appending the redundant list diluted the prompt's attention, shifting model focus away from the table.
- **Safeguard**: Conservative table-list deduplication (`deduplicate_table_list_overlap`). If candidate list items duplicate facts already represented ($\ge 80\%$) in selected table cells, the redundant list block is suppressed.
- **Verification**: `test_regression_ef634417_scorpions_song_evidence` passes. Redundant band member lists are suppressed while novel lists (album release dates, recording studios) are preserved.

### 3. Case `8f1f9bd9`: Apostle Thomas / Didymus

- **Query**: "What was the name of the apostle who doubted Jesus?"
- **Gold Answers**: `Thomas`, `Didymus`
- **Root Cause in Condition E**: In Wikipedia's list of apostles, Thomas is listed with his epithet and Greek translation (`"Thomas (also called Didymus) -- One of the Twelve Apostles"`). An overly aggressive regex delimiter stripped parentheticals, dropping `Didymus`.
- **Safeguard**: `RobustListParser` preserves parentheticals and qualifiers within `clean_text`, ensuring alternate names and translations survive extraction.
- **Verification**: `test_regression_8f1f9bd9_thomas_definition_evidence` passes. Both `Thomas` and `Didymus` are preserved in the extracted list chunk.
