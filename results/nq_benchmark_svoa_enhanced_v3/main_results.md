### Main Evaluation Results

| Condition | EM | ROUGE-L | BERTScore (DeBERTa) | MiniLM Cosine | Context Words | Generated Tokens | Compression Rate | Latency |
|---|---|---|---|---|---|---|---|---|
| Baseline A (Naive RAG 512-chunk) | 0.285 | 0.531 | 0.689 | 0.627 | 159 | 17 | 0.0% | 525ms |
| Baseline B (SVOA Pure Similarity) | 0.180 | 0.411 | 0.617 | 0.535 | 260 | 21 | 1.0% | 681ms |
| Baseline C (SVOA w/o Modality) | 0.190 | 0.413 | 0.619 | 0.538 | 259 | 23 | 1.0% | 645ms |
| **Précis (Full 6-Stage)** | 0.190 | 0.415 | 0.620 | 0.539 | 257 | 23 | 2.2% | 538ms |
