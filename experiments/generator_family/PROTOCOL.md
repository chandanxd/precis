# Third generator family on the fixed fresh-cohort contexts: protocol (written before any model call of this experiment)

Purpose: answer the expected review objection that the primary generator (qwen2.5-coder:7b) is code-specialised and that
the only other generator (qwen3.5:9b) is from the same family. Nothing here changes any context, arm, cohort or earlier result.

Why a replay is a full run: in `scripts/run_fresh_table_cohort.py` and `scripts/run_baseline_budget.py` every context
(N_raw, N_clean, D, F2, G, TC, H, W) is built before and independently of the generator call; retrieval and packing make
no model calls. Running the pipeline end to end with another generator therefore reproduces the same contexts, and
replaying the stored contexts is equivalent.

## Setting
- Generator: gemma4:e4b (Ollama, Google Gemma 4 family; not used elsewhere in the paper as a generator). gemma4:12b, the
  answer-equivalence judge, is NOT used here.
- Contexts: unchanged from experiments/fresh_table_cohort/records.jsonl (N_raw, N_clean, D, F2, G) and
  experiments/baseline_budget/single_records.jsonl (TC, H, W at the 2,048 ceiling). 200 questions x 8 arms.
- Prompt: pipeline concise template; temperature 0.0, top-p 0.9, seed 42, 512 new tokens, thinking disabled, num_ctx 8192.
- Scoring: exact match and containment with the gold answer and all MRQA alternatives (scripts/scoring.py rule).

## Analysis (exploratory; no new confirmatory claim)
For each arm: EM and containment counts. For G against each other arm: EM difference with exact McNemar p (unadjusted) and
a 95% question-level bootstrap interval (10,000 resamples, seed 42). Reported descriptively next to the qwen2.5-coder:7b and
qwen3.5:9b results. The question asked is only whether the ordering found with the other generators (G level with the
structure-keeping baselines N_raw, W, TC, H; ahead of D and F2) holds for a third family. A non-significant difference is
not read as equivalence.

## Rules
No change to the generator, prompt, decoding, arms or analysis after the first model call. Deviations go in DEVIATIONS.md.
