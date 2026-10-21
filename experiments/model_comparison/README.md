# Précis: Model-Selection Experiments Protocol and Documentation

This document records the prespecified experimental protocol, hypotheses, model registry, baseline context-parity audit, cohort definitions, and inferential decision rules for the Précis model-selection investigation.

> **Naming note**: Stages A–C in this directory are the *prompt-comparison* stages. They are unrelated to the "Stage C" of the table-decompilation runs in `results/diagnostic_structural_decompilation_v3`.

---

## 1. Research Objectives & Scope

The objective is to determine whether replacing the current generator, `qwen2.5-coder:7b`, with a more suitable locally running instruction-following model improves question-answering quality for Précis and reduces its performance deficit relative to conventional Naive RAG.

This investigation preserves all existing project artifacts, the canonical v3 frozen benchmark (`results/nq_benchmark_svoa_enhanced_v3/`), historical manuscript files, the supervisor-review draft, and the manuscript phase gate.

---

## 2. Prespecified Hypotheses

### H1: General-Purpose Model Suitability (Primary Positive Hypothesis)
A general-purpose instruction-following model selected on development data will achieve higher Exact Match for Précis than the existing `qwen2.5-coder:7b` generator on an evaluation set not used for model selection:
$$\text{EM}_{\text{Précis}}(\text{Candidate}) > \text{EM}_{\text{Précis}}(\text{Reference})$$

### H2: Reduced Performance Gap (Differential Representation Hypothesis)
The selected model will reduce the Exact Match gap between Précis and Naive RAG when both systems use the same generator and are evaluated on the same held-out questions:
$$\Delta_{\text{gap}} = \left[\text{EM}_{\text{Précis}}(\text{Candidate}) - \text{EM}_{\text{Naive}}(\text{Candidate})\right] - \left[\text{EM}_{\text{Précis}}(\text{Reference}) - \text{EM}_{\text{Naive}}(\text{Reference})\right] > 0$$
A positive $\Delta_{\text{gap}}$ indicates that Précis has become relatively more competitive against Naive RAG under the candidate generator.

### H3: Quality Versus Local Inference Cost (Secondary Engineering Analysis)
Measure whether the candidate model improves answer quality at an acceptable cost in latency, memory use, and context footprint on the local RTX 4060 Laptop GPU (8,188 MiB VRAM).

---

## 3. Evaluated Models Registry

All models run sequentially on the local Ollama instance (version `0.35.1`):

| Role | Model Identifier | Architecture / Family | Parameter Size | Quantization | Digest (Ollama SHA-256) | Inference Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Reference Control** | `qwen2.5-coder:7b` | Qwen2 (`qwen2`) | 7.6B | `Q4_K_M` | `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364` | `/api/chat` (`think: false`) |
| **Candidate 1** | `qwen3.5:4b` | Qwen3.5 (`qwen35`) | 4.2B | `Q4_K_M` | `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` | `/api/chat` (`think: false`) |
| **Candidate 2** | `qwen3.5:9b` | Qwen3.5 (`qwen35`) | 9.0B | `Q4_K_M` | `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90` | `/api/chat` (`think: false`) |
| **Candidate 3** | `gemma4:e2b` | Gemma4 (`gemma4`) | 4.6B | `Q4_K_M` | `b37049369adfe3d2b653af0ab301a062ca5cbe96ace6aa0d3f2559ee9b563fc2` | `/api/chat` (`think: false`) |
| **Candidate 4** | `gemma4:e4b` | Gemma4 (`gemma4`) | 7.5B | `Q4_K_M` | `dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c` | `/api/chat` (`think: false`) |
| **Candidate 5** | `gemma4:12b` | Gemma4 (`gemma4`) | 11.9B | `Q4_K_M` | `6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b` | `/api/chat` (`think: false`) |
| **Exploratory Reasoning** | `deepseek-r1:8b` | Qwen3 (`qwen3`) | 8.2B | `Q4_K_M` | `6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763` | `/api/chat` (native reasoning) |

> [!NOTE]
> `nomic-embed-text:latest` is exclusively used as an embedding model for vector retrieval and is strictly excluded from generation.

---

## 4. Inference API Consistency & Reasoning Protocol

Empirical probing of Ollama `0.35.1` revealed:
- `qwen2.5-coder:7b`, `qwen3.5:4b`, `qwen3.5:9b`, `gemma4:e2b`, `gemma4:e4b`, and `gemma4:12b` cleanly return direct answers in `message.content` with 0 thinking tokens when queried via `/api/chat` with `think: false`.
- `deepseek-r1:8b` cannot suppress reasoning under `think: false` without generating empty answers or causing tag leakage. With 512 tokens, it generates an internal thought trace (~200+ tokens) before emitting `message.content`.
- **Protocol Decision**: The primary controlled comparison evaluates the five candidate models and reference control under `/api/chat` with `think: false`. `deepseek-r1:8b` is segregated into a separate exploratory reasoning configuration and does not compete in the non-thinking selection ranking.

### Canonical Decoding Settings
- `temperature`: 0.0 (greedy deterministic decoding)
- `top_p`: 0.9
- `seed`: 42
- `num_predict`: 512 tokens

---

## 5. Baseline Context-Parity Audit & Within-Experiment Identity

The canonical v3 benchmark code and records were audited prior to experiment execution:
- **Naive RAG** (`backend/src/precis/evaluation/naive_rag.py`):
  - 512-word sliding window with 128-word overlap (`chunk_document`).
  - Embeddings: `sentence-transformers/all-MiniLM-L6-v2`.
  - Top-$k=5$ cosine similarity ranking.
  - Context format: `"\n\n".join(top_chunks)`.
  - **Audit Finding**: Recomputed context word counts matched canonical records on **200 of 200 samples (100.0% parity, 0 mismatches)**.
- **Précis v3 Pipeline** (`backend/src/precis/evaluation/harness.py`):
  - Coreference resolution -> SVOA extraction -> in-memory Chroma `FactStore` -> SDH scoring -> epistemic modality filtering -> greedy packing into 2,048 token ceiling.
  - **Audit Finding**: Recomputed context word counts matched canonical records on **20 of 20 audited samples (100.0% parity, 0 mismatches)**.

### Historical Parity vs. Within-Experiment Identity
- The audit proves **verified word-count parity** with the canonical benchmark.
- For the new experiment, **within-experiment context identity is absolute**: each sample's evidence context is pre-extracted once, stored in `cached_contexts.jsonl` with an explicit SHA-256 context checksum (`sha256(context_text)`), and reused identically across all models evaluated under that retrieval condition.

---

## 6. Cohort Construction & Manifest Specifications

### Stage A: Development Screening Cohort (101 Samples)
- Extracted all 74 distinct normalized question strings from the canonical 200 samples.
- Sorted by `SHA256(normalized_question)` lexicographically and selected the first 35 question clusters.
- All canonical samples associated with these 35 clusters are included, yielding exactly **101 sample records** (leaving 39 clusters with 99 sample records).

### Stage B: Deduplicated Held-Out Evaluation Cohort (100 Samples)
- Scanned all 12,836 lines of `backend/data/nq_subset/nq_dev.jsonl` under strict exclusion criteria:
  - Canonical doc ID overlap: 200 excluded
  - Canonical QA-document content hash overlap (`SHA256(q|gold|doc)`): 6 excluded
  - Canonical normalized question string overlap: 14 excluded
  - Canonical source document text hash overlap (`SHA256(document)`): 18 excluded
  - Duplicate question strings in candidate pool: 8,265 excluded
  - Duplicate source documents in candidate pool: 329 excluded
- **Eligible Pool**: Exactly **4,004 candidate records** satisfy all joint uniqueness criteria simultaneously.
- **Deterministic Selection**: Sorted by `SHA256(normalized_question)` and selected the first **100 records**.
- **Sample Structure & Statistical Interpretation**: Each record possesses a unique normalized question string and a unique source document, with zero detected overlap with canonical samples. Deduplication eliminates repeated questions and shared passages from the evaluation cohort, but does not prove statistical or distributional independence across web-scraped QA records. In Stage B bootstrap resampling, question-cluster resampling is numerically identical to paired sample-level resampling ($K = N = 100$). Confidence intervals will be reported with explicit recognition of potential unobserved semantic correlation.

---

## 7. Decision Rules & Inferential Protocols

### Stage A Candidate Selection Decision Rule
1. Compute record-weighted Précis Exact Match ($\text{EM}_{\text{Précis}}$) and Précis Containment ($\text{Cont}_{\text{Précis}}$) across the 101 Stage A samples.
2. **Containment Guardrail**: A candidate is eligible for selection if and only if:
   $$\text{Cont}_{\text{Précis}}(\text{Candidate}) \ge \text{Cont}_{\text{Précis}}(\text{Reference})$$
3. **Primary Rank**: Select the candidate with the highest $\text{EM}_{\text{Précis}}$ satisfying the guardrail.
4. **Tiebreakers**: (1) Highest $\text{Cont}_{\text{Précis}}$, (2) Lowest mean latency, (3) Smallest parameter size.
5. **No-Eligible-Candidate Fallback Protocol**:
   - If every candidate fails the containment guardrail, the guardrail will **not** be relaxed.
   - The Stage A screening will be formally reported as having **zero qualifying candidates**.
   - No candidate will be designated as a confirmatory candidate for Stage B. Stage B will run the reference model as control and the top unconstrained candidate strictly labeled as an exploratory run that failed pre-screening.

### H2 Inferential Decision Rule (Stage B)
Compute the quadruply paired change in the Exact Match gap:
$$\Delta_{\text{gap}} = \left[\text{EM}_{\text{Précis}}(\text{Candidate}) - \text{EM}_{\text{Naive}}(\text{Candidate})\right] - \left[\text{EM}_{\text{Précis}}(\text{Reference}) - \text{EM}_{\text{Naive}}(\text{Reference})\right]$$
with 10,000 paired bootstrap resamples yielding percentile 95% confidence interval $[CI_{2.5\%}, CI_{97.5\%}]$.
- **Supported**: H2 is supported **if and only if** the 95% bootstrap confidence interval lies entirely above zero ($CI_{2.5\%} > 0.0$).
- **Inconclusive**: H2 is inconclusive **whenever the 95% confidence interval spans zero** ($CI_{2.5\%} \le 0.0 \le CI_{97.5\%}$), regardless of whether the point estimate $\Delta_{\text{gap}}$ is positive, zero, or negative.
- **Opposite Direction (Negative Shift)**: Evidence of a statistically supported widened deficit in the opposite direction is reported **only when the entire 95% confidence interval lies strictly below zero** ($CI_{97.5\%} < 0.0$).
- Précis Exact Match improvements in isolation will **never** be cited as evidence supporting H2.

---

## 8. Stage C Answer-Formatting Experiment (Exploratory)

- Executed strictly after Stage B results, logs, and analyses are locked.
- Tests a concise answer prompt variant against the standard control prompt on the Stage B cohort using the preselected candidate.
- Concise instruction:
  `"Provide ONLY the shortest complete answer supported by the supplied evidence. Do not include full sentences, explanations, conversational filler, or introductory phrases. Give only the entity, name, date, number, or exact phrase that directly answers the question."`
- Labeled exploratory; cannot retroactively alter Stage A candidate selection or redefine hypotheses.
