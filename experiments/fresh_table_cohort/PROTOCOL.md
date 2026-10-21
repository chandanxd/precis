# Fresh table-bearing cohort: protocol (written before any model call)

Purpose: test Candidate G on documents that were never used to design or tune it (the earlier 200-case
cohort was used to diagnose F, design G and set the table threshold, so those comparisons are in-sample).

## Cohort
- Source: `backend/data/nq_subset/nq_dev.jsonl` (12,836 records).
- Candidates: records whose raw document contains `<table`, `<ul` or `<ol` (the marker rule of the earlier cohort)
  and whose sanitized text is within the 100,000-character ingestion limit.
- Excluded: every doc_id and every question string used by any earlier experiment: the 600 historical
  exclusions, the 300-case decompilation manifest, the 300-case table-selection manifest, the 200 NQ-benchmark
  development documents, the model-comparison cohorts and the 100-case confirmatory prompt cohort.
- Sampling: one record per distinct question; questions shuffled with `random.Random(42)`; first 200 taken.
  The manifest and its SHA-256 are written before generation.

## Conditions (all: qwen2.5-coder:7b, concise prompt, temperature 0.0, top-p 0.9, 512 new tokens, ceiling 2,048 est. tokens)
- N_raw: 512-word chunks, 128 overlap, top-5 cosine (MiniLM) on the raw document with markup (as in earlier naive baselines).
- N_clean: the same on the tag-stripped text (`sanitize_document`).
- D: table retention alone (theta = 0.0, Markdown tables, no lists, no facts); empty context is scored incorrect.
- F2: current extraction and structural assembly WITHOUT same-document fact suppression. This is a reconstruction
  of variant F, not the frozen F, which cannot be regenerated from the current code.
- G: current production assembly (guarded structural-priority packing).

## Scoring
Exact match and containment against the gold answer and all MRQA alternative answers (as in the earlier table cohort).

## Pre-specified analyses
Primary family (exact match; two-sided exact McNemar; Holm over m = 4): G vs D, G vs F2, G vs N_raw, G vs N_clean.
Secondary: the same four contrasts on containment (Holm, m = 4); G vs F2 on estimated context tokens and on
model-reported prompt tokens (Wilcoxon signed-rank); share of cases with a table in the cohort whose answer string
appears in a table. Intervals use question-level resampling (questions are distinct by construction).
Exploratory (unadjusted, labelled as such): D vs N_raw, D vs N_clean, F2 vs D, results by markup type (table / list-only).
A non-significant result is not read as equivalence.
No outcome-dependent changes to conditions, cohort or thresholds after the first model call. Any deviation is logged
in `DEVIATIONS.md` with its reason.
