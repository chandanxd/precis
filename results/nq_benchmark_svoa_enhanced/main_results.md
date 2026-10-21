### Main Evaluation Results

| Condition | EM | ROUGE-L | BERTScore (DeBERTa) | MiniLM Cosine | Context Words | Generated Tokens | Compression Rate | Latency |
|---|---|---|---|---|---|---|---|---|
| Baseline A (Naive RAG 512-chunk) | 0.285 | 0.531 | 0.689 | 0.627 | 159 | 17 | 0.0% | 525ms |
| Baseline B (SVOA Pure Similarity) | 0.165 | 0.391 | 0.603 | 0.516 | 253 | 22 | 1.2% | 684ms |
| Baseline C (SVOA w/o Modality) | 0.180 | 0.407 | 0.611 | 0.525 | 252 | 23 | 1.3% | 639ms |
| **Précis (Full 6-Stage)** | 0.180 | 0.410 | 0.612 | 0.529 | 249 | 23 | 2.6% | 531ms |
