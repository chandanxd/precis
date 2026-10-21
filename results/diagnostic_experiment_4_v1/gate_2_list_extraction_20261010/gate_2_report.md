# Précis Experiment 4.3 Gate 2 Report: Isolated List-Extraction Evaluation

**Status**: Completed  
**Date**: October 10, 2026  
**Cohort**: 31-Case Targeted Diagnostic Cohort (Verified Gate 1 List Omission Failures)  
**Evaluator**: `scripts/eval_experiment_4_3_gate2_runner.py`  
**Reference Condition (A)**: Frozen Experiment 4.2 Condition D ($\theta=0.0$, tables only, 0% baseline accuracy on this cohort)  
**Candidate Condition (B)**: Condition D ($\theta=0.0$) + Isolated Content List Extractor (`scripts/diagnostic_list_extractor.py`)  

---

## 1. Executive Summary

Experiment 4.3 Gate 2 evaluated whether augmenting the structural table retention pipeline ($\theta=0.0$) with an isolated HTML content-list extractor (`<ul>` and `<ol>`) reliably recovers missing gold evidence and translates that recovered evidence into end-to-end question answering gains without regressions.

The evaluation was conducted strictly on the **31 verified extraction-omission cases** identified during Gate 1 failure attribution.

### Key Findings
1. **Deterministic Evidence Recovery (Stage 2A)**:
   - **31 / 31 cases (100.0%)** successfully recovered the target gold answer substring in the extracted context.
   - Navigation menus, sidebars, and footer link farms were cleanly filtered (0 boilerplate leaks).
   - Mean list block size was ~290 tokens; the maximum total context across all 31 cases was **1,037 tokens**, remaining well below the **2,048-token context ceiling** (0 ceiling violations).

2. **Targeted Generation Pilot (Stage 2B)**:
   - **Condition A (Reference)**: Exact Match = **0 / 31 (0.0%)**, Containment = **0 / 31 (0.0%)**.
   - **Condition B (Candidate)**: Exact Match = **11 / 31 (35.5%)**, Containment = **16 / 31 (51.6%)**.
   - **Paired Discordant Transitions**: Exactly **11 wins, 0 losses, 20 ties** (+11 net wins, $+35.5$ percentage points).
   - **Containment Transitions**: Exactly **16 wins, 0 losses, 15 ties** (+16 net wins, $+51.6$ percentage points).
   - **Exact McNemar Test**: $p = 0.0009765625$ ($p < 10^{-3}$, statistically significant).
   - **Regressions**: **0 regressions** introduced (0 EM losses, 0 containment losses).

---

## 2. Stage 2A: Deterministic Evidence Recovery

Before running live model inference, Stage 2A processed the raw HTML of all 31 cases through `diagnostic_list_extractor.py` and combined them with clean prose and selected tables ($\theta=0.0$).

| Metric | Condition A (Reference) | Condition B (Candidate) | Delta / Outcome |
| :--- | :---: | :---: | :---: |
| **Gold Answer Presence** | 0 / 31 (0.0%) | 31 / 31 (100.0%) | +31 (+100.0%) |
| **List Blocks Packed** | 0 | 46 total (1.48 / case) | +46 blocks |
| **List Items Packed** | 0 | 412 total (13.3 / case) | +412 items |
| **Mean List Tokens** | 0 | 289.8 tokens | +289.8 tokens |
| **Max Context Observed** | 744 tokens | 1,037 tokens | +293 tokens |
| **Token Ceiling (2,048) Violations** | 0 | 0 | None (Safe margin: 1,011 tokens) |
| **Boilerplate Navigation Leaks** | 0 | 0 | 100% Filter Precision |

All 31 cases passed Stage 2A gating criteria, authorizing progression to Stage 2B.

---

## 3. Stage 2B: Targeted Generation Pilot

Stage 2B executed model generation on the local `qwen2.5-coder:7b` model under identical frozen hyperparameters (temperature 0.0, top_p 0.9, seed 42, max_tokens 512, concise prompt template).

### 3.1 Primary Aggregate Metrics

| Condition | Attempted | Completed | Failed / Unscorable | Exact Match | Containment |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Condition A (Reference)** | 31 | 31 | 0 | 0 / 31 (0.0%) | 0 / 31 (0.0%) |
| **Condition B (Candidate)** | 31 | 31 | 0 | **11 / 31 (35.5%)** | **16 / 31 (51.6%)** |

### 3.2 Paired 2x2 Contingency Table (Exact Match)

$$\begin{array}{c|cc|c}
& \text{Cond B Correct} & \text{Cond B Incorrect} & \text{Total} \\
\hline
\text{Cond A Correct} & 0 & 0 & 0 \\
\text{Cond A Incorrect} & 11 & 20 & 31 \\
\hline
\text{Total} & 11 & 20 & 31
\end{array}$$

- **Discordant Pairs**: 11 wins (A=0, B=1), 0 losses (A=1, B=0).
- **Net Wins**: +11 (+35.48 percentage points).
- **Exact McNemar Test (Two-Tailed)**:
  $$p = 2 \times \left(\frac{1}{2}\right)^{11} = \frac{1}{1024} \approx 0.0009765625$$
- **Odds Ratio**: $\infty$ (zero losses).

---

## 4. Case-Level Failure and Recovery Breakdown

### 4.1 The 11 Exact Match Wins
The 11 recovered cases represent direct, high-precision answers extracted from previously omitted bulleted/numbered lists:

1. `4a3eb5f5`: *"what is the area code for phoenix arizona"* $\rightarrow$ **602** (Gold: `['602', '480', '623']`)
2. `e6bfa9f3`: *"what is the second book in the alchemyst series"* $\rightarrow$ **The Magician** (Gold: `['The Magician']`)
3. `363edbaa`: *"what part of maryland is close to washington dc"* $\rightarrow$ **Frederick County** (Gold includes `Frederick County`)
4. `8fe0d283`: *"who played the detective in little boy blue"* $\rightarrow$ **Stephen Graham** (Gold: `['Stephen Graham']`)
5. `bd673bbb`: *"when was the last time the womens hockey team won gold"* $\rightarrow$ **2018** (Gold: `['2018']`)
6. `f3bd270e`: *"when did world war 2 end in the pacific"* $\rightarrow$ **September 2, 1945** (Gold: `['September 2 , 1945']`)
7. `521b6a03`: *"who played the little boy in polar express"* $\rightarrow$ **Dante Pastula** (Gold: `['Dante Pastula']`)
8. `3d3088e3`: *"who plays big momma in big mommas house"* $\rightarrow$ **Martin Lawrence** (Gold: `['Martin Lawrence', 'Ella Mitchell']`)
9. `02365027`: *"what is the zebras name in peppa pig"* $\rightarrow$ **Zoe Zebra** (Gold includes `Zoe Zebra`)
10. `04070d67`: *"uruguay is located along what body of water"* $\rightarrow$ **Bay of Montevideo** (Gold: `['Bay of Montevideo']`)
11. `c530f07f`: *"who plays the queen in victoria and abdul"* $\rightarrow$ **Judi Dench** (Gold: `['Judi Dench']`)

### 4.2 The 5 Containment Wins (Near-Misses on Exact Match)
Five cases achieved full containment and contained the exact correct answer entities, but missed Exact Match due to comprehensive multi-item enumeration requested by the question:

1. `abe22dfa`: *"the cast of a good day to die hard"* $\rightarrow$ Predicted full cast list (*Bruce Willis, Jai Courtney, Sebastian Koch, Yuliya Snigir, Sergei Kolesnikov, Radivoje Bukvić, Mary Elizabeth Winstead*).
2. `ed97c452`: *"who was allowed to vote in scottish referendum"* $\rightarrow$ Predicted the full 5-clause eligibility criteria text.
3. `2a25e7ad`: *"all of the states in the northeast region"* $\rightarrow$ Listed all 9 Northeastern states.
4. `503e0316`: *"which is the fastest train in india and what is its speed"* $\rightarrow$ Output train name and speed (*Mumbai Rajdhani Express, 140 km / h*).
5. `3e87ec57`: *"what are the spices in chinese 5 spice powder"* $\rightarrow$ Listed all five spices (*star anise, cloves, Chinese cinnamon, Sichuan pepper, fennel seeds*).

### 4.3 Detailed Audit of the 15 Unrecovered Cases

Analysis of the 15 remaining unrecovered cases reveals three distinct sub-patterns:

1. **Strict Scoring Artifacts (4 cases)**:
   The model generated the correct answer, but NQ gold normalization differences prevented an exact match:
   - `0c0db792`: *"american horror story freak show girl kidnapped by clown"* $\rightarrow$ Predicted **Bonnie Lipton**, whereas NQ gold string includes actor annotation: `Bonnie Lipton ( portrayed by Skyler Samuels )`.
   - `a96d5b00`: *"who was the ruler of england in 1616"* $\rightarrow$ Predicted **James I**, whereas NQ gold string has title suffix: `James I , King of England`.
   - `3e9bc967`: *"cast of the have and have nots play"* $\rightarrow$ Predicted actor list without character names.
   - `70f2237c`: *"what does it mean on tinder common connections"* $\rightarrow$ Condensed explanation vs verbose NQ paragraph.

2. **"Insufficient Information" Responses (8 cases)**:
   The model abstained despite the presence of the list. These cases involve lengthy list contexts where the relationship is indirect or requires multi-hop reasoning (e.g., `16caa32e` wool producer, `64cd81b2` Star Wars characters, `895b5134` most Super Bowls as player, `5fe035e5` rushing yards).

3. **Entity / Distractor Misattributions (3 cases)**:
   - `680012c3` & `a0ee91b8`: *"who is the father of lucius in gladiator"* $\rightarrow$ Predicted *Lucilla* (his mother, mentioned adjacent in the list).
   - `9d4004bf`: *"who plays reggie the robot in justin 's house"* $\rightarrow$ Predicted character name *Reginald T Robot* instead of actor *Ben Faulks*.

---

## 5. Safeguards and Integrity Verifications

- **Zero Production Modifications**: `backend/src/precis/` remained completely untouched. All evaluation was conducted via isolated diagnostic scripts (`scripts/diagnostic_list_extractor.py` and `scripts/eval_experiment_4_3_gate2_runner.py`).
- **Context Ceiling Compliance**: The packed context length never exceeded 1,037 tokens (ceiling: 2,048 tokens).
- **Strict Failure Accounting**: All 31 cases were executed with 0 timeouts, 0 exceptions, and 0 imputed scores.
- **Regression Check**: Exactly 0 regressions were observed ($0 / 31$).

---

## 6. Methodological Limitations

> [!NOTE]
> **Diagnostic Cohort Limitation**:
> This experiment was conducted on a targeted diagnostic cohort ($N=31$) selected specifically because the baseline table-only system omitted the gold evidence. The $+35.5\%$ EM uplift demonstrates that the isolated list extractor provides substantial recoverable upside when list evidence is missing. It is not an unbiased estimate of general population performance. A full-cohort evaluation ($N=200$) is required to measure net accuracy gains and verify that list retention does not introduce distractor regressions on the broader corpus.

---

## 7. Recommendation

### **READY FOR FULL-COHORT EVALUATION**

**Rationale**:
1. **Strong Empirical Win**: $+11$ net Exact Match wins, $+16$ net Containment wins, 0 regressions, and a statistically significant McNemar exact test ($p = 0.0009765$).
2. **Safe Token Budget**: Context consumption averaged ~290 tokens for lists, leaving over 1,000 tokens of headroom below the 2,048-token limit.
3. **Clean Separation of Concerns**: The list extractor operates independently of table selection and retains clean prose.

**Next Step**:
Awaiting user authorization before preparing the full 200-case confirmatory evaluation harness and preflight protocol.
