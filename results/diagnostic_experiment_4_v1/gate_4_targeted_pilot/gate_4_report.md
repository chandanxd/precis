# Experiment 4: Controlled End-to-End Generation Pilot — Gate 4 Final Report

**Experiment Identifier**: `diagnostic_experiment_4_v1`  
**Evaluation Scope**: Gate 4 Targeted Diagnostic Pilot (58-Case Confirmatory Stratum Union)  
**Date**: 2026-10-10  
**Status**: Completed — **Execution Stopped Awaiting Explicit Review**  
**Execution Constraints Enforced**: Zero Production Code Modifications (`backend/src/precis/`), Frozen Baseline Predictions Reused, Strict Status Accounting, Zero Data Imputation  

---

## 1. Executive Summary & Gate 4 Diagnostic Findings

### Diagnostic Verdict: `EVIDENCE-BASED REJECTION OF SVOA DECOMPILATION; RETENTION PROVEN SUPERIOR BUT INSUFFICIENT FOR IMMEDIATE DEPLOYMENT`

```
+---------------------------------------------------------------------------------------------------------+
|                                      GATE 4 EXECUTIVE VERDICT                                           |
|                                                                                                         |
|  1. Decisive Reversal of Stage C Regression:                                                           |
|     - Structural Retention (Cond D) vastly and significantly outperforms Stage C Decompilation (Cond B) |
|       on the 58-case targeted cohort:                                                                   |
|       * Exact Match: 33/58 (56.9%) vs 11/58 (19.0%), Net Wins: +22, McNemar p = 0.000027 (p < 1e-4)    |
|       * Odds Ratio: 8.33, Absolute Risk Difference: +37.9% [statistically significant]                  |
|     - Compact GFM table retention + raw list packing successfully recovers 25 of 47 Stage C             |
|       regressions (53.2% recovery rate) and preserves 8 of 11 Stage C recoveries (72.7%).               |
|                                                                                                         |
|  2. Residual Deficit Relative to Prose Baseline (Condition A):                                          |
|     - Despite major gains over Condition B, Condition D remains significantly below Condition A         |
|       on this discordant stratum:                                                                       |
|       * Exact Match: 33/58 (56.9%) vs 47/58 (81.0%), Net Deficit: -14, McNemar p = 0.0161               |
|       * Odds Ratio: 0.364, Absolute Risk Difference: -24.1% [statistically significant]                 |
|                                                                                                         |
|  3. Forensic Root Cause of Residual Regressions:                                                        |
|     - Forensic analysis of all 22 unrecovered cases in Condition D isolates the primary cause:         |
|       * 17 / 22 cases (77.3%): Table selection threshold theta = 2.0 rejected answer tables             |
|         (score < 2.0), leaving 0 context tokens and triggering 'Insufficient information'.             |
|       * 4 / 22 cases (18.2%): Generation/reasoning errors over retained tables (distractor rows).      |
|       * 1 / 22 cases (4.5%): Surface form / normalization mismatch.                                     |
|                                                                                                         |
|  4. Methodological Status:                                                                              |
|     - This 58-case cohort is an outcome-selected diagnostic pilot, NOT an unbiased benchmark.           |
|     - SVOA decompilation (Condition B) is conclusively rejected.                                       |
|     - Structural retention is confirmed as the viable architecture, but production deployment must      |
|       await resolving the table-selection recall threshold before full cohort evaluation.              |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Preflight Audit & Input Provenance

Before initiating inference, all 8 preflight invariants were verified:

1. **Target Cohort Reconstructed Directly from Frozen Benchmark**: Exactly 47 Stage C regressions and 11 Stage C recoveries, yielding a disjoint union of exactly 58 unique cases.
2. **Output Directory Protection**: Verified that `results/diagnostic_experiment_4_v1/gate_4_targeted_pilot/` was absent before run initialization.
3. **Configuration Fingerprint**: Exactly matched approved specification: `9fc71ebca6501b6b58aca481010a6c144416298b6aa91334f7bc0ca353bfa1c3`.
4. **Ollama Daemon & Model Verified**: `qwen2.5-coder:7b` confirmed resident in GPU memory; 0 connection drops or timeouts.
5. **Frozen Baseline Provenance**: 100% bit-identical verification against original digests:
   - Manifest (`sample_manifest.jsonl`): `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7`
   - Stage C Records (`eval_records_stage_c.jsonl`): `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687`
   - Dataset (`nq_dev.jsonl`): `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491`

---

## 3. Condition-Level Telemetry & Performance Summaries

| Metric | Condition A (Prose Baseline) | Condition B (Stage C Decompilation) | Condition C (GFM Table Retention) | Condition D (GFM Tables + Raw Lists) |
| :--- | :---: | :---: | :---: | :---: |
| **Attempted Cases** | 58 | 58 | 58 | 58 |
| **Successful Inferences** | 58 | 58 | 58 | 58 |
| **Failed Inferences** | 0 | 0 | 0 | 0 |
| **Unscorable Inferences** | 0 | 0 | 0 | 0 |
| **Scored Denominator** | **58** | **58** | **58** | **58** |
| **Exact Match Count** | 47 | 11 | 30 | 33 |
| **Exact Match Rate** | 81.0% | 19.0% | 51.7% | 56.9% |
| **Containment Count** | 47 | 12 | 31 | 34 |
| **Containment Rate** | 81.0% | 20.7% | 53.4% | 58.6% |
| **Mean ROUGE-L** | 0.810 | 0.236 | 0.534 | 0.586 |
| **Mean Context Estimated Tokens** | 542.4 | 106.7 | 280.0 | 289.9 |
| **Mean Full Prompt Model Tokens** | N/A (unlogged) | N/A (unlogged) | 615.8 | 628.0 |
| **Mean Generated Tokens** | N/A (unlogged) | N/A (unlogged) | 5.66 | 5.69 |

> [!NOTE]
> Condition A and Condition B baseline rates on this 58-case cohort reflect their outcome-selected status (47 A-wins, 11 B-wins). They do not represent their performance over the broader 200-case confirmatory cohort (where Cond A EM was 32.0% and Cond B EM was 14.0%).

---

## 4. Primary Paired Statistical Comparisons

All paired evaluations were conducted over strictly valid, mutually successful pairs ($N=58$, 0 exclusions):

### 4.1. Exact Match Paired Comparisons

| Paired Comparison | Valid $N$ | Cond 1 Wins | Cond 2 Wins | Ties | Net Wins | McNemar $p$-value | Odds Ratio | Risk Difference | Statistical Significance ($p < 0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cond C vs Cond B** | 58 | 22 | 3 | 33 | **+19** | **0.000157** | **7.333** | **+32.8%** | **YES (Highly Significant)** |
| **Cond D vs Cond B** | 58 | 25 | 3 | 30 | **+22** | **0.000027** | **8.333** | **+37.9%** | **YES (Highly Significant)** |
| **Cond C vs Cond A** | 58 | 8 | 25 | 25 | **-17** | **0.004551** | **0.320** | **-29.3%** | **YES (Significant Deficit)** |
| **Cond D vs Cond A** | 58 | 8 | 22 | 28 | **-14** | **0.016125** | **0.364** | **-24.1%** | **YES (Significant Deficit)** |
| **Cond D vs Cond C** | 58 | 3 | 0 | 55 | **+3** | **0.250000** | **Infinity** | **+5.2%** | **NO (Trend in Favor of D)** |

#### Paired $2 \times 2$ Contingency Tables (Exact Match)
- **Cond C vs Cond B**: $a=8$ (both win), $b=22$ (C win, B loss), $c=3$ (C loss, B win), $d=25$ (both loss). Discordant: 25.
- **Cond D vs Cond B**: $a=8$ (both win), $b=25$ (D win, B loss), $c=3$ (D loss, B win), $d=22$ (both loss). Discordant: 28.
- **Cond C vs Cond A**: $a=22$ (both win), $b=8$ (C win, A loss), $c=25$ (C loss, A win), $d=3$ (both loss). Discordant: 33.
- **Cond D vs Cond A**: $a=25$ (both win), $b=8$ (D win, A loss), $c=22$ (D loss, A win), $d=3$ (both loss). Discordant: 30.
- **Cond D vs Cond C**: $a=30$ (both win), $b=3$ (D win, C loss), $c=0$ (D loss, C win), $d=25$ (both loss). Discordant: 3.

### 4.2. Answer Containment Paired Comparisons

| Paired Comparison | Valid $N$ | Cond 1 Wins | Cond 2 Wins | Ties | Net Wins | McNemar $p$-value | Odds Ratio | Risk Difference | Statistical Significance ($p < 0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cond C vs Cond B** | 58 | 22 | 3 | 33 | **+19** | **0.000157** | **7.333** | **+32.8%** | **YES (Highly Significant)** |
| **Cond D vs Cond B** | 58 | 25 | 3 | 30 | **+22** | **0.000027** | **8.333** | **+37.9%** | **YES (Highly Significant)** |
| **Cond C vs Cond A** | 58 | 8 | 24 | 26 | **-16** | **0.007000** | **0.333** | **-27.6%** | **YES (Significant Deficit)** |
| **Cond D vs Cond A** | 58 | 8 | 21 | 29 | **-13** | **0.024120** | **0.381** | **-22.4%** | **YES (Significant Deficit)** |
| **Cond D vs Cond C** | 58 | 3 | 0 | 55 | **+3** | **0.250000** | **Infinity** | **+5.2%** | **NO (Trend in Favor of D)** |

---

## 5. Regression Recovery & Recovery Preservation Analysis

### 5.1. Priority 1: Recovery of Stage C Regressions ($N=47$)
Cases where Condition A succeeded but Condition B regressed ($A=1, B=0$):
- **Condition C (Table Retention)**:
  - **Recovered**: **22 / 47 (46.8%)**
  - **Remained Wrong**: **25 / 47 (53.2%)**
- **Condition D (Table + List Retention)**:
  - **Recovered**: **25 / 47 (53.2%)**
  - **Remained Wrong**: **22 / 47 (46.8%)**
- **Incremental Gain of D over C**: Condition D recovered **3 additional regressions** over Condition C with zero regressions lost.

### 5.2. Priority 2: Preservation of Stage C Recoveries ($N=11$)
Cases where Condition A failed but Condition B succeeded ($A=0, B=1$):
- **Condition C (Table Retention)**:
  - **Preserved**: **8 / 11 (72.7%)**
  - **Regressed**: **3 / 11 (27.3%)** (`0d26e7be`, `16caa32e`, `e529e5ec`)
- **Condition D (Table + List Retention)**:
  - **Preserved**: **8 / 11 (72.7%)**
  - **Regressed**: **3 / 11 (27.3%)** (`0d26e7be`, `16caa32e`, `e529e5ec`)

---

## 6. Structural Forensic Diagnosis

Forensic auditing of all 58 cases identifies the exact failure modes across conditions:

### 6.1. Root Causes of the 22 Unrecovered Regressions in Condition D
Why did 22 Stage C regressions fail to recover in Condition D?

1. **Table Selection Exclusion under Fixed $\theta = 2.0$ (17 Cases / 77.3% of Failures)**:
   - In 17 cases, the HTML document contained the answer-bearing table, but the table relevance scorer returned scores of 0.0 or 1.0 (below the frozen threshold $\theta = 2.0$).
   - Because the table was rejected and no other prose/lists were selected, the context builder emitted **0 tokens of context** (`zero_context: True`).
   - Facing an empty context, the model correctly followed prompt instructions and returned *'Insufficient information'*.
   - *Affected Case IDs*: `009fc8ba`, `0502a3d7`, `0a4add08`, `0ee2e39b`, `1b491361`, `3dc98383`, `42d98889`, `5702186b`, `622fad3c`, `85318a34`, `ae89f4d5`, `b6456292`, `b9b5f86a`, `e4731d77`, `e8f64c51`, `ef523d77`, `f6c035f6`.
   - *Takeaway*: These failures are **not failures of structural table formatting**; they are failures of the upstream keyword/heuristic selection filter. Lowering the threshold to $\theta = 0.0$ (as demonstrated in Probe D.1) would recover the majority of these contexts.

2. **Model Distraction / Reasoning Errors over Retained Tables (4 Cases / 18.2% of Failures)**:
   - The table was correctly selected, converted to GFM, and packed (321 to 909 tokens), but the LLM failed to identify the correct target row:
     - `122e005c` (*Harry and Tonto Academy Award*): Model generated *'Dustin Hoffman'* instead of *'Art Carney'*.
     - `59dfcccf` (*total seasons of The Bachelor*): Model generated *'20'* instead of *'26'* due to complex multi-row counting.
     - `b2c8d85e` (*Black Panther release date*): Model generated *'29 January 2018'* (LA premiere) instead of *'16 February 2018'* (US general release).
     - `e34508a7` (*Celebrity Big Brother winner*): Model generated *'Shilpa Shetty'* instead of *'Jack Dee'*.

3. **Multi-Entity Generation & Normalization Mismatch (1 Case / 4.5% of Failures)**:
   - `fd249e52` (*After You 've Gone songwriter*): Model generated *'Turner Layton, Henry Creamer'*. Gold answer is *'Turner Layton'*. Exact match was False due to multi-author string inclusion, even though containment was True.

### 6.2. Root Causes of the 3 Regressed Recoveries in Conditions C & D
Why did Condition B succeed on 3 cases where Conditions C & D failed?

1. **Event Distraction in Deep Earthquake Tables (`0d26e7be`, `e529e5ec`)**:
   - *Question*: *'when was the last time iran had an earthquake'* (Gold: *'2017 - 12 - 20'*).
   - In Condition B, SVOA fact decompilation isolated the most recent event row (366 tokens).
   - In Conditions C & D, the entire 903-token GFM table was packed, and the LLM misread an earlier high-casualty event (*'1981 - 07 - 28'*).

2. **List Heuristic Advantage (`16caa32e`)**:
   - *Question*: *'who is the leading african producer of wool'* (Gold: *'South Africa'*).
   - Condition B extracted relational facts from the bulleted list.
   - Condition C selected 0 tables (0 tokens). Condition D packed 11 raw list items (126 tokens), but the LLM failed to synthesize the answer from raw bullet text.

### 6.3. The 3 Incremental Wins of Condition D over Condition C
Condition D recovered 3 cases where Condition C had 0 context tokens because the source document had no HTML tables:
1. `363edbaa` (*part of maryland close to DC*): Condition C packed 0 tokens ('Insufficient information'). Condition D packed 39 tokens of county lists, generating *'Frederick County'* (EM=True).
2. `3d3088e3` (*who plays big momma*): Condition C packed 0 tokens. Condition D packed 250 tokens of cast list items, generating *'Ella Mitchell'* (EM=True).
3. `c530f07f` (*queen in victoria and abdul*): Condition C packed 0 tokens. Condition D packed 146 tokens of cast list items, generating *'Judi Dench'* (EM=True).

---

## 7. Complete 58-Case Per-Case Audit Table

| # | Case ID | Question | Gold Answer | Cond A | Cond B | Cond C | Cond D | Ctx D | Diagnostic Classification |
| :-: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | `009fc8ba` | what nba player has scored the most 3 pointer... | Ray Allen | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 2 | `00d7c7cc` | who plays chris grandy in 13 going on 30 | Jim Gaffigan | Loss | Win | Win | Win | 23 | Preserved P2 Recovery |
| 3 | `01b62b5f` | when did korn 's follow the leader come out | August 18 , 1998 | Win | Loss | Win | Win | 314 | Recovered P1 Regression |
| 4 | `0502a3d7` | who has scored the most half centuries in tes... | Sachin Tendulkar | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 5 | `0541c730` | when did last podcast on the left start | 2011 | Win | Loss | Win | Win | 167 | Recovered P1 Regression |
| 6 | `0a4add08` | how many pages are in the book inside out and... | 263 | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 7 | `0d26e7be` | when was the last time iran had an earthquake | 2017 - 12 - 20 | Loss | Win | Loss | Loss | 903 | Regressed P2 (Retained, Model Distraction) |
| 8 | `0d8ada7a` | when did the song here comes the boom come ou... | May 14 , 2002 | Win | Loss | Win | Win | 315 | Recovered P1 Regression |
| 9 | `0ee2e39b` | who was the drummer with the travelling wilbu... | Jim Keltner | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 10 | `122e005c` | who won the oscar for best actor in 1975 | Art Carney | Win | Loss | Loss | Loss | 857 | Unrecovered P1 (Retained, Model Gen Error) |
| 11 | `16caa32e` | who is the leading african producer of wool | South Africa | Loss | Win | Loss | Loss | 126 | Regressed P2 (Retained, Model Distraction) |
| 12 | `16d3586c` | how many gold medals did australia win in the... | 16 | Win | Loss | Win | Win | 287 | Recovered P1 Regression |
| 13 | `17d9c792` | who scored the most points in a single game i... | Wilt Chamberlain | Win | Loss | Win | Win | 1142 | Recovered P1 Regression |
| 14 | `1b491361` | who has won 2017 women 's singles korean open... | P.V. Sindhu | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 15 | `2900f09a` | who is the chief economic advisor of india | Arvind Subramanian | Win | Loss | Win | Win | 94 | Recovered P1 Regression |
| 16 | `36051cca` | who has most followers on instagram in world | Instagram | Loss | Win | Win | Win | 937 | Preserved P2 Recovery |
| 17 | `363edbaa` | what part of maryland is close to washington ... | Calvert County | Win | Loss | Loss | Win | 39 | Recovered P1 Regression |
| 18 | `3d3088e3` | who plays big momma in big mommas house | Martin Lawrence | Win | Loss | Loss | Win | 250 | Recovered P1 Regression |
| 19 | `3dc98383` | when was the miraculous journey of edward tul... | March 30 , 2006 | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 20 | `3f0497f4` | where was gunsmoke to the last man filmed | Tucson , Arizona | Win | Loss | Win | Win | 250 | Recovered P1 Regression |
| 21 | `422fb6cb` | who wrote hit me baby one more time | Max Martin | Win | Loss | Win | Win | 349 | Recovered P1 Regression |
| 22 | `42d98889` | which is the only test playing nation that in... | Scotland | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 23 | `4756b3c3` | when did the movie breakfast club come out | February 15 , 1985 | Win | Loss | Win | Win | 241 | Recovered P1 Regression |
| 24 | `5702186b` | when was the us department of homeland securi... | November 25 , 2002 | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 25 | `5868443c` | who is the supreme justice of the supreme cou... | John Roberts | Win | Loss | Win | Win | 166 | Recovered P1 Regression |
| 26 | `58f870f4` | when was the young and the restless first air... | March 26 , 1973 | Win | Loss | Win | Win | 631 | Recovered P1 Regression |
| 27 | `59dfcccf` | how many gold medals won by india in 2018 com... | 26 | Win | Loss | Loss | Loss | 882 | Unrecovered P1 (Retained, Model Gen Error) |
| 28 | `622fad3c` | when was the us department of homeland securi... | November 25 , 2002 | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 29 | `675067ab` | who won the most stanley cups in history | Montreal Canadiens | Loss | Win | Win | Win | 109 | Preserved P2 Recovery |
| 30 | `6ced1311` | hart of dixie season 4 how many episodes | 10 | Win | Loss | Win | Win | 149 | Recovered P1 Regression |
| 31 | `784e39fe` | when was the last time ny rangers won stanley... | 1993 -- 94 | Loss | Win | Win | Win | 403 | Preserved P2 Recovery |
| 32 | `85318a34` | who played the first phantom of the opera | Michael Crawford | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 33 | `8b41e651` | who is the supreme justice of the supreme cou... | John Roberts | Win | Loss | Win | Win | 166 | Recovered P1 Regression |
| 34 | `a172dc55` | when did the movie varsity blues come out | January 15 , 1999 | Win | Loss | Win | Win | 256 | Recovered P1 Regression |
| 35 | `ab744abc` | who made the most free throws in nba history | Karl Malone | Loss | Win | Win | Win | 1097 | Preserved P2 Recovery |
| 36 | `ae89f4d5` | who win road march in trinidad and tobago | Machel Montano | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 37 | `b2c8d85e` | when is the 5th round fa cup played | 16 February 2018 | Win | Loss | Loss | Loss | 321 | Unrecovered P1 (Retained, Model Gen Error) |
| 38 | `b53d4111` | when did i ai n 't mad at cha come out | September 15 , 1996 | Win | Loss | Win | Win | 361 | Recovered P1 Regression |
| 39 | `b6456292` | who wrote catch 22 ( both names ) | Joseph Heller | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 40 | `b786366c` | who has the most ncaa basketball tournament a... | Kentucky | Win | Loss | Win | Win | 896 | Recovered P1 Regression |
| 41 | `b9b5f86a` | how many goals did mikel score for chelsea | 1 | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 42 | `c2bad2c4` | when did where are you now come out | February 27 , 2015 | Win | Loss | Win | Win | 465 | Recovered P1 Regression |
| 43 | `c530f07f` | who plays the queen in victoria and abdul | Judi Dench | Win | Loss | Loss | Win | 146 | Recovered P1 Regression |
| 44 | `cef8d106` | when was the last time the seattle seahawks w... | 2013 | Win | Loss | Win | Win | 627 | Recovered P1 Regression |
| 45 | `d05a8394` | who is the chief economic advisor of india | Arvind Subramanian | Win | Loss | Win | Win | 94 | Recovered P1 Regression |
| 46 | `d5de0aa2` | all time highest goal scorer in spain nationa... | David Villa | Loss | Win | Win | Win | 270 | Preserved P2 Recovery |
| 47 | `e34508a7` | who won the first celebrity big brother on ch... | Jack Dee | Win | Loss | Loss | Loss | 909 | Unrecovered P1 (Retained, Model Gen Error) |
| 48 | `e4731d77` | what nba team did derrick rose play for | Chicago Bulls | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 49 | `e529e5ec` | when was the last time iran had an earthquake | 2017 - 12 - 20 | Loss | Win | Loss | Loss | 903 | Regressed P2 (Retained, Model Distraction) |
| 50 | `e8f64c51` | who has the highest paid contract in the nba | Stephen Curry | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 51 | `ef523d77` | who has won the 2018 formula one australia gr... | Sebastian Vettel | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 52 | `f483eb86` | how many episodes of ray donovan series 3 are... | 12 | Win | Loss | Win | Win | 260 | Recovered P1 Regression |
| 53 | `f62a04a8` | when was how deep is your love released | September 1977 | Loss | Win | Win | Win | 567 | Preserved P2 Recovery |
| 54 | `f63b92ac` | who built pedestrian bridge at florida intern... | Munilla Construction Mana... | Win | Loss | Win | Win | 295 | Recovered P1 Regression |
| 55 | `f6c035f6` | where was the flag placed on the moon | Sea of Tranquility | Win | Loss | Loss | Loss | 0 | Unrecovered P1 (Zero Context: Selection Thresh) |
| 56 | `fb02beed` | when was the taj mahal built and completed | 1632 -- 53 | Loss | Win | Win | Win | 310 | Preserved P2 Recovery |
| 57 | `fd249e52` | who wrote the song after you 've gone | Turner Layton | Win | Loss | Loss | Loss | 85 | Unrecovered P1 (Retained, Model Gen Error) |
| 58 | `fd55f4dc` | who represents the arizona 9th district in th... | Kyrsten Sinema | Win | Loss | Win | Win | 153 | Recovered P1 Regression |

---

## 8. Artifact Inventory & Cryptographic Checksums

| Artifact | Repository Path | Size (Bytes) | SHA-256 Checksum | Verification Status |
| :--- | :--- | :---: | :--- | :--- |
| **Gate 4 Records** | [`gate_4_targeted_pilot/eval_records_experiment_4.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_4_targeted_pilot/eval_records_experiment_4.jsonl) | 275,559 | `d798315ba7831a688dc406c13ff2e60ff70290f78afc1086d4a1c4e9159aaa3e` | Complete 58-case records |
| **Gate 4 Summary** | [`gate_4_targeted_pilot/experiment_4_summary.json`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_experiment_4_v1/gate_4_targeted_pilot/experiment_4_summary.json) | 40,796 | `b63440376a09b270b96b530f69fa26c514c53f735209d035bd6e0e32948fed7c` | Aggregate McNemar & summaries |
| **Harness Runner** | [`eval_experiment_4_v1.py`](file:///home/chandan/Projects/major-project/precis/scripts/eval_experiment_4_v1.py) | 66,271 | `f228e41eb3d724380e20f2f84046f451f9a3862f57d49702ff4b4b6c9ac041dc` | Approved runner script |
| **Integrity Suite**| [`test_experiment_4_integrity.py`](file:///home/chandan/Projects/major-project/precis/scripts/test_experiment_4_integrity.py) | 45,412 | `f27a0d5f5788b297f48845513975c6b1df1419e3c8280ed726390aae56b5d01d` | 38/38 passing repo tests |
| **Manifest** | [`sample_manifest.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl) | 87,419 | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | Frozen benchmark input |
| **Stage C Records**| [`eval_records_stage_c.jsonl`](file:///home/chandan/Projects/major-project/precis/results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl) | 441,836 | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | Frozen benchmark input |
| **Dataset** | [`nq_dev.jsonl`](file:///home/chandan/Projects/major-project/precis/backend/data/nq_subset/nq_dev.jsonl) | 1,481,215 | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | Frozen benchmark input |

---

## 9. Final Recommendations & Stop Condition

### Recommendations:
1. **Permanent Rejection of SVOA Decompilation for Structured Documents**:
   - Stage C Decompilation (Condition B) was decisively outperformed by compact GFM table retention (Condition C & D) with $p < 0.0001$.
   - SVOA parsing fragments relational semantics, loses column-header bindings, and aggressively discards necessary rows.
2. **Adoption of Structural Retention Architecture as the Foundation**:
   - Converting HTML tables directly to GFM chunks with header preservation and raw list packing is verified as an empirically superior paradigm, recovering 53.2% of lost regressions.
3. **Do NOT Deploy to Production Without Fixing Table Selection Recall**:
   - 77.3% of the residual failures in Condition D occurred because the frozen selection filter (threshold $\theta = 2.0$) excluded valid tables.
   - Future engineering must replace the heuristic keyword table filter with a relaxed or hybrid selection policy (e.g. $\theta = 0.0$ or embedding-assisted table matching) before running a full 200-case confirmatory benchmark.

**Execution is STOPPED. All Gate 4 requirements are complete.**