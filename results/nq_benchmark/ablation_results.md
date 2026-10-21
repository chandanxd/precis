### SDH Ablation Study

| Configuration | Dropped Term | EM | ROUGE-L | BERTScore (DeBERTa) | MiniLM Cosine | Δ ROUGE-L | Context Words | Compression Rate |
|---|---|---|---|---|---|---|---|---|
| **full** | None (Full SDH) (-) | 0.150 | 0.352 | 0.580 | 0.477 | - | 163 | 2.8% |
| drop_E | Entity Relatedness E(s,o) (α = 0) | 0.160 | 0.356 | 0.580 | 0.475 | +0.003 | 163 | 2.8% |
| drop_I | Verb Informativeness I(v) (β = 0) | 0.140 | 0.342 | 0.573 | 0.469 | -0.011 | 163 | 2.8% |
| drop_U | Uniqueness U(t,G) (γ = 0) | 0.140 | 0.342 | 0.570 | 0.466 | -0.010 | 163 | 2.8% |
| drop_A | Adjunct Density A(t) (δ = 0) | 0.160 | 0.346 | 0.577 | 0.466 | -0.006 | 163 | 2.8% |
