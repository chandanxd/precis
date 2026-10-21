# Second labeller for the answer-equivalence judge: instructions

Who: a co-author who has **not** seen `judge_validation_sheet.csv` (labeller A's labels and notes), `judge_validation_key.json`
(the judge's verdicts) or `judge_records.jsonl`. Do not open those files until you have finished.

File: `judge_validation_sheet_B.csv` (the same 100 items as labeller A, in the same order, with no labels).

For each row, read the question, the reference answer and the candidate answer, and fill `label_B` with exactly one of:
- `CORRECT`: the candidate gives the same answer as the reference, even if it is phrased differently, is longer, or
  adds correct context. A partial list counts only if the question asks for one item.
- `INCORRECT`: the candidate gives a different answer, an answer that contradicts the reference, or abstains (for example
  "Insufficient information") when the reference has an answer.
- `HARD`: you cannot decide (for example the reference itself is ambiguous). Use this sparingly.

Use only the reference as the truth, not outside knowledge. Write a short reason in `notes_B` when the decision is not obvious.
Label independently: do not discuss items with labeller A until both sheets are complete.

When finished, run from the repository root:

    backend/venv/bin/python scripts/score_judge_validation_B.py

It reports judge-vs-B agreement and A-vs-B agreement (Cohen's kappa) on the items both labelled.
