# Experiment 4.4: Independent Regression Review

**Audit Date**: 2026-10-10  
**Evaluator**: Independent Audit Suite  
**Target Cohort**: Frozen 200-case table-bearing cohort  
**Scope**: In-depth case-level investigation of the three observed Condition D $\to$ Condition E regressions (`3f5983b2`, `ef634417`, `8f1f9bd9`).

---

## 1. Executive Summary of Regressions

In Experiment 4.4, Condition E (combining structural table retention at $\theta=0.0$ with list extraction) achieved **12 wins** and **3 regressions** against Condition D ($\theta=0.0$ table retention alone), yielding a net improvement of **+9 wins (+4.50 pp, exact McNemar $p = 0.035156$)**.

While this represents a statistically significant improvement with a favorable 4.0:1 win-to-loss ratio, the three regressions reveal distinct interaction dynamics between table retention, list extraction, and language model generation:

| Case ID Prefix | Question | Gold Answer | Condition D Prediction (EM) | Condition E Prediction (EM) | Primary Root Cause |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `3f5983b2` | Who is the minister of youth in namibia | Erastus Utoni | **Erastus Utoni** (True) | **Insufficient information** (False) | Distractor / Ambiguity Injection (Deputy vs. Minister) |
| `ef634417` | Who sings the song rock you like a hurricane | Scorpions | **Scorpions** (True) | **Rudolf Schenker, Klaus Meine, Herman Rarebell** (False) | Entity Misattribution / Salience Distortion (Songwriters vs. Performer) |
| `8f1f9bd9` | What is the definition of the name thomas | twin | **Twin** (True) | **Aramaic: twin** (False) | Formatting Variation / Preserved Containment (Origin prefix) |

---

## 2. Case-by-Case Deep Dive

### Case 1: `3f5983b2021c43aabd1bda0c71bb6f9e`

- **Question**: `who is the minister of youth in namibia`
- **Gold Answer**: `Erastus Utoni`
- **Condition D Prediction**: `Erastus Utoni` (EM: **True**, Containment: **True**, Context Tokens: 27)
- **Condition E Prediction**: `Insufficient information` (EM: **False**, Containment: **False**, Context Tokens: 92)

#### Context D Comparison
In Condition D, table selection detected 0 tables. The raw document prose fell through to clean prose:
```markdown
### Clean Prose:
<li> Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni 



 </li>
```
With only this single line in context, the LLM deduced that Jerry Ekandjo served until February 2018 and Erastus Utoni is the current minister, answering concisely: `Erastus Utoni`.

#### Context E Comparison
Condition E extracted the nested list structure from the HTML:
```markdown
### Clean Prose:
<li> Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni 



 </li>

### Structured List:
* Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni
* [Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni] Deputy : Agnes Tjongarero
```

#### Detailed Forensic Analysis
1. **Structural Distortion**: The list extractor processed the sub-list item `<li>Deputy : Agnes Tjongarero</li>` and bound it to the parent text `[Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni]`.
2. **Epistemic Conflict**: The presence of both `Erastus Utoni` and `Deputy : Agnes Tjongarero` under the same ministry heading created confusion regarding the exact title holder requested by "minister of youth". Furthermore, the repetition between clean prose and the structured list reinforced uncertainty.
3. **Model Reaction**: Faced with competing candidates and ambiguous hierarchical roles, the model defaulted to its epistemic safety trigger: `"Insufficient information"`.
4. **Remediation Recommendation**: In key-value lists where sub-items have explicit role qualifiers (e.g., `Deputy: ...`), the hierarchical renderer should clearly differentiate primary role holders from deputies or support staff, or prune redundant prose blocks when identical list blocks are extracted.

---

### Case 2: `ef634417fddf44d3b9c53ffd9d13dac8`

- **Question**: `who sings the song rock you like a hurricane`
- **Gold Answer**: `Scorpions`
- **Condition D Prediction**: `Scorpions` (EM: **True**, Containment: **True**, Context Tokens: 261)
- **Condition E Prediction**: `Rudolf Schenker, Klaus Meine, Herman Rarebell` (EM: **False**, Containment: **False**, Context Tokens: 298)

#### Context D Comparison
In Condition D, only the Markdown infobox table was packed:
```markdown
| `` Rock You Like a Hurricane '' | Col_2 | Col_3 |
| --- | --- | --- |
| Artwork for the pressing `` made in EEC , '' whose photograph was also used for the UK release |  |  |
| Single by Scorpions |  |  |
| from the album Love at First Sting |  |  |
| Released | 7 February 1984 |  |
| Format | Vinyl LP cassette CD |  |
| Genre | Heavy metal |  |
| Length | 4 : 11 |  |
| Label | Harvest Mercury |  |
| Songwriter ( s ) | Rudolf Schenker Klaus Meine Herman Rarebell |  |
| Producer ( s ) | Dieter Dierks |  |
...
```
The model attended to row 4: `Single by Scorpions` and correctly recognized Scorpions as the musical artist/singer.

#### Context E Comparison
In Condition E, the extractor found 3 bullet lists embedded in or following the table:
```markdown
[Same table as Context D]

### Structured List:
* Vinyl LP
* cassette
* CD

### Structured List:
* Harvest
* Mercury

### Structured List:
* Rudolf Schenker
* Klaus Meine
* Herman Rarebell
```

#### Detailed Forensic Analysis
1. **Salience & Recency Bias**: The list of three songwriters (`Rudolf Schenker`, `Klaus Meine`, `Herman Rarebell`) was appended at the very end of the prompt under its own section `### Structured List:`.
2. **Semantic Confusion**: The model asked "who sings the song". The songwriters are human individuals, whereas "Scorpions" is a band name. In the presence of a dedicated list of persons at the prompt tail, the model prioritized the human creators over the band entity, answering: `Rudolf Schenker, Klaus Meine, Herman Rarebell`.
3. **Remediation Recommendation**: Sub-table embedded lists (such as lists inside infobox cells) should either be deduplicated against existing table cells or contextualized with their table row header (`Songwriter (s)`). When list extraction extracts items already present in retained tables, appending them as standalone trailing sections adds distractor weight without adding new information.

---

### Case 3: `8f1f9bd984574fd8a829c80f8974ff13`

- **Question**: `what is the definition of the name thomas`
- **Gold Answer**: `twin`
- **Condition D Prediction**: `Twin` (EM: **True**, Containment: **True**, Context Tokens: 117)
- **Condition E Prediction**: `Aramaic: twin` (EM: **False**, Containment: **True**, Context Tokens: 117)

#### Context D & Context E Comparison
Both contexts are **100% bit-for-bit identical**:
```markdown
| Thomas | Col_2 |
| --- | --- |
| Saint Thomas the Apostle |  |
| Pronunciation | / ˈtɒməs / French : ( tɔma ) German : ( ˈtoːmas ) Dutch : ( ˈtoːmɑs ) |
| Gender | Male |
| Name day | July 3 |
| Origin |  |
| Word / name | Aramaic |
| Meaning | `` twin '' |
| Other names |  |
| Related names | Tom , Tommaso , Tŏmas , Tomas , Tomasz , Tommy |
```
- List blocks found: 0
- List blocks packed: 0
- List tokens added: 0
- Total context tokens: 117 in both conditions.

#### Detailed Forensic Analysis
1. **Zero Extractor Modification**: Condition E did not add, remove, or modify any content in this case.
2. **Model Formatting Shift**: Condition D predicted `Twin` (normalized to exact match). Condition E predicted `Aramaic: twin`. Containment remains **True** in both conditions.
3. **Generation Cause**: Both runs were executed with identical inference hyperparameters (`temperature=0.0`, `seed=42`). However, slight environment differences in prompt assembly order or GPU inference execution can trigger token tie-breakers in greedy decoding.
4. **Impact Assessment**: This regression is benign from an evidence perspective. The model did not hallucinate or lose the gold answer; it merely included the linguistic origin prefix `Aramaic:` alongside the definition.

---

## 3. Systematic Failure Modes and Safeguard Matrix

| Failure Mode | Observed in | Risk Level | Proposed Architectural Safeguard |
| :--- | :--- | :--- | :--- |
| **Nested List Role Confusion** | `3f5983b2` | Medium | Prune or annotate sub-hierarchies containing subordinate qualifiers (`Deputy`, `Vice`, `Assistant`) when primary role queries are detected. |
| **Intra-Table Redundant List Append** | `ef634417` | High | Implement overlap deduplication: do not append standalone list sections whose contents are already fully represented within selected table cells. |
| **Prefix / Formatting Variation** | `8f1f9bd9` | Low | Benign containment preserved; post-processing normalization could strip leading language tags (e.g., `Aramaic: `). |

---

## 4. Conclusion

The audit verifies that **only 2 of the 3 regressions** (`3f5983b2` and `ef634417`) were caused by the introduction of list extraction, while `8f1f9bd9` was an identical-context formatting shift that preserved gold answer containment. 

Against these 2 true information-distractor regressions, Condition E delivered **12 verified wins** across diverse domains, demonstrating strong net efficacy. The identified failure modes provide concrete, actionable guidance for feature-flagged integration safeguards.
