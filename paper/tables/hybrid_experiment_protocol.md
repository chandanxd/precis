# Précis Research Evaluation: Three-Part Hybrid Diagnostic Protocol ($H_{\text{HYBRID}}$)

**Document Status**: Authoritative Pre-Implementation Experimental Specification (Version 3.0 Final)  
**Date**: October 9, 2026  
**Target Hypothesis**: $H_{\text{HYBRID}}$ (Decomposed into $H_{\text{HYBRID\_A}}$, $H_{\text{HYBRID\_B}}$, and $H_{\text{HYBRID\_C}}$)  
**Target Cohort**: 40 Outcome-Selected Discordant Samples from Frozen v3 NQ Benchmark ($N=200$, Seed 42)  
**Execution Architecture**: Standalone Offline Evaluation Script (`scripts/eval_hybrid_diagnostic.py`)  
**Strict Implementation Invariant**: **ZERO** modifications to `backend/src/precis/`, **ZERO** test changes, **ZERO** benchmark overwrites.

---

## 1. Executive Summary & Experimental Separation

To address the methodological limitation of conflating oracle usability, precision preservation, and independent retrieval into a single compound evaluation, this protocol decomposes the investigation of $H_{\text{HYBRID}}$ into **three logically and statistically independent experiments**:

```
+----------------------------------------------------------------------------------------------------+
|                         THE THREE-PART HYBRID EXPERIMENTAL FRAMEWORK                               |
+----------------------------------------------------------------------------------------------------+
| EXPERIMENT A: HYBRID-ORACLE-SPAN (Usability Diagnostic)                                            |
|   - Cohort: ONLY the 29 Deficit Cases (Naive Won, Précis Failed)                                   |
|   - Question: Can the 7B LLM use a correct source span to repair representation loss?               |
|   - Mechanism: Audited originating sentence/table-row injection (Oracle Usability Probe)          |
|   - Primary Metric: Failure Repair Rate (b / 29)                                                   |
+----------------------------------------------------------------------------------------------------+
| EXPERIMENT B: PRECISION-PRESERVATION STRESS TEST (Distractor Vulnerability Diagnostic)             |
|   - Cohort: ONLY the 11 Win Cases (Précis Won, Naive Failed)                                       |
|   - Question: Does adding source text reintroduce distractors and destroy relational precision?     |
|   - Mechanism: Non-oracle span selection rule (no gold labels, no manual audit)                    |
|   - Primary Metric: Win Retention Rate (r / 11) & Regression Rate (s / 11)                         |
+----------------------------------------------------------------------------------------------------+
| EXPERIMENT C: HYBRID-RETRIEVED-SPAN (End-to-End Span Discovery Diagnostic)                         |
|   - Cohort: 29 Deficit Cases (Primary); All 40 Discordant Cases (Secondary)                        |
|   - Question: Can an independent sentence retriever locate useful spans without SVOA provenance?   |
|   - Mechanism: Dense sentence cosine similarity (all-MiniLM-L6-v2) on document spans               |
|   - Primary Metric: Source-Span Retrieval Success Rate & Downstream Repair Rate                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Decomposed Causal Hypotheses

The investigation explicitly tests three distinct subclaims rather than a monolithic "hybrid QA accuracy" claim:

- **$H_{\text{HYBRID\_A}}$ (Representation Usability)**:  
  *When an answer-bearing source span is explicitly provided alongside structured SVOA facts, a local 7B generator can successfully synthesize factual answers that were omitted or truncated during syntactic proposition extraction.* (Tested primarily by **Experiment A**).
- **$H_{\text{HYBRID\_B}}$ (Relational Precision Preservation)**:  
  *Adding source text spans to structured evidence does not reintroduce narrative distractors or substantially degrade the relational precision isolation that enables Précis to outperform Naive RAG on distractor-heavy queries.* (Tested primarily by **Experiment B**).
- **$H_{\text{HYBRID\_C}}$ (Independent Span Discoverability)**:  
  *A deterministic, query-adaptive sentence-level retriever can discover the textual spans required to repair proposition extraction failures without relying on SVOA provenance or gold annotations.* (Tested primarily by **Experiment C**).

---

## 3. Cohort Definitions & Selection Bias Governance

The evaluation cohort consists strictly of the **40 discordant samples** from the frozen v3 Natural Questions benchmark ($N = 200$, seed 42):
- **Deficit Cohort ($N = 29$)**: Questions where Naive RAG produced a containment-correct answer, but Frozen Précis Full v3 failed.
  - 15 Complete SVOA Extraction Omissions (0 answer-bearing facts extracted)
  - 6 Incomplete Predicate Complements (truncated arguments / appositives)
  - 7 Downstream Local LLM Reasoning Failures (facts delivered, 7B model chose distractor)
  - 1 String Containment Metric Artifact (model generated "in 1980", gold required full phrase)
- **Win Cohort ($N = 11$)**: Questions where Précis Full v3 produced a containment-correct answer, but Naive RAG failed due to narrative distractor confusion.

### Formal Selection Bias Disclosure
- **What this cohort CAN answer**: 
  1. Whether providing source text repairs known representation failures.
  2. Whether adding source text causes regressions on known Précis precision wins.
  3. Whether independent sentence retrieval can locate the necessary spans in those known failure cases.
- **What this cohort CANNOT answer**:
  1. General open-domain QA accuracy on Natural Questions.
  2. Unbiased benchmark leaderboard ranking.
  3. Generalization to unseen corpora or non-factual domains.

---

## 4. Identical Experimental Controls & V3 Re-Baselining

To eliminate generation confounds and prevent comparing new hybrid outputs against historical benchmark runs under mismatched parameters, the experiment requires a simultaneous generation of **Condition 1 (V3-REBASELINE)** alongside the hybrid conditions.

### Exact Hardware and Decoding Parameters (Identical Across All Conditions):
- **Generator**: Local Ollama serving `qwen2.5-coder:7b`
- **Decoding Temperature**: `0.0` (strict greedy decoding)
- **Top-p Sampling**: `0.9` (matching authoritative v3 benchmark metadata; do NOT change to 1.0)
- **Max Generation Tokens**: `512` (matching authoritative v3 benchmark metadata; do NOT reduce to 128)
- **Deterministic Seed**: `42`
- **Context Ceiling**: `2048` tokens
- **Vector Embeddings**: Frozen `sentence-transformers/all-MiniLM-L6-v2`
- **Prompt Wrapper & Grounding Rules**: Identical to `backend/src/precis/pipeline/inference.py`

---

## 5. Token-Budget Control: Token-Matched Representation Comparison

Because Précis contexts are already +56.4% longer in tokens than Naive RAG, the hybrid condition must not gain an advantage simply by receiving more context tokens.

### The Token-Matched Invariant:
$$	ext{Tokens}(	ext{Context}_{\text{hybrid}}) \le \text{Tokens}(	ext{Context}_{\text{v3\_rebaseline}})$$

### Deterministic Packing Algorithm:
1. For each query, measure the exact context token count of the V3-REBASELINE condition ($T_{\text{baseline}}$).
2. Rank candidate SVOA facts via standard SDH score.
3. For each candidate fact, attempt to attach its corresponding source span (audited span in Exp A, top retrieved span in Exp B/C).
4. If the combined (Fact + Span) exceeds the remaining budget up to $T_{\text{baseline}}$, attach the structured fact alone if it fits; otherwise stop packing.
5. Record per-sample telemetry: V3 context tokens, Hybrid context tokens, token delta, facts packed, spans packed, and span omission events.
6. **Terminology Governance**: Strictly call this a **token-matched representation comparison**. Do NOT use the word "compression".

---

## 6. Detailed Specifications for the Three Experiments

### 6.1 Experiment A: HYBRID-ORACLE-SPAN (Usability Diagnostic)
- **Purpose**: Test whether an edge 7B LLM can utilize an explicitly preserved originating source span to recover information lost during proposition extraction ($H_{\text{HYBRID\_A}}$).
- **Cohort**: **ONLY the 29 Deficit Cases ($N = 29$)**.
- **Span Selection**:
  - Injects the manually audited originating sentence, table row, or list item identified in `representation_loss_audit_v3.json` and `audit_29_naive_only.json`.
  - For incomplete fact cases, injects the complete originating sentence from which the partial fact was extracted.
- **Guardrails**:
  - Gold answer strings must **NEVER** be inserted into the prompt.
  - The span is selected using the manual audit because this is explicitly an **oracle usability study**, not an end-to-end retrieval evaluation.
- **Primary Metric**: **Failure Repair Rate**:
  $$	ext{Repair Rate} = rac{b}{29}$$
  Reported across:
  - 15 Complete Extraction Omissions
  - 6 Incomplete Predicate Complements
  - 7 Downstream LLM Reasoning Failures
  - 1 Evaluation Metric Artifact

---

### 6.2 Experiment B: PRECISION-PRESERVATION STRESS TEST
- **Purpose**: Determine whether adding textual source spans re-introduces narrative distractors and causes Précis to lose its existing relational precision advantage ($H_{\text{HYBRID\_B}}$).
- **Cohort**: **ONLY the 11 Précis-Only Win Cases ($N = 11$)**.
- **Span Selection**:
  - Must use the **same non-oracle span selection rule** intended for the general hybrid system (top-1 sentence retrieved by query similarity, or originating sentence of top-ranked SVOA fact).
  - **PROHIBITED**: Do NOT use known correct answers, do NOT use manual audit labels, do NOT use oracle span selection.
- **Primary Metrics**:
  - **Win Retention Rate**:
    $$	ext{Retention Rate} = rac{r}{11}$$
  - **Regression Rate**:
    $$	ext{Regression Rate} = rac{s}{11}$$
- **Reporting**: Report retained wins ($r$), regressions ($s$), and unchanged outcomes.
- **Analysis Isolation**: Do **NOT** combine these 11 cases with Experiment A for the primary headline analysis.

---

### 6.3 Experiment C: HYBRID-RETRIEVED-SPAN (End-to-End Span Discovery)
- **Purpose**: Determine whether an independent, deterministic span retriever can locate necessary source spans without relying on SVOA provenance or gold annotations ($H_{\text{HYBRID\_C}}$).
- **Cohort**: **29 Deficit Cases (Primary)**; All 40 Discordant Cases (Secondary).
- **Retriever Specification**:
  1. Segment the raw source document into:
     - Prose sentences (via spaCy `sentencizer`)
     - Table rows (via HTML `<tr>` or `<td>` boundaries)
     - List items (via HTML `<li>` or bullet boundaries)
  2. Embed each span using frozen `all-MiniLM-L6-v2`.
  3. Embed the query with `all-MiniLM-L6-v2`.
  4. Compute cosine similarity: $\cos(\mathbf{e}_q, \mathbf{e}_s)$.
  5. Select the top-$1$ span (or top-$2$ if fitting within the token-matched budget).
  6. Pair selected span(s) with structured SVOA facts in the prompt.
- **Guardrails**: No gold answers, no gold failure labels, no learned rerankers, no second LLM, no manual tuning on test outcomes.
- **Primary Metric**: **Source-Span Retrieval Success Rate**:
  $$	ext{Retrieval Success Rate} = rac{	ext{Spans Containing Audited Evidence}}{29}$$
- **Three-Way Failure Separation**:
  Report:
  1. *Downstream Repair Rate*: Retrieved span contained evidence AND generator answered correctly.
  2. *Retrieval Success Without Repair*: Retrieved span contained evidence BUT generator failed (LLM reasoning / synthesis failure).
  3. *Retrieval Failure*: Retriever failed to select the span containing the evidence (retriever failure).

---

## 7. Evidence Formatting & Prompt Template

Structured facts are explicitly paired with their source spans:

```
Fact 1:
[Subject: Daisuke Ohata]
[Verb: scored]
[Object: 69 tries]
[Status: ASSERTED]
Source Span:
"<td> Daisuke Ohata </td> <td> Japan </td> <td> 69 </td>"

Fact 2:
[Subject: Sakshi Malik]
[Verb: named]
[Object: brand ambassador]
[Status: ASSERTED]
Source Span:
"Sakshi Malik was named the brand ambassador for the Beti Bachao, Beti Padhao campaign in Haryana."
```

- **Prose**: Smallest originating sentence.
- **Tables**: Smallest originating table row.
- **Lists**: Smallest originating list item.
- **Deduplication**: Repeated source spans are rendered only once.

---

## 8. Secondary Metrics & Measurement Standards

For all three experiments, report:
- **Token Containment (%)**: Normalized token containment where punctuation and casing are removed.
- **Raw-String Containment (%)**: Strict character substring match.
- **Exact Match (EM)**: Official MRQA evaluation script.
- **ROUGE-L**: Lexical overlap F1.
- **DeBERTa BERTScore**: Semantic embedding similarity (`microsoft/deberta-large-mnli`).
- **Context Telemetry**: Exact context tokens, context words, generated tokens, latency (ms).

---

## 9. Statistical Reporting vs. Engineering Decision Criteria

### 9.1 Statistical Reporting Plan
- Report raw descriptive outcome distributions for Experiment A ($N = 29$), Experiment B ($N = 11$), and Experiment C ($N = 29$).
- If paired statistical tests are performed, report exact two-sided McNemar tests and exact binomial confidence intervals separately within each cohort.
- A combined 40-case paired test may be included **only as an exploratory descriptive supplement**; it must **NOT** be presented as the headline inferential result.

### 9.2 Engineering & Project Governance Decision Criteria
Arbitrary post-hoc thresholds ($\ge 15/21$, $< 8$, etc.) are **strictly rejected as statistical hypotheses**. However, for project governance, future production implementation decisions will follow qualitative engineering gates:

- **Criteria Favoring Future Production Implementation**:
  1. *Meaningful Failure Repair*: Substantial repair of representation-limited failures in Experiment A ($b_{\text{rep}}$ is high).
  2. *Low Regressions*: Near-zero win degradation in Experiment B ($s \le 1 / 11$).
  3. *Token-Matched Efficacy*: Repairs occur under strict token budgets ($T_{\text{hybrid}} \le T_{\text{baseline}}$).
  4. *Retriever-Generator Agreement*: Non-oracle span retrieval in Experiment C successfully recovers a substantial portion of oracle gains.
- **Criteria Favoring Abandoning Hybrid Representation**:
  1. *Low Usability*: Oracle spans fail to repair representation failures in Experiment A ($b_{\text{rep}}$ is low).
  2. *High Distractor Sensitivity*: Adding text spans causes frequent regressions in Experiment B ($s \ge 3 / 11$).
  3. *Retriever Breakdown*: Non-oracle span retrieval in Experiment C fails to locate the necessary spans.

---

## 10. Research-Only Implementation Boundary

- **Script Path**: `scripts/eval_hybrid_diagnostic.py` (standalone execution).
- **Output Directory**: `results/diagnostic_hybrid_n40/`
- **Production Code Status**: `backend/src/precis/` remains **100% frozen**.
