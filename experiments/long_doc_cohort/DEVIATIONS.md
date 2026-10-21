# Deviations

- 2026-10-19 ~17:15 local: the run stopped after 38 of 200 cases with CUDA out of memory in the coreference model (F-coref) on a very long page, because Ollama held the generator on the same 8 GB GPU. `scripts/run_long_doc_cohort.py` now frees the cache, unloads the Ollama model and retries the same ingestion once on such an error. The computation is unchanged (same models, device and settings); the 38 completed cases were kept and nothing was regenerated.
