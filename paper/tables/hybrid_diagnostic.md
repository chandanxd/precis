# Précis Hybrid Diagnostic Experiment: Results & Mechanistic Analysis

**Document Status**: Authoritative Research Report  
**Target Hypothesis**: $H_{\text{HYBRID}}$ ($H_{\text{HYBRID\_A}}$, $H_{\text{HYBRID\_B}}$, $H_{\text{HYBRID\_C}}$)  
**Execution Environment**: Local Deterministic Inference (`qwen2.5-coder:7b`, seed 42, temperature 0.0, top_p 0.9, max_tokens 512, context ceiling 2048 estimated tokens)  
**Production Code Status**: `backend/src/precis/` 100% Frozen (Zero production code or test modifications)  
**Data Artifacts**: `results/diagnostic_hybrid_n40/hybrid_diagnostic_cases.jsonl`, `results/diagnostic_hybrid_n40/hybrid_diagnostic_cases_v2.jsonl`, `results/diagnostic_hybrid_n40/rebaseline_v3_results.jsonl`, `paper/tables/hybrid_diagnostic_results.json`, `paper/tables/hybrid_diagnostic_results.csv`  

---

## 1. Executive Summary

To investigate the performance divergence between Précis v3 and passage-based Naive RAG on the Natural Questions benchmark, we conducted an isolated, three-part diagnostic experiment across all 40 outcome-selected discordant cases: 29 Deficit cases and the Legacy 11-Case Diagnostic Cohort (containing 10 verified historical Précis-only wins and one evaluation/selection artifact).

```
+-------------------------------------------------------------------------------------------------------------------------+
|                                    SUMMARY OF DIAGNOSTIC EXPERIMENTAL FINDINGS                                          |
+------------------------------------+---------------+-------------+---------------------+---------------+----------------+
| Experiment                         | Cohort        | Sample Size | Primary Metric      | Value / Rate  | Interpretation |
+------------------------------------+---------------+-------------+---------------------+---------------+----------------+
| Synchronous V3 Rebaseline          | Deficit Cases | 29          | Containment Rate    |  0 / 29 (0.0%)| Reconfirms     |
|                                    | Legacy Cohort | 11          | Containment (Single)| 10 / 11(90.9%)| baseline error |
|                                    |               |             | Containment (Alias) | 11 / 11(100.%)| states         |
+------------------------------------+---------------+-------------+---------------------+---------------+----------------+
| Exp A: Hybrid-Oracle-Span          | Deficit Cases | 29          | Oracle Repair Rate  | 16 / 29(55.2%)| Characterizes  |
| (Audited Gold Span Restored)       |               |             | Unrecovered Cases   | 13 / 29(44.8%)| recoverability |
+------------------------------------+---------------+-------------+---------------------+---------------+----------------+
| Exp B: Precision-Preservation      | Verified Wins | 10          | Verified Retention  |  7 / 10(70.0%)| Raw text noise |
| (Dense Span + Token Budget Match)  | Synch Baseline| 10          | Synch Retention     |  7 / 10(70.0%)| induces        |
|                                    |               |             | Regressions         |  3 / 10(30.0%)| regressions    |
|                                    | Legacy Cohort | 11          | Legacy Coverage     |  7 / 11(63.6%)| 7 win, 3 reg,  |
|                                    |               |             | Selection Artifact  |  1 / 11 (9.1%)| 1 artifact     |
+------------------------------------+---------------+-------------+---------------------+---------------+----------------+
| Exp C: Hybrid-Retrieved-Span       | Deficit Cases | 29          | Successful Recovery |  4 / 29(13.8%)| Reconciled     |
| (Dense MiniLM Top-1 Span + Facts)  | (Primary)     |             | Retrieval Miss Rate | 14 / 29(48.3%)| 4-Way          |
|                                    |               |             | Budget Fallback Rate|  3 / 29(10.3%)| Decomposition  |
|                                    |               |             | Retrieved Gen Fail  |  8 / 29(27.6%)| (Mutually Excl)|
|                                    +---------------+-------------+---------------------+---------------+----------------+
|                                    | Verified Wins | 10          | Verified Retention  |  7 / 10(70.0%)| Reproduces     |
|                                    | Synch Baseline| 10          | Synch Retention     |  7 / 10(70.0%)| Exp B distractor|
|                                    |               |             | Regressions         |  3 / 10(30.0%)| cost           |
+------------------------------------+---------------+-------------+---------------------+---------------+----------------+
```

### Core Diagnostic Findings:
1. **Source-Span Recoverability Under Oracle Intervention ($H_{\text{HYBRID\_A}}$)**:
   Under the tested oracle-span intervention, 16 of 29 outcome-selected deficit cases became correct. The remaining 13 cases were not recovered under this experimental setup. These observations characterize source-span recoverability; they do not establish mutually exclusive causal attributions for individual errors.
2. **Distractor Vulnerability on Verified Wins ($H_{\text{HYBRID\_B}}$)**:
   Adding raw source spans into Précis contexts—even under an estimated-token budget matched invariant ($\text{Tokens}_{\text{est}}(\text{Hybrid}) \le \text{Tokens}_{\text{est}}(\text{Baseline})$)—causes regressions on previously won cases. Among the **10 verified historical Précis-only wins** under the canonical single-reference metric, **7 were retained (70.0%)** and **3 regressed (30.0%)**. Evaluating against the independently defined **10 synchronous-baseline wins** yields the identical primary rate: **7/10 retained (70.0%)** and **3/10 regressed (30.0%)**. Across the full 11-record legacy diagnostic cohort (which includes 1 legacy selection artifact), coverage is 7 retained wins, 3 regressed wins, and 1 artifact (7/11, 63.6%). The added text introduced distractor noise that triggered negative prompt fallbacks and confabulations (e.g., attributing the *Mission: Impossible* theme to John Williams).
3. **Compound Bottleneck in Non-Oracle Retrieval ($H_{\text{HYBRID\_C}}$)**:
   In an un-oracled pipeline where candidate spans were retrieved via dense MiniLM similarity without access to gold answers, only **4 of 29 deficit cases (13.8%)** were recovered. Complete four-way mutually exclusive decomposition reveals:
   - **Top-Ranked-Span Retrieval Misses**: **14 / 29 (48.3%)**  
     Dense MiniLM failed to rank an evidence-bearing span first.
   - **Context-Admission Failures / Budget Fallbacks**: **3 / 29 (10.3%)**  
     The retriever found the evidence-bearing span, but the span could not be admitted into the prompt because the baseline budget was too small ($T_{\text{baseline}} < T_{\text{span}}$); generator received baseline facts/empty context.
   - **Retrieved-Evidence Generation Failures**: **8 / 29 (27.6%)**  
     The evidence-bearing span was successfully admitted into the prompt within budget, but the generator failed to synthesize the gold answer.
   - **Successful Recoveries**: **4 / 29 (13.8%)**  
     The evidence-bearing span was admitted and the generator succeeded.

---

## 2. Selection Bias Disclosure & Cohort Definitions

> [!IMPORTANT]
> **Mandatory Epistemic Boundary Disclosure**:  
> *This experiment is a mechanistic diagnostic on outcome-selected discordant cases ($N = 40$: 29 Deficit + 11 Legacy Diagnostic Cohort) from the Natural Questions benchmark. It is NOT an unbiased estimate of general benchmark performance, does NOT claim general QA superiority over Naive RAG, and does NOT claim general hallucination reduction.*

The cohorts were selected *post-hoc* because they represent the exact boundary conditions where Précis and Naive RAG diverged in benchmark v3:
- The 29 deficit cases isolate where Précis failed and Naive RAG succeeded.
- The legacy 11-case diagnostic cohort isolates where Précis demonstrated advantages over Naive RAG.

### Formal Cohort Distinctions:
1. **Deficit Cohort ($N = 29$)**: Verified cases where Naive RAG succeeded and Précis v3 failed under containment.
2. **Legacy 11-Case Diagnostic Cohort ($N = 11$)**: The full 11-record outcome-selected evaluation set preserved for exact raw-trace reproducibility.
3. **Verified Historical Wins ($N = 10$)**: The 10 cases within the legacy cohort confirmed correct under the canonical single-reference metric (`gold_answer`).
4. **Legacy Selection/Annotation Artifact ($N = 1$, `c4691863`)**: A record admitted by the historical failure analysis script because its alternative-answer logic accepted character names (`"Foofa"`, `"Brobee"`) as answers to a question asking who plays the characters. The canonical benchmark evaluates against the primary reference answer (`"DJ Lance Rock"`), which the model's answer omitted.
5. **Synchronous-Baseline-Win Cohort ($N = 10$)**: The 10 cases in the legacy cohort evaluated as correct under the synchronous V3 rebaseline run. (Distinct definition from verified historical wins, though sharing the same 10 samples).

---

## 3. Alternative-Answer Semantics & Rebaseline Discrepancy

### 3.1 Dataset Schema & Annotation Semantics
The benchmark dataset (`backend/data/nq_subset/nq_dev.jsonl`) was generated by `backend/scripts/convert_mrqa_nq.py` from the official MRQA 2019 NaturalQuestions dev split.
- **`gold_answer` Field**: In MRQA conversion, `gold_answer` is strictly assigned to `answers[0]` (the primary reference span).
- **`answers` Field**: Represents the list of alternative acceptable answer spans provided by annotators in the MRQA dataset. For list-type questions, annotators frequently marked separate individual entity spans or list bullet headers.

### 3.2 Evaluation Logic Across Pipeline Stages
1. **Canonical 200-Question Benchmark (`harness.py`)**:  
   Exclusively evaluated against `sample.gold_answer` (`answers[0]`). It did **not** use the `answers` list for Exact Match, ROUGE-L, or BERTScore.
2. **Historical Failure Analysis (`analyze_benchmark_failures.py`)**:  
   Used `is_answer_correct(pred, gold_answer, answers=d['answers'])`, checking if the prediction contained `gold_answer` OR any element of `d['answers']`. This broader metric defined the legacy 11-case diagnostic cohort in `audit_11_precis_only.json`.
3. **Synchronous Rebaseline & Experiments A/B/C (`eval_hybrid_diagnostic.py`)**:  
   Evaluated strict single-gold containment (`contains_answer(pred, gold_answer)`), matching `harness.py`.

### 3.3 Deep Dive on Sample `c4691863`
- **Question**: `"who plays the characters in yo gabba gabba"`
- **Reference `gold_answer`**: `"DJ Lance Rock"`
- **Dataset `answers` List**: `['DJ Lance Rock', 'Muno', 'Foofa', 'Brobee', 'Toodee', 'Plex', 'Gooble']`
- **Semantic Finding**:  
  The strings `"Muno"`, `"Foofa"`, `"Brobee"`, `"Toodee"`, `"Plex"`, and `"Gooble"` are **the fictional characters**, NOT the actors who play them. The question asked for the actors/performers (`Lance Robertson`, `Christian Jacobs`, etc.). Annotators in MRQA marked the character bullet headers in the Wikipedia article. Treating character names as interchangeable answers to "who plays..." is a semantic annotation artifact.
- **Model Output**: Both historical canonical V3 and synchronous rebaseline generated the exact same response listing characters and actors (e.g., `DJ Lance: Lance Robertson`, `Plex: Christian Jacobs`).
- **Discrepancy Resolution**:
  - Under canonical single-reference containment against `"DJ Lance Rock"`, both historical and rebaseline are **0 / 1** (the text omits the suffix `"Rock"`).
  - Under multi-alias matching, both are **1 / 1** (matching `"Foofa"`, `"Brobee"`, etc.).
  - The model output was **100% byte-for-byte identical**.
  - Therefore, `c4691863` is a legacy selection/annotation artifact, and the verified historical win count under the canonical single-reference metric is **$N = 10$**.

### 3.4 Limits of Determinism
While all 11 cases in the legacy cohort were 100% identical between historical and rebaseline runs, **5 of the 29 Deficit cases** showed minor phrasing variations (e.g., `"mentioned in the given facts"` vs `"mentioned in the facts"`). All 29 remained 0/29 correct. We therefore avoid unqualified claims of absolute system-level determinism; greedy decoding ($T = 0.0$) restricts variance but does not completely eliminate minor floating-point kernel drift across environment invocations.

---

## 4. Win-Retention Analysis & Cross-Tabulation

Cross-tabulation across historical canonical V3, synchronous rebaseline V3, Experiment B, and Experiment C:

```
+----------+-------------------------------------+-----------+-----------+-----------+-----------+-----------------------------------+
| Sample ID| Question                            | Hist V3   | Rebase V3 | Exp B Hyb | Exp C Hyb | Diagnostic Status                 |
|          |                                     | (s / m)   | (s / m)   | (s / m)   | (s / m)   |                                   |
+----------+-------------------------------------+-----------+-----------+-----------+-----------+-----------------------------------+
| f93efe1f | leader of the ontario pc party      | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| fdf29e25 | seasons of prison break on netflix  | 1 / 1     | 1 / 1     | 0 / 0     | 0 / 0     | Regressed Verified Win            |
| 576f27f0 | reasons states impose protectionism | 1 / 1     | 1 / 1     | 0 / 0     | 0 / 0     | Regressed Verified Win            |
| 2ebac283 | member states of the eu             | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| 9ce6b865 | member states of the eu             | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| dc8cf325 | member states of the eu             | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| dab82978 | member states of the eu             | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| 3d27d21e | actor playing the beast in beauty   | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| c4691863 | who plays characters yo gabba gabba | 0 / 1     | 0 / 1     | 0 / 1     | 0 / 1     | Legacy Selection Artifact         |
| bad74caa | what did the 19th amendment do      | 1 / 1     | 1 / 1     | 1 / 1     | 1 / 1     | Retained Verified Win             |
| ab4a64fe | composer mission impossible theme   | 1 / 1     | 1 / 1     | 0 / 0     | 0 / 0     | Regressed Verified Win            |
+----------+-------------------------------------+-----------+-----------+-----------+-----------+-----------------------------------+
Legend: (s / m) = Single-Gold Containment / Multi-Answer Alias Containment
```

### Primary Win-Retention Figures:
1. **Experiment B Verified-Win Retention**: **7 / 10 (70.0%)**
2. **Experiment B Verified-Win Regression**: **3 / 10 (30.0%)** (`fdf29e25`, `576f27f0`, `ab4a64fe`)
3. **Experiment C Verified-Win Retention**: **7 / 10 (70.0%)**
4. **Experiment C Verified-Win Regression**: **3 / 10 (30.0%)**

### Separated Denominator Accounting:
- **Verified Historical Wins ($N_{\text{verified}} = 10$)**:
  - Retention: **7 / 10 (70.0%)**
  - Regressions: **3 / 10 (30.0%)**
- **Synchronous Rebaseline Wins ($N_{\text{reb}} = 10$)**:
  - Rebaseline Wins: **10 / 10**
  - Retention: **7 / 10 (70.0%)**
  - Regressions: **3 / 10 (30.0%)**
- **Legacy 11-Record Cohort Coverage ($N_{\text{legacy}} = 11$)**:
  - Retained Verified Wins: **7 / 11 (63.6%)**
  - Regressed Verified Wins: **3 / 11 (27.3%)**
  - Legacy Selection Artifact: **1 / 11 (9.1%)** (`c4691863`)

---

## 5. Experiment A: Hybrid-Oracle-Span (Source-Span Recoverability)

### 5.1 Protocol & Measured Recovery
- **Cohort**: 29 Deficit Cases.
- **Intervention**: Context = Ranked SVOA Facts + Audited Originating Source Span.
- **Result**: **16 of 29 (55.17%)** outcome-selected deficit cases became correct. Exact Match: 5/29 (17.2%). Mean ROUGE-L: 0.3591. Mean BERTScore: 0.5825.

### 5.2 Bounded Interpretation
> *Under the tested oracle-span intervention, 16 of 29 outcome-selected deficit cases became correct. The remaining cases were not recovered under this experimental setup. These observations characterize source-span recoverability; they do not establish mutually exclusive causal attributions for individual errors.*

### 5.3 Audit of the 13 Unrecovered Cases & Experimental Limitations
The 13 unrecovered cases cannot be categorized as proven LLM reasoning failures; rather, they reflect several observable experimental and evaluative limitations:
1. **Span Truncation on Semi-Structured Tables ($n = 5$, rugby union tries)**:
   - Samples `d79cf472`, `2d73cf78`, `f1698b6e`, `db3b37f0`, `62bed1a5` ask for the top rugby try scorer (*Daisuke Ohata*).
   - In Exp A, the injected oracle span was a 20-character table cell fragment (`"Daisuke Ohata ( 69 )"`). The context also contained an SVOA fact: `"Jonah Lomu has scored... 74 tries"`. Faced with a truncated fragment versus a fully formed propositional sentence, the LLM prioritized the SVOA fact.
2. **Surface Form & Compositional Equivalence ($n = 2$)**:
   - `11cabb55` (*University of Texas enrollment*): Gold is `"51,331"`. The LLM answered: `"40,168 undergraduate students and 11,163 graduate students..."`. The sum equals 51,331, but strict containment failed.
   - `9725b91f` (*Eleventh amendment trigger*): Gold is `"the Supreme Court 's ruling in Chisholm v. Georgia"`. The LLM answered: `"...decision in Chisholm v. Georgia"`.
3. **Multi-Fact Synthesis Hesitation ($n = 3$)**:
   - `85177baa`, `2f3afcf1` (*Stereo to mono*): Gold is `"Panning"`. LLM answered `"Creating a dual mono signal"` due to conflicting prepositional attachments in the prompt facts.
   - `5eead8e2` (*Lost in space release date*): LLM answered that release date was not mentioned.
4. **Formatting Word-Boundary Mismatches ($n = 3$)**:
   - Extended quotation marks and punctuation in references (`cde724cb`, `d6a6644d`, `ea73a38b`) prevented exact substring regex alignment.

---

## 6. Experiment C: Hybrid-Retrieved-Span & Budget Fallback Audit

### 6.1 Audit of the Three Context-Budget Fallback Cases
In Experiment C, three cases were flagged with `token_constraint_satisfied == False`:
- **`35d3ce1b` & `7385d04e`** (*"who has been chosen as the brand ambassador of the campaign 'beti bachao-beti padhao'"*, gold: *"Sakshi Malik"*):
  - *Retrieved Span*: `"In 26 August 2016 , Olympics 2016 bronze medallist Sakshi Malik was made brand ambassador for BBBP ."` (Retriever similarity: 0.428).
  - *Span Evidence*: Contains the gold answer (`"Sakshi Malik"`).
  - *Baseline Budget*: Baseline context had only 1 fact (23 estimated tokens).
  - *Admission Outcome*: The retrieved span formatted with headers required ~28 tokens, exceeding the 23-token budget. Under the budget-matching rule, the algorithm fell back to baseline facts alone.
  - *Generator Experience*: The generator **never received the retrieved span**; it received baseline facts only and predictably replied that the ambassador was not mentioned.
- **`9dd3961d`** (*"who has participated in the most super bowls"*, gold: *"New England Patriots"*):
  - *Retrieved Span*: `"New England Patriots XX , XXXI , XXXVIII , ..."` (Retriever similarity: 0.409).
  - *Span Evidence*: Contains the gold answer (`"New England Patriots"`).
  - *Baseline Budget*: Baseline context was a complete extraction failure (0 facts, 0 estimated tokens).
  - *Admission Outcome*: Span (17 tokens) could not fit in a 0-token budget. The algorithm fell back to empty context.
  - *Generator Experience*: Generator received empty context and replied with insufficient information.

### 6.2 Corrected Four-Way Mutually Exclusive Decomposition ($N = 29$)

```
+-------------------------------------------------------+-------------+---------------+-----------------------+
| Category                                              | Count       | Percentage    | Operational Definition|
+-------------------------------------------------------+-------------+---------------+-----------------------+
| Top-Ranked-Span Retrieval Misses                      | 14 / 29     | 48.28%        | Span lacked gold text |
| Context-Admission Failures / Budget Fallbacks         |  3 / 29     | 10.34%        | Span had gold, but was|
|                                                       |             |               | excluded by base budget|
| Retrieved-Evidence Generation Failures                |  8 / 29     | 27.59%        | Span had gold, was in |
|                                                       |             |               | prompt, but gen failed|
| Successful Recoveries                                 |  4 / 29     | 13.79%        | Span had gold, was in |
|                                                       |             |               | prompt, gen succeeded |
+-------------------------------------------------------+-------------+---------------+-----------------------+
| Total Deficit Cohort                                  | 29 / 29     | 100.0%        | Mutually Exclusive Sum|
+-------------------------------------------------------+-------------+---------------+-----------------------+
```

This four-way categorization corrects the previous reporting where the 3 budget fallbacks were conflated with generation failures. Among the 12 cases where the span was actually admitted into the generator's prompt, 4 were recovered (33.3% admitted-span recovery rate) and 8 failed generation.

---

## 7. Context-Budget Accounting & Tokenizer Disclosures

- **Estimated-Token Proxy**: The context budget was computed using $\text{Tokens}_{\text{est}} = \lfloor \text{Words} \times 1.3 \rfloor$, matching the benchmark harness.
- **Native Tokenizer Compliance**: This word-based proxy **does not guarantee native token-ceiling compliance** with the model's native BPE tokenizer (`Qwen2Tokenizer`). Exact offline tokenizer counts were not available in the local cache. We therefore describe the conditions as **estimated-token budget matched** rather than strictly token matched.
- **Budget Compliance**:
  - Experiment B: 11 / 11 compliant.
  - Experiment C (Legacy 11): 11 / 11 compliant.
  - Experiment C (Deficit 29): 26 / 29 admitted within budget; 3 fell back to baseline facts alone. In zero cases did hybrid context exceed the baseline budget.

---

## 8. Summary of Corrected Claims

1. **Cohort Terminology & Denominators**:
   - Replaced all descriptions of "11 Précis-only wins" with the precise distinction: **Legacy 11-Case Diagnostic Cohort**, containing **10 verified historical Précis-only wins** and **one legacy selection/annotation artifact (`c4691863`)**.
   - Established primary win-retention rates as **7 / 10 (70.0%)** retention and **3 / 10 (30.0%)** regression across both verified historical wins and synchronous-baseline wins.
2. **Replaced Causal Attribution**: Replaced claims that 55.2% of deficit is "caused by representation loss" with bounded recoverability statements under the oracle intervention.
3. **Reconciled Experiment C Failure Taxonomy**: Separated the 3 context-admission budget fallbacks (`CONTEXT_ADMISSION_FAILURE`) from genuine generation failures (`RETRIEVED_EVIDENCE_GENERATION_FAILURE`), establishing a clean 14 / 3 / 8 / 4 decomposition across all 29 cases.
4. **Clarified Alternative-Answer Semantics**: Documented that sample `c4691863`'s dataset aliases represent fictional characters rather than actors, explaining why multi-alias failure-analysis labeling diverged from strict single-gold rebaseline scoring while generated text was 100% byte-for-byte identical.
5. **No General Generalizations**: Explicitly stated that these diagnostic results do not establish general dense retrieval failure, general reasoning limitations, or hallucination reduction.
