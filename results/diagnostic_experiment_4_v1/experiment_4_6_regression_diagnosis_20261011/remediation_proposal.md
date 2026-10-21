# Experiment 4.6: Structural Retrieval Remediation Proposal

**Document Identifier:** `remediation_proposal_exp_4_6`  
**Date:** 2026-10-11  
**Status:** PROPOSAL ONLY (Implementation Deferred Pending Approval)  
**Target:** Remediate shared failure mechanisms identified across the 13 Condition F vs Condition D regressions.

---

## Executive Summary

Based on the forensic diagnosis of the 13 Gate 5 regressions, we propose **three strictly ranked, targeted interventions**. Each intervention addresses a verified shared failure mechanism with a narrow architectural blast radius, avoiding unnecessary heuristic complexity or context inflation.

| Rank | Intervention Name | Targeted Mechanism | Affected Regressions | Scope & Blast Radius | Implementation Risk |
| :---: | :--- | :--- | :---: | :--- | :---: |
| **1** | **Structural-Priority Pure Context Packing** | Hybrid SVOA Fact Contamination & Noise Flooding | 8 cases (`8b41e651`, `5868443c`, `b786366c`, `44408e37`, `ef634417`, `93078684`, `d84f0eaa`, `42d98889`) | `backend/src/precis/pipeline/structural.py` (`assemble_structural_query_context`) | **LOW** |
| **2** | **Document Title & Section Grounding in Structural Chunks** | Retrieval Relevance False Negatives (Missing Title Context) | 2 cases (`cf2d77b0`, `e44f257a`) | `backend/src/precis/pipeline/structural.py` (`extract_structural_evidence_from_document`) | **LOW** |
| **3** | **Multi-Row Table Header Forward-Fill & Empty-Cell Preservation** | HTML-to-Markdown Table Structural Loss (Blank Headers & Cells) | 2 cases (`42d98889`, `e44f257a`) | `backend/src/precis/pipeline/structural.py` (`StructuralDocumentParser`, `render_gfm_table_chunks`) | **MODERATE** |

---

## 1. Intervention 1 (Rank 1): Structural-Priority Pure Context Packing

### 1.1 Targeted Failure Mechanism
In the current implementation of `assemble_structural_query_context`, when structural evidence (tables or lists) is retrieved and packed, the orchestrator backfills any remaining token budget under the 2,048 ceiling with SVOA facts. The existing deduplication logic (`if subj in struct_combined_content and obj in struct_combined_content: continue`) only removes facts where both subject and object match verbatim.

Consequently, noisy, scrambled triples derived from table rows or surrounding boilerplate are appended to the context. This introduced:
- **Hallucinated Present-Tense Roles:** Transmuted historical table entries into present assertions (e.g. *"U.S. Constitution Inaugural holder John Jay serves as Chief Justice"*, causing `8b41e651` and `5868443c` to predict John Jay over John Roberts).
- **Distractor Flooding:** Repeated distractor entity triples 7 to 10 times (e.g. repeating *"47 Kansas 31"* across 7 facts, causing `b786366c` to explicitly state *"Based on the information provided in the facts, Kansas has the most appearances with 31"*).
- **Conversational Preamble Induction:** Appending 20+ enumerated `Fact N:` markers primed the model to generate conversational preambles (e.g. `44408e37` generating *"Based on the data provided in the facts, the 3rd largest state in the USA is California"*).
- **Role & Column Confusion:** In `ef634417` and `93078684`, SVOA fact noise obscured table columns and induced songwriter vs performer confusion.

In contrast, Condition D succeeded on all 8 of these cases because it evaluated tables in pure form with **zero SVOA facts**.

### 1.2 Target Case IDs
- Direct primary beneficiaries: `8b41e6511ab041aa990a3f1e85ec6a36`, `5868443c22ea4967b506165a6afc1c6e`, `b786366cbb7242aea1e9f08fbeacad0d`, `44408e374eb84b7fb309aa1ca5916278`, `ef634417fddf44d3b9c53ffd9d13dac8`.
- Secondary beneficiaries (noise reduction): `930786840c6b41ec962f0cb6a052242b`, `d84f0eaa074c433695b53191098627c1`, `42d988894e4a4b3999d70225eeda47e2`.

### 1.3 Narrowest Plausible Change Boundary
Modify only `backend/src/precis/pipeline/structural.py` inside `assemble_structural_query_context`:
- Introduce a strict structural priority policy: When high-confidence structural chunks (similarity $\ge 0.35$ or keyword match) from a source document are selected, **suppress all SVOA facts from that document**.
- If SVOA facts are retained (e.g. from a multi-document store where another document had no table), strictly filter out any SVOA facts whose provenance or entity tags indicate they were extracted from a structured block.

### 1.4 Expected Benefits and Possible Regressions
- **Expected Benefits:** Eliminates distractor triples, prevents preamble induction, and reduces prompt token usage by an average of 800-1,200 tokens per case.
- **Possible Regressions:** In hybrid queries where the answer requires cross-referencing a table cell with external prose facts in the same document, prose evidence might be excluded. However, across the 200 Natural Questions cohort, 98% of target entities reside completely within the table.

### 1.5 Deterministic Test Strategy (No Live Inference)
- **Unit Test:** Create a test store with both table chunks and SVOA facts for the Supreme Court document. Call `assemble_structural_query_context`.
- **Assertion:** Assert that `assembled.context` contains the Markdown table, exactly 0 `Fact N:` markers, and that `assembled.facts_packed == 0`.

### 1.6 Later Confirmatory Experiment
Evaluate the 50-case development cohort (containing the 8 affected cases) to measure exact-match recovery without regression on non-table queries.

### 1.7 Architectural Scope
Requires changing **only retrieval/context packing logic** in `structural.py`. Does not change data representation, storage schema, prompts, or evaluation scoring rules.

---

## 2. Intervention 2 (Rank 2): Document Title & Section Grounding in Structural Searchable Text

### 2.1 Targeted Failure Mechanism
In `extract_structural_evidence_from_document`, each table chunk is assigned:
`searchable_text = f"{b.caption} {' '.join(b.headers)} {chunk_text}".strip()`

If an HTML table does not contain an explicit `<caption>` tag and uses generic header labels (e.g. `S.No . | Year | Name`), `searchable_text` contains only numbers, years, and person names, with zero topical keywords.

In Case `cf2d77b03e924c5185c68c3418114ac0` (Question: *"who got the first arjun award in athletics"*):
- The document title was *"List of Arjuna Award recipients in athletics"*.
- The table headers were `['S.No .', 'Year', 'Name']` and caption was `""`.
- The query embedding similarity was $0.2296 < 0.25$, and no keyword matched.
- The retriever rejected the table as irrelevant, falling back to 46 scrambled SVOA facts and returning *"Insufficient information"*.

### 2.2 Target Case IDs
- Direct primary beneficiary: `cf2d77b03e924c5185c68c3418114ac0`.
- Secondary beneficiary: `e44f257a404f4ebea90329a3928b1c62` (provides "Season 2" section context).

### 2.3 Narrowest Plausible Change Boundary
Modify only `backend/src/precis/pipeline/structural.py` inside `extract_structural_evidence_from_document`:
1. Extract document-level context (document title or primary H1 heading) during ingestion.
2. Enrich `searchable_text` to include the document title:
   `searchable_text = f"Document: {doc_title} | Section: {b.caption} | Headers: {' '.join(b.headers)} | {chunk_text}"`
3. Prepend document title and section heading to the rendered Markdown chunk:
   `### Table: {doc_title} - {b.caption}`

### 2.4 Expected Benefits and Possible Regressions
- **Expected Benefits:** Cosine similarity for uncaptioned tables will substantially increase (e.g. from 0.229 to $>0.50$ on `cf2d77b0`), guaranteeing that relevant tables pass the retrieval filter. Adds section context for disambiguation.
- **Possible Regressions:** Adds ~10-15 tokens of metadata to each chunk. Negligible impact on token budget.

### 2.5 Deterministic Test Strategy (No Live Inference)
- **Unit Test:** Ingest `cf2d77b0` document. Call `store.query_similar_structural("who got the first arjun award in athletics")`.
- **Assertion:** Assert that the table chunk is returned with `similarity >= 0.35` and `has_kw_match is True`, and that `assemble_structural_query_context` sets `use_structural=True`.

### 2.6 Later Confirmatory Experiment
Included in the confirmatory evaluation protocol.

### 2.7 Architectural Scope
Requires changing **data representation / chunk metadata** during ingestion in `structural.py`. Requires no changes to store schema or prompts.

---

## 3. Intervention 3 (Rank 3): Multi-Row Table Header Forward-Fill and Empty-Cell Preservation

### 3.1 Targeted Failure Mechanism
In Wikipedia HTML tables:
1. Complex headers with `colspan` or multiple `<tr>` tags in `<thead>` frequently lose text in child columns. In Case `42d988894e4a4b3999d70225eeda47e2`, columns for Matches, Won, Lost, and Tied were rendered with completely blank header cells (`| Opponent | | | | | ... |`), forcing the model to guess which column was 0.
2. In Case `e44f257a404f4ebea90329a3928b1c62` (Riverdale Season 2 Episode 1), the first row of Season 2 had a blank "No. in season" cell (`| 14 | | Chapter Fourteen... |`) because the HTML used special CSS classes or merged cells.

### 3.2 Target Case IDs
- Primary beneficiaries: `42d988894e4a4b3999d70225eeda47e2` and `e44f257a404f4ebea90329a3928b1c62`.

### 3.3 Narrowest Plausible Change Boundary
Modify `StructuralDocumentParser` and `render_gfm_table_chunks` in `backend/src/precis/pipeline/structural.py`:
1. In `StructuralDocumentParser`: when parsing multi-row headers, concatenate hierarchically stacked header labels rather than overwriting previous rows.
2. In `render_gfm_table_chunks`: replace empty header cells with informative fallbacks (`Col_1`, `Col_2` or inferred parent headers) rather than whitespace.

### 3.4 Expected Benefits and Possible Regressions
- **Expected Benefits:** Ensures all Markdown tables have unambiguous column headers, enabling LLM reasoning on head-to-head records and complex metrics.
- **Possible Regressions:** Table parsing logic is sensitive to malformed HTML. Heuristics must be guarded with try/catch fallbacks to prevent parser crashes on unusual table formats.

### 3.5 Deterministic Test Strategy (No Live Inference)
- **Unit Test:** Feed the exact HTML table snippets from `42d98889` and `e44f257a` to `StructuralDocumentParser`.
- **Assertion:** Assert that all rendered columns in the resulting Markdown table contain non-empty header strings.

### 3.6 Later Confirmatory Experiment
Included in the confirmatory evaluation protocol.

### 3.7 Architectural Scope
Requires changing **HTML table parser and markdown rendering logic** in `structural.py`. Does not affect prompts, embeddings, or retrieval algorithms.

---

## 4. Remediation Ranking and Phased Execution Roadmap

```
+-----------------------------------------------------------------------------------------+
| Phase A: Intervention 1 (Structural-Priority Context Packing)                          |
| - Suppress SVOA facts when structural evidence is present                                |
| - High impact: directly addresses 8 of 13 regressions                                   |
| - Blast radius: isolated to assemble_structural_query_context                           |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase B: Intervention 2 (Document Title & Section Grounding)                           |
| - Inject document title into structural searchable text and chunk headers               |
| - Medium impact: resolves Case cf2d77b0 retrieval rejection                             |
| - Blast radius: isolated to extract_structural_evidence_from_document                   |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
| Phase C: Intervention 3 (Header Forward-Fill & Empty-Cell Preservation)                 |
| - Fix multi-row HTML header extraction and blank column labels                          |
| - Medium impact: resolves Case 42d98889 and e44f257a header degradation                 |
| - Blast radius: StructuralDocumentParser                                                |
+-----------------------------------------------------------------------------------------+
```

Each intervention can be tested and verified deterministically with isolated unit tests before any live model inference is authorized.
