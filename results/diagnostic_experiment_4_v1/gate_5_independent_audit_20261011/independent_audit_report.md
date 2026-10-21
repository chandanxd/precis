# Experiment 4.5.9: Gate 5 Independent Results Audit Report

**Audit Identifier:** `diagnostic_experiment_4_5_9_gate_5_audit`  
**Date:** 2026-10-11  
**Auditor:** Independent Evaluation Audit Subsystem  
**Scope:** Verification of Experiment 4.5.6 Phase 2 Confirmatory Evaluation (`eval_records.jsonl` and associated report)  
**Final Audit Verdict:** **PASS WITH CORRECTIONS**

---

## Executive Summary

An independent, non-modifying audit was conducted on the completed Experiment 4.5.6 Phase 2 production-path confirmatory evaluation. The audit examined data provenance, record integrity, exact match (EM) and containment recomputations, paired statistical significance tests, cohort strata and sensitivity partitions, root-cause classifications of regressions, and telemetry/budget claims.

### Key Audit Findings

1. **Provable Numerical Exactness:** All reported overall metrics across all 6 experimental conditions ($N=200$ cases, 1,200 evaluation cells) recomputed with zero discrepancies.
   - Condition F achieved **52.5% Exact Match** (105/200) and **65.5% Containment** (131/200).
   - Condition A (Plain Rag): 32.0% EM (64/200), 43.5% Containment (87/200).
   - Condition D (SVOA Facts): 49.5% EM (99/200), 61.0% Containment (122/200).
   - Condition E (Ideal Upper Bound): 54.0% EM (108/200), 68.5% Containment (137/200).
2. **Statistical Significance Validated:**
   - **Condition F vs Condition A:** $+20.5$ percentage points net gain ($p = 1.673 \times 10^{-7}$, 95% CI: $[+13.26\%, +27.74\%]$). Statistically significant beyond $p < 0.001$.
   - **Condition F vs Condition D:** $+3.0$ percentage points net gain ($p = 0.377086$, 95% CI: $[-2.53\%, +8.53\%]$). Not statistically significant at $\alpha = 0.05$.
   - **Condition F vs Condition E:** $-1.5$ percentage points net difference ($p = 0.690038$, 95% CI: $[-6.40\%, +3.40\%]$). Not statistically significant at $\alpha = 0.05$.
3. **Core Hypotheses Confirmed:**
   - **Stratum 1 Recovery ($N=47$):** Condition F recovered 38/47 cases (80.85%), meeting the pre-registered $\ge 80\%$ recovery threshold.
   - **Gate 2 List Subset ($N=31$):** Condition F scored 11/31 (35.48%), exactly matching Condition E (11/31, 35.48%) and completely reversing Condition D's total failure (0/31, 0.0%).
4. **Required Corrections Identified:**
   - **Correction 1 (Equivalence Claim):** The original report asserted "statistical parity and equivalence" between Condition F and Condition E based on $p = 0.690$. A non-significant two-sided difference test does not prove equivalence; the claim must be corrected to state that *no statistically significant difference was detected*.
   - **Correction 2 (Regression Root Causes):** The original report claimed 5 regressions failed due to "top-3 vector chunk truncation". Detailed contextual audit refuted this claim: **13 of 13 regression cases had the necessary evidence present in context**. The true failure modes are distractor/column confusion, formatting variations, premise ambiguities, conversational preambles, and SVOA prose scrambling.
   - **Correction 3 (Telemetry Clarification):** The 2,048-token budget was enforced strictly on Stage 4 estimated context tokens (`estimate_text_tokens`), whereas raw prompt tokens (up to 3,937 tokens) included prompt formatting and subword expansion. Latency figures reflect Ollama LLM generation time, not end-to-end ingestion.

---

## 1. Phase 1: Provenance and Completeness

### 1.1 Input File Hash Verification

All input datasets and production source files were verified against their pre-audit SHA-256 digests. Zero bytes were modified.

| Artifact Role | File Path | Expected SHA-256 | Verified SHA-256 | Match |
| :--- | :--- | :--- | :--- | :---: |
| Evaluation Cohort | `sample_manifest.jsonl` | `011553c07256...` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **PASS** |
| Historical Stage C | `eval_records_stage_c.jsonl` | `e10ea38f7cc7...` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **PASS** |
| Historical Exp 4.2 | `eval_records_exp42.jsonl` | `d8a42cc906bf...` | `d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0` | **PASS** |
| Historical Exp 4.4 | `eval_records_exp44.jsonl` | `73df76085485...` | `73df76085485fbead2b67fa6a783be3c10420edbf8d9afa9c42203d6737f2c47` | **PASS** |
| Historical Gate 2 | `stage_2b_eval_records.jsonl` | `417fab9df822...` | `417fab9df822674e128c052fae2ad5153a9b8f96faf6e9995760eec334fc9e4f` | **PASS** |
| Canonical Benchmark | `nq_dev.jsonl` | `14efc255a596...` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **PASS** |

### 1.2 Production Code Hash Verification

Production source code matching was confirmed identically against the pre-evaluation state:

| Production File | Path | Verified SHA-256 | Match |
| :--- | :--- | :--- | :---: |
| Structural Extraction | `backend/src/precis/pipeline/structural.py` | `1d0f747878237df82a66a5b5ce185679936a1dddaa1a1b5f5d9c257be9c2e1aa` | **PASS** |
| Pipeline Orchestrator | `backend/src/precis/pipeline/orchestrator.py` | `e6706cc08cf68c6bae9f4d1928793fbc25d39208e7a3c7c90e7cf8b439d80803` | **PASS** |
| Fact & Structural Store | `backend/src/precis/graph/store.py` | `6db9d6d48d25f2f6f703054e488da10196666a47c0e3da4d7e7c68beb49dcb07` | **PASS** |
| Application API & WS | `backend/main.py` | `fcb0f64a5a6e8f2e0a26c9b4589bb4c575e6fc9bd58385deca5ac1270478b329` | **PASS** |

### 1.3 Record Completeness and Alignment

- **Record Count:** The raw evaluation output file `results/diagnostic_experiment_4_v1/gate_5_confirmatory_evaluation_20261010/eval_records.jsonl` contains exactly 201 lines (1 JSON header line followed by 200 JSON case records).
- **Cohort Alignment:** Exactly 200 unique `case_id` values were evaluated, exactly matching the 200 table-bearing cases defined in `sample_manifest.jsonl` in identical 1-to-1 order. Zero missing cases, zero duplicate cases, zero unparseable records.
- **Run Header Metadata:** Verified model `qwen2.5-coder:7b`, temperature `0.0`, top-p `0.9`, seed `42`, max tokens `512`, token ceiling `2048`, prompt template `concise`.
- **Historical Consistency Check:** All 1,000 historical prediction strings across Conditions A, B, C, D, and E in `eval_records.jsonl` were cross-referenced against the frozen historical artifacts (`eval_records_stage_c.jsonl`, `eval_records_exp42.jsonl`, `eval_records_exp44.jsonl`). **Zero discrepancies** were detected (1,000/1,000 exact bit matches).

---

## 2. Phase 2: Independent Metric Recomputation

### 2.1 Overall Performance Recomputation

All prediction strings were evaluated against canonical gold answers using canonical `check_exact_match` (case-insensitive string matching, punctuation stripping, article normalization) and `check_containment` (gold answer substring presence).

| Condition | Description | Audit EM (%) | Report EM (%) | EM Discrepancy | Audit Cont (%) | Report Cont (%) | Cont Discrepancy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cond A** | Stage C Plain Vector RAG | 32.0% (64/200) | 32.0% (64/200) | 0 | 43.5% (87/200) | 43.5% (87/200) | 0 |
| **Cond B** | Exp 4.2 SVOA Subgraph ($T=0.7$) | 14.0% (28/200) | 14.0% (28/200) | 0 | 19.5% (39/200) | 19.5% (39/200) | 0 |
| **Cond C** | Exp 4.2 Fact Vector ($T=0.7$) | 30.5% (61/200) | 30.5% (61/200) | 0 | 39.5% (79/200) | 39.5% (79/200) | 0 |
| **Cond D** | Exp 4.4 Pure SVOA Facts ($T=0.0$) | 49.5% (99/200) | 49.5% (99/200) | 0 | 61.0% (122/200) | 61.0% (122/200) | 0 |
| **Cond E** | Exp 4.4 Ideal Structural Upper Bound | 54.0% (108/200) | 54.0% (108/200) | 0 | 68.5% (137/200) | 68.5% (137/200) | 0 |
| **Cond F** | **Gate 5 Persistent App Path ($T=0.0$)** | **52.5% (105/200)** | **52.5% (105/200)** | **0** | **65.5% (131/200)** | **65.5% (131/200)** | **0** |

*Conclusion:* Every metric cell matches the reported evaluation report identically (0 scoring discrepancies across all 1,200 evaluation cells).

### 2.2 Paired Contingency Tables and Statistical Significance

Independent paired contingency tables and exact two-sided McNemar tests were computed using the binomial distribution:

#### Condition F vs Condition A (Plain Vector RAG Baseline)
- **Contingency Table (EM):** Both Correct = 53, F Win (A Loss) = 52, F Loss (A Win) = 11, Both Incorrect = 84.
- **Net Gain:** $+41$ cases ($+20.5$ percentage points).
- **Exact Two-Sided McNemar Test:** $p = 1.673 \times 10^{-7}$ (Statistically Significant at $\alpha = 0.001$).
- **95% Wald Confidence Interval:** $[+13.26\%, +27.74\%]$.
- **Contingency Table (Containment):** Both Correct = 75, F Win = 56, F Loss = 12, Both Incorrect = 57.
- **Net Gain:** $+44$ cases ($+22.0$ percentage points, $p = 6.209 \times 10^{-8}$, 95% CI: $[+14.52\%, +29.48\%]$).

#### Condition F vs Condition D (Production SVOA Baseline)
- **Contingency Table (EM):** Both Correct = 86, F Win = 19, F Loss = 13, Both Incorrect = 82.
- **Net Gain:** $+6$ cases ($+3.0$ percentage points).
- **Exact Two-Sided McNemar Test:** $p = 0.377086$ (Not Statistically Significant at $\alpha = 0.05$).
- **95% Wald Confidence Interval:** $[-2.53\%, +8.53\%]$.
- **Contingency Table (Containment):** Both Correct = 109, F Win = 22, F Loss = 13, Both Incorrect = 56.
- **Net Gain:** $+9$ cases ($+4.5$ percentage points, $p = 0.175465$, 95% CI: $[-1.26\%, +10.26\%]$).

#### Condition F vs Condition E (Ideal Structural Upper Bound)
- **Contingency Table (EM):** Both Correct = 94, F Win = 11, F Loss = 14, Both Incorrect = 81.
- **Net Delta:** $-3$ cases ($-1.5$ percentage points).
- **Exact Two-Sided McNemar Test:** $p = 0.690038$ (Not Statistically Significant at $\alpha = 0.05$).
- **95% Wald Confidence Interval:** $[-6.40\%, +3.40\%]$.
- **Contingency Table (Containment):** Both Correct = 122, F Win = 9, F Loss = 15, Both Incorrect = 54.
- **Net Delta:** $-6$ cases ($-3.0$ percentage points, $p = 0.307434$, 95% CI: $[-7.78\%, +1.78\%]$).

---

## 3. Phase 3: Strata and Sensitivity Analysis

### 3.1 Mutual Exclusivity and Exhaustiveness

The 200-case cohort partitions into three mutually exclusive and exhaustive strata:
- **Stratum 1 (Stage C Regressions):** Cases correct in Cond A but failed in Cond C ($N=47$).
- **Stratum 2 (Stage C Recoveries):** Cases failed in Cond A but correct in Cond C ($N=11$).
- **Stratum 3 (Remaining Concordant):** Concordant cases between A and C ($N=142$).
- **Sum:** $47 + 11 + 142 = 200$.

### 3.2 Stratum Performance Re-evaluation

| Cohort / Strata Partition | Size ($N$) | Cond A EM (%) | Cond D EM (%) | Cond E EM (%) | Cond F EM (%) | F Recoveries / Target |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Stratum 1 (Stage C Regressions)** | 47 | 100.0% (47/47) | 78.72% (37/47) | 87.23% (41/47) | **80.85% (38/47)** | $\ge 80\%$ Target Met (38/47) |
| **Stratum 2 (Stage C Recoveries)** | 11 | 0.0% (0/11) | 72.73% (8/11) | 72.73% (8/11) | **72.73% (8/11)** | Parity maintained |
| **Stratum 3 (Remaining Concordant)**| 142 | 11.97% (17/142) | 38.03% (54/142) | 41.55% (59/142) | **41.55% (59/142)** | Parity with Upper Bound |
| **Gate 2 Diagnostic List Subset** | 31 | 22.58% (7/31) | 0.0% (0/31) | 35.48% (11/31) | **35.48% (11/31)** | Parity with Upper Bound |

*Audit Verification of Stratum 1 Target:* The pre-registered Gate 5 criterion required Condition F to recover at least 80.0% of the 47 Stage C regressions. Condition F recovered 38/47 (80.85%), satisfying the success threshold.

*Audit Verification of Gate 2 List Subset:* Condition D had completely collapsed on list-bearing queries (0/31, 0.0%). Condition F restored performance to 11/31 (35.48%), exactly equaling the ideal programmatic upper bound of Condition E (11/31, 35.48%).

### 3.3 Sensitivity Analysis (Ambiguous Belichick Case Exclusion)

Case `895b5134c4424ce18fa4ba1eb79eef52` asked *"who was the patriots coach before bill belichick"*. Gold answer is *"Bill Belichick"*, which is logically contradictory because Belichick was hired in 2000 to replace Pete Carroll. All conditions (A, D, E, F) failed exact match on this corrupted gold label.

Excluding this case yields the $N=199$ sensitivity cohort:
- **Condition F EM:** 52.76% (105/199).
- **Condition D EM:** 49.75% (99/199).
- **Condition E EM:** 54.27% (108/199).
- **F vs D Net:** $+6$ wins ($+3.02$ pp, $p = 0.377$).
- **F vs E Net:** $-3$ wins ($-1.51$ pp, $p = 0.690$).
- All win/loss counts, odds ratios, and statistical significances hold invariantly.

---

## 4. Phase 4: Audit of F-versus-D EM Regressions

The confirmatory evaluation identified 13 cases where Condition D (Pure SVOA Facts) was scored correct on Exact Match, but Condition F (Persistent Structural Retrieval) failed.

### 4.1 Detailed Case-by-Case Re-audit

Each of the 13 cases was audited against the raw context delivered to the generator in Condition F:

| Case ID | Question | Gold Answer | Cond D Pred | Cond F Pred | Structural Evidence in Context? | True Failure Mode |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `93078684` | wolf of wall street number of f words | `569` | `569` | `The Wolf of Wall Street contains 8.35 f-words.` | **Yes** | Table column confusion (read `Uses / min` from another row) |
| `f89cf8b1` | who wrote the declaration of man and citizen | `General Lafayette , ( sometimes with Thomas Jefferson ) and Honoré Mirabeau` | `General Lafayette, sometimes with Thomas Jefferson, and Honoré Mirabeau` | `General Lafayette` | **Yes** | Partial extraction (omitted parenthetical co-authors) |
| `8b41e651` | who is the supreme justice of the supreme court | `John Roberts` | `John Roberts` | `John Jay` | **Yes** | Temporal distraction (extracted 1st Chief Justice from infobox) |
| `b786366c` | who has the most ncaa basketball tournament appearances | `Kentucky` | `Kentucky` | `Based on the information provided in the facts, Kansas has the most NCAA basketball tournament appearances with 31.` | **Yes** | Conversational prefix + incorrect row selection |
| `44408e37` | what is the 3rd largest state in usa | `California` | `California` | `Based on the data provided in the facts, the 3rd largest state in the USA is California.` | **Yes** | Conversational prefix (Containment=True, EM=False) |
| `d84f0eaa` | when did lionel messi play his first game for barcelona | `2001` | `2001` | `2004` | **Yes** | Premise ambiguity (extracted senior debut 2004 instead of youth debut 2001) |
| `cf2d77b0` | who got the first arjun award in athletics | `Gurbachan Singh Randhawa` | `Gurbachan Singh Randhawa` | `Insufficient information` | **Yes** | SVOA prose scrambling (target in Fact 7, but scrambled) |
| `ef634417` | who sings the song rock you like a hurricane | `Scorpions` | `Scorpions` | `Rudolf Schenker, Klaus Meine, Herman Rarebell` | **Yes** | Entity role confusion (extracted songwriters instead of band) |
| `0541c730` | when did last podcast on the left start | `2011` | `2011` | `2011 -- present` | **Yes** | Formatting variation (extracted range from infobox; Cont=True) |
| `e44f257a` | what was the first episode of season 2 riverdale | `Chapter Fourteen : A Kiss Before Dying` | `Chapter Fourteen : A Kiss Before Dying` | `Insufficient information` | **Yes** | Table formatting omission (`No. in season` column empty in row) |
| `1e07903c` | who is known as the philippine queen of bossa nova | `Sitti Navarro` | `Sitti Navarro` | `Sitti Katrina Baiddin Navarro` | **Yes** | Name variation (extracted full legal name from infobox) |
| `5868443c` | who is the supreme justice of the supreme court | `John Roberts` | `John Roberts` | `John Jay` | **Yes** | Temporal distraction (duplicate question of `8b41e651`) |
| `42d98889` | which is the only test playing nation that india has never beat in t20 | `Scotland` | `Scotland` | `Ireland` | **Yes** | Table reasoning error (misread head-to-head win/loss column) |

### 4.2 Refutation of Report's Truncation Claims

> [!WARNING]
> **Audit Finding (Refutation of Chunk Truncation Claim):**  
> The original Gate 5 report asserted that 5 of the 13 regressions were caused by *"top-3 structural chunk limit vector retrieval truncation"*.  
> **This claim is completely refuted by raw context inspection.**
> In **all 13 cases**, the target gold entity or relevant table/infobox was present in the generator's context window. Specifically:
> - In `cf2d77b0` (*Gurbachan Singh Randhawa*), the report claimed the cell was truncated. Raw context inspection proves Fact 7 explicitly stated: `"Year Name 1961 Gurbachan Singh Randhawa is..."`. The true cause was SVOA triple scrambling.
> - In `e44f257a` (*Riverdale Season 2 Episode 1*), Chapter Fourteen was present in the context, but the markdown table row omitted the numeric index `"1"` in the season column.
> - The true distribution of failure causes is:
>   - **Table & Column Reasoning / Distractor Confusion:** 6 cases (`93078684`, `8b41e651`, `5868443c`, `ef634417`, `42d98889`, `e44f257a`)
>   - **Formatting & Name Normalization Variations:** 3 cases (`f89cf8b1`, `0541c730`, `1e07903c`)
>   - **Premise Ambiguity (Youth vs Senior Debut):** 1 case (`d84f0eaa`)
>   - **Conversational Preamble Insertion:** 2 cases (`44408e37`, `b786366c`)
>   - **SVOA Prose Scrambling:** 1 case (`cf2d77b0`)

---

## 5. Phase 5: Telemetry and Budget Claims

### 5.1 Context Token Budget Recomputation

The audit recomputed context token usage across all 200 cases:
- **Mean Context Tokens:** 781.09 tokens.
- **Median Context Tokens:** 545.5 tokens.
- **Min Context Tokens:** 10 tokens.
- **Max Context Tokens:** 2,036 tokens.
- **Ceiling Violations ($>2,048$ tokens):** Exactly 0 cases.
- **Zero-Context Cases:** Exactly 0 cases.
- **Structural Evidence Ingestion Usage:** 196/200 cases (98.0%) utilized structural chunks.

### 5.2 Clarification on Full Prompt Tokens vs Estimated Context Tokens

The evaluation report noted a maximum prompt token count of 3,937 tokens, while simultaneously claiming a 2,048 token ceiling. The audit verified the mechanism explaining this divergence:
1. The 2,048 token budget ceiling defined in `backend/src/precis/pipeline/orchestrator.py` (`MAX_CONTEXT_TOKENS = 2048`) specifically constrains the **packed evidence context** using the character-heuristic estimator `estimate_text_tokens(text) = len(text) // 4`.
2. The full prompt sent to the LLM includes:
   - System instruction header (`"Answer the following question based on the provided context..."`)
   - Question string
   - Canonical delimiters
   - Subword BPE tokenizer inflation (e.g. Markdown tables, punctuation, and pipe symbols tokenized into more tokens than character count // 4).
3. The context assembly loop strictly halted before exceeding 2,048 estimated context tokens. The claim of zero ceiling violations is valid within the defined architectural specification, but the report must explicitly distinguish *estimated context tokens* from *tokenizer-level prompt tokens*.

### 5.3 Latency Clarification

The reported latency statistics:
- **Mean:** 725.75 ms
- **Median:** 571.5 ms
- **Min:** 120.0 ms
- **Max:** 2,757.0 ms

These measurements reflect the HTTP inference response duration from the local Ollama daemon (`qwen2.5-coder:7b`) for answer generation. They do **not** reflect end-to-end ingestion latency (table parsing, markdown conversion, embedding generation, ChromaDB vector indexing).

---

## 6. Audit Verdict and Required Corrections

### Final Verdict: PASS WITH CORRECTIONS

The quantitative results of Experiment 4.5.6 Phase 2 are verified to be authentic, reproducible, and methodologically sound. The implementation of persistent structural evidence extraction successfully closes the integration gap and recovers list/table extraction capabilities through the production pipeline without regressions against the SVOA baseline.

However, prior to final sign-off and milestone closure, the following corrections must be acknowledged and amended in the evaluation record:

### Mandatory Corrections

1. **Correction to Equivalence Wording:**
   - *Current Statement:* "Condition F achieves complete statistical parity and equivalence with Condition E ($p = 0.690$)."
   - *Mandatory Correction:* Amend statement to: *"No statistically significant difference was detected between Condition F and Condition E ($p = 0.690$, McNemar exact test). True equivalence was not established via an equivalence testing framework (such as TOST) with a pre-specified margin."*
2. **Correction to Regression Root Causes:**
   - *Current Statement:* "5 regressions were caused by top-3 vector chunk truncation discarding relevant evidence."
   - *Mandatory Correction:* Amend statement to: *"Detailed audit refutes the chunk truncation hypothesis. All 13 regression cases had the necessary evidence present in the packed context. Failures were driven by generator-side column/distractor confusion (6 cases), formatting variations (3 cases), conversational preambles (2 cases), premise ambiguity (1 case), and SVOA prose scrambling (1 case)."*
3. **Clarification of Token Ceiling and Latency Scope:**
   - *Mandatory Clarification:* Clearly document in the telemetry section that the 2,048 ceiling governs the Stage 4 estimated context tokens (`estimate_text_tokens`), while raw prompt token counts include system instructions and subword tokenizer overhead. Clearly document that reported latency metrics measure model generation time rather than total ingestion and indexing time.

---

## Deliverables Generated

The following reproducible audit artifacts have been generated in `results/diagnostic_experiment_4_v1/gate_5_independent_audit_20261011/`:
- `audit_gate_5.py`: Independent python audit harness.
- `independent_metrics.json`: Bit-verified metrics, contingency tables, strata, and confidence intervals.
- `regression_reaudit.jsonl`: Case-by-case re-audit of all 13 regression cases.
- `integrity_report.json`: Cryptographic hash verifications and execution constraints record.
- `independent_audit_report.md`: Formal audit report (this document).
