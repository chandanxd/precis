# Diagnostic Probe D.2: Markdown Table Retention with Header Preservation Report

**Précis Experiment 3 Forensic Investigation**  
**Evaluation Cohort**: Frozen 200-Case Table/List Confirmatory Stratum  
**Date**: 2026-10-10  
**Status**: Completed  
**Execution Environment**: Strict Read-Only, Sandboxed, Zero LLM / Embedding Invocations  

---

## Executive Summary & Decision Gate

Diagnostic Probe D.2 evaluated whether representing HTML tables as compact GitHub Flavored Markdown (GFM) tables—preserving header schemas, 2D relational structure, and all data rows without aggressive lexical row pruning—preserves answer-bearing evidence more reliably than the Stage C structural decompilation pipeline.

### Decision Gate Determination: `STRUCTURE RETENTION IMPROVES EVIDENCE RECALL`

```
+---------------------------------------------------------------------------------------------------------+
|                                    DECISION GATE DETERMINATION                                          |
|                                                                                                         |
|                           STRUCTURE RETENTION IMPROVES EVIDENCE RECALL                                  |
|                                                                                                         |
|  Representing tables as compact GitHub Flavored Markdown (GFM) tables preserves substantially more       |
|  answer-bearing evidence at a measured, highly predictable, and acceptable token cost.                   |
|                                                                                                         |
|  Key Evidence:                                                                                          |
|  1. Pure Representation Gain (Isolating Structure under identical threshold θ=2.0):                    |
|     - Overall Answer Retrieval Recall jumps from 31.0% (62/200) to 54.0% (108/200) (+23.0 pp).         |
|     - Stage C EM Regressions (P1) recovered jumps from 6.4% (3/47) to 57.4% (27/47) (+51.0 pp).         |
|     - Mean context tokens is 227.9 tokens (-63.2% below Condition A's 618.8 tokens; max 1,215 tokens;   |
|       zero ceiling violations).                                                                         |
|                                                                                                         |
|  2. Deep Row Truncation Resolved:                                                                        |
|     - Probe D.1 established that 26 of 47 regressions failed because row-level lexical filtering scored |
|       rows 0.0 (query keywords appeared in the table title, not the data cell), dropping the row.       |
|     - Under GFM table retention (500-token per-table cap), 100% of these rows fit naturally within      |
|       chunk boundaries. When the table is selected, row preservation is 100.0% (2,830 / 2,830 rows).   |
|                                                                                                         |
|  3. Upper-Bound Potential (Combining Structure Retention with Threshold Relaxation θ=0.0):             |
|     - When table rejection is eliminated (θ=0.0), table evidence recall reaches 167/200 (83.5%) table-  |
|       only, recovering 44 of 47 regressions (93.6%).                                                    |
|     - Adding raw list item retention achieves 200/200 (100.0%) total evidence recall and 47/47 (100.0%) |
|       regression recovery, at an average context cost of 429.6 tokens (-30.6% below Condition A).      |
+---------------------------------------------------------------------------------------------------------+
```

---

## 1. Input Verification & Provenance

Diagnostic Probe D.2 was conducted under strict non-destructive isolation. All inputs and prior experimental records were cryptographically verified prior to execution:

| File Artifact | Path | SHA-256 Checksum | Verification Status |
| :--- | :--- | :--- | :--- |
| **Sample Manifest** | `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** |
| **Stage C Eval Records** | `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** |
| **Stage D.1 Evidence Audit** | `results/diagnostic_structural_decompilation_v3/stage_d1_evidence_audit.jsonl` | `916d9ae633fba042c464ad7739f619ce38be733ef6c79b828b88a74ab5c673b7` | **MATCH** |
| **Stage D.1 Sweep Results** | `results/diagnostic_structural_decompilation_v3/stage_d1_retrieval_sweep.jsonl` | `9885b3a5b9fdf2466aba6609e9f940d4046a32fe091ddd05f42abf36f865b2b5` | **MATCH** |
| **Stage D.1 Summary** | `results/diagnostic_structural_decompilation_v3/stage_d1_summary.json` | `c312cb9aaac80e6ea56f6d90410a9e521dfedc18015f64c51b532c0d63b0e73b` | **MATCH** |
| **Evaluation Harness** | `scripts/eval_structural_decompilation_v3.py` | `ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4` | **MATCH** |
| **Evaluation Dataset** | `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** |

### Execution Safety & Constraints Compliance
- **Zero Modifications to Production Code**: `backend/src/precis/` remained completely untouched.
- **Zero Model / Embedding Invocations**: No local (Ollama) or remote language models or dense embedding models were invoked.
- **Zero Re-runs of Evaluation Harness**: Model inference accuracy was neither re-run nor inferred.
- **Frozen Cohort Invariant**: Evaluated exactly the 200 confirmatory table/list cases (47 P1 regressions, 11 P2 recoveries, 142 remaining cases).

---

## 2. Representation and Token-Budget Methodology

### Diagnostic Condition Architecture

```
                                      Source HTML Document
                                               │
                                 StructuralDocumentParser
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
                  Clean Prose                                  Structured Blocks
             (Excised prose text)                                      │
                       │                               ┌───────────────┴───────────────┐
                       │                               ▼                               ▼
                       │                         HTML Tables                      HTML Lists
                       │                               │                               │
                       │                      GFM Table Serializer            Raw List Serializer
                       │                 - Escapes pipes ('\|')            - Preserves item text
                       │                 - Unescapes entities              - Preserves item order
                       │                 - Title banner -> Caption         - Formats source tag
                       │                 - Row index column ('| Row |')    - Isolated evaluation
                       │                 - Deterministic 500-tok chunking
                       │                               │                               │
                       └───────────────────────┬───────┴───────────────────────────────┘
                                               │
                                               ▼
                               Context Packer & Simulator
                                 - Token budget: 2048 ceiling
                                 - Token metric: words * 1.3
                                 - Output packed context string
```

### Table Representation Specifications
1. **Clean Prose Excised**: Clean prose text extracted by `StructuralDocumentParser` is preserved as narrative context if present.
2. **GFM Markdown Table Syntax**:
   - Headers: Available column headers are formatted into the top header row (`| Row | Col 1 | Col 2 |`).
   - Title Banners: When the top HTML row is a single cell spanning multiple columns (typical Wikipedia infoboxes), the title is mapped to the table caption (`### Table {block_id}: {caption}`), while columns are assigned descriptive labels (`| Property | Value |`).
   - Row Mapping & Index Preservation: Every rendered row contains its exact 0-indexed source row number in the `Row` column, enabling 100% deterministic traceability.
   - Robust Escaping: Literal pipes are escaped (`|` $\to$ `\|`), newlines within cells are converted to spaces, and HTML entities (`&amp;`, `&#39;`) are decoded.
   - Column Padding: Rows with fewer cells than the table width are padded with empty cells to prevent Markdown formatting breaks.
3. **Deterministic Token-Budget Enforcement (500-Token Table Cap)**:
   - Token measurement uses the standard Précis harness formula: `int(len(text.split()) * 1.3)`.
   - If a table's serialized Markdown representation exceeds 500 tokens, it is split into contiguous row chunks.
   - Each chunk repeats the full table title, column header line, and separator line (`[Rows start-end]`), ensuring self-contained schema comprehension.
4. **Primary Selection Isolation ($\theta=2.0$)**:
   - To strictly isolate the effect of *representation* from *threshold relaxation*, the primary Condition D2 evaluation applies the exact same table selection policy as Condition B (`score_and_select_tables` with threshold $\ge 2.0$ or infobox rule).
   - Secondary ablations evaluate list integration and threshold relaxation ($\theta=0.0$).

---

## 3. Comprehensive Experimental Results

### Comparative Performance Matrix

| Metric / Cohort | Condition A (Reference) | Condition B (Stage C Baseline) | Diagnostic Probe D.1 (Best $\theta=0.0, K=15$) | Condition D2 (Primary: Table-Only, $\theta=2.0$) | Condition D2 (+ Lists, $\theta=2.0$) | Condition D2 (Relaxed: Table-Only, $\theta=0.0$) | Condition D2 (Relaxed + Lists, $\theta=0.0$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Table Representation** | Raw Prose SVOA | SVOA Triples (Top-5 Rows) | SVOA Triples (Top-15 Rows) | **GFM Markdown Tables** | **GFM Markdown Tables** | **GFM Markdown Tables** | **GFM Markdown Tables** |
| **Table Threshold ($\theta$)** | N/A | 2.0 | 0.0 | **2.0 (Matched)** | **2.0 (Matched)** | 0.0 | 0.0 |
| **Row Selection Policy** | N/A | Top-5 Lexical Overlap | Top-15 Lexical Overlap | **All Rows (500-tok Cap)** | **All Rows (500-tok Cap)** | **All Rows (500-tok Cap)** | **All Rows (500-tok Cap)** |
| **List Representation** | Raw Prose SVOA | Proposition Regex | Proposition Regex | None (Excised) | **Raw List Items** | None (Excised) | **Raw List Items** |
| **Total Cases Evaluated** | 200 | 200 | 200 | **200** | **200** | **200** | **200** |
| **Answer in Packed Context** | *(43.5% Cont)* | 62 / 200 (31.0%) | 113 / 200 (56.5%) | **108 / 200 (54.0%)** | **141 / 200 (70.5%)** | **167 / 200 (83.5%)** | **200 / 200 (100.0%)** |
| **$\Delta$ Recall vs. Baseline B** | +12.5 pp *(Cont)* | 0.0 pp | +25.5 pp | **+23.0 pp** | **+39.5 pp** | **+52.5 pp** | **+69.0 pp** |
| **P1 Regressions ($N=47$)** | 47 / 47 (100%) | 3 / 47 (6.4%) | 18 / 47 (38.3%) | **27 / 47 (57.4%)** | **30 / 47 (63.8%)** | **44 / 47 (93.6%)** | **47 / 47 (100.0%)** |
| **P2 Recoveries ($N=11$)** | 0 / 11 (0.0%) | 11 / 11 (100%) | 11 / 11 (100%) | **10 / 11 (90.9%)**\* | **11 / 11 (100.0%)** | **10 / 11 (90.9%)**\* | **11 / 11 (100.0%)** |
| **Remaining Cases ($N=142$)** | -- | 48 / 142 (33.8%) | 84 / 142 (59.2%) | **71 / 142 (50.0%)** | **100 / 142 (70.4%)** | **113 / 142 (79.6%)** | **142 / 142 (100.0%)** |
| **Mean Context Tokens** | **618.8** | **155.4** | **266.3** | **227.9** | **277.7** | **379.8** | **429.6** |
| **Median Context Tokens** | 584 | 65 | 148 | **109** | **191** | **289** | **314** |
| **P95 Context Tokens** | 1,240 | 612 | 936 | **909** | **937** | **1,097** | **1,097** |
| **Max Context Tokens** | 1,878 | 1,213 | 1,878 | **1,215** | **1,215** | **1,343** | **1,343** |
| **Zero-Context Cases** | 0 | 71 | 12 | **90** | **59** | **31** | **0** |
| **Ceiling Violations (>2048)**| 0 | 0 | 0 | **0** | **0** | **0** | **0** |

*\*Note: In Condition D2 Table-Only, 1 recovery (`00d7c7cc7b534abeaf1f9dded1d3639b`) is situated exclusively inside an HTML list (`tbls=0, lists=1`). When lists are retained, P2 recall is 11/11 (100.0%).*

---

## 4. Deep-Dive: Why Markdown Table Retention Outperforms Lexical Row Selection

### The Flaw of Lexical Row Ranking in Stage C and D.1
In Stage C (and even in Probe D.1 with $K=15$), table rows were ranked by lexical keyword overlap between the query and cell text. This created a systematic failure mode:
1. **The Row-Context Decoupling Problem**: In Wikipedia tables, the entity or topic name (*"Korn"*, *"The Breakfast Club"*, *"Wilt Chamberlain"*) appears in the article title or table header, while individual rows contain data attributes without repeating the entity name.
2. **Artificial Zero-Scoring**: In `rank_table_rows()`, rows with zero query word matches were scored `0.0`. The harness rule `selected = [r for r in scored_rows if r.score > 0][:max_selected_rows]` discarded zero-scoring rows completely—even if only 3 or 4 rows had score $>0$. Expanding the budget from 5 to 15 or "All" never selected these rows because their score was not $>0$.

### How Markdown Retention Solves the Problem
1. **Preservation of Row Context**: By serializing rows as contiguous table lines under the table caption, the relationship between table entity and row data is preserved in natural Markdown syntax.
2. **Compact Token Economy**: The average GFM table in this corpus contains 17.3 rows and serializes to just **168.4 tokens**. A 500-token budget comfortably fits **100% of all rows** in 91.5% of tables without any chunking.
3. **100% Row Preservation**: Across all 164 source tables in the 200 cases, exactly **2,830 out of 2,830 rows (100.0%)** were rendered and mapped directly to their source row indices. Zero rows were lost to truncation or parsing failure.

### Representative Case Studies (Regressions Recovered by Condition D2 Primary)

```
Case ID: 01b62b5fd83f43c9b64aad4a286d8247
Question: "when did korn 's follow the leader come out"
Gold Answer: "August 18 , 1998"
Stage C Baseline (B): FAILED (Row 2 discarded; score 0.0; facts = 5)
Probe D.1 (K=15):     FAILED (Row 2 discarded; score 0.0; facts = 5)
Condition D2 Primary: RECOVERED (Full 16-row GFM table serialized in 118 tokens; Row 2 intact)
Rendered Excerpt:
  ### Table 0: Follow the Leader [Rows 0-15]
  | Row | Property | Value |
  | --- | --- | --- |
  | 0 | Studio album by | Korn |
  | 1 | Recorded | March -- May 1998 |
  | 2 | Released | August 18 , 1998 |

Case ID: 422fb6cb1e94484eb3d965376f8efa18
Question: "who wrote hit me baby one more time"
Gold Answer: "Max Martin"
Stage C Baseline (B): FAILED (Row 10 discarded; score 0.0)
Probe D.1 (K=15):     FAILED (Row 10 discarded; score 0.0)
Condition D2 Primary: RECOVERED (Full 21-row GFM table serialized in 184 tokens; Row 10 intact)
Rendered Excerpt:
  ### Table 0: `` ... Baby One More Time '' [Rows 0-20]
  | Row | Property | Value |
  | --- | --- | --- |
  | 10 | Songwriter ( s ) | Max Martin |
  | 11 | Producer ( s ) | Max Martin Rami |

Case ID: 3f0497f4a228459c8b2201e7f871a520
Question: "where was gunsmoke to the last man filmed"
Gold Answer: "Tucson , Arizona"
Stage C Baseline (B): FAILED (Row 9 discarded; score 0.0)
Probe D.1 (K=15):     FAILED (Row 9 discarded; score 0.0)
Condition D2 Primary: RECOVERED (Full 17-row GFM table serialized in 142 tokens; Row 9 intact)
Rendered Excerpt:
  ### Table 0: Gunsmoke : To the Last Man [Rows 0-16]
  | Row | Property | Value |
  | --- | --- | --- |
  | 9 | Location ( s ) | Tucson , Arizona |
```

---

## 5. Granular Cohort Analysis: Regressions, Recoveries, and Remaining Cases

### Cohort 1: Stage C Regressions (P1: 47 Cases)
- **Condition B Baseline ($\theta=2.0, K=5$)**: 3 / 47 (6.4%) answer recall.
- **Probe D.1 Maximum ($\theta=0.0, K=15$)**: 18 / 47 (38.3%) answer recall.
- **Condition D2 Primary (Table-Only, $\theta=2.0$)**: **27 / 47 (57.4%) answer recall** (+24 regressions recovered over Baseline B, +9 regressions recovered over D.1 best).
- **Condition D2 (+ Lists, $\theta=2.0$)**: **30 / 47 (63.8%) answer recall** (+27 regressions recovered).
  - The remaining 17 regressions were missed solely because `score_and_select_tables()` rejected the table at $\theta=2.0$.
- **Condition D2 Relaxed ($\theta=0.0$)**: **44 / 47 (93.6%) table-only**, and **47 / 47 (100.0%) with lists**!
  - Every single one of the 44 table-bearing regressions and 3 list-bearing regressions is preserved.

### Cohort 2: Stage C Recoveries (P2: 11 Cases)
- **Condition B Baseline**: 11 / 11 (100.0%) answer recall.
- **Condition D2 Primary (Table-Only)**: 10 / 11 (90.9%). Case `00d7c7cc7b534abeaf1f9dded1d3639b` (*"who plays chris grandy in 13 going on 30"*) is in a list-only document (`tbls=0`).
- **Condition D2 (+ Lists)**: **11 / 11 (100.0%)**. Retaining lists maintains all 11 recoveries with zero regressions.

### Cohort 3: Remaining Cases (142 Cases)
- **Condition B Baseline**: 48 / 142 (33.8%) answer recall.
- **Probe D.1 Maximum**: 84 / 142 (59.2%) answer recall.
- **Condition D2 Primary (Table-Only)**: **71 / 142 (50.0%) answer recall**.
- **Condition D2 (+ Lists)**: **100 / 142 (70.4%) answer recall**.
- **Condition D2 Relaxed (+ Lists)**: **142 / 142 (100.0%) answer recall**.

---

## 6. Isolating the List Problem (Section 6 Findings)

In Probe D.1, three specific regression cases were diagnosed as list extractor regex failures:
1. `363edbaa51694fedbd2a264c881f23a1`: *"what part of maryland is close to washington dc"* $\to$ Gold answer: *"Calvert County"*
2. `3d3088e34ece49d8b9850f44ff05c029`: *"who plays big momma in big mommas house"* $\to$ Gold answer: *"Martin Lawrence"*
3. `c530f07f4ff040f5925b9a3599d9fb19`: *"who plays the queen in victoria and abdul"* $\to$ Gold answer: *"Judi Dench"*

### Findings:
- The rule-based regex in `extract_list_propositions()` discarded these items because it strictly searched for `^[*-]\s*(.+)` with `Key - Value` hyphens. Cast lists (`Actor as Role`) and county lists failed this pattern.
- In Condition D2, raw list items were preserved verbatim with source location markers (`- [Item N]: {text}`).
- **Result**: **All 3 of these regressions were 100% recovered** in context (`30 / 47` total P1 recall under $\theta=2.0$; `47 / 47` under $\theta=0.0$).
- Raw list preservation adds an average of only **49.8 tokens** per document across the 35 list-bearing cases.

---

## 7. Token Overhead & Trade-off Analysis

```
                              Mean Context Tokens vs. Recall
  Tokens
   700 +---------------------------------------------------------------+
       |                                                               |
   600 |  * Cond A (618.8 tok, 43.5% Cont)                             |
       |                                                               |
   500 |                                                               |
       |                                  * D2 Relaxed+List (429.6 tok, 100% Rec)
   400 |                                  * D2 Relaxed (379.8 tok, 83.5% Rec)
       |
   300 |                      * D2+List (277.7 tok, 70.5% Rec)
       |                      * D1 Best (266.3 tok, 56.5% Rec)
   200 |  * D2 Primary (227.9 tok, 54.0% Rec)
       |  * Cond B (155.4 tok, 31.0% Rec)
   100 +---------------------------------------------------------------+
          Baseline (θ=2.0)         Hybrid                    Relaxed (θ=0.0)
```

1. **Substantial Compression Maintained**:
   Condition D2 Primary achieves **54.0% recall** at **227.9 mean tokens**, saving **390.9 tokens per query (-63.2%)** compared to Condition A (618.8 tokens).
2. **Predictable Linear Scaling**:
   Even under the fully unconstrained configuration ($\theta=0.0$, tables + lists), mean context tokens is **429.6 tokens**, which remains **30.6% below Condition A**.
3. **Zero Context Window Risk**:
   The maximum context length observed across all 200 cases and all conditions was **1,343 tokens**, far below the 2048-token context window. Zero cases experienced ceiling truncation.

---

## 8. Summary of Conversion Audit Metrics

From `stage_d2_table_conversion_audit.jsonl` (164 source tables):
- **Total Source Tables**: 164
- **Successful Conversions**: 164 (100.0%)
- **Conversion Failures**: 0 (0.0%)
- **Total Source Rows**: 2,830
- **Total Rendered Rows**: 2,830 (100.0% row preservation rate)
- **Header Classification**:
  - `TITLE_BANNER_TO_CAPTION`: 99 tables (60.4%)
  - `PRESERVED_EXPLICIT`: 63 tables (38.4%)
  - `GENERATED_DEFAULT`: 2 tables (1.2%)
- **Answer-Bearing Tables**: 158 of 164 tables contained gold answer evidence.
- **Answer Retention in Converted Chunks**: 158 of 158 (100.0%).

---

## 9. Next Steps & Smallest Next Experiment Recommendation

Having conclusively proven that GFM Markdown table representation resolves the evidence loss crisis of Stage C without token bloat, the path forward is clear:

### Recommended Experiment: Experiment 4 (End-to-End LLM Generation Pilot)
1. **Objective**: Measure actual language model generation accuracy (Exact Match and Answer Containment) using GFM Markdown tables versus Naive RAG (Condition A) and Structural Decompilation (Condition B).
2. **Pilot Cohort**: A targeted 50-case pilot cohort drawn from the 47 P1 regressions and 11 P2 recoveries.
3. **Candidate Configurations**:
   - Condition A (Reference Naive RAG)
   - Condition B (Stage C Baseline)
   - Condition D2.1 (GFM Markdown Tables + Raw Lists with Adaptive Table Selection $\theta=1.0$)
4. **Hypothesis**: Condition D2.1 will restore Exact Match to $\ge 32.0\%$ (matching or exceeding Condition A) while maintaining a $\ge 50\%$ reduction in context tokens.

---

## Artifact Inventory & Cryptographic Hashes

All newly generated diagnostic artifacts in `results/diagnostic_structural_decompilation_v3/`:

| Artifact Path | SHA-256 Checksum | Description |
| :--- | :--- | :--- |
| `stage_d2_case_audit.jsonl` | `2e13ccec907f7e5db2d0e5c229dbc283db00c2cc2c68e85e6a793858c03af470` | Case-level audit across all 200 cases and all 4 conditions |
| `stage_d2_table_conversion_audit.jsonl` | `05414212fa8b7a571512a1282a9530de32b7bdf9a5e59cfbf022ecf84341d430` | Table-level audit for all 164 source tables (100% conversion verified) |
| `stage_d2_summary.json` | `00b97c858c346691282bb29c482deb1a13461b80ebfb43f95fd002a872fea6a8` | Reconciled summary statistics, token distributions, and cohort breakdowns |
| `stage_d2_walkthrough.md` | `379a49ef018be40c49442cd77e0651d78809cc6946e2288ccd0a420e8b32fca7` | Reviewer walkthrough guide and reproducible verification commands |
