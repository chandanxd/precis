### Main Evaluation Results

| Condition | EM | ROUGE-L | BERTScore (DeBERTa) | MiniLM Cosine | Context Words | Generated Tokens | Compression Rate | Latency |
|---|---|---|---|---|---|---|---|---|
| Baseline A (Naive RAG 512-chunk) | 0.285 | 0.533 | 0.691 | 0.632 | 159 | 16 | 0.0% | 508ms |
| Baseline B (SVOA Pure Similarity) | 0.165 | 0.397 | 0.610 | 0.526 | 253 | 21 | 1.1% | 672ms |
| Baseline C (SVOA w/o Modality) | 0.180 | 0.414 | 0.618 | 0.535 | 252 | 23 | 1.1% | 636ms |
| **Précis (Full 6-Stage)** | 0.180 | 0.414 | 0.616 | 0.536 | 250 | 22 | 2.5% | 525ms |
