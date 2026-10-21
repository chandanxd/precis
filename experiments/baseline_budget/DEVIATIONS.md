# Deviations and notes (baseline_budget; follow-up)

Run on 2026-10-18. No arm, cohort, ceiling or margin was changed after the first model call.

1. E4 reference. The first analysis compared each perturbed G with the stored G (96/200). The perturbed contexts that equal G's
   were taken from the regenerated G (95/200), so the comparison mixed two generations of the same contexts. The analysis was
   corrected (before any text was written) to compare against the regenerated G. Regenerating G on 200 identical contexts changed
   3 outcomes (96 -> 95 EM): decoding noise of the local server at temperature 0. Table 6 uses the stored G records as the protocol says.
2. Judge. The answer-equivalence judge (gemma4:12b) was run on all 1,600 outputs. It has not been validated against human labels;
   `experiments/prompt_validation/followup/judge_validation_sheet.csv` holds 100 stratified items for that (key in
   judge_validation_key.json, which annotators must not see).
3. E6 (qwen3.5:9b replay) was added for review item S6; it replays fixed contexts and does not repeat retrieval.
4. Environment: the machine ran out of RAM during the multi-document run (Open WebUI and Firefox were closed); the runner is
   resumable and no record was lost or edited.
