# Précis Experiment 2: Query-Aware Table Selection & Row-Level Relevance — Frozen Protocol

## 1. Overview & Objective
This document defines the frozen experimental protocol for Précis Experiment 2.
The objective is to determine whether query-aware HTML table selection and row-level relevance improve downstream question answering while reducing context overhead and eliminating regressions.

## 2. Experimental Conditions

Holding model (`qwen2.5-coder:7b`), decoding parameters (greedy $T=0.0$, top-p $0.9$, seed $42$, max tokens $512$), prompt (`CONCISE_PROMPT_TEMPLATE`), and token ceiling ($2,048$) strictly identical:

- **Condition A (Original SVOA Baseline)**: Pure prose sentential SVOA extraction; zero table/list propositions.
- **Condition B_frozen (Existing Table/List Prototype)**: Unranked table/list extraction using Experiment 1 defaults (`max_rows=25, max_facts=30`, document cap 45).
- **Condition B_approved (Approved Caps Sensitivity Analysis)**: Unranked table/list extraction using approved caps (`max_rows=10, max_facts=15`, document cap 15).
- **Condition C_full (Proposed Method)**:
  - Intervention 1: Query-aware table selection with entity-level negative constraint resolution and conservative fallback.
  - Intervention 2: Row-level relevance ranking with typed qualifier parsing (season vs episode), global row scope, and budget control (top-5 rows, max 10 facts/table, max 15 table facts/doc).
- **Ablation C1 (Table-Selection Only)**: Query-aware table selection ON; unranked row extraction (first $N$ rows up to cap).
- **Ablation C2 (Row-Ranking Only)**: All candidate tables ingested (no table selection); row-level relevance ranking ON.

## 3. Pre-Registered Hypotheses & Multiplicity Control

### 3.1 Primary Efficacy Outcome
- **Comparison**: Condition C_full vs Condition A.
- **Target Population**: Untouched Table-Bearing Stratum ($N=200$).
- **Primary Metric**: Exact Match (EM).
- **Statistical Test**: Two-sided McNemar’s exact test ($H_0: \delta_{\text{EM}} = 0$, $\alpha = 0.05$).
- **Effect Size**: Risk difference $\delta_{\text{EM}} = (b - c)/N$ with 95% Agresti-Min paired CI; discordance odds ratio $\psi = b/c$ with exact conditional binomial 95% CI.

### 3.2 Secondary Family (Holm Step-Down FWER at $\alpha=0.05$)
1. **Secondary 1 (Containment Efficacy)**: Condition C_full vs Condition A on Table Stratum ($N=200$). Two-sided McNemar exact test; $\delta_{\text{Cont}}$ with 95% Agresti-Min CI.
2. **Secondary 2 (Context Overhead vs Baseline)**: Condition C_full vs Condition A on Table Stratum ($N=200$). Two-sided Wilcoxon signed-rank test; percentage overhead $\frac{\bar{T}_C - \bar{T}_A}{\bar{T}_A} \times 100\%$.
3. **Secondary 3 (Context Reduction vs Frozen Prototype)**: Condition C_full vs Condition B_frozen on Table Stratum ($N=200$). Two-sided Wilcoxon signed-rank test.
4. **Secondary 4 (Accuracy Retention vs Frozen Prototype)**: Condition C_full vs Condition B_frozen on Table Stratum ($N=200$). Two-sided McNemar exact test on Exact Match.

### 3.3 Power Sensitivity & Detection Boundaries
The $N=200$ table-bearing stratum is powered ($\ge 80\%$) to detect **moderate-to-large effects ($\delta \ge +0.08$)**. For modest effects ($\delta \le +0.05$), $N=200$ has only $56.9\%$ power. Any gain $< +0.08$ that fails significance will be classified as **inconclusive due to sample size constraints**, not proof of null effect.

## 4. Stratified Reporting Architecture
All results will be presented with three separate reporting scopes:
1. **Stratum 1: Table-Bearing Stratum ($N=200$)**: Primary/secondary confirmatory outcomes and strict engineering guardrail compliance.
2. **Stratum 2: Prose-Only Stratum ($N=100$)**: Negative control cohort verifying zero spurious activation and zero context inflation.
3. **Combined Overview ($N=300$)**: Population-level secondary overview.
- **Anti-Dilution Guardrail**: Guardrails ($\le 10.0\%$ overhead, $\le 1$ regression) must be satisfied on Stratum 1 alone; combining strata to mask table overhead is prohibited.

## 5. Frozen Algorithms

### 5.1 Negative Constraint & Entity-Level Resolution
- Query parser detects exclusions: `r'\b(?:other\s+than|except|excluding|aside\s+from|besides|not\s+including)\s+([a-z0-9\s,\'-]+?)(?:\s+in|\s+for|\s+of|\?|$)'`
- Individual entities are resolved via direct lexical matching.
- Excluded groups/categories are resolved via document evidence:
  - *Layer 1*: Table structural hierarchy and category/type columns.
  - *Layer 2*: Document co-occurrence and Hearst hyponymy patterns.
  - *Layer 3*: Row annotations, footnotes, and notes columns.
- Resolved member entities are penalized/rejected in the candidate table, while eligible non-members remain selectable.
- *Ambiguity Fallback*: If group membership cannot be established from document evidence, record `UNRESOLVED_GROUP_AMBIGUITY`, do not claim exclusion success, enforce conservative fallback budget ($\le 3$ facts), and prioritize prose facts.

### 5.2 Typed Qualifier Matching & Global Row Scope
- Parse typed qualifiers separately: `Q_season`, `Q_episode`, `Q_rank`.
- Match `Q_episode` strictly against episode headers ($+10.0$ match bonus, $-5.0$ mismatch penalty to suppress Episode 1 when Episode 3 requested).
- Match `Q_season` strictly against season headers ($+5.0$ bonus).
- Score all candidate rows across the entire table so relevant rows at index 13 or 15 (e.g. Grey's Anatomy) can be selected on merit within strict output caps ($\le 5$ rows selected, $\le 10$ facts/table, $\le 15$ table facts/doc).
- Token counting matches production directly via `pack_context(...).tokens_used`.

## 6. Pre-Registered Acceptance Criteria Matrix

| Criterion | Type | Threshold | Cohort Scope | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **Parser Robustness** | Engineering | 0 unhandled exceptions; 100% valid provenance tags | All cohorts | Fatal: Halts evaluation |
| **Budget Compliance** | Engineering | Max 10 facts/table, max 15 table facts/doc, context $\le 2048$ tokens | All cohorts | Fatal: Disqualifies condition |
| **Context Overhead** | Engineering | $\le 10.0\%$ growth vs Condition A | **Table Stratum ($N=200$) only** | Guardrail breach: Flags bloat |
| **Cohort B Regressions** | Engineering | $\le 1$ Containment regression on $N=50$; $0$ EM regressions | Cohort B ($N=50$) | Guardrail breach: Falsifies safety |
| **Specific Regressions** | Engineering | `bad74caad5` (Lakes) and `51c8273468` (Flash) preserved correct | Diagnostic cases | Falsifies regression fix |
| **Primary Efficacy** | Scientific | Two-sided McNemar exact test $p < 0.05$ on Exact Match ($b > c$) | **Table Stratum ($N=200$)** | Confirms Efficacy |
| **Secondary Efficacy** | Scientific | Holm-corrected $p < 0.05$ across Containment & Context Reduction | Table Stratum ($N=200$) | Confirms Secondary Hypotheses |
