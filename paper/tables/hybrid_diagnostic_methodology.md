# Précis Hybrid Diagnostic Experiment Methodology

**Document Status**: Authoritative Research Methodology  
**Target Hypothesis**: $H_{\text{HYBRID}}$ (Decomposed into $H_{\text{HYBRID\_A}}$, $H_{\text{HYBRID\_B}}$, and $H_{\text{HYBRID\_C}}$)  
**Evaluation Scope**: 40 Outcome-Selected Discordant Cases from Natural Questions MRQA Benchmark ($N = 200$, seed 42): 29 Deficit Cases and the Legacy 11-Case Diagnostic Cohort (containing 10 verified historical Précis-only wins and one evaluation/selection artifact)  
**Codebase State**: Read-Only Execution; Zero Modifications to `backend/src/precis/`  

---

## 1. Research Objective & Scientific Scope

The Précis evaluation integrity audit established that Précis Full achieves **70.5% (141/200)** answer containment and **19.0% (38/200)** Exact Match on the Natural Questions benchmark, trailing conventional passage-based Naive RAG (**79.5%** containment, **28.5%** Exact Match). Across the 200 questions:
- Naive RAG answered correctly on **29 questions** where Précis failed (**Deficit Cohort**, $N = 29$).
- Précis demonstrated isolated advantages on a **Legacy 11-Case Diagnostic Cohort**, which subsequent metric auditing revealed contains **10 verified historical Précis-only wins** under the canonical single-reference metric, alongside one legacy selection/annotation artifact (`c4691863`).

### The Diagnostic Objective:
To test whether selectively restoring originating source spans for cases where SVOA propositional extraction failed can diagnose how much of the observed Naive-only deficit is attributable to **upstream representation loss** versus **downstream LLM reasoning**.

### Crucial Epistemic Boundary & Disclaimers:
1. **Not a General Benchmark Evaluation**: This experiment is conducted strictly on outcome-selected discordant cases. It does **not** measure general open-domain QA performance.
2. **Not a Benchmark Superiority Claim**: It does **not** claim that a hybrid system outperforms Naive RAG or improves general benchmark accuracy.
3. **Not a Hallucination Reduction Claim**: No general hallucination reduction is claimed, as no dedicated hallucination benchmark is evaluated.
4. **Mechanistic Diagnostic Only**: It serves solely as an inspectable diagnostic probe of source-span recoverability and distractor vulnerability under controlled interventions.

---

## 2. Selection Bias Disclosure & Cohort Definitions

> **Mandatory Disclosure**:  
> *"This experiment is a mechanistic diagnostic on outcome-selected discordant cases and is not an unbiased estimate of general benchmark performance."*

The 29 deficit cases and 11 legacy diagnostic cohort cases were identified *post-hoc* because they exhibited divergent outcomes between Naive RAG and Précis v3. Consequently:
- The repair rate on the 29 deficit cases represents the **recoverability of known representation failures**, not the expected recovery rate across the broader Natural Questions distribution.
- The retention rate on the legacy diagnostic cohort measures **vulnerability to distractor reintroduction**, not general precision preservation across unselected queries.

### Cohort Definitions & Denominators:
1. **Deficit Cohort ($N = 29$)**: Verified cases where Naive RAG succeeded and Précis v3 failed under containment.
2. **Legacy 11-Case Diagnostic Cohort ($N = 11$)**: The full 11-record legacy evaluation set preserved for exact trace reproducibility.
3. **Verified Historical Wins ($N = 10$)**: The 10 cases within the legacy cohort confirmed correct under the canonical single-reference metric (`gold_answer`).
4. **Legacy Selection/Annotation Artifact ($N = 1$, `c4691863`)**: A record admitted by the historical failure analysis script because its alternative-answer logic accepted character names (`"Foofa"`, `"Brobee"`) as answers to a question asking who plays the characters. The canonical benchmark evaluates against the primary reference answer (`"DJ Lance Rock"`), which the model's answer omitted.
5. **Synchronous-Baseline-Win Cohort ($N = 10$)**: The 10 cases in the legacy cohort evaluated as correct under the synchronous V3 rebaseline run. (Distinct definition from verified historical wins, though sharing the same 10 samples).

---

## 3. The Three-Part Decomposed Diagnostic Framework

```
+----------------------------------------------------------------------------------------------------+
|                         THE THREE-PART HYBRID EXPERIMENTAL FRAMEWORK                               |
+----------------------------------------------------------------------------------------------------+
| EXPERIMENT A: HYBRID-ORACLE-SPAN (Representation Usability Diagnostic)                             |
|   - Cohort: ONLY the 29 Deficit Cases (Naive Won, Précis Failed)                                   |
|   - Objective: Test whether a 7B LLM can utilize an audited originating source span to repair     |
|                known SVOA extraction loss.                                                         |
|   - Mechanism: Injects audited originating sentence, table row, or list item.                      |
|   - Primary Metric: Oracle-Span Repair Rate (b / 29).                                              |
|   - Boundary: Characterizes source-span recoverability under the tested oracle intervention;       |
|               does not establish mutually exclusive causal attributions for individual errors.     |
+----------------------------------------------------------------------------------------------------+
| EXPERIMENT B: PRECISION-PRESERVATION STRESS TEST (Distractor Vulnerability Diagnostic)             |
|   - Cohort: Legacy 11-Case Diagnostic Cohort (10 verified historical wins + 1 selection artifact)   |
|   - Objective: Test whether adding source text reintroduces distractors and causes regressions     |
|                on cases where Précis's relational isolation succeeded.                             |
|   - Mechanism: Non-oracle dense MiniLM retrieval over candidate document units.                    |
|   - Budget: Estimated-token budget matched Tokens_est(Hybrid) <= Tokens_est(V3 Rebaseline).        |
|   - Primary Metrics: Verified-Win Retention Rate (7/10, 70.0%) and Regression Rate (3/10, 30.0%).  |
|                      (Coverage across all 11 records reported with artifact accounted for).        |
+----------------------------------------------------------------------------------------------------+
| EXPERIMENT C: HYBRID-RETRIEVED-SPAN (End-to-End Span Discovery Diagnostic)                         |
|   - Cohort: 29 Deficit Cases (Primary); 40 Discordant Cases (Secondary).                           |
|   - Objective: Decompose downstream outcomes into span retrieval misses, context-admission         |
|                budget fallbacks, and generator failures.                                           |
|   - Mechanism: Independent query-to-span retriever using all-MiniLM-L6-v2 without gold access.     |
|   - Budget: Estimated-token budget matched Tokens_est(Hybrid) <= Tokens_est(V3 Rebaseline).        |
|   - Primary Metric: Successful Recovery Rate & Four-Way Mutually Exclusive Decomposition:          |
|                     Top-Ranked Retrieval Miss vs Context Admission Failure vs                      |
|                     Retrieved-Evidence Generation Failure vs Successful Recovery.                  |
+----------------------------------------------------------------------------------------------------+
```

---

## 4. Synchronous V3 Rebaseline Control & Generation Behavior

To prevent generation confounds arising from environmental drift between historical benchmark logs and current test runs, **Condition 1 (V3-REBASELINE)** was executed simultaneously alongside the hybrid conditions for all 40 discordant cases:
- Model: `qwen2.5-coder:7b` via local Ollama
- Decoding: `temperature = 0.0` (greedy decoding), `top_p = 0.9`, `max_tokens = 512`, `seed = 42`
- Context Ceiling: `2048` estimated tokens
- Prompt Template: Exact frozen `PROMPT_TEMPLATE` from `backend/src/precis/pipeline/inference.py`

### Baseline Verification Findings:
1. **Identical Generation on Legacy Diagnostic Cohort**: For all 11 cases, the generated text in the synchronous rebaseline is 100% byte-for-byte identical to the canonical historical V3 output.
2. **Single-Gold Evaluation on Sample `c4691863`**: Both historical and rebaseline text omit `"Rock"`, evaluating to 0/1 under strict single-gold containment against `"DJ Lance Rock"`.
3. **Minor Floating-Point Phrasing Drift on Deficit Cohort**: On 5 of 29 deficit cases, minor token variation occurred (e.g., "mentioned in the given facts" vs "mentioned in the facts"), although correctness remained 0/29 across both runs. Unqualified claims of absolute system-level determinism are avoided; greedy decoding limits but does not eliminate minor numerical drift across kernel invocations.

---

## 5. Context-Budget Governance: Estimated-Token Budget Parity

Because Précis contexts are already +56.4% longer in words than Naive RAG, any hybrid representation must not gain an advantage simply by expanding context length.

### The Budget Heuristic:
$$\text{Tokens}_{\text{est}}(\text{Context}_{\text{hybrid}}) \le \text{Tokens}_{\text{est}}(\text{Context}_{\text{v3\_rebaseline}})$$

### Accounting Method:
- **Token Estimation Formula**: Standard benchmark word-based heuristic $\text{Tokens}_{\text{est}} = \lfloor \text{Words} \times 1.3 \rfloor$, matching `backend/src/precis/evaluation/harness.py`.
- **Distinction from Native Tokenizer**: This estimator is a standardized proxy used for budget parity across benchmark conditions; it **does not guarantee native token-ceiling compliance** with the model's native BPE tokenizer (`Qwen2Tokenizer`). We therefore describe the conditions as **estimated-token budget matched** rather than strictly token matched.

### Enforcement Procedure & Fallback Rule:
1. Measure the exact context token footprint of the synchronous V3 rebaseline ($T_{\text{baseline}}$).
2. Rank SVOA candidate facts via standard SDH score.
3. Attach the candidate source span.
4. If the combined facts + span exceed $T_{\text{baseline}}$, greedily drop SVOA facts from the lowest rank until the total token count fits within $T_{\text{baseline}}$.
5. **Fallback Rule**: If the candidate span alone exceeds $T_{\text{baseline}}$ (e.g. baseline had only 1 fact of 23 tokens or 0 facts, while the span is 35 tokens), the algorithm falls back to the baseline facts alone to prevent inflating the context budget.
   - **Classification**: When fallback occurs, the generator does not receive the retrieved span. Cases where the span contained gold evidence but was excluded by this rule are classified as **`CONTEXT_ADMISSION_FAILURE`** (`BUDGET_FALLBACK`), rather than generation failures.

---

## 6. Diagnostic Outcome Taxonomy

Every evaluated case is categorized under a strict, observable failure taxonomy grounded in logged evidence:

| Outcome Category | Operational Definition | Applicable Experiments |
| :--- | :--- | :---: |
| **`SUCCESSFUL_RECOVERY`** | Hybrid answer satisfies word-boundary normalized containment of the gold answer on a baseline deficit case. | Exp A, Exp C |
| **`RETAINED_VERIFIED_WIN`** | Hybrid answer satisfies containment on a verified historical or rebaseline win case. | Exp B, Exp C |
| **`TOP_RANKED_SPAN_RETRIEVAL_MISS`** | Independent MiniLM retriever ranked a top-1 span that did not contain the gold answer text under normalized containment. | Exp C |
| **`CONTEXT_ADMISSION_FAILURE`** | Top-ranked span contained the gold answer, but could not be admitted into the context prompt because the span alone exceeded the baseline budget ($T_{\text{baseline}} < T_{\text{span}}$); generator received baseline facts/empty context. | Exp C |
| **`RETRIEVED_EVIDENCE_GENERATION_FAILURE`** | Top-ranked span contained the gold answer, was successfully admitted into the prompt within the estimated-token budget, but the generated answer was incorrect. | Exp C |
| **`VERIFIED_WIN_REGRESSION`** | A verified baseline win becomes incorrect under the hybrid prompt. | Exp B, Exp C |
| **`LEGACY_SELECTION_ARTIFACT`** | A case in the legacy 11-record cohort that was not correct under canonical single-reference containment in either baseline or hybrid. | Exp B, Exp C |
| **`ORACLE_UNRECOVERED`** | Deficit case remains incorrect despite receiving the audited gold originating span. | Exp A |

---

## 7. Metrics & Measurement Standards

1. **Answer Containment Correctness (Single-Gold)**: Word-boundary normalized substring containment (`contains_answer(pred, gold_answer)`).
2. **Answer Containment Correctness (Multi-Alias)**: Multi-answer alias containment (`is_answer_correct(pred, gold_answer, answers=alts)`).
3. **Exact Match (EM)**: Normalized exact string equality (`compute_exact_match`).
4. **ROUGE-L**: Longest common subsequence F1 (`compute_rouge_l`).
5. **DeBERTa BERTScore**: Token-level contextual F1 using `microsoft/deberta-large-mnli` (`compute_bert_score`).
6. **Context Token Accounting**: Word count $\times 1.3$ estimated tokens, matched against rebaseline.
