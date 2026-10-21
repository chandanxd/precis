# Semantic Density Heuristic (SDH) Ranking & Fact-Set Sensitivity Methodology

**Document Status**: Authoritative Research Methodology  
**Target Hypothesis**: $H_{\text{SDH\_04}}$ ("Each SDH component contributes measurably and independently to proposition-ranking effectiveness")  
**Evaluation Scope**: Natural Questions MRQA Benchmark ($N = 200$ paired samples, seed 42)  
**Codebase State**: Read-Only Analysis; Zero Production Modifications (`backend/src/precis/` 100% frozen; Zero LLM Inference)  

---

## 1. Core Research Scope & Methodological Scope

This evaluation investigates the behavior and empirical identifiability of the Semantic Density Heuristic (SDH) proposition re-ranking mechanism in Précis:

$$\mathrm{SDH}(t) = \alpha \cdot E(s,o) + \beta \cdot I(v) + \gamma \cdot U(t, G) + \delta \cdot A(t)$$

$$\text{pack\_score}(t, q) = \mathrm{SDH}(t) \times \cos(\mathbf{e}_t, \mathbf{e}_q)$$

with uniform production weights:
$$\alpha = \beta = \gamma = \delta = 0.25, \quad \sum \theta_k = 1.0$$

### Critical Methodological Distinction:
1. **True Permutation-Based Component Feature Importance**: **`NOT IDENTIFIABLE`**.  
   Determining the empirical importance of individual components ($E, I, U, A$) via feature permutation requires serialized per-fact component values, exact candidate similarity floats, and exhaustive candidate relevance labels. Because these fields were not logged in existing frozen benchmark caches, true component importance cannot be computed without fabricating labels or synthetic approximations.
2. **SDH Ranking & Fact-Set Sensitivity Analysis**: **`EXECUTED`**.  
   Using the complete empirical traces from the 200-question v3 benchmark, we evaluate how the composite full SDH pipeline behaves relative to pure vector similarity, analyzing proposition set retention, prompt reordering rates, and downstream answer sensitivity under strictly fixed weights.

---

## 2. Pre-Flight Data Availability Audit & Identifiability Limitations

Before conducting the analysis, all disk caches, schemas, and benchmark logs were audited across all 200 benchmark questions:

| Feature / Field | Status in Existing Caches | Exact Location / Trace | Methodological Consequence |
| :--- | :---: | :--- | :--- |
| **Question Identifiers** | **PRESENT** | `sample_id` in `failure_analysis.jsonl`, `per_question_results.jsonl` | Document & query mapping fully verified. |
| **Document Identifiers** | **PRESENT** | `source_document_id` in `failure_analysis.jsonl` | 200 unique document instances identified. |
| **Candidate Fact Text** | **PRESENT** | `retrieved_svoa_facts` (899 facts), `packed_svoa_facts` (2101 facts) | Canonical rendered proposition strings available. |
| **Composite SDH Score** | **PRESENT** | `sdh_question_level_analysis.json`, `avg_sdh_score` in results | Composite score logged; benchmark mean = 0.494. |
| **Candidate Rank / Order** | **PRESENT** | `rank` in `sdh_question_level_analysis.json` & list order | Exact baseline packing order available. |
| **Answer-Bearing Annotations** | **PARTIALLY PRESENT** | `relevant_fact_candidates` in `failure_analysis.jsonl` (329 facts) | Flags retrieved facts containing gold answer string. |
| **Exact Query-Fact Similarity** | **NOT CACHED** | Implicit in ChromaDB retrieval order; raw float not saved | Precludes exact offline dot-product re-ranking. |
| **Per-Fact $E(s,o)$ Values** | **MISSING** | `Fact` dataclass schema omits component fields; not logged | Component breakdown not pre-cached on disk. |
| **Per-Fact $I(v)$ Values** | **MISSING** | Not saved to JSON/JSONL during benchmark runs | Component breakdown not pre-cached on disk. |
| **Per-Fact $U(t,G)$ Values** | **MISSING** | Not saved to JSON/JSONL during benchmark runs | Component breakdown not pre-cached on disk. |
| **Per-Fact $A(t)$ Values** | **MISSING** | Not saved to JSON/JSONL during benchmark runs | Component breakdown not pre-cached on disk. |
| **Exhaustive Candidate Relevance Labels** | **MISSING** | No graded relevance judgments across unretrieved facts | Precludes supervised ranking-metric importance. |

### Methodological Rule:
- **Do not invent or fabricate candidate relevance labels from QA outcomes**.
- **Do not infer empirical feature importance from theoretical mathematical properties**.
- True component-level feature importance is formally declared **NOT IDENTIFIABLE**.

---

## 3. Mathematical Properties vs. Empirical Feature Importance

Under the production configuration where $\alpha = \beta = \gamma = \delta = 0.25$:

$$\frac{\partial \mathrm{SDH}}{\partial E} = \frac{\partial \mathrm{SDH}}{\partial I} = \frac{\partial \mathrm{SDH}}{\partial U} = \frac{\partial \mathrm{SDH}}{\partial A} = 0.25$$

### Critical Distinctions:
1. **Equal Local Coefficient Sensitivity $\neq$ Empirical Feature Importance**:
   - The identical partial derivative ($\partial \mathrm{SDH}/\partial X_k = 0.25$) indicates that a 1-unit change in any component has an identical linear impact on the composite score. It does **not** indicate equal empirical importance, nor does it establish empirical rankings among components.
2. **Theoretical Dynamic Range $\neq$ Practical Ranking Influence**:
   - The theoretical ranges of components ($E \in [0.0, 1.0]$, $I \in [0.10, 0.98]$, $U \in [0.0, 1.0]$, $A \in [0.20, 1.0]$) describe possible mathematical bounds. They do **not** imply that components with wider bounds have greater practical influence in actual retrieval, as actual empirical variance across candidate propositions may be constrained.
3. **Qualitative Observations $\neq$ Empirical Component Rankings**:
   - Observing that $I(v)$ demotes copulas in specific examples or that $A(t)$ inflates distractor clauses in others provides qualitative architectural insight into failure modes, but **cannot support ranking components as "strongest" or "weakest"**.

---

## 4. Empirical Protocol: SDH Ranking & Fact-Set Sensitivity Analysis

Rather than manufacturing invalid permutation importance metrics, we evaluate the empirical traces of the existing benchmark suite:

### 4.1 Fact-Set Membership Stability vs. Ordering Sensitivity
By comparing the 200 benchmark questions across Condition 1 (Pure Vector Similarity, `svoa_similarity`) and Condition 2 (Full SDH with Modality Filtering, `precis_full`), we measure:
- **Answer Identity Rate**: Proportion of queries yielding identical generated answer strings.
- **Fact-Set Preservation Rate**: Proportion of queries where the packed set of propositions remains 100% identical between conditions.
- **Internal Ordering Rate**: Proportion of answer shifts occurring purely due to rank-ordering permutations of identical facts.
- **Attribution of Altered Fact Sets**: Disentangling whether proposition set changes stem from epistemic modality filtering or SDH prompt budget dynamics.

### 4.2 Downstream Answer Generation Comparison
Evaluating paired differences ($d_i = \text{Full}_i - \text{Sim}_i$) across all $N = 200$ samples on:
- Exact Match (McNemar exact test)
- Containment Correctness (McNemar exact test)
- ROUGE-L (Wilcoxon signed-rank test)
- DeBERTa BERTScore (Wilcoxon signed-rank test)

---

## 5. Methodological Flaw of Historical Drop-One Ablations

In historical evaluations (`results/nq_benchmark/per_question_results.jsonl`), component drops were implemented in `backend/src/precis/pipeline/sdh.py:472-478` with automatic weight renormalization:
```python
w = weights if weights is not None else DEFAULT_WEIGHTS
total_w = sum(w.values())
w_norm = {k: v / total_w for k, v in w.items()}
```

When dropping a component (e.g., $\alpha = 0$ for $E$):
$$\theta_E = 0.0, \quad \theta_I = \frac{0.25}{0.75} = \frac{1}{3} \approx 0.3333, \quad \theta_U = \frac{1}{3}, \quad \theta_A = \frac{1}{3}$$

### Why This Confound Invalided Component Claims:
1. **Surviving Weight Inflation**: Dropping any single component automatically increased the weights of all three surviving components by **$+33.3\%$ relative boost** (from $0.250$ to $0.333$).
2. **Violation of *Ceteris Paribus***: It is impossible to determine whether an outcome change was caused by removing component $X_k$ or by amplifying the remaining components.
3. **Artifactual Improvements**: When $E$ or $A$ was dropped in historical v1 runs, Exact Match increased from $0.150$ to $0.160$ ($+1.0\text{ pp}$). These increases were mathematical artifacts of weight inflation, not evidence of independent component behavior.
4. **Methodological Conclusion**: The historical component-drop results cannot isolate the independent contribution of $E, I, U,$ or $A$, and must remain in the audit only as a documented methodological limitation.

---

## 6. Statistical Governance & Research Invariants

1. **Zero LLM Inference**: No model inference (Ollama, Qwen-2.5) was executed.
2. **Zero Codebase Modifications**: `backend/src/precis/` remains 100% frozen.
3. **Zero Benchmark Overwrites**: All frozen v1 and v3 results remain intact.
4. **Deterministic Seed**: All statistical checks utilize random seed `42`.
