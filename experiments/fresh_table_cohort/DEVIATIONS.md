# Deviations from PROTOCOL.md

None. The cohort, conditions and analysis ran exactly as written; the analysis script
(`scripts/analyze_fresh_table_cohort.py`) was run once after all 200 cases finished and its output is `analysis.json`.

Notes (not deviations):
- Candidates: 1,425 records after exclusions (748 distinct questions); 996 identifiers and 785 questions were excluded.
- 31 of 200 cases gave condition D an empty context (list-only documents without a table); they are scored incorrect, as pre-specified.
- F2 is a reconstruction of F (see protocol); the frozen F cannot be regenerated from the current code.
- The protocol file was written before the run but, like the earlier experiment folders, is not under version control;
  its SHA-256 (`PROTOCOL.sha256`) and time stamp (`PROTOCOL.timestamp`) were recorded before the first model call.
