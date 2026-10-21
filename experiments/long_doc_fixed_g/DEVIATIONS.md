# Deviations

- 2026-10-19 ~23:05 local: the run stopped after 39 of 200 cases on an Ollama HTTP 500 during generation (GPU memory held by the coreference model). `scripts/run_long_doc_fixed_g.py` now frees the PyTorch cache and retries the same request once on such an error. Same models and settings; the 39 completed cases were kept, nothing regenerated.
