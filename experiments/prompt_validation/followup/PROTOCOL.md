# RQ2 follow-up: separating answer format from abstention policy (protocol, written before any run of this follow-up)

Status: this follow-up is NOT part of the 2026-10-09 pre-specified 2x2x2 experiment. It was designed after that
experiment and its audit, in response to the observation that the standard and concise prompts differ in two ways:
(a) format (sentence versus short span) and (b) abstention instruction ("say so explicitly" versus output
"Insufficient information"). 5 of the 12 audited corrections were abstention -> answer transitions.

## Design
Same 100 question-document pairs, same cached contexts (SHA-256 verified), same two generators, same two retrieval
conditions, same decoding (/api/chat, think false, temperature 0, top-p 0.9, seed 42, 512 new tokens).
Two new prompts complete a 2 x 2 factorial in (format, abstention wording):

|                       | abstention: "say so explicitly" | abstention: output "Insufficient information" |
|-----------------------|---------------------------------|------------------------------------------------|
| format: sentence      | STANDARD (existing)             | SENT_TOKEN (new)                               |
| format: short span    | SHORT_EXPLICIT (new)            | CONCISE (existing)                             |

SHORT_EXPLICIT is CONCISE with its abstention line replaced by the STANDARD abstention line. SENT_TOKEN is STANDARD
with its abstention line replaced by the CONCISE abstention line. Nothing else changes. Prompt hashes are recorded.

## Analyses (pre-specified for this follow-up)
Primary: format effect with abstention fixed (SHORT_EXPLICIT - STANDARD, CONCISE - SENT_TOKEN) and abstention effect with
format fixed (SENT_TOKEN - STANDARD, CONCISE - SHORT_EXPLICIT) on exact match, per model x retrieval cell, two-sided exact
McNemar, Holm over the 16 tests (4 contrasts x 4 cells). Also the rate of abstention outputs per prompt.
Secondary: (1) normalised token F1 against the gold answer; (2) an answer-equivalence judgement by a local LLM
(gemma4:12b, temperature 0, fixed rubric below), reported with its agreement with human labels on a stratified
subsample that the authors label (reported only if those labels exist); (3) whether the Naive-RAG versus Precis v3
ranking changes between exact match and the equivalence measures.
Judge rubric: "Question, reference answer, candidate answer. Does the candidate give the same answer as the reference
(same entity, number or date; extra correct detail is allowed; an abstention is incorrect)? Reply with exactly
CORRECT or INCORRECT."
No outcome-dependent changes after the first model call; deviations go in followup/DEVIATIONS.md.
