### Main Evaluation Results

| Condition | EM | ROUGE-L | BERTScore (DeBERTa) | MiniLM Cosine | Context Words | Generated Tokens | Compression Rate | Latency |
|---|---|---|---|---|---|---|---|---|
| Baseline A (Naive RAG 512-chunk) | 0.285 | 0.531 | 0.689 | 0.627 | 159 | 0 | 0.0% | 609ms |
| Baseline B (SVOA Pure Similarity) | 0.160 | 0.356 | 0.584 | 0.480 | 166 | 20 | 1.3% | 584ms |
| Baseline C (SVOA w/o Modality) | 0.140 | 0.342 | 0.573 | 0.470 | 166 | 20 | 1.3% | 533ms |
| **Précis (Full 6-Stage)** | 0.140 | 0.344 | 0.575 | 0.473 | 163 | 20 | 2.8% | 473ms |
