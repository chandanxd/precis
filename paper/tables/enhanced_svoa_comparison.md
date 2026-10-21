# SVOA Enhancement: Pre- vs. Post-Intervention Evaluation Report

**Benchmark Dataset:** 200 NaturalQuestions Samples (`backend/data/nq_subset/nq_dev.jsonl`)  
**Hardware:** AMD Ryzen 9 8945HS (16 GB RAM), NVIDIA RTX 4060 Laptop GPU (8 GB VRAM), CUDA  
**Evaluator LLM:** `qwen2.5-coder:7b` via Ollama (`temperature=0.0`, `seed=42`, `top_p=0.9`)  
**BERTScore Evaluator:** `microsoft/deberta-large-mnli` (genuine, GPU offline, batch size 4)  

---

## 1. Executive Summary

A controlled experimental modification was applied exclusively to **Stage 2 SVOA Extraction** (`backend/src/precis/pipeline/svoa.py`) to determine whether the observed QA accuracy degradation in the Précis pipeline was primarily driven by information loss during triple extraction.

The targeted modifications introduced:
1. **HTML/XML markup normalization:** Stripping non-semantic tags (e.g. `<Li>`, `<P>`, `</Li>`) that prevented SpaCy tokenizers and dependency parsers from identifying clausal boundaries.
2. **Appositive extraction:** Detecting nominal appositives (`dep_ == "appos"`) and mapping them into explicit copular assertions (`[Head] is [Appositive]`).
3. **Role list-item extraction:** Extracting verbless listing structures of the form `[Entity] as [Role]` into `[Entity] plays/serves as [Role]`.
4. **Subject span cleaning:** Preventing subjects from absorbing trailing commas and appositive tokens.

**Key Outcome:**
- **Extraction Failures dropped by 40.7% relative** (from 59 questions down to 35).
- **SVOA Answer Coverage increased by +14.0 percentage points** (from 68.5% to 82.5%).
- **Exact Match increased by +28.6% relative** (from 0.140 to 0.180).
- **ROUGE-L increased by +19.2% relative** (from 0.344 to 0.410).
- **BERTScore increased by +6.5% relative** (from 0.575 to 0.612).
- **Exact Match Win/Tie/Loss vs Original:** 8 Wins, 192 Ties, **0 Losses**.

---

## 2. Aggregate Benchmark Results (N=200)

| Condition | EM | ROUGE-L | BERTScore (DeBERTa) | MiniLM Cosine | Context Words | Context Tokens | Generated Tokens | Latency | Facts Packed |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Original Précis (Full)** | 0.140 | 0.344 | 0.575 | 0.473 | 163.6 | 204.7 | 20.85 | 473.4ms | 7.42 |
| **Enhanced Précis (Full)** | **0.180** | **0.410** | **0.612** | **0.529** | **249.6** | **313.6** | **23.16** | **532.0ms** | **10.28** |
| *Delta (Enhanced - Original)* | *+0.040* | *+0.066* | *+0.037* | *+0.056* | *+86.0* | *+108.9* | *+2.31* | *+58.6ms* | *+2.86* |
| *Relative Change (%)* | *+28.6%* | *+19.2%* | *+6.5%* | *+11.9%* | *+52.6%* | *+53.2%* | *+11.1%* | *+12.4%* | *+38.5%* |
| **Baseline A (Naive RAG)** | 0.285 | 0.531 | 0.689 | 0.627 | 159.3 | 206.6 | 17.08* | 525.2ms | N/A |
| **Baseline B (SVOA Pure Similarity)** | 0.165 | 0.391 | 0.603 | 0.516 | 253.2 | 318.5 | 22.37 | 684.0ms | 10.28 |
| **Baseline C (SVOA w/o Modality)** | 0.180 | 0.407 | 0.611 | 0.525 | 252.0 | 316.9 | 22.95 | 639.4ms | 10.28 |

*\*Note: Baseline A generated tokens telemetry fix verified (previously reported 0 due to tuple unpacking omission).*

---

## 3. Failure Mode Distribution Shift

Analysis conducted using the 5-stage deterministic coverage diagnostic across all 200 questions.

| Failure Category | Original Count | Original % | Enhanced Count | Enhanced % | Delta (Count) | Relative Change |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CORRECT** | 109 | 54.5% | **135** | **67.5%** | **+26** | **+23.9%** |
| **EXTRACTION_FAILURE** | 59 | 29.5% | **35** | **17.5%** | **-24** | **-40.7%** |
| **RETRIEVAL_FAILURE** | 0 | 0.0% | 0 | 0.0% | 0 | 0.0% |
| **PACKING_FAILURE** | 0 | 0.0% | 0 | 0.0% | 0 | 0.0% |
| **GENERATION_FAILURE** | 32 | 16.0% | 30 | 15.0% | -2 | -6.3% |
| **UNCERTAIN** | 0 | 0.0% | 0 | 0.0% | 0 | 0.0% |

---

## 4. SVOA Coverage Funnel Comparison

| Stage | Original Present | Original % | Enhanced Present | Enhanced % | Net Gain |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Source Document** | 200 | 100.0% | 200 | 100.0% | - |
| **2. SVOA Representation** | 137 | 68.5% | 165 | 82.5% | **+28 (+14.0 pp)** |
| **3. ChromaDB Retrieval** | 137 | 68.5% | 165 | 82.5% | **+28 (+14.0 pp)** |
| **4. Context Packing** | 137 | 68.5% | 165 | 82.5% | **+28 (+14.0 pp)** |
| **5. Model Output Correct** | 109 | 54.5% | 135 | 67.5% | **+26 (+13.0 pp)** |

---

## 5. Question-Level Head-to-Head Comparisons (N=200)

### Enhanced Précis vs. Original Précis
- **Exact Match:**
  - Enhanced Wins: **8** (Enhanced EM=1, Original EM=0)
  - Ties: **192** (164 both 0, 28 both 1)
  - Enhanced Losses: **0** (Enhanced never regressed from 1 to 0)
- **ROUGE-L:**
  - Enhanced Wins: **47** (Higher ROUGE-L)
  - Ties: **124**
  - Enhanced Losses: **29**
  - Net: **+18 Wins**
- **BERTScore (DeBERTa):**
  - Enhanced Wins: **67** (Higher BERTScore)
  - Ties: **96**
  - Enhanced Losses: **37**
  - Net: **+30 Wins**

### Enhanced Précis vs. Naive RAG
- **Exact Match:** Naive RAG = 57, Enhanced Précis = 36
- **ROUGE-L:** Précis Wins = 44, Ties = 69, Naive Wins = 87
- **BERTScore:** Précis Wins = 44, Ties = 53, Naive Wins = 103
- **Contingency (Answer Correctness):**
  - Both Correct: **122**
  - Naive Correct, Précis Incorrect: **37** *(reduced from 53 in original run)*
  - Précis Correct, Naive Incorrect: **13**
  - Neither Correct: **28**

---

## 6. Synthesis & Technical Assessment

1. **Was extraction loss the primary bottleneck?**
   **Yes.** Resolving basic appositives, role listing items, and HTML tag interference recovered 28 previously dropped answer-bearing documents (+14.0 pp coverage) and converted 26 previously failed questions into correct predictions (+13.0 pp correctness). Extraction failures fell from 29.5% to 17.5%.

2. **Did the enhancement introduce regressions?**
   **No structural regressions.** On Exact Match, there were 0 regressions (Enhanced Précis never degraded a previously correct answer). For ROUGE-L and BERTScore, enhanced wins substantially exceeded losses (47 vs 29 on ROUGE-L, 67 vs 37 on BERTScore).

3. **Remaining Gap to Naive RAG:**
   The remaining gap (Naive RAG EM 0.285 vs Enhanced Précis EM 0.180; Naive Correct-Only 37 questions) stems from:
   - **Remaining Extraction Loss (35 questions / 17.5%):** Non-standard table entries, multi-hop sentences, and complex prepositional chains.
   - **Atomic Fact Synthesis / Disfluency (30 questions / 15.0%):** Presenting discrete bulleted SVOA triples sometimes deprives smaller LLMs (`qwen2.5-coder:7b`) of the surrounding discourse flow and contextual cohesion present in continuous 512-word passage chunks.
