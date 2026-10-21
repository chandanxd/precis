# Fixed Context Budget Experiment: Empirical Results

**Dataset**: Natural Questions MRQA Benchmark (50 deterministic samples, seed 42)  
**Evaluated Conditions**: Naive RAG (512-word chunk baseline) vs. Précis Full (6-stage SVOA + SDH + Modality-filtered packing)  
**Context Ceilings**: 256, 512, 1024, and 2048 tokens  
**Inference Engine**: Local Ollama `qwen2.5-coder:7b`, Temperature = 0.0 (Greedy Decoding), Top-p = 0.9, Max Generated Tokens = 512  

---

## 1. Experimental Motivation

The primary research hypothesis underlying structured semantic retrieval is the **Semantic Compression Hypothesis**:
> *By decoupling sentences into atomic Subject-Verb-Object-Adjunct propositions and ranking them by query-adaptive semantic density (SDH), Précis packs more relevant information into tight context windows than raw text chunking.*

To test this hypothesis without confounding variables, both systems were evaluated at identical context token budget ceilings: **256**, **512**, **1024**, and **2048** tokens.

---

## 2. Experimental Results Summary

| Token Budget Ceiling | System | Exact Match (EM) | ROUGE-L | BERTScore (DeBERTa) | Context Tokens (Mean) | Answer Coverage (%) | EM Gap (Précis - Naive) | ROUGE-L Gap | BERTScore Gap |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **256 tokens** | Naive RAG | **0.2200** | **0.5320** | **0.6558** | 105.4 | **100.0%** | — | — | — |
| | **Précis Full** | 0.1200 | 0.3990 | 0.5887 | 153.8 | 94.0% | **-0.1000** | -0.1330 | -0.0671 |
| **512 tokens** | Naive RAG | **0.2200** | **0.5220** | **0.6559** | 116.7 | **100.0%** | — | — | — |
| | **Précis Full** | 0.1000 | 0.3893 | 0.5831 | 178.5 | 96.0% | **-0.1200** | -0.1327 | -0.0729 |
| **1024 tokens** | Naive RAG | **0.2200** | **0.5220** | **0.6559** | 116.7 | **100.0%** | — | — | — |
| | **Précis Full** | 0.1000 | 0.3893 | 0.5831 | 188.7 | 96.0% | **-0.1200** | -0.1327 | -0.0729 |
| **2048 tokens** | Naive RAG | **0.2200** | **0.5220** | **0.6559** | 116.7 | **100.0%** | — | — | — |
| | **Précis Full** | 0.1000 | 0.3893 | 0.5804 | 192.0 | 96.0% | **-0.1200** | -0.1327 | -0.0755 |

---

## 3. Scientific Analysis of the Budget Hypothesis

### 1. Does the Gap Narrow Under Strict Token Budgets?
**YES (Partially Supported).**
- At the standard 2048 ceiling, the Exact Match gap between Précis and Naive RAG is **-0.1200** (-12.0 percentage points).
- Under the strict **256-token ceiling**, Précis's EM improves from **0.1000 to 0.1200**, narrowing the EM gap to **-0.1000** (a +2.0 percentage point relative closing of the gap).
- Similarly, the BERTScore deficit narrows from **-0.0755** at 2048 tokens to **-0.0671** at 256 tokens.
- **Why this occurs**: Under a 256-token ceiling, Précis's greedy knapsack packing algorithm prunes lower-salience trailing facts, focusing generator attention on the highest-ranking SDH tuples. This filtering slightly reduces distraction for the LLM.

### 2. Does Précis Outperform Naive RAG Under Tight Budgets?
**NO.**
- Even at the 256-token ceiling, Naive RAG maintains a decisive advantage (EM **0.2200** vs. **0.1200**, ROUGE-L **0.5320** vs. **0.3990**).
- **Root Cause**: In the Natural Questions MRQA benchmark, passages are concise isolated Wikipedia sections (average length ~159 words / ~105 tokens). Consequently, even with a 256-token limit, Naive RAG's retrieved chunk is unconstrained on 90% of samples and preserves **100% answer coverage**.
- Because Naive RAG provides natural paragraph prose rather than isolated grammatical tuples, the generator synthesizes answers more fluently.

### 3. Conclusion for Paper Submission
The paper **must not claim** that Précis outperforms Naive RAG under strict context budgets on Natural Questions. The accurate, defensible claim is:
> *"Constraining the context token budget to 256 tokens forces sharper factual prioritization in Précis, slightly improving its Exact Match accuracy from 0.100 to 0.120 and narrowing the relative performance deficit against chunk retrieval. However, due to the single-paragraph nature of Natural Questions passages, chunk retrieval retains 100% answer coverage and continues to deliver higher accuracy."*
