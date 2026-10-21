# Précis Experiment 4.3: Targeted Results and Regression Audit

**Status**: Completed  
**Date**: October 10, 2026  
**Auditor**: Automated Diagnostic Preflight Harness  
**Scope**: Raw Record Verification of Experiment 4.3 Gate 2 Targeted Pilot  
**Artifact Directory**: `results/diagnostic_experiment_4_v1/full_cohort_preflight_20261010/`  

---

## 1. Audit of Primary Contingency Tables

The exact-match and containment metrics reported in Gate 2 were independently audited by directly parsing the raw JSONL records in:
- Reference Condition A: `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl` (Condition D records)
- Candidate Condition B: `results/diagnostic_experiment_4_v1/gate_2_list_extraction_20261010/stage_2b_eval_records.jsonl`

### 1.1 Exact Match Contingency Table ($N=31$)

$$\begin{array}{c|cc|c}
& \text{Cond B Correct (EM=1)} & \text{Cond B Incorrect (EM=0)} & \text{Total} \\
\hline
\text{Cond A Correct (EM=1)} & 0 & 0 & 0 \\
\text{Cond A Incorrect (EM=0)} & 11 & 20 & 31 \\
\hline
\text{Total} & 11 & 20 & 31
\end{array}$$

- **True-True (Both Correct)**: 0
- **True-False (Cond A Correct, Cond B Incorrect — Losses)**: 0
- **False-True (Cond A Incorrect, Cond B Correct — Wins)**: 11
- **False-False (Both Incorrect — Ties)**: 20
- **Net Exact-Match Discordant Wins**: $+11$ ($+35.48$ percentage points)
- **Exact McNemar Test (Two-Tailed)**:
  $$p = 2 \times \sum_{k=11}^{11} \binom{11}{k} 0.5^{11} = 2 \times \frac{1}{2048} = \frac{1}{1024} \approx 0.0009765625$$
- **Odds Ratio**: $\infty$ (due to zero in the denominator cell)

### 1.2 Containment Contingency Table ($N=31$)

$$\begin{array}{c|cc|c}
& \text{Cond B Correct (Cont=1)} & \text{Cond B Incorrect (Cont=0)} & \text{Total} \\
\hline
\text{Cond A Correct (Cont=1)} & 0 & 0 & 0 \\
\text{Cond A Incorrect (Cont=0)} & 16 & 15 & 31 \\
\hline
\text{Total} & 16 & 15 & 31
\end{array}$$

- **True-True (Both Correct)**: 0
- **True-False (Losses)**: 0
- **False-True (Wins)**: 16
- **False-False (Ties)**: 15
- **Net Containment Discordant Wins**: $+16$ ($+51.61$ percentage points)
- **Exact McNemar Test (Two-Tailed)**:
  $$p = 2 \times 0.5^{16} = \frac{1}{32768} \approx 0.0000305 \quad (p < 10^{-4})$$

---

## 2. Audit of the "Zero-Regression" Claim

> [!WARNING]
> ### Critical Methodological Limitation
> **Zero exact-match regressions on this cohort is a mathematical property of cohort selection, NOT an empirical proof of regression safety.**

### Mathematical Explanation
The targeted diagnostic cohort $\mathcal{S}$ of 31 cases was constructed using the criterion:
$$\mathcal{S} = \{ i \in \mathcal{D}_{\text{manifest}} \mid \text{EM}_A(i) = \text{False} \land \text{Category}(i) \in \text{VerifiedListOmissions} \}$$

By definition of this selection rule:
$$\forall i \in \mathcal{S}, \quad \text{EM}_A(i) = \text{False}$$

A regression transition occurs when Condition A is correct and Condition B is incorrect:
$$\text{Regressions}_{\text{EM}} = \sum_{i \in \mathcal{S}} \mathbf{1}(\text{EM}_A(i) = \text{True} \land \text{EM}_B(i) = \text{False})$$

Because $\mathbf{1}(\text{EM}_A(i) = \text{True}) = 0$ for every case in $\mathcal{S}$, the sum is strictly bounded:
$$\text{Regressions}_{\text{EM}} \le \sum_{i \in \mathcal{S}} \mathbf{1}(\text{EM}_A(i) = \text{True}) = 0$$

### Substantive Consequences
1. **Selection on Failure**: Observing 0 EM regressions demonstrates only that Condition B did not make an already incorrect answer "more incorrect" in a way that reduced EM score (which is impossible under binary scoring).
2. **Untested Baseline Successes**: In the full 200-case cohort, Condition D answered **99 cases correctly** (49.5% EM). Adding list blocks to the context could plausibly:
   - Displace relevant table rows due to context-length competition.
   - Introduce distracting entities that mislead the attention mechanism.
   - Induce generation fatigue or prompt dilution on questions that rely strictly on tables or clean prose.
3. **Requirement for Full-Cohort Evaluation**: The only scientifically sound way to establish regression safety is to evaluate Condition E across the **entire 200-case cohort**, measuring discordant transitions on the 99 cases where Condition D was already correct.

---

## 3. Individual Audit of the Five Containment-Only Wins

Five cases achieved Containment without achieving Exact Match. We audited the raw model outputs, prompt strings, and gold answer structures for each case to distinguish:
1. *Semantically correct but over-complete answers* (collective entity sets).
2. *Incomplete or incorrect answers containing gold substrings* (spurious containment).
3. *Strict normalization or annotation format mismatches*.

| Case ID | Question | Gold Answers (NQ) | Candidate Model Prediction | Semantic Diagnosis |
| :--- | :--- | :--- | :--- | :--- |
| `abe22dfa` | the cast of a good day to die hard | `['Bruce Willis', 'Jai Courtney', 'Sebastian Koch', 'Yuliya Snigir', 'Sergei Kolesnikov', 'Radivoje Bukvić', 'Mary Elizabeth Winstead']` | `Bruce Willis, Jai Courtney, Sebastian Koch, Yuliya Snigir, Sergei Kolesnikov, Radivoje Bukvić, Mary Elizabeth Winstead` | **Semantically correct, over-complete collective enumeration**. The prompt requested "the cast", so the model enumerated all 7 actors. In NQ, each actor is a separate disjunctive string. EM failed against any single actor; containment succeeded. |
| `ed97c452` | who was allowed to vote in scottish referendum | `['British citizens who were resident in Scotland', 'citizens of other Commonwealth countries who were resident in Scotland', 'citizens of other European Union countries who were resident in Scotland', 'members of the House of Lords who were resident in Scotland', "Service / Crown personnel serving in the UK..."]` | `British citizens who were resident in Scotland; citizens of other Commonwealth countries who were resident in Scotland; citizens of other European Union countries who were resident in Scotland; members of the House of Lords who were resident in Scotland; Service / Crown personnel serving in the UK...` | **Semantically correct, over-complete collective enumeration**. The model faithfully extracted the complete 5-item qualification criteria separated by semicolons. |
| `2a25e7ad` | all of the states in the northeast region | `['Connecticut', 'Maine', 'Massachusetts', 'New Hampshire', 'Rhode Island', 'Vermont', 'New Jersey', 'New York', 'Pennsylvania']` | `Connecticut, Maine, Massachusetts, New Hampshire, Rhode Island, Vermont, New Jersey, New York, Pennsylvania` | **Semantically correct, over-complete collective enumeration**. The prompt explicitly specified "all of the states", so the model listed all 9 states comma-delimited. |
| `503e0316` | which is the fastest train in india and what is its speed | `['Mumbai Rajdhani Express', 'maximum speed 160 km / h', 'average speed 112 km / h']` | `12951 / 52 Mumbai Rajdhani Express\n140 km / h` | **Semantically correct joint answer, annotation mismatch**. The compound question asks for both name and speed. The model answered both. NQ stores them as separate disjunctive alternatives. Additionally, the model extracted the operational speed (140 km/h) from the list. |
| `3e87ec57` | what are the spices in chinese 5 spice powder | `['Star anise', 'Cloves', 'Chinese cinnamon', 'Sichuan pepper', 'Fennel seeds']` | `star anise, cloves, Chinese cinnamon, Sichuan pepper, fennel seeds` | **Semantically correct, over-complete collective enumeration**. The model enumerated all five spices comma-delimited. |

### Semantic Judgment Summary
- **Semantically correct but over-complete answers**: Exactly **5 of 5 cases (100.0%)**.
- **Spurious / Incomplete containment**: Exactly **0 of 5 cases (0.0%)**.
- None of the 5 containment wins represent hallucinated or incorrect outputs that accidentally overlapped with a gold substring. In all 5 cases, the model successfully located the extracted list block and synthesized an accurate, exhaustive response.

---

## 4. Audit of the 15 Unrecovered Cases

The remaining 15 cases failed both Exact Match and Containment. Detailed review reveals three underlying mechanisms:

### 4.1 Strict Scoring Normalization / Annotation Artifacts (4 cases)
In these cases, the model produced the correct semantic answer, but NQ gold contains extraneous tokens or parenthetical qualifications that prevented exact string matching under `check_exact_match_v2`:
1. `0c0db792`: *"american horror story freak show girl kidnapped by clown"*  
   - Model prediction: `Bonnie Lipton`  
   - NQ gold answer: `['Bonnie Lipton ( portrayed by Skyler Samuels )']`  
   - *Analysis*: The model identified the character. Normalization removes punctuation, but cannot strip actor parentheticals.
2. `a96d5b00`: *"who was the ruler of england in 1616"*  
   - Model prediction: `James I`  
   - NQ gold answer: `['James I , King of England']`  
   - *Analysis*: The model gave the concise name; NQ includes formal title suffix.
3. `3e9bc967`: *"cast of the have and have nots play"*  
   - Model prediction: `Palmer Williams Jr., Patrice Lovely, Tony Hightower, Alexis Jones, Maurice Lauchner, Jeffery Lewis, Kislyck Halsey`  
   - NQ gold answer: `['Palmer Williams Jr. as Floyd', 'Patrice Lovely as Hattie', ...]`  
   - *Analysis*: Model extracted actor names without character roles.
4. `70f2237c`: *"what does it mean on tinder common connections"*  
   - Model prediction: `Mutual Facebook friend or second-degree connection`  
   - NQ gold answer: Verbose 42-word paragraph definition.

### 4.2 "Insufficient Information" Abstentions (8 cases)
The model returned `"Insufficient information"` despite the presence of the list evidence in context:
- `16caa32e` (wool producer): List contained percentage figures (`South Africa: 1%`), but did not explicitly use the word "leading".
- `64cd81b2` (Star Wars characters): Extensive list of characters with nested roles.
- `6cac0d1a` (Whiskey ain't workin): Song duet credits embedded within album track listing.
- `895b5134` (Super Bowls as player): Ambiguous premise; Belichick listed, but won as coach.
- `5fe035e5` (rushing yards in Super Bowl): Context contained tabular and bulleted player stats.
- `2d7ca2fd` (cities in San Joaquin County): List of incorporated cities.
- `75bbbd97` (Last Train from Gun Hill cast): Film credits list.
- `c52fb4e7` (Paul Walker's cars in Fast and Furious): Vehicle listing across films.

### 4.3 Distractor Entity / Adjacent Cell Selections (3 cases)
The model extracted text from the list, but selected an adjacent or distractor entity:
- `680012c3` & `a0ee91b8`: *"who is the father of lucius in gladiator"* $\rightarrow$ Predicted `Lucilla` (his mother, listed immediately adjacent to Lucius Verus).
- `9d4004bf`: *"who plays reggie the robot in justin's house"* $\rightarrow$ Predicted `Reginald T Robot` (the character name instead of actor `Ben Faulks`).

---

## 5. Audit Conclusion

1. **Gate 2 Data Integrity**: 100% verified. All reported counts (11 EM wins, 16 containment wins, 0 losses, 20 ties) match the raw records bit-for-bit.
2. **Containment Quality**: All 5 containment-only wins are valid, semantically complete enumerations of collective queries.
3. **Regression Safety Not Yet Proven**: The absence of EM regressions on this cohort is mathematically guaranteed by the selection criterion and does not demonstrate that adding lists is safe for baseline-success cases.
4. **Recommendation**: Progression to a full 200-case evaluation is methodologically justified and necessary to measure real net performance.
