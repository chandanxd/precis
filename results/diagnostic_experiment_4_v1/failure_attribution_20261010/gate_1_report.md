# Experiment 4.3: Failure Attribution & Targeted Recovery Research — Gate 1 Final Report

**Experiment Identifier**: `diagnostic_experiment_4_3_failure_attribution`  
**Evaluation Scope**: Gate 1 Failure Attribution, Structural Omission Verification & Extraction Fixtures ($N=101$ Condition D Failures)  
**Date**: 2026-10-10  
**Status**: Gate 1 Completed — **Execution Stopped Awaiting Explicit Review Before Gate 2**  
**Execution Constraints Enforced**: Zero Production Code Modifications (`backend/src/precis/` untouched), Zero Live Model Inference, Frozen Baseline Predictions Reused, Zero Data Imputation.

---

## 1. Executive Summary & Diagnostic Recommendation

### Formal Recommendation: `READY FOR TARGETED DIAGNOSTICS`

```
========================================================================================
                          GATE 1 DIAGNOSTIC VERDICT SUMMARY
========================================================================================
1. PROVISIONAL LIST OMISSION CLAIM CONFIRMED WITH RIGOR:
   - All 34 cases historically classified as EXTRACTION_OMISSION under Condition D have been
     individually verified against raw HTML, parsed blocks, and clean prose.
   - 33 of 34 cases (97.1%) reside strictly within HTML list blocks (<ul> or <ol>) that were
     parsed by StructuralDocumentParser but excluded because include_lists=False was enforced
     to isolate the table selection threshold.
   - 1 of 34 cases (2.9%) had list evidence retained in clean prose (a5c30bbe..., Bob Geldof).
   - Exactly 0 cases had gold evidence residing in tables or unextracted deep HTML.

2. EVIDENCE PRESENCE SEPARATED FROM SEMANTIC ANSWERABILITY:
   - Of the 34 list cases, 31 (91.2%) are FULLY SUPPORTED by the list text.
   - 2 cases (5.9%) are ANNOTATOR_ERROR_UNSUPPORTED:
     * 2b464be1...: Q asks for the dad in A Christmas Story; gold is Ian Petrella (who played
       the brother Randy Parker; Darren McGavin played the dad).
     * f2438373...: Q asks for the Nobel laureate who began career as accountant; gold is
       Amartya Sen (the list only enumerates laureates, and historically C.V. Raman was the accountant).
   - 1 case (2.9%) is AMBIGUOUS_OR_CONSTRAINED:
     * 895b5134...: Q asks who won most Super Bowls "as a player"; gold is Bill Belichick
       (list explicitly states Belichick won as coach and defensive coordinator, not player).

3. COMPLETE TAXONOMY OF ALL 101 CONDITION D FAILURES:
   - Genuine Extraction Omissions: 31 cases (30 unordered lists, 1 ordered list).
   - Generation / Reasoning Failures: 44 cases (14 attention/insufficient info, 30 distractor rows).
   - Surface-Form / Scoring Mismatches: 24 cases (14 multi-entity over-complete, 2 parentheticals,
     7 unit/category specifiers, 1 incomplete).
   - Dataset / Annotator Errors: 2 cases (irrecoverable under gold metric).

4. MINIMAL REPRODUCIBLE FIXTURES & ISOLATED EXTRACTOR IMPLEMENTED:
   - 5 minimal HTML fixtures created covering entity-role binding, nested hierarchies,
     ordered sequences, malformed unclosed tags, and negative boilerplate filtering.
   - Isolated diagnostic list extractor implemented in scripts/diagnostic_list_extractor.py.
   - 100% test pass rate (5 passed in 0.02s) on fixture suite; 13/13 passed on Exp 4.2 suite.
========================================================================================
```

---

## 2. Individual Case-by-Case Audit of the 34 Extraction Omissions

Every extraction omission case was individually traced to its exact parsed block, block type, row index, HTML tag, and text snippet.

| # | Case ID | Question | Gold Answer | Element Type | Block & Row | Exact Source Excerpt | Semantic Answerability |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| 1 | `16caa32e50d3` | leading african producer of wool | `South Africa` | `ordered_list` | Block 0, Row 10 | `South Africa : 1 %` | **SUPPORTED** |
| 2 | `4a3eb5f5ce6a` | area code for phoenix arizona | `602` | `unordered_list` | Block 0, Row 0 | `602 - For telephone numbers in Phoenix city proper except for Ahwatukee...` | **SUPPORTED** |
| 3 | `e6bfa9f3feec` | second book in the alchemyst series | `The Magician` | `unordered_list` | Block 0, Row 1 | `The Magician -- released on 5 June 2008 ( UK ) , 24 June 2008 ( US )` | **SUPPORTED** |
| 4 | `680012c3f0b8` | father of lucius in gladiator | `Lucius Verus` | `unordered_list` | Block 0, Row 12 | `Spencer Treat Clark as Lucius Verus : The young son of Lucilla . He is named after his father Lucius Verus` | **SUPPORTED** |
| 5 | `363edbaa5169` | what part of maryland close to washington dc | `Calvert County` | `unordered_list` | Block 0, Row 0 | `Calvert County` (in list of Southern Maryland counties bordering DC) | **SUPPORTED** |
| 6 | `64cd81b2b268` | attack of the clones characters | `Obi - Wan Kenobi` | `unordered_list` | Block 0, Row 0 | `Ewan McGregor as Obi - Wan Kenobi : A Jedi Master and mentor of Anakin Skywalker .` | **SUPPORTED** |
| 7 | `abe22dfa12e7` | cast of a good day to die hard | `Bruce Willis` | `unordered_list` | Block 0, Row 0 | `Bruce Willis as John McClane` | **SUPPORTED** |
| 8 | `6cac0d1aa165` | who sings the whiskey ai n 't workin anymore | `Travis Tritt` | `unordered_list` | Block 0, Row 3 | `Travis Tritt -- lead vocals` | **SUPPORTED** |
| 9 | `70f2237c7d82` | what does it mean on tinder common connections | `Common Connections allows users to see...` | `unordered_list` | Block 0, Row 2 | `Common Connections allows users to see whether they share a mutual Facebook friend with a match...` | **SUPPORTED** |
| 10 | `0c0db792e51c` | freak show girl kidnapped by clown | `Bonnie Lipton ( portrayed by Skyler Samuels )` | `unordered_list` | Block 0, Row 1 | `Bonnie Lipton ( portrayed by Skyler Samuels ) is a young girl who is kidnapped by Twisty...` | **SUPPORTED** |
| 11 | `8fe0d283d48f` | who played the detective in little boy blue | `Stephen Graham` | `unordered_list` | Block 0, Row 0 | `Stephen Graham -- Detective Superintendent Dave Kelly` | **SUPPORTED** |
| 12 | `bd673bbbf88e` | last time womens hockey won gold | `2018` | `unordered_list` | Block 0, Row 5 | `2018 -- Won gold medal` | **SUPPORTED** |
| 13 | `895b51341738` | won most superbowls as a player | `Bill Belichick` | `unordered_list` | Block 0, Row 0 | `Bill Belichick : two as defensive coordinator... and five as head coach...` | **AMBIGUOUS** |
| 14 | `5fe035e52e2f` | most rushing yards in a super bowl | `Timmy Smith` | `unordered_list` | Block 0, Row 0 | `Timmy Smith -- Washington vs. Denver , XXII` | **SUPPORTED** |
| 15 | `f3bd270e6e39` | when did ww2 end in the pacific | `September 2 , 1945` | `unordered_list` | Block 0, Row 22 | `September 2 , 1945 -- Formal Japanese surrender ceremony aboard USS Missouri...` | **SUPPORTED** |
| 16 | `2b464be1aa40` | who played the dad in a christmas story | `Ian Petrella` | `unordered_list` | Block 0, Row 2 | `Ian Petrella as Randy Parker` (Darren McGavin played Mr. Parker / The Old Man) | **ANNOTATOR_ERROR** |
| 17 | `2d7ca2fd4dc8` | cities in san joaquin county california | `Escalon` | `unordered_list` | Block 0, Row 0 | `Escalon` (in list of incorporated cities) | **SUPPORTED** |
| 18 | `75bbbd97c66a` | who played in last train from gun hill | `Kirk Douglas` | `unordered_list` | Block 0, Row 0 | `Kirk Douglas as Matt Morgan` | **SUPPORTED** |
| 19 | `ed97c4527e06` | allowed to vote in scottish referendum | `British citizens who were resident in Scotland` | `unordered_list` | Block 0, Row 0 | `British citizens who were resident in Scotland ;` | **SUPPORTED** |
| 20 | `9d4004bfbffc` | plays reggie the robot in justin 's house | `Ben Faulks` | `unordered_list` | Block 0, Row 13 | `Ben Faulks -- Mr Bloom & Reginald T Robot` | **SUPPORTED** |
| 21 | `a96d5b005f1b` | ruler of england in 1616 | `James I , King of England` | `unordered_list` | Block 0, Row 4 | `England - James I , King of England ( 1603 -- 1625 )` | **SUPPORTED** |
| 22 | `521b6a03b870` | played little boy in polar express | `Dante Pastula` | `unordered_list` | Block 0, Row 27 | `Dante Pastula as the Little Boy` | **SUPPORTED** |
| 23 | `3d3088e34ece` | plays big momma in big mommas house | `Martin Lawrence` | `unordered_list` | Block 0, Row 0 | `Martin Lawrence as Agent Malcolm Turner / Big Momma` | **SUPPORTED** |
| 24 | `a0ee91b8934a` | father of lucius in gladiator | `Lucius Verus` | `unordered_list` | Block 0, Row 12 | `Spencer Treat Clark as Lucius Verus : The young son of Lucilla . He is named after his father Lucius Verus` | **SUPPORTED** |
| 25 | `3e9bc967f199` | cast of the have and have nots play | `Palmer Williams Jr. as Floyd` | `unordered_list` | Block 0, Row 0 | `Palmer Williams Jr. as Floyd` | **SUPPORTED** |
| 26 | `f24383739b99` | nobel laureate began career as accountant | `Amartya Sen` | `unordered_list` | Block 0, Row 4 | `Amartya Sen ( 1998 , Economics )` (Only names/years listed; Raman was accountant) | **ANNOTATOR_ERROR** |
| 27 | `023650271daf` | zebras name in peppa pig | `Zoe Zebra` | `unordered_list` | Block 0, Row 0 | `Zoe Zebra ( voiced by Sian Taylor in series 2 -- 4... ) -- Zoe is one of Peppa 's best friends...` | **SUPPORTED** |
| 28 | `a5c30bbe447b` | played pink in pink floyd the wall | `Bob Geldof as Pink` | `clean_prose` / `ul` | Block 0, Row 0 | `Bob Geldof as Pink` (in list, but also in clean prose; model answered `Bob Geldof`) | **SUPPORTED** |
| 29 | `2a25e7ad4ad4` | states in northeast region | `Connecticut` | `unordered_list` | Block 0, Row 0 | `Division 1 : New England ( Connecticut , Maine , Massachusetts , Rhode Island... )` | **SUPPORTED** |
| 30 | `503e03162815` | fastest train in india and speed | `Mumbai Rajdhani Express` | `unordered_list` | Block 0, Row 0 | `Fastest train in India : 12951 / 52 Mumbai Rajdhani Express considering average speed...` | **SUPPORTED** |
| 31 | `04070d67a81e` | uruguay located along what body of water | `Bay of Montevideo` | `unordered_list` | Block 0, Row 0 | `Bay of Montevideo` | **SUPPORTED** |
| 32 | `3e87ec576a42` | spices in chinese 5 spice powder | `Star anise` | `unordered_list` | Block 0, Row 0 | `Star anise ( bajiao 八角 )` | **SUPPORTED** |
| 33 | `c530f07f4ff0` | plays the queen in victoria and abdul | `Judi Dench` | `unordered_list` | Block 0, Row 0 | `Judi Dench as Queen Victoria` | **SUPPORTED** |
| 34 | `c52fb4e74cf6` | paul walkers cars in fast and furious | `1995 Mitsubishi Eclipse` | `unordered_list` | Block 0, Row 0 | `1995 Mitsubishi Eclipse - Shot at by Johnny Tran and later destroyed...` | **SUPPORTED** |

---

## 3. Comprehensive Breakdown of All 101 Condition D Failures

Across the 101 Condition D failure cases ($200 - 99 = 101$), the audit establishes the following mutually exclusive categories:

```
Total Condition D Failures (N = 101)
├── 1. Genuine Extraction Omissions: 31 cases (30.7%)
│   ├── Unordered List Omissions: 30 cases
│   └── Ordered List Omissions: 1 case
│
├── 2. Surface-Form / Scoring Mismatches: 24 cases (23.8%)
│   ├── Multi-Entity Over-Complete Answers: 14 cases (model provided all valid entities; gold is singular)
│   ├── Unit or Category Specifier Additions: 7 cases (e.g. "Stone bridge" vs "Stone")
│   ├── Parenthetical Additions: 2 cases (e.g. "$205,700 annually (Executive Schedule I)")
│   └── Incomplete / Partial Entity: 1 case ("Bob Geldof" vs "Bob Geldof as Pink")
│
├── 3. Generation & Reasoning Failures: 44 cases (43.6%)
│   ├── Attention / Insufficient Information: 14 cases (table was in context, but model yielded)
│   └── Distractor Row / Entity Misattribution: 30 cases (wrong season, wrong year, or adjacent cell)
│
└── 4. Irrecoverable Dataset / Annotator Errors: 2 cases (2.0%)
    ├── Ian Petrella (labeled as dad; text clearly says brother Randy Parker)
    └── Amartya Sen (labeled as accountant; text does not support)
```

### 3.1. Analysis of Surface-Form Mismatches ($N=24$)
In 14 cases (`SURFACE_FORM_MULTI_ENTITY_OVERCOMPLETE`), the model answered questions with high precision, generating the complete set of requested entities where the Natural Questions benchmark only credited a single entity:
- **Q**: *what are the band members names of the rolling stones* $\to$ **Gold**: `Mick Jagger` $\to$ **Model**: `Mick Jagger, Keith Richards, Charlie Watts, Ronnie Wood`.
- **Q**: *who starred in the movie romancing the stone* $\to$ **Gold**: `Michael Douglas` $\to$ **Model**: `Michael Douglas, Kathleen Turner, Danny DeVito, Alfonso Arau, Manuel Ojeda`.
- **Q**: *who wrote trust and believe by keyshia cole* $\to$ **Gold**: `Keyshia Cole` $\to$ **Model**: `Keyshia Cole, Darhyl Camper, Jr., Jessyca Wilson & Guordan Banks`.

Under strict string Exact Match, these are scored as failures (`exact_match = False`), but under containment they are correct (`containment = True`).

### 3.2. Analysis of Generation / Reasoning Failures ($N=44$)
1. **Attention / Context-Length Fatigue (14 cases)**: The model returned `"Insufficient information"` even though the containing markdown table was present in the prompt. These tables are generally dense ($>15$ rows or $>8$ columns), causing the local LLM to miss the specific coordinate cell.
2. **Distractor Row Selections (30 cases)**: The model extracted an answer from the table, but selected the wrong row:
   - Temporal mismatch: e.g. *who won the first celebrity big brother* $\to$ model extracted `Shilpa Shetty` (winner of series 5) instead of `Jack Dee` (winner of series 1).
   - Format mismatch: e.g. *where is the eagle creek fire located in oregon* $\to$ model answered `Cascade Locks, Oregon, United States` whereas gold was geographic coordinates `45 ° 37 ′ 48 '' N 121 ° 54 ′ 14 '' W`.

---

## 4. Minimal Reproducible Extraction Fixtures

To enable rigorous, test-driven validation of list extraction without touching production code, 5 minimal HTML fixtures and an isolated parser were developed in `results/diagnostic_experiment_4_v1/failure_attribution_20261010/extraction_fixtures/`:

1. `fixture_01_key_value_list.html`: Tests entity-role binding (`Entity -- Role`, `Entity as Role`) and qualifier preservation (release dates, regional restrictions).
2. `fixture_02_nested_list.html`: Tests nested hierarchy preservation (`Parent Category > Child Item`) so sub-items do not lose their division context.
3. `fixture_03_ordered_list.html`: Tests ranked sequence preservation (`1. China: 19%`, `6. South Africa: 1%`).
4. `fixture_04_malformed_list.html`: Tests unclosed `<li>` recovery and ensures subsequent `<p>` tags are not swallowed.
5. `fixture_05_negative_distractor_list.html`: Tests boilerplate/navigation link filtering so navigation menus are excluded from the context token budget.

### 4.1. Fixture Test Suite Execution
The test suite `scripts/test_experiment_4_3_fixtures.py` was executed via pytest:
```
============================= test session starts ==============================
rootdir: /home/chandan/Projects/major-project/precis
collected 5 items

scripts/test_experiment_4_3_fixtures.py::TestExperiment43Fixtures::test_fixture_01_key_value_binding_and_qualifiers PASSED [ 20%]
scripts/test_experiment_4_3_fixtures.py::TestExperiment43Fixtures::test_fixture_02_nested_list_hierarchy PASSED [ 40%]
scripts/test_experiment_4_3_fixtures.py::TestExperiment43Fixtures::test_fixture_03_ordered_rankings PASSED [ 60%]
scripts/test_experiment_4_3_fixtures.py::TestExperiment43Fixtures::test_fixture_04_malformed_unclosed_tags PASSED [ 80%]
scripts/test_experiment_4_3_fixtures.py::TestExperiment43Fixtures::test_fixture_05_negative_boilerplate_filtering PASSED [100%]

============================== 5 passed in 0.02s ===============================
```

---

## 5. Safety, Verification & Artifact Digest Table

All preflight and post-execution hashes match bit-for-bit. Production files remain 100% untouched.

| Artifact | Path | SHA-256 Digest | Status |
| :--- | :--- | :--- | :---: |
| `sample_manifest.jsonl` | `results/diagnostic_structural_decompilation_v3/sample_manifest.jsonl` | `011553c0725621b7dda73aad12254d100e6fc15f49a5f80f4524156eb4e25db7` | **MATCH** |
| `eval_records_stage_c.jsonl` | `results/diagnostic_structural_decompilation_v3/eval_records_stage_c.jsonl` | `e10ea38f7cc7cfa9a98d494851de8c41c322b5f148dfff653077193917933687` | **MATCH** |
| `nq_dev.jsonl` | `backend/data/nq_subset/nq_dev.jsonl` | `14efc255a596433d6bf10dd853a1915474a5d3f6b47c593f77911ab4bb8eb491` | **MATCH** |
| `eval_records.jsonl` | `results/diagnostic_experiment_4_v1/full_cohort_threshold_20261010/eval_records.jsonl` | `d8a42cc906bf7fa4aebafff6868345c20a0667f971dea4f2309e3e199a3079f0` | **MATCH** |
| `eval_experiment_4_2_threshold.py` | `scripts/eval_experiment_4_2_threshold.py` | `2ebabbcfb247721935366f69999fd798c9fcd6105cbf44e5967435a582fac606` | **MATCH** |
| `test_experiment_4_2_integrity.py` | `scripts/test_experiment_4_2_integrity.py` | `f01840d94d02de61c099c2e67f448ef7c18254ec1931e341f101df6afbf38487` | **MATCH** |
| `diagnostic_list_extractor.py` | `scripts/diagnostic_list_extractor.py` | `217d8383f98018e6921fb9be54c5c249a2123ee977a4a067ffdb5ea32560a63d` | **NEW (Isolated)** |
| `test_experiment_4_3_fixtures.py` | `scripts/test_experiment_4_3_fixtures.py` | `1160358893d5f8185d34190c427387a2ae5523ce2eb5b508f75c02bcf1b15175` | **NEW (Isolated)** |

- `git diff --check`: **0 issues**.
- Production modifications under `backend/src/precis/`: **0 lines modified**.
- Live inference performed: **0 tokens generated**.

---

## 6. Gate 1 Deliverables Summary

All Gate 1 artifacts are serialized in `results/diagnostic_experiment_4_v1/failure_attribution_20261010/`:
1. `failure_inventory.jsonl`: Auditable case-by-case records for all 101 Condition D failures.
2. `failure_taxonomy_summary.json`: Aggregated counts across categories, structures, answerability, and interventions.
3. `extraction_fixtures/`: 5 minimal reproducible HTML fixtures and test assets.
4. `gate_1_report.md`: This comprehensive report.
5. `walkthrough.md`: Executive summary walkthrough.
6. `integrity_report.json`: Verification of all frozen digests and test runs.

---

## 7. Decision Gate & Next Steps Recommendation

**Recommendation**: **READY FOR TARGETED DIAGNOSTICS**

### Supporting Rationale:
1. **Definitive Root Cause Identified**: The 31 genuine extraction omission cases have a single, clean architectural root cause: they reside in HTML list markup (`<ul>`/`<ol>`) that was parsed by `StructuralDocumentParser` but excluded by `include_lists = False`.
2. **High Recovery Potential**: 31 of 34 cases have clear, unambiguous evidence in the list structures that answers the query directly.
3. **Low Token Overhead**: Packing compact GFM list representations adds modest tokens (mean list size $\sim 40$ tokens), well within the 2,048 token context ceiling.
4. **Targeted Diagnostic Protocol for Gate 2**:
   - Evaluate the candidate list extraction module specifically on the **31 verified extraction omission cases** first.
   - Run in an isolated runner with zero changes to production code.
   - Verify that recovering list evidence translates to end-to-end answer accuracy without introducing new regressions before proposing any full-cohort run.

Execution stops here. We await your explicit review and authorization before proceeding to Gate 2.
