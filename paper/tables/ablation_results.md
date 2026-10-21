### SDH Ablation Study

| Configuration | Dropped Term | EM | ROUGE-L | MiniLM Cosine | Δ ROUGE-L | Context Words | Compression Rate |
|---|---|---|---|---|---|---|---|
| **full** | None (Full SDH) (-) | 0.000 | 0.194 | 0.584 | - | 85 | 0.0% |
| drop_E | Entity Relatedness E(s,o) (α = 0) | 0.000 | 0.194 | 0.584 | +0.000 | 85 | 0.0% |
| drop_I | Verb Informativeness I(v) (β = 0) | 0.000 | 0.234 | 0.595 | +0.040 | 85 | 0.0% |
| drop_U | Uniqueness U(t,G) (γ = 0) | 0.000 | 0.194 | 0.584 | +0.000 | 85 | 0.0% |
| drop_A | Adjunct Density A(t) (δ = 0) | 0.000 | 0.234 | 0.595 | +0.040 | 85 | 0.0% |
