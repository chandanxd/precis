# Long-document cohort: protocol (written before the cohort is drawn and before any model call)

Purpose: test the comparison of the paper's Section 6.3 in a setting where the 2,048-token ceiling actually binds. In the
MRQA release every document is cut to at most 800 words, so no earlier cohort can do this. Nothing here changes any earlier
cohort, arm, threshold or result. G, its thresholds (Eq. (4)) and every baseline are used exactly as implemented in the
paper version tagged before this experiment; no parameter is tuned on this cohort.

## Data
- Source: Natural Questions v1.0 development set, full pages, from the Hugging Face release
  `google-research-datasets/natural_questions` (dev shards `validation-0000{0,1,2}-of-00007.parquet`, read in that order).
- Document text: the NQ token stream joined with single spaces (HTML tokens such as `<Table>`, `<Tr>`, `<P>` kept), starting
  at the first `<H1>` token. This is the same format as the MRQA documents, without truncation.
- Answers: gold = the first short-answer text of the first annotator (in annotation order) who gives a short answer;
  alternatives = every distinct short-answer text over all annotators (as MRQA's answer list).

## Eligibility (applied in this order)
1. At least one annotator gives a non-empty short answer; yes/no answers are excluded.
2. The document contains a `<Table>` token.
3. The document has at least 3,000 non-HTML tokens (about twice what the 2,048-token estimate covers, so the ceiling binds).
4. The system's own input limits accept the document (`sanitize_document` on the text and `sanitize_document_layout` on the
   markup raise no error). Documents beyond the limits are excluded, not truncated, and their number is reported.
5. The question does not occur in any earlier cohort of this project (the exclusion set of
   `scripts/run_fresh_table_cohort.py`, plus the questions of the fresh cohort and the prompt experiment).

## Draw
Distinct eligible questions, shuffled with `random.Random(42)`; the first 200 form the cohort. The manifest records the
SHA-256 of this file, the pool size and the counts excluded at each step. Per case it also records (descriptive strata,
fixed before any model call): whether a gold short-answer span lies inside a `<Table>` region, the word offset of the first
gold span, and the document length.

## Arms (implementations of scripts/run_baseline_budget.py and scripts/run_fresh_table_cohort.py, unchanged)
- G: guarded structural priority (Précis, list extraction on), whole document ingested.
- N: tag-stripped 512-word chunks, 128 overlap, top 5, cut at the ceiling.
- N_raw: the same chunking on the raw markup, cut at the ceiling.
- W: whole document as Markdown in document order, truncated at the ceiling.
- TC: table-aware chunks, dense retrieval, at most 5 chunks under the ceiling.
- H: table-aware chunks, BM25 + dense fused by reciprocal rank fusion (k = 60), at most 5 chunks under the ceiling.
Ceilings: 2,048 estimated tokens (primary) and 1,024 (secondary).

## Generation and scoring
qwen2.5-coder:7b (Ollama), pipeline concise prompt, temperature 0.0, top-p 0.9, seed 42, 512 new tokens. Exact match and
containment with the gold answer and all alternatives (scripts/scoring.py rule). Per context: estimated tokens and whether
it contains any answer string.

## Analysis
Primary family (2,048 ceiling, exact match): G against N, N_raw, W, TC and H.
- Non-inferiority, margin **5 percentage points, fixed here before any result of this cohort is known**: G is non-inferior
  to a comparator if the lower bound of the 99% bootstrap interval (10,000 resamples, seed 42; 99% for five comparators)
  for EM(G) − EM(comparator) exceeds −5 points.
- Difference in either direction: two-sided exact McNemar, Holm over the five comparisons.
Secondary (reported, not confirmatory): the same at 1,024; containment; answer-in-context counts per arm (the stage-loss
trace); mean estimated tokens and EM per 100 tokens; strata by answer-in-table.
Exploratory: replay of the fixed contexts through qwen3.5:9b and gemma4:e4b.
A non-significant difference is never read as equivalence; only the interval rule establishes non-inferiority.

## Rules
No change to data, eligibility, draw, arms, ceilings, generator, margin or analysis after the manifest is built. Deviations
go in DEVIATIONS.md with the reason and the time.
