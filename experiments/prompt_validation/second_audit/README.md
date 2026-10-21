# Second audit of the 30-case error-mode sample

- `human_rater_sheet.md` + `human_rater_labels.csv`: clean, blinded materials for the human second rater. Fill in the CSV.
  Do not open the other files here until finished.
- `blinded_input_for_second_rater.json`, `second_rater_labels.json`: the same items labelled by a blind language-model subagent
  (a model, not a human; run 2026-10-17). `comparison.json` / `compare_raters.py`: its comparison with Table 7 and the objective checks.
- After the human labels exist, compare them with the LLM rater and with Table 7; the first rater's per-output labels were never stored,
  so item-level agreement with the first rater is not computable.
