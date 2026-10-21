# Baseline-adequacy and binding-budget experiments: protocol (written before any model call of this experiment)

Purpose: answer review items B2 (strong cheap baselines, non-inferiority, accuracy per token), B3 (a setting in which
the token ceiling binds) and R4 (threshold sensitivity of Candidate G). Nothing here changes G, the fresh cohort or its
earlier results (`experiments/fresh_table_cohort/`, protocol hash 1aeb9b7d...). The earlier results are reused as they are
for N_raw, N_clean, D, F2 and G at the 2,048 ceiling.

Honest status of the margin: the non-inferiority margin below was chosen AFTER the fresh-cohort results for G, N_raw,
N_clean, F2 and D were known, and BEFORE any of the new arms (W, TC, H) or any other ceiling was run. It is therefore
pre-specified for the new arms only.

## Common setting
qwen2.5-coder:7b (Ollama), concise prompt (pipeline wording), temperature 0.0, top-p 0.9, 512 new tokens. Exact match and
containment as in the fresh cohort (gold plus all MRQA alternatives). Tokens are the word-count estimate (1.3 per word).
Cohort: the 200 fresh-cohort questions (distinct by construction).

## New arms (all independent of the SVOA/SDH code)
- W: the whole document converted from HTML to Markdown in document order (tables as GFM tables, lists as bullet lists),
  truncated at the ceiling.
- TC: table-aware chunking (tables are kept whole or split by rows with the header repeated; lists are kept whole; prose
  is grouped to about 128 words) with dense retrieval (MiniLM cosine), best chunks added in rank order under the ceiling
  (at most 5 chunks).
- H: the same table-aware chunks with hybrid retrieval, BM25 and dense rankings fused by reciprocal rank fusion (k = 60).
- N (budgeted): the existing chunked baseline (512-word chunks, 128 overlap, top 5, tag-stripped), cut at the ceiling.

## E1. Parity and efficiency at the 2,048 ceiling (primary)
Comparators: N_raw, N_clean, W, TC, H (all with G as the reference). Margin: delta = 5 percentage points of exact match.
G is called non-inferior to a comparator if the lower bound of the 99% question-level bootstrap interval (10,000
resamples, seed 42) for EM(G) - EM(comparator) exceeds -5 points (99% because five comparators are tested). Otherwise
parity is NOT established. The same is reported for containment. Accuracy per 100 estimated context tokens (EM and
containment) and mean tokens are reported for every arm including D and F2. The 5-comparator family is the only primary
family of this experiment.

## E2. Ceiling sweep (exploratory, descriptive)
Ceilings 256, 512 and 1,024 estimated tokens, single document, arms G, N (budgeted), H and W. The question: do the
arms separate when the ceiling binds? Paired exact McNemar tests are reported, unadjusted, and labelled exploratory.

## E3. Multi-document corpus (exploratory, descriptive)
For each question the relevant document is mixed with 4 distractor documents (random other development documents,
seed 42, none containing the question), in shuffled order. G ingests all five documents into one store; the other arms
treat the concatenation as one text (chunked arms) or one Markdown text truncated at the ceiling (W). Ceilings 1,024 and
2,048. Same arms as E2.

## E4. Threshold sensitivity of G (secondary)
One-at-a-time perturbations of G at the 2,048 ceiling: relevance threshold 0.25 -> 0.20 / 0.30, keyword-assisted threshold
0.15 -> 0.10 / 0.20, eligibility threshold 0.40 -> 0.30 / 0.50, element cap 3 -> 2 / 4. A variant is generated only when its
context differs from G's; otherwise G's result is reused. Reported as the change in EM and in tokens with exact McNemar p.

## Rules
No change to arms, cohort, ceilings or margin after the first model call. Any deviation goes in DEVIATIONS.md.
A non-significant difference is never read as equivalence; only the interval rule of E1 can establish non-inferiority.
