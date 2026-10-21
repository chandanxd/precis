# Experiment 4.7: Confirmatory Evaluation Protocol Design

**Document Identifier:** `evaluation_plan_exp_4_7`  
**Date:** 2026-10-11  
**Status:** PROTOCOL DESIGN ONLY (No inference or benchmark execution permitted)  
**Objective:** Define a rigorous, leak-free confirmatory evaluation protocol for testing the remediations proposed in Experiment 4.6.

---

## 1. Experimental Design and Cohort Partitioning

To avoid overfitting against the 13 diagnosed regression cases and maintain strict methodological validity, the evaluation dataset will be partitioned into two distinct cohorts:

```
Total Available Natural Questions Dataset (NQ-Dev)
                  |
    +-------------+-------------+
    |                           |
Development Cohort          Untouched Confirmatory Cohort
(N = 50 cases)              (N = 150 table-bearing + 50 prose-only = 200 cases)
- 13 diagnosed regressions  - 150 unseen table-bearing cases from Gate 5
- 17 concordant table cases - 50 clean prose-only cases (negative control)
- 20 prose-only cases       - Strictly untouched during tuning/diagnosis
```

### 1.1 Development Cohort ($N=50$)
- **Purpose:** Used during engineering implementation for iteration, local regression checks, and deterministic unit testing.
- **Composition:**
  - All 13 diagnosed Gate 5 regressions (`93078684`, `f89cf8b1`, `8b41e651`, `b786366c`, `44408e37`, `d84f0eaa`, `cf2d77b0`, `ef634417`, `0541c730`, `e44f257a`, `1e07903c`, `5868443c`, `42d98889`).
  - 17 randomly sampled concordant cases where Condition F was already successful in Gate 5.
  - 20 prose-only cases from `sample_manifest.jsonl` to ensure SVOA-only workflows are not degraded.

### 1.2 Untouched Confirmatory Cohort ($N=200$)
- **Purpose:** Final, independent validation of remediation efficacy.
- **Composition:**
  - **150 Table-Bearing Cases:** The remaining 150 table-bearing cases from Gate 5 Phase 2 that were never inspected or tuned against.
  - **50 Prose-Only Cases:** Drawn from `sample_manifest.jsonl` (Stratum 2) to serve as a negative control for detecting unintended side-effects on standard prose RAG.
- **Rules of Engagement:** Strictly quarantined. Zero hyperparameter tuning, prompt tailoring, or inspection of error cases against this cohort before final evaluation.

---

## 2. Frozen Historical Baselines

All historical results from Gate 5 Phase 2 will be preserved as immutable frozen baselines:
- **Condition A (Plain Vector RAG):** 32.0% EM (64/200), 43.5% Containment (87/200).
- **Condition D (Pure SVOA Facts, $\theta=0.0$):** 49.5% EM (99/200), 61.0% Containment (122/200).
- **Condition E (Ideal Programmatic Upper Bound):** 54.0% EM (108/200), 68.5% Containment (137/200).
- **Condition F (Gate 5 Production Baseline):** 52.5% EM (105/200), 65.5% Containment (131/200).

The newly remediated candidate path will be designated **Condition F' (Remediated Production Path)**.

---

## 3. Pre-Registered Hypotheses and Acceptance Thresholds

### 3.1 Primary Metric: Exact Match (EM)
- **Criterion 1 (Superiority over Production Baseline):**
  On the 150 untouched table-bearing cases, Condition F' must achieve a net gain over Condition F of at least $+2.0$ percentage points ($p < 0.05$ or net positive wins $\ge 5$).
- **Criterion 2 (Parity with Ideal Upper Bound):**
  Across the full 200 table-bearing cohort, Condition F' must achieve $\text{EM} \ge 54.0\%$ (matching or exceeding Condition E's 54.0% rate).

### 3.2 Secondary Metric: Prose-Only Regression Tolerance
- **Criterion 3 (Zero Regression on Prose-Only Queries):**
  On the 50 prose-only control cases, Condition F' must exhibit $\le 1$ regression against Condition A/D baseline ($p > 0.50$). This guarantees that prioritizing structural tables does not degrade ordinary text retrieval.

### 3.3 Telemetry and Operational Budgets
- **Token Ceiling:** Strict limit of 2,048 estimated context tokens. Exactly **0 ceiling violations allowed**.
- **Context Availability:** Exactly **0 zero-context cases**.
- **Inference Latency:** Mean generation latency must remain within $10\%$ of Gate 5 baseline ($\le 800\text{ ms}$).

---

## 4. Hyperparameter and Environment Controls

To guarantee bit-level reproducibility and eliminate confounders, all execution settings are frozen identically to Gate 5:
- **Model:** `qwen2.5-coder:7b` via local Ollama daemon.
- **Decoding Strategy:** Greedy decoding ($T = 0.0$, $\text{top-p} = 0.9$, $\text{seed} = 42$).
- **Generation Budget:** Maximum 512 completion tokens.
- **Context Estimator:** Heuristic character count: $\text{estimate\_text\_tokens}(s) = \text{len}(s) // 4$.
- **Prompt Template:** Canonical `concise` prompt template:
  ```
  Answer the following question based on the provided context. Be as concise as possible. If the context does not contain the answer, say "Insufficient information".
  
  Context:
  {context}
  
  Question: {query}
  Answer:
  ```

---

## 5. Statistical Analysis Plan

All comparisons will be conducted paired case-by-case:
1. **Paired McNemar Exact Test:** Two-sided binomial test on discordant pairs between Condition F' and Condition F, and between Condition F' and Condition D.
2. **Confidence Intervals:** 95% Wald and exact binomial confidence intervals for net difference in proportions:
   $$\text{CI}_{95\%} = \frac{b - c}{n} \pm 1.96 \sqrt{\frac{b + c - \frac{(b - c)^2}{n}}{n^2}}$$
3. **Subgroup Strata Analysis:**
   - Stratum 1: Historical Stage C regressions ($N=47$). Recovery target: $\ge 85\%$.
   - Stratum 2: Gate 2 list-bearing subset ($N=31$). Target: maintain $35.48\%$ ($11/31$).
4. **Mandatory Case-by-Case Regression Audit:**
   Any case where Condition F was correct but Condition F' failed must undergo an immediate root-cause audit before acceptance.

---

## 6. Pre-Registered Stop Rules and Abort Conditions

The evaluation runner must automatically halt and declare an evaluation failure if:
1. **Material Prose Regression:** Condition F' suffers $\ge 3$ net losses against baseline on the 50 prose-only cases.
2. **Budget Breach:** A single case exceeds the 2,048 estimated context token limit.
3. **Empty Output Drift:** The model produces $> 2$ empty or unparseable completions.
4. **Configuration Drift:** Any discrepancy in model checksum, temperature, prompt formatting, or scoring functions.

---

## 7. Feature Flag Production Safeguard

Under all circumstances:
- The feature flag `PRECIS_ENABLE_LIST_EXTRACTION` must remain **`False` by default** in production code (`backend/src/precis/pipeline/structural.py`).
- Enabling the feature flag globally requires separate, explicit authorization after successful completion of the confirmatory evaluation.
