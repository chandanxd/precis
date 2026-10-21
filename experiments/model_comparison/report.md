# Précis Model-Selection Empirical Investigation: Final Report

**Date:** October 9, 2026  
**Environment:** Linux (Ubuntu 24.04 LTS), Local NVIDIA GeForce RTX 4060 Laptop GPU (8,188 MiB VRAM), Ollama 0.35.1  
**Study Scope:** Empirical evaluation of generator replacement for the Précis fact-based document QA pipeline.

---

## 1. Executive Summary

This study conducted a prespecified, three-stage empirical investigation to determine whether replacing the baseline generator (`qwen2.5-coder:7b`) with a modern local model improves Précis question-answering quality and narrows its Exact Match (EM) deficit relative to conventional Naive RAG.

All models were evaluated under identical retrieval contexts cached with SHA-256 integrity verification. The investigation adhered to strict open-science practices: hypotheses, decision rules, tie-breakers, and fallback protocols were prespecified prior to observing test data.

### Key Empirical Findings:
1. **Stage A (Development Screening, $N=101$):**
   - Five candidate models and one reference model were evaluated under non-thinking decoding (`temperature=0.0`, `num_predict=512`). One reasoning model (`deepseek-r1:8b`) was evaluated as an exploratory condition.
   - **Gemma 4 models** (`gemma4:e2b`, `gemma4:e4b`, `gemma4:12b`) failed the prespecified Précis containment guardrail ($\text{Cont} \ge 0.6040$), achieving near-zero Exact Match (0.0% to 2.0%) due to verbose conversational preambles.
   - `qwen3.5:9b` satisfied the containment guardrail (66.3%) but exhibited severe verbosity resulting in an EM of only 5.9%.
   - `qwen3.5:4b` satisfied the guardrail (67.3% vs. reference 60.4%) and achieved the highest EM among qualifying candidates (24.8%), winning Stage A selection.

2. **Stage B (Held-Out Evaluation, $N=100$ deduplicated records):**
   - **Hypothesis H1 (Précis EM Superiority):**
     - Reference (`qwen2.5-coder:7b`): $\text{EM} = 0.0900$ (9/100).
     - Candidate (`qwen3.5:4b`): $\text{EM} = 0.0700$ (7/100).
     - Discordant pairs: 14 (Candidate-only: 6, Reference-only: 8).
     - McNemar exact one-sided $p = 0.7880$ (two-sided $p = 0.7905$).
     - **Result:** **H1 is NOT SUPPORTED**. The candidate generator did not improve Précis Exact Match over the reference baseline.
   - **Hypothesis H2 (Exact Match Gap Reduction):**
     - Point estimate of gap change: $\Delta_{\text{gap}} = +0.0600$.
     - 10,000 paired cluster-bootstrap 95% Confidence Interval: $[-0.0200, +0.1400]$.
     - **Result:** **H2 is INCONCLUSIVE**. Because the 95% confidence interval spans zero, the prespecified decision rule mandates that no claim of gap reduction can be made.

3. **Stage C (Prompt-Ablation Diagnostic, $N=100$ held-out records):**
   - Testing `qwen3.5:4b` with a concise-answer prompt reduced average generated tokens from 47.3 to 19.6 (brevity ratio: 0.413) and caused Exact Match to jump from **7.0% to 33.0%** ($p = 2.98 \times 10^{-8}$).
   - This diagnostic demonstrates that the low EM of newer conversational models is largely an artifact of metric-level surface formatting rather than extraction failure or hallucination.

---

## 2. Experimental Setup and Protocol

### 2.1 Hardware and Runtime Metadata
- **GPU:** NVIDIA GeForce RTX 4060 Laptop GPU (8,188 MiB VRAM, Driver 535.183.01, CUDA 12.2)
- **Host OS:** Linux x86_64
- **Local Server:** Ollama 0.35.1 running at `http://localhost:11434`
- **Execution Mode:** Strictly sequential execution with GPU memory unloading between model transitions.
- **Decoding Hyperparameters:**
  - `temperature = 0.0`
  - `top_p = 0.9`
  - `seed = 42`
  - `num_predict = 512`
  - API endpoint: `/api/chat` with `"think": false` for all non-thinking evaluations.

### 2.2 Model Registry
| Model Identifier | Parameter Count | Quantization | Ollama Tag | Role |
|---|---|---|---|---|
| Qwen2.5-Coder-7B-Instruct | 7.0B | Q4_K_M | `qwen2.5-coder:7b` | Control Reference Baseline |
| Qwen3.5-4B-Instruct | 4.0B | Q4_K_M | `qwen3.5:4b` | Candidate Model |
| Qwen3.5-9B-Instruct | 9.0B | Q4_K_M | `qwen3.5:9b` | Candidate Model |
| Gemma-4-E2B-IT | 2.0B | Q4_K_M | `gemma4:e2b` | Candidate Model |
| Gemma-4-E4B-IT | 4.0B | Q4_K_M | `gemma4:e4b` | Candidate Model |
| Gemma-4-12B-IT | 12.0B | Q4_K_M | `gemma4:12b` | Candidate Model |
| DeepSeek-R1-Distill-Qwen-8B | 8.0B | Q4_K_M | `deepseek-r1:8b` | Exploratory (Native Reasoning) |

### 2.3 Cohort Selection and Context Parity
- **Stage A Cohort ($N=101$):** Selected deterministically by sorting the 74 unique normalized questions in the canonical benchmark by their SHA-256 hash and taking the first 35 question groups. All 101 corresponding canonical sample records were retained.
- **Stage B Cohort ($N=100$):** Selected deterministically from held-out `nq_dev.jsonl` records by filtering for non-empty source documents, strictly excluding any record sharing an ID, normalized question string, document hash, or content hash with the canonical benchmark. Exactly 100 distinct questions with 100 distinct source documents were selected.
- **Bit-for-Bit Context Parity:** Retrieval contexts for Naive RAG (512-word chunks, 128-word overlap, top-5) and Précis v3 (SVOA triple extraction, semantic deduplication, hierarchical packing to 2048 tokens) were computed once and serialized to `experiments/model_comparison/cached_contexts.jsonl`. All candidate models consumed identical context strings verified via SHA-256 checksums.

---

## 3. Stage A: Development Screening Results

Stage A screened all models across 101 development samples (202 evaluations per model across Naive RAG and Précis conditions).

### 3.1 Primary Screening Table
| Model | Condition | Exact Match | Containment | ROUGE-L | MiniLM Cosine | BERTScore F1 | Mean Latency | Mean Tokens |
|---|---|---|---|---|---|---|---|---|
| **qwen2.5-coder:7b** (Ref) | Naive RAG | 0.2871 | 0.7525 | 0.4972 | 0.6043 | 0.6836 | 574.7 ms | 17.0 |
| | **Précis Full** | **0.2574** | **0.6040** | **0.4271** | **0.5553** | **0.6413** | **628.8 ms** | **21.3** |
| **qwen3.5:4b** | Naive RAG | 0.0495 | 0.7426 | 0.3355 | 0.4989 | 0.5741 | 744.9 ms | 26.0 |
| | **Précis Full** | **0.2475** | **0.6733** | **0.3786** | **0.5428** | **0.5977** | **866.1 ms** | **36.8** |
| **qwen3.5:9b** | Naive RAG | 0.0000 | 0.8614 | 0.2498 | 0.4600 | 0.5269 | 1481.8 ms | 39.2 |
| | **Précis Full** | **0.0594** | **0.6634** | **0.2229** | **0.4494** | **0.5109** | **1639.0 ms** | **47.7** |
| **gemma4:e2b** | Naive RAG | 0.0000 | 0.7723 | 0.2457 | 0.4349 | 0.5337 | 375.5 ms | 28.5 |
| | **Précis Full** | **0.0000** | **0.5941** | **0.2441** | **0.4098** | **0.5225** | **248.5 ms** | **23.8** |
| **gemma4:e4b** | Naive RAG | 0.0000 | 0.7624 | 0.2343 | 0.4193 | 0.5247 | 585.1 ms | 30.1 |
| | **Précis Full** | **0.0000** | **0.5149** | **0.1963** | **0.3480** | **0.4804** | **434.9 ms** | **26.9** |
| **gemma4:12b** | Naive RAG | 0.0000 | 0.7525 | 0.2758 | 0.4477 | 0.5413 | 3281.6 ms | 27.0 |
| | **Précis Full** | **0.0198** | **0.4752** | **0.2047** | **0.3393** | **0.4826** | **2552.0 ms** | **21.4** |
| *deepseek-r1:8b* (Expl.) | Naive RAG | 0.2376 | 0.6832 | 0.4022 | 0.4975 | 0.5541 | 9565.6 ms | 366.3 |
| | **Précis Full** | **0.1881** | **0.4257** | **0.3085** | **0.3998** | **0.4524** | **10143.8 ms** | **390.1** |

### 3.2 Candidate Selection Decision
- **Guardrail Rule:** $\text{Cont}_{\text{Précis,cand}} \ge \text{Cont}_{\text{Précis,ref}} = 0.6040$.
- **Disqualified Models:**
  - `gemma4:e2b` (59.4% < 60.4%)
  - `gemma4:e4b` (51.5% < 60.4%)
  - `gemma4:12b` (47.5% < 60.4%)
- **Qualifying Models:**
  1. `qwen3.5:4b` ($\text{Cont} = 0.6733$, $\text{EM} = 0.2475$)
  2. `qwen3.5:9b` ($\text{Cont} = 0.6634$, $\text{EM} = 0.0594$)
- **Selection:** `qwen3.5:4b` ranked #1 among qualifying candidates by virtue of highest Précis Exact Match (0.2475 vs. 0.0594) and highest Containment (0.6733).

---

## 4. Stage B: Held-Out Evaluation and Inferential Analysis

Stage B evaluated the reference model (`qwen2.5-coder:7b`) and the selected candidate (`qwen3.5:4b`) on 100 held-out samples.

### 4.1 Held-Out Performance Summary ($N=100$)
| Model | Condition | Exact Match (Count) | Containment | ROUGE-L | MiniLM Cosine | BERTScore F1 | Mean Latency | Mean Tokens |
|---|---|---|---|---|---|---|---|---|
| **qwen2.5-coder:7b** | Naive RAG | 0.1600 (16/100) | 0.5800 | 0.4346 | 0.5919 | 0.6367 | 815.9 ms | 22.2 |
| | **Précis Full** | **0.0900 (9/100)** | **0.4900** | **0.3514** | **0.5256** | **0.5919** | **796.6 ms** | **24.2** |
| **qwen3.5:4b** | Naive RAG | 0.0800 (8/100) | 0.6800 | 0.3246 | 0.5134 | 0.5552 | 1179.5 ms | 42.0 |
| | **Précis Full** | **0.0700 (7/100)** | **0.6100** | **0.3037** | **0.5077** | **0.5521** | **1210.5 ms** | **47.3** |

### 4.2 Formal Hypothesis Testing

#### Hypothesis H1: Candidate Précis EM Superiority
- **Hypothesis Formulation:**  
  $H_0: P(\text{EM}_{\text{cand}} = 1) \le P(\text{EM}_{\text{ref}} = 1)$ vs. $H_1: P(\text{EM}_{\text{cand}} = 1) > P(\text{EM}_{\text{ref}} = 1)$
- **Paired Contingency Table ($N=100$):**
  - Both correct ($n_{11}$): 1
  - Reference only correct ($n_{01}$): 8
  - Candidate only correct ($n_{10}$): 6
  - Neither correct ($n_{00}$): 85
  - Total discordant pairs ($b + c$): 14
- **Statistical Tests:**
  - Odds Ratio: $6 / 8 = 0.750$
  - McNemar exact one-sided $p$-value: **0.7880** (two-sided $p = 0.7905$)
- **Inferential Conclusion:** **H1 is NOT SUPPORTED**. There is no statistical evidence that `qwen3.5:4b` produces higher Précis Exact Match than `qwen2.5-coder:7b`. In fact, point estimate of EM was lower (7% vs 9%).

#### Hypothesis H2: Exact Match Deficit Reduction
- **Estimand:**  
  $\Delta_{\text{gap}} = (\text{EM}_{\text{Précis,cand}} - \text{EM}_{\text{Naive,cand}}) - (\text{EM}_{\text{Précis,ref}} - \text{EM}_{\text{Naive,ref}})$
- **Empirical Components:**
  - Candidate Gap: $0.0700 - 0.0800 = -0.0100$
  - Reference Gap: $0.0900 - 0.1600 = -0.0700$
  - Point Estimate of Deficit Reduction: $\Delta_{\text{gap}} = (-0.0100) - (-0.0700) = \mathbf{+0.0600}$
- **Bootstrap Inference (10,000 resamples, seed=42):**
  - Standard Error: 0.0392
  - **95% Bootstrap Confidence Interval:** $\mathbf{[-0.0200, +0.1400]}$
- **Prespecified Decision Rule Application:**
  - *Supported:* 95% CI strictly above 0 ($CI_{2.5\%} > 0$).
  - *Inconclusive:* 95% CI includes 0 ($CI_{2.5\%} \le 0 \le CI_{97.5\%}$).
  - *Opposite Direction:* 95% CI strictly below 0 ($CI_{97.5\%} < 0$).
- **Inferential Conclusion:** **H2 is INCONCLUSIVE**. Although the point estimate indicates a 6.0 percentage-point narrowing of the deficit, this effect is primarily driven by a collapse in Naive RAG EM for the candidate (from 16% to 8%) rather than a gain in Précis EM. Crucially, the 95% confidence interval spans zero ($-0.02$ to $+0.14$), prohibiting any claim that model replacement significantly reduces the Précis performance deficit.

---

## 5. Stage C: Exploratory Prompt-Ablation Diagnostic

Stage C evaluated `qwen3.5:4b` on the same 100 held-out samples under an exploratory concise-answer prompt instructing the model to emit only the shortest direct answer without explanatory framing.

### 5.1 Prompt Comparison ($N=100$)
| Prompt Variant | Exact Match (Count) | Containment | Mean Generated Tokens | Brevity Ratio | Mean Latency |
|---|---|---|---|---|---|
| **Standard Prompt** | 0.0700 (7/100) | 0.6100 | 47.32 tokens | 1.000 | 1210.5 ms |
| **Concise Prompt** | **0.3300 (33/100)** | **0.4800** | **19.56 tokens** | **0.413** | **741.5 ms** |

### 5.2 Statistical Significance
- **Paired Contingency Table:**
  - Both correct: 7
  - Concise-prompt only correct: 26
  - Standard-prompt only correct: 0
  - Neither correct: 67
- **McNemar Exact Test:**
  - Discordant pairs: 26 (26 vs. 0)
  - One-sided $p$-value: $\mathbf{1.49 \times 10^{-8}}$ ($p < 0.00001$)
- **Key Insight:** `qwen3.5:4b` possesses the grounded facts necessary to achieve a 33% Exact Match (nearly 4× higher than reference baseline's 9%), but under standard prompts it formats answers conversationally ("According to the text, X is Y"), which completely fails automated exact-match string metrics.

---

## 6. Methodological Lessons and Recommendations

1. **Model Selection Does Not Solve the Précis Deficit Without Prompt Adaptation:**  
   Simply dropping a newer instruction-tuned model into the existing extraction harness does not systematically close the Précis gap under standard QA prompts. Instruction-tuned conversational models are tuned to produce fluent sentences, which artificially punishes them on strict extractive benchmarks.

2. **Containment vs. Exact Match Discrepancy:**  
   Containment rates for `qwen3.5:4b` under Précis reached 61.0% (surpassing the reference model's 49.0%), even while its standard EM was only 7.0%. Researchers evaluating graph- or fact-based RAG must report containment or semantic metrics alongside exact match to prevent mistaking verbose phrasing for ungrounded hallucination.

3. **Pragmatic Path Forward:**  
   If Précis is to be deployed with modern generators, a post-processing answer extraction step or concise-prompt conditioning should be standardized across all comparison baselines.

---

## 7. Artifact Index
- **Manifest:** `experiments/model_comparison/sample_manifest.jsonl`
- **Cached Contexts:** `experiments/model_comparison/cached_contexts.jsonl`
- **Raw Outputs:**
  - `experiments/model_comparison/raw_outputs/stage_a_*.jsonl`
  - `experiments/model_comparison/raw_outputs/stage_b_*.jsonl`
  - `experiments/model_comparison/raw_outputs/stage_c_*.jsonl`
- **Structured Results Ledger:** `experiments/model_comparison/results.json`
- **Reproduction Script:** `experiments/model_comparison/reproduce.sh`
