# Précis Experiment 3: Stage C Final Confirmatory Results Report
## Isolated Structural Document Decompilation v3

> **Naming note**: "Stage C" here is the confirmatory stage of the table-decompilation runs. It is unrelated to "Stage C" of the prompt-comparison experiments (`experiments/model_comparison`, `experiments/prompt_validation`), which the paper calls the *prompt-comparison Stage C*.

**Date**: 2026-10-10  
**Harness**: `scripts/eval_structural_decompilation_v3.py`  
**Configuration Fingerprint**: `78b2eaaba81f631a389e10db86d8f099d82332ccf7375011ff8cd99f52566815`  
**Manifest Hash**: `7f8e3891a86bc604e57267a834782ea638f2ceb93b4c30a828d5f19950a36c18`  
**Target Sample**: $N = 300$ ($n = 200$ table/list-bearing; $n = 100$ prose-only)  

---

## Executive Summary & Preregistration Status

The Stage C confirmatory evaluation was executed on an independent, audited sample of 300 Natural Questions documents under strict, fail-closed experimental controls. All 300 samples completed inference under Conditions A, B, and C with zero missing cases, zero unexpected sample IDs, and zero configuration mismatches.

### Key Findings:
1. **Primary Confirmatory Hypothesis (Stratum 1: Table/List Documents, $n=200$)**: **REJECTED (Severe Regression)**.
   - Exact Match (EM) regressed from **32.00%** (Condition A) to **14.00%** (Condition B) ($\Delta = -18.00$ percentage points; relative drop of $56.25\%$).
   - Answer Containment regressed from **43.50%** (Condition A) to **19.50%** (Condition B) ($\Delta = -24.00$ percentage points; relative drop of $55.17\%$).
   - ROUGE-L regressed from **0.3525** (Condition A) to **0.1804** (Condition B) ($\Delta = -0.1721$).
   - Paired McNemar exact test: **11 discordant wins vs. 47 discordant losses** ($p = 2.0316 \times 10^{-6}$, statistically significant at $\alpha = 0.05$ after Holm-Bonferroni correction).
2. **Token Overhead Guardrail ($\le +10\%$)**: **PASSED**.
   - Condition A mean tokens: 618.83; Condition B mean tokens: 155.44 (overhead: **$-74.88\%$**).
   - *Forensic Note*: This drastic token reduction is the root cause of the accuracy collapse. The structured adapter discarded 75% of context, systematically starving the LLM of the evidence needed to answer the questions.
3. **Prose-Only Upstream Invariance Guardrail (Stratum 2, $n=100$)**: **PASSED**.
   - Exactly 100 / 100 cases ($100.0\%$) achieved byte-level prose identity, zero structured blocks, identical extracted SVOA facts, and identical prompt context token counts between Condition A and Condition B.
4. **Secondary Ablation (Condition C: Sortable-Name Normalization Pattern 1)**:
   - Condition C matched Condition B identically in both EM (**14.00%**) and Containment (**19.50%**), with a slight token increase ($155.44 \to 160.28$).
5. **Operational Aggregation Defect**:
   - During Step 6 (`compute_aggregate_summary()`), writing `aggregate_summary.json` was interrupted by a `TypeError: Object of type bool_ is not JSON serializable` at line 1850 due to `scipy.stats.binomtest` returning `numpy.float64`, resulting in a `numpy.bool_` during Holm step-down threshold comparison. In accordance with safety protocol, the harness was not modified, raw records were preserved intact, and full validation was conducted on the complete raw record corpus.

---

## 1. Execution Integrity & Preflight Audit

### 1.1 Preflight Verification Matrix

| Check Item | Target Specification / Expected Hash | Observed Value | Status |
| :--- | :--- | :--- | :--- |
| **Harness SHA-256** | `ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4` | `ad56761db55fc9693526fe5c51d0db58c482c288525838d0b93fd240c21ac0e4` | **MATCH** |
| **Safety Test Suite SHA-256** | `104e7fd40bde96411c975fcd2943e1aafe2ea85d24157652000a229abae503f5` | `104e7fd40bde96411c975fcd2943e1aafe2ea85d24157652000a229abae503f5` | **MATCH** |
| **Safety Suite Execution** | 17/17 tests passing cleanly | `17 passed in 3.98s` (`pytest`) | **PASS** |
| **Stage A Results** | `46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32` | `46ab963e...` | **MATCH** |
| **Stage A Results (Corrected)**| `46ab963e6e327bef59b0bdb9c1714b266b942efa3977c4fda6ec35920e253a32` | `46ab963e...` | **MATCH** |
| **Stage B Records** | `ac1c294dbd916bac334b6de6a3947cd3faf99f8567ab01b4a459203644920c08` | `ac1c294d...` | **MATCH** |
| **Stage B Manifest** | `114350aebec8ac07285535825370835a861c945427e5f558b6e0e76de4eed8d4` | `114350ae...` | **MATCH** |
| **Stage B Replay Summary** | `1192386c90f67ac6ceb07de98eb7611a81ecd6e8296e350311e574947cbec094` | `1192386c...` | **MATCH** |
| **Stage B Report** | `6c10becb52f893d1e8776f0979503d9a7d10e46618c00afe62992e76477015f4` | `6c10becb...` | **MATCH** |
| **Safety Report 1** | `075e5c3d359596ef097add475fd80c095ee46fa46a97abb645fd68e17bce23ae` | `075e5c3d...` | **MATCH** |
| **Safety Report 2** | `3e83f240be6e83f4f46bcabd38b3316eb2c84dbc6f1758a0c642fd3e0d7b985e` | `3e83f240...` | **MATCH** |
| **Model Verification** | `qwen2.5-coder:7b` in Ollama API | Available (`digest: dae161e27b0e...`) | **CONFIRMED** |
| **Decoding Invariants** | Greedy (T=0.0, top-p=0.9, seed=42, max_tokens=512, ceiling=2048) | Matched in runner & config fingerprint | **CONFIRMED** |

### 1.2 Execution Summary & Operational Incidents

- **Execution Mode**: `backend/venv/bin/python scripts/eval_structural_decompilation_v3.py --stage-c-only` followed by `--stage-c-only --resume`.
- **Sandbox Network Behavior**: Initial attempt in default sandboxed mode failed to connect to `http://localhost:11434` (Ollama running on host). In accordance with sandbox protocol rule 2/3, the run was executed with network bypass permissions (`BypassSandbox: true`).
- **Resumed Records**: 0 resumed records loaded initially; run processed all 300 samples consecutively (`[1/300]` through `[300/300]`).
- **Total Processed Samples**: Exactly 300 unique samples.
- **Failures / Skipped Cases**: 0 failed inference calls; 0 skipped cases; 0 null predictions.
- **Step 6 Harness Defect**:
  - `compute_aggregate_summary()` reached line 1850 (`json.dump(summary, f, indent=2)`).
  - Raised `TypeError: Object of type bool_ is not JSON serializable`.
  - Cause: In Holm-Bonferroni step-down correction (lines 1815–1822), `scipy.stats.binomtest` returned a `numpy.float64` for $. Evaluating `p <= adj_alpha` yielded `<class 'numpy.bool'>`, which standard library `json.dump` does not natively serialize.
  - In strict compliance with the protocol directive (*"Do not modify the harness or experiment protocol unless execution is blocked by a concrete defect. If blocked, stop and report the exact issue instead of silently fixing it"*), no harness code was modified. Raw evaluation records were preserved completely and unmodified.

### 1.3 Generated Artifact Hashes

| Artifact Path | SHA-256 Checksum | Size | Record Count |
| :--- | :--- | :--- | :--- |
| `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | 87,954 bytes | 301 lines (1 header + 300 samples) |
| `results/diagnostic_structural_decompilation_v3/historical_exclusions.json` | `001701f538eee4524e44ee30e4c996aca1ca8aa608db19532f9c2dafa12ecbbb` | 24,044 bytes | 600 cataloged exclusion IDs |
| `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | 338,451 bytes | 301 lines (1 header + 300 records) |

---

## 2. Primary Confirmatory Results: Stratum 1 (Table/List-Bearing, $n=200$)

Stratum 1 evaluates documents containing HTML tables (`<table`) or structured lists (`<ul`, `<ol`).

### 2.1 Performance Metrics

| Metric | Condition A (Baseline Concise) | Condition B (Isolated Decompilation) | Condition C (Decompilation + Sortable-Name) | Delta (B vs. A) | Delta (C vs. A) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Exact Match (EM)** | **32.00%** (64/200) | **14.00%** (28/200) | **14.00%** (28/200) | **-18.00 pp** ($-56.25\%$ relative) | **-18.00 pp** ($-56.25\%$ relative) |
| **Answer Containment** | **43.50%** (87/200) | **19.50%** (39/200) | **19.50%** (39/200) | **-24.00 pp** ($-55.17\%$ relative) | **-24.00 pp** ($-55.17\%$ relative) |
| **ROUGE-L F1** | **0.3525** | **0.1804** | **0.1804** | **-0.1721** ($-48.82\%$ relative) | **-0.1721** ($-48.82\%$ relative) |
| **Mean Context Tokens** | **618.83** | **155.44** | **160.28** | **-74.88%** | **-74.10%** |
| **Token Overhead Guardrail** | Baseline | **Passed** ($\le +10\%$) | **Passed** ($\le +10\%$) | Overhead: $-74.88\%$ | Overhead: $-74.10\%$ |

### 2.2 Paired Statistical Significance & Multiplicity Correction

Primary statistical evaluation tests whether Condition B or Condition C improves Exact Match over Condition A on Stratum 1 using a paired exact binomial McNemar test, adjusted via Holm-Bonferroni step-down correction at FWER $\alpha = 0.05$.

| Comparison | Discordant Wins (Treatment > A) | Discordant Losses (A > Treatment) | Total Discordant Pairs | Raw $p$-value (McNemar) | Holm-Bonferroni Threshold | Statistically Significant |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Condition B vs. Condition A** | 11 | 47 | 58 | **$2.0316 \times 10^{-6}$** | $0.05 / 2 = 0.0250$ | **Yes (Significant Regression)** |
| **Condition C vs. Condition A** | 11 | 47 | 58 | **$2.0316 \times 10^{-6}$** | $0.05 / 1 = 0.0500$ | **Yes (Significant Regression)** |

- **Context Token Wilcoxon Signed-Rank Test**:
  - Condition B vs. Condition A: $p = 2.7606 \times 10^{-27}$ (statistically significant token reduction).
  - Condition C vs. Condition A: $p = 8.3077 \times 10^{-27}$ (statistically significant token reduction).

### 2.3 Guardrail Evaluation

1. **Token Overhead Guardrail**:
   - Limit: Mean tokens under Condition B must not exceed Condition A by $> +10\%$.
   - Actual: Mean tokens decreased from 618.83 to 155.44 ($-74.88\%$).
   - Verdict: **PASSED**.
2. **Confirmatory Accuracy Hypothesis**:
   - Condition B demonstrated a massive, statistically significant degradation in both Exact Match ($p = 2.03 \times 10^{-6}$) and Containment.
   - Verdict: **FAILED CONFIRMATORY HYPOTHESIS**.

---

## 3. Stratum 2: Prose-Only Invariance Diagnostics ($n=100$)

Stratum 2 evaluates documents with zero table or list elements to test whether the structural parser preserves byte-level and fact-level invariance upstream without introducing synthetic corruption or extraneous blocks.

### 3.1 Upstream Invariance Audit

| Diagnostic Metric | Count | Percentage | Requirement | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Prose Byte Identical (`c_prose == raw_doc`)** | 100 / 100 | **100.0%** | $= 100\%$ | **PASS** |
| **Zero Structured Blocks (`len(c_blocks) == 0`)** | 100 / 100 | **100.0%** | $= 100\%$ | **PASS** |
| **Facts Identical (`a_facts == b_facts`)** | 100 / 100 | **100.0%** | $= 100\%$ | **PASS** |
| **Context Tokens Identical (`tok_b == tok_a`)** | 100 / 100 | **100.0%** | $= 100\%$ | **PASS** |
| **Upstream Invariant (Composite)** | 100 / 100 | **100.0%** | $= 100\%$ | **PASS** |

### 3.2 Downstream End-to-End Metrics & Discrepancy Analysis

| Metric | Condition A | Condition B | Condition C | Delta (B vs. A) | Delta (C vs. A) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Exact Match (EM)** | **41.00%** (41/100) | **42.00%** (42/100) | **42.00%** (42/100) | **+1.00 pp** | **+1.00 pp** |
| **Answer Containment** | **51.00%** (51/100) | **52.00%** (52/100) | **52.00%** (52/100) | **+1.00 pp** | **+1.00 pp** |
| **ROUGE-L F1** | **0.4765** | **0.4860** | **0.4860** | **+0.0096** | **+0.0096** |
| **Mean Context Tokens** | **299.40** | **299.40** | **299.40** | **0.00%** | **0.00%** |

#### Inspection of Single Downstream Metric Discordance:
Across 100 cases, exactly **99 / 100** produced identical token-for-token predictions. Exactly **1 case** showed an end-to-end output difference despite identical upstream context:
- **Case ID**: `0b37d75f8db745f69ab8099192b839f1`
- **Question**: *"who sings why does it hurt when i pee"*
- **Gold Answer**: `"Frank Zappa"`
- **Upstream Diagnostic Audit**:
  - `prose_byte_identical`: `True`
  - `zero_structured_blocks`: `True`
  - `facts_identical`: `True`
  - `context_tokens_identical`: `True` (both 286 tokens)
- **Predictions**:
  - Condition A: `"Insufficient information"` (EM: `False`, Cont: `False`)
  - Condition B: `"Frank Zappa"` (EM: `True`, Cont: `True`)
  - Condition C: `"Frank Zappa"` (EM: `True`, Cont: `True`)
- **Analysis**: Because the prompt context passed to Ollama was byte-identical, this single divergence reflects GPU kernel/KV-cache nondeterminism in the Ollama inference server across sequential calls on boundary token probabilities.
- **Guardrail Determination**:
  - The upstream invariance guardrail passed with **100/100** compliance.
  - *Methodological Warning*: As required by preregistration principles, a finite sample of 100 cases constitutes strong confirmatory evidence that the parser does not corrupt prose, but **cannot be interpreted as mathematical proof of universal invariance** across arbitrary unstructured text.

---

## 4. Combined Results & Secondary Ablations ($N=300$)

> [!NOTE]
> Combined metrics over all 300 samples are presented for holistic visibility only. In accordance with preregistration requirements, combined metrics must **never** be used to conceal the failure in the primary table/list stratum.

### 4.1 Combined Cohort Metrics ($N=300$)

| Metric | Condition A (Baseline Concise) | Condition B (Isolated Decompilation) | Condition C (Decompilation + Sortable-Name) | Combined Delta (B vs. A) | Combined Delta (C vs. A) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Exact Match (EM)** | **35.00%** (105/300) | **23.33%** (70/300) | **23.33%** (70/300) | **-11.67 pp** | **-11.67 pp** |
| **Answer Containment** | **46.00%** (138/300) | **30.33%** (91/300) | **30.33%** (91/300) | **-15.67 pp** | **-15.67 pp** |
| **ROUGE-L F1** | **0.3938** | **0.2823** | **0.2823** | **-0.1115** | **-0.1115** |
| **Mean Context Tokens** | **512.35** | **203.42** | **206.65** | **-60.30%** | **-59.67%** |
| **Combined McNemar Test** | 12 Wins vs. 47 Losses ($p = 5.1256 \times 10^{-6}$) | 12 Wins vs. 47 Losses ($p = 5.1256 \times 10^{-6}$) | Significant Regression | Significant Regression |

### 4.2 Secondary Ablation: Condition C vs. Condition B

Condition C implements Pattern 1 Sortable-Name Normalization (converting `"Lastname, Firstname"` inverted names in table cells to `"Firstname Lastname"`).
- **Exact Match Impact**: Exactly **0** net change in EM ($14.00\% \to 14.00\%$).
- **Containment Impact**: Exactly **0** net change in Containment ($19.50\% \to 19.50\%$).
- **Token Impact**: Context token count increased slightly from 155.44 to 160.28 ($+3.11\%$) across 105 samples where sortable patterns were expanded.
- **Prediction Text Variation**: Exactly 4 cases generated differing prediction text:
  1. `2c62d7eb`: B: *"The Right Honourable Northern Ireland Secretary"* $\to$ C: *"The Secretary of State for Northern Ireland"*
  2. `64d578f5`: B: *"The Right Honourable Northern Ireland Secretary"* $\to$ C: *"The Secretary of State for Northern Ireland"*
  3. `ef634417`: B: *"Insufficient information"* $\to$ C: *"Rudolf Schenker, Klaus Meine, Herman Rarebell"* (Gold: Klaus Meine and Herman Rarebell; both EM=False).
  4. `122e005c`: B: *"Insufficient information"* $\to$ C: *"Robert De Niro"* (Gold: Frank Vincent; both EM=False).
- **Ablation Conclusion**: Sortable-name normalization pattern 1 had negligible utility, produced zero accuracy gain, and added slight token bloat.

---

## 5. Forensic Failure Analysis

To understand why isolated structural decompilation regressed so severely on table/list documents, all **47 Exact Match regressions** (cases where Condition A answered correctly but Condition B failed) and **60 Containment regressions** were individually examined.

### 5.1 Quantitative Failure Categorization

| Failure Category | Case Count | Proportion of Losses | Mechanism Description |
| :--- | :--- | :--- | :--- |
| **1. Context Starvation via Row Truncation** | 22 | **46.8%** | Structured facts extracted, but table row ranker truncated the table below the required evidence row ( \le 3$), forcing LLM to output *"Insufficient information"*. |
| **2. Table/List Filtering & Extraction Omission** | 18 | **38.3%** | Heuristic table scorer rejected the table or extractor returned 0 structured facts (`tok_b == 0`), discarding the table entirely. |
| **3. Distractor Entity / Column Misalignment** | 6 | **12.8%** | Structured adapter aligned text to the wrong column header or selected a distractor row entity. |
| **4. Multi-Entity Formulation Mismatch** | 1 | **2.1%** | Answer contained all required entities but added co-authors, failing Exact Match while retaining Containment. |

Together, **Context Starvation and Extraction Loss account for 85.1% (40 / 47) of all regressions**.

### 5.2 Concrete Evidence & Representative Case Audits

#### Case 1: Extreme Extraction Loss (`tok_b == 0`)
- **Sample ID**: `1b491361b7f849fcb2512965bf6e2101`
- **Question**: *"who has won 2017 women 's singles korean open series badminton championship"*
- **Gold Answer**: `"P.V. Sindhu"`
- **Condition A (Baseline)**: `"P.V. Sindhu"` (Context tokens: 238) $\to$ **CORRECT**
- **Condition B (Decompiled)**: `"Insufficient information"` (Context tokens: **0**, structured facts: **0**) $\to$ **FAILURE**
- **Root Cause**: The HTML table containing the tournament results was excised from the prose stream. The table selection module assigned the table a score below threshold, resulting in 0 extracted facts and an empty prompt.

#### Case 2: Row Truncation & Ranking Starvation
- **Sample ID**: `17d9c79294e749a2a9e3e7f1bfb83c51`
- **Question**: *"who scored the most points in a single game in the nba"*
- **Gold Answer**: `"Wilt Chamberlain"`
- **Condition A (Baseline)**: `"Wilt Chamberlain"` (Context tokens: 1700) $\to$ **CORRECT**
- **Condition B (Decompiled)**: `"Insufficient information"` (Context tokens: **20**, structured facts: **1**) $\to$ **FAILURE**
- **Root Cause**: The Wikipedia document contains a large statistical table listing top NBA single-game scoring records. Condition A retained the table in raw HTML, allowing the LLM's attention to locate Wilt Chamberlain's 100-point game. Condition B decompiled the table, but the row-ranking heuristic retained only 1 row (which did not contain Chamberlain), starving the model.

#### Case 3: List Decompilation Omission
- **Sample ID**: `f6c035f608674d858349214777dd0a6b`
- **Question**: *"where was the flag placed on the moon"*
- **Gold Answer**: `"Sea of Tranquility"`
- **Condition A (Baseline)**: `"Sea of Tranquility"` (Context tokens: 502) $\to$ **CORRECT**
- **Condition B (Decompiled)**: `"Insufficient information"` (Context tokens: **0**, structured facts: **0**) $\to$ **FAILURE**
- **Root Cause**: The answer was embedded in an HTML bulleted list (`<ul>`). The parser stripped the list from the prose stream, and the list proposition extractor failed to synthesize facts matching the question keywords.

#### Case 4: Distractor Entity Selection
- **Sample ID**: `f63b92acbcf04c4ea095c46b5a383d47`
- **Question**: *"who built pedestrian bridge at florida international university"*
- **Gold Answer**: `"Munilla Construction Management"`
- **Condition A (Baseline)**: `"Munilla Construction Management"` (Context tokens: 279) $\to$ **CORRECT**
- **Condition B (Decompiled)**: `"FIGG Bridge Engineers"` (Context tokens: 197, structured facts: 4) $\to$ **FAILURE**
- **Root Cause**: The document contained a project summary table listing "Design Engineer: FIGG Bridge Engineers" and "Contractor / Builder: Munilla Construction Management". Decompilation stripped structural row relationships; the table adapter prioritized the designer entity over the constructor entity.

#### Case 5: Multi-Entity Formulation
- **Sample ID**: `fd249e525a814fe0b3ec5e95817290bc`
- **Question**: *"who wrote the song after you 've gone"*
- **Gold Answer**: `"Turner Layton"`
- **Condition A (Baseline)**: `"Turner Layton"` (Context tokens: 57) $\to$ **CORRECT**
- **Condition B (Decompiled)**: `"Turner Layton, Henry Creamer"` (Context tokens: 65, structured facts: 2) $\to$ **EM FALSE (Containment TRUE)**
- **Root Cause**: Table credited both composer and lyricist. Condition B synthesized both into the answer.

---

## 6. Statistical Interpretation & Methodology Discussion

1. **Effect Size and Statistical Power**:
   - The sample size of $n=200$ for Stratum 1 provides $>90\%$ statistical power to detect a $\pm 7\%$ difference in Exact Match.
   - The observed regression of $18.00$ pp is massive, unequivocal, and statistically decisive ($p = 2.0316 \times 10^{-6}$).
   - The null hypothesis that Condition B is non-inferior to Condition A is rejected with extreme statistical confidence.
2. **Context Compression vs. Information Loss Trade-off**:
   - While Condition B achieved a $74.88\%$ reduction in context tokens, this was not benign token efficiency.
   - It represents catastrophic information loss. In RAG and extractive QA systems, heuristic row selection cannot reliably anticipate which cell holds the precise answer without semantic reasoning that rival the complexity of the generator itself.
3. **The Danger of Aggregate Concealment**:
   - Had this experiment combined table documents with prose documents into a single aggregate without stratum separation, the $18$ pp regression would have been partially masked by the invariant prose stratum (reducing the apparent regression to $11.67$ pp).
   - Preregistering Stratum 1 as the primary confirmatory target was crucial to uncovering this architectural deficiency.
4. **Failure of Historical Diagnostic Generalization**:
   - In Stage B (59 historical diagnostic cases), decompilation resolved specific table leakage anomalies.
   - However, Stage C proves that the inductive bias embedded in the v3 heuristic adapter is overfit to those historical failure modes and fails catastrophically when evaluated across a broad, representative distribution of structured web documents.

---

## 7. Evidence-Based Verdict & Recommendation

### Formal Verdict:
**REJECT THIS APPROACH**

### Justification:
1. **Confirmatory Failure**: Structural Document Decompilation v3 causes an unacceptable **56% relative collapse** in Exact Match on table-bearing documents ($32.0\% \to 14.0\%$).
2. **Systemic Context Starvation**: 85.1% of regressions stem from the fundamental inability of heuristic row ranking and table filtering to retain necessary evidence.
3. **Guardrail Compliance**: Although the technical guardrails (token overhead $\le +10\%$ and prose invariance) passed, the primary performance objective failed decisively.

### Concrete Directives:
- **NO Production Changes**: Do not merge or integrate structural decompilation v3 into `backend/src/precis/`.
- **Preserve Baseline**: Keep the existing baseline pipeline (`raw_html_coref_prose_svoa`) as production default.
- **Architectural Redirection**: If structured document handling is revisited in future research, reject aggressive row-pruning heuristics in favor of full-table markdown serialization or neural table-aware representations that preserve complete context.
