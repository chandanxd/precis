# Repaired guarded packing (G2) on a fresh long-document draw: protocol (written before the draw and before any model call)

Purpose: test whether the failure of G on full pages (experiments/long_doc_cohort) is repaired by the two changes that the
post hoc diagnostic of that cohort points to, on questions that were not used to design them.

Honest status: G2 was designed AFTER the results of the first long-document cohort were known, from that cohort's G contexts.
It is therefore evaluated only on a fresh draw that excludes every question of that cohort. Nothing in G, its thresholds or
the baselines is changed; G2 is an additional arm.

## G2: exactly two changes to G (implemented by patching assemble_structural_query_context, as F2 was)
1. Per-element instead of per-document suppression: the rule "suppress every fact whose source document contributed a
   packed element" is removed. The rule "suppress a fact whose subject and object both occur in the packed structural
   text" is kept.
2. Reference/boilerplate filter: a structural candidate is skipped before ranking if at least 30% of its non-header lines
   match `Jump up|Retrieved|Archived from|ISBN|doi:|Wikimedia Commons|Official website|External links` (case-insensitive).
No other parameter changes (thresholds 0.25/0.15/0.40, cap 3, k = 100, ceilings).

## Data and draw
Same source, document construction, eligibility rules and system input limits as experiments/long_doc_cohort/PROTOCOL.md
(NQ v1.0 dev shards 0-2). Additionally excluded: every question of the first long-document cohort. Distinct eligible
questions shuffled with random.Random(43); the first 200 form the cohort.

## Arms and setting
G, G2, TC, W, N (implementations unchanged; G2 as above) at the 2,048-token ceiling only; qwen2.5-coder:7b, pipeline concise
prompt, temperature 0.0, top-p 0.9, seed 42, 512 new tokens; exact match and containment with gold and alternatives; per
context: estimated tokens and whether it contains an answer string.

## Analysis
Primary (two tests, Holm over the two p-values where applicable):
- H1 (repair): EM(G2) vs EM(G), two-sided exact McNemar.
- H2 (adequacy): G2 non-inferior to TC (the best arm of the first cohort) at a 5-point margin: lower bound of the 97.5%
  question-level bootstrap interval (10,000 resamples, seed 42) for EM(G2) - EM(TC) above -5 points.
Secondary (descriptive): G2 against W and N (differences with 95% intervals, McNemar unadjusted); answer-in-context counts;
mean tokens; the share of G2 contexts containing prose facts.
A non-significant difference is never read as equivalence.

## Rules
No change to G2, data, draw, arms, generator or analysis after the manifest is built. Deviations go in DEVIATIONS.md.
