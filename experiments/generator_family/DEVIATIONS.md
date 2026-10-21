# Deviations

- 2026-10-19 ~16:30 local: the first replay run stopped after 966 of 1,600 generations on a single 300 s HTTP read timeout from the local Ollama server. The run was resumed with the same script and settings; completed generations were kept, nothing was regenerated. Not a design change.
- 2026-10-19 ~16:55 local: a second 300 s read timeout at 1,573 of 1,600, while the long-document cohort was using the same Ollama server (model swapping). Resumed with the same script and settings; nothing regenerated.
