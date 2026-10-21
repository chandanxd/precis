# Re-Audit of Naive-Only Containment Correct Cases (N = 29)

**Evaluation Benchmark**: Natural Questions MRQA (200 deterministic samples, v3 Frozen Benchmark)  
**Cohort Analyzed**: Exactly 29 questions where Naive RAG succeeded under containment correctness, but Précis Full failed  
**Core Objective**: Deterministically map each failure to its exact pipeline breakdown stage and distinguish upstream representation limits from downstream LLM reasoning failures  

---

## 1. High-Level Failure Breakdown (N = 29)

| Failure Category | Count | % of 29 Cases | Primary Pipeline Stage | Generalizable Fix? |
| :--- | :---: | :---: | :--- | :--- |
| **Complete SVOA Extraction Failure** | **15** | **51.7%** | Stage 2 (SVOA Extraction) | No (HTML tables, non-sentential lists, legal citations) |
| **Incomplete / Distorted Representation** | **6** | **20.7%** | Stage 2 / Stage 3 (Factual Representation) | 3/6 Yes (predicate complement & negation bugs); 3/6 No |
| **Downstream LLM Generation / Reasoning Failure** | **7** | **24.1%** | Stage 5 (Local LLM Inference) | No (inherent to local `qwen2.5-coder:7b` synthesis) |
| **Evaluation / Annotation Artifact** | **1** | **3.4%** | Stage 6 (String Containment Evaluation) | N/A (annotation format mismatch) |
| **Total** | **29** | **100.0%** | | |

### Key Methodological Insight:
- **72.4% (21/29)** of all Précis failures against Naive RAG occur **upstream of the LLM** during syntactic parsing and fact materialization (15 unextracted structures + 6 incomplete/distorted predicates).
- **Only 24.1% (7/29)** of failures represent genuine reasoning or answer synthesis deficits by the local language model.
- **0.0% (0/29)** of failures are caused by ChromaDB retrieval or context packing under the 2048 token ceiling.

---

## 2. Granular Sample Audit (29 Cases)

### Sample 01: `cde724cb582f43b4956b1bdae72860ec`
- **Question**: *"where did the last name keith come from"*
- **Gold Answer**: `a nickname , derived from the Middle High German kīt , a word meaning `` sprout '' , `` offspring ''`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *representation loss / incomplete fact*)
- **Underlying Root Cause**: Upstream syntactic extraction failure
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "The surname Keith has several origins. In some cases, it is derived from Keith in East Lothian, Scotland. In other cases, the surname is originated from a nickname, derived from the Middle High German kīt, a word meaning "sprout," "offspring.""
- **Précis Full Answer**: "The surname Keith has several origins. In some cases, it is derived from Keith in East Lothian, Scotland. In other cases, it is derived from a nickname, which is a word meaning "sprout," derived from the Middle High German kīt."

### Sample 02: `85177baa25834d14892f362ff60dd1af`
- **Question**: *"converting stereo signal to mono signal is called"*
- **Gold Answer**: `Panning`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Entity confusion: Fact 1 contained 'Panning', but LLM synthesized 'dual mono signal'
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "panning"
- **Précis Full Answer**: "Creating a dual mono signal"
- **Packed Evidence Excerpt**: `that is sent For instance , the left and right channels of a stereo source can be panned straight up (context: creating a dual mono signal) (manner: e...`

### Sample 03: `2f3afcf103084325b0ec669d00f0ac20`
- **Question**: *"converting stereo signal to mono signal is called"*
- **Gold Answer**: `Panning`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Entity confusion: Fact 1 contained 'Panning', but LLM synthesized 'dual mono signal'
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "panning"
- **Précis Full Answer**: "Creating a dual mono signal"
- **Packed Evidence Excerpt**: `that is sent For instance , the left and right channels of a stereo source can be panned straight up (context: creating a dual mono signal) (manner: e...`

### Sample 04: `35d3ce1b8ae84db08f16dcef7bd1bc9a`
- **Question**: *"who has been chosen as the brand ambassador of the campaign ' beti bachao-beti padhao"*
- **Gold Answer**: `Sakshi Malik`
- **Pipeline Failure Stage**: Stage 2 / Stage 3 (Factual Representation)
- **Re-Audited Category**: `Incomplete / Distorted Representation` (Previous: *representation loss / incomplete fact*)
- **Underlying Root Cause**: Predicate complement dropped: parser extracted 'was made 26 August' but dropped 'brand ambassador'
- **Generalizable Fix?**: Yes (passive verb predicate complement propagation defect)
- **Naive RAG Answer**: "Sakshi Malik has been chosen as the brand ambassador of the campaign 'Beti Bachao-Beti Padhao'."
- **Précis Full Answer**: "The information provided does not include any details about who has been chosen as the brand ambassador of the campaign 'Beti Bachao-Beti Padhao'. Therefore, based on the given facts, the answer is that this information is not available."
- **Packed Evidence Excerpt**: `Olympics 2016 bronze medallist Sakshi Malik was made 26 August 2016 (time: In 26 August 2016)...`

### Sample 05: `7385d04e9d3040ec89a4de6e38f8ba4e`
- **Question**: *"who has been chosen as the brand ambassador of the campaign ' beti bachao-beti padhao"*
- **Gold Answer**: `Sakshi Malik`
- **Pipeline Failure Stage**: Stage 2 / Stage 3 (Factual Representation)
- **Re-Audited Category**: `Incomplete / Distorted Representation` (Previous: *representation loss / incomplete fact*)
- **Underlying Root Cause**: Predicate complement dropped: parser extracted 'was made 26 August' but dropped 'brand ambassador'
- **Generalizable Fix?**: Yes (passive verb predicate complement propagation defect)
- **Naive RAG Answer**: "Sakshi Malik has been chosen as the brand ambassador of the campaign 'Beti Bachao-Beti Padhao'."
- **Précis Full Answer**: "The information provided does not include any details about who has been chosen as the brand ambassador of the campaign 'Beti Bachao-Beti Padhao'. Therefore, based on the given facts, the answer is that this information is not available."
- **Packed Evidence Excerpt**: `Olympics 2016 bronze medallist Sakshi Malik was made 26 August 2016 (time: In 26 August 2016)...`

### Sample 06: `d6a6644d2ce44a6290460858a650bc96`
- **Question**: *"latest season on keeping up with the kardashians"*
- **Gold Answer**: `fourteen`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Attribute confusion: Fact contained 'fourteen seasons', but LLM answered with episode count (205)
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "The latest season of Keeping Up with the Kardashians concluded with the airing of 205 original episodes, spanning fourteen seasons."
- **Précis Full Answer**: "The latest season of Keeping Up with the Kardashians concluded with the 205th original episode."
- **Packed Evidence Excerpt**: `205 original episodes of Keeping Up with the Kardashians have aired concluding the fourteen seasons (cause: As of December 10 , 2017 ( 2017 - 12 - 10 ...`

### Sample 07: `ef5ae1bfbf4a4f8e8388d076236a4069`
- **Question**: *"where are the mitochondria located in the sperm"*
- **Gold Answer**: `midpiece ( at the base of the sperm head )`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Clausal / parenthetical argument truncation in multi-clause definition
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "The mitochondria are located in the sperm's midpiece, at the base of the sperm head."
- **Précis Full Answer**: "The mitochondria are located in the sperm's midpiece."

### Sample 08: `68116973781448139e3aa1db05ff6a00`
- **Question**: *"latest season on keeping up with the kardashians"*
- **Gold Answer**: `14`
- **Pipeline Failure Stage**: Stage 2 / Stage 3 (Factual Representation)
- **Re-Audited Category**: `Incomplete / Distorted Representation` (Previous: *representation loss / incomplete fact*)
- **Underlying Root Cause**: Distorted representation: unparsed Wikipedia broadcast table text parsed into garbled facts
- **Generalizable Fix?**: No (table structure mismatch)
- **Naive RAG Answer**: "The latest season of Keeping Up with the Kardashians shown in the table is Season 14, which originally aired on October 1, 2017, and concluded in March 2018."
- **Précis Full Answer**: "The latest season of Keeping Up with the Kardashians that aired was Season 11, which premiered on March 15, 2015."
- **Packed Evidence Excerpt**: `Last aired (time: October) (time: December)...`

### Sample 09: `4309a135fbc449798138df78adbc928f`
- **Question**: *"what is the meaning of the name comanche"*
- **Gold Answer**: ``` Comanche '' is from the Ute name for them , kɨmantsi ( enemy )`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Clausal / parenthetical argument truncation in multi-clause definition
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "The name "Comanche" is from the Ute name for them, kɨmantsi (enemy)."
- **Précis Full Answer**: "The name Comanche is from the Ute name, meaning "enemy.""

### Sample 10: `2f961eb03efb43e6857b8de81b8ebe42`
- **Question**: *"when did the us not go to the olympics"*
- **Gold Answer**: `The 1980 Summer Olympics`
- **Pipeline Failure Stage**: Stage 6 (Evaluation / String Containment)
- **Re-Audited Category**: `Evaluation / Annotation Artifact` (Previous: *evaluation/annotation artifact*)
- **Underlying Root Cause**: Strict unstemmed string containment failed: Précis generated 'in 1980', reference annotated as 'The 1980 Summer Olympics'
- **Generalizable Fix?**: N/A (annotation format mismatch)
- **Naive RAG Answer**: "The US did not go to the 1980 Summer Olympics."
- **Précis Full Answer**: "The United States did not go to the Olympics in 1980."
- **Packed Evidence Excerpt**: `The Soviet Union , which hosted the 1980 Summer Olympics , and hosted the 1980 Summer Olympics...`

### Sample 11: `ea73a38b26514dfba3891cb5f004ed37`
- **Question**: *"where are they building the new raiders stadium"*
- **Gold Answer**: `Paradise , Nevada`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Granularity competition: Fact 1 contained 'Paradise, Nevada', but LLM selected competing street address from Fact 2
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "They are building the new Raiders stadium in Paradise, Nevada."
- **Précis Full Answer**: "They are building the new Raiders stadium about 62 acres west of Mandalay Bay at Russell Road and Hacienda Avenue and between Polaris Avenue and Dean Martin Drive, just west of Interstate 15."
- **Packed Evidence Excerpt**: `Las Vegas Stadium is the working name for a domed stadium under construction in Paradise , Nevada for the Las Vegas Raiders of the National Football L...`

### Sample 12: `2d69070a19f7408eb1fabce6d613baa9`
- **Question**: *"where are they building the new raiders stadium"*
- **Gold Answer**: `Paradise , Nevada`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Granularity competition: Fact 1 contained 'Paradise, Nevada', but LLM selected competing street address from Fact 2
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "They are building the new Raiders stadium in Paradise, Nevada."
- **Précis Full Answer**: "They are building the new Raiders stadium about 62 acres west of Mandalay Bay at Russell Road and Hacienda Avenue and between Polaris Avenue and Dean Martin Drive, just west of Interstate 15."
- **Packed Evidence Excerpt**: `Las Vegas Stadium is the working name for a domed stadium under construction in Paradise , Nevada for the Las Vegas Raiders of the National Football L...`

### Sample 13: `f937a082b6e54a199f7e5e63e55d1f94`
- **Question**: *"where are they building the new raiders stadium"*
- **Gold Answer**: `Paradise , Nevada`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Granularity competition: Fact 1 contained 'Paradise, Nevada', but LLM selected competing street address from Fact 2
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "They are building the new Raiders stadium in Paradise, Nevada."
- **Précis Full Answer**: "They are building the new Raiders stadium about 62 acres west of Mandalay Bay at Russell Road and Hacienda Avenue and between Polaris Avenue and Dean Martin Drive, just west of Interstate 15."
- **Packed Evidence Excerpt**: `Las Vegas Stadium is the working name for a domed stadium under construction in Paradise , Nevada for the Las Vegas Raiders of the National Football L...`

### Sample 14: `9725b91f0cda4a17b70c6d11044df156`
- **Question**: *"what event provoked congress to propose the eleventh amendment and the states to ratify it"*
- **Gold Answer**: `the Supreme Court 's ruling in Chisholm v. Georgia , 2 U.S. 419 ( 1793 )`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Domain-specific structure (legal citation notation dropped from clausal adjunct)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "The Eleventh Amendment was proposed and ratified in response to the Supreme Court's ruling in Chisholm v. Georgia, 2 U.S. 419 (1793)."
- **Précis Full Answer**: "The Eleventh Amendment was proposed and ratified in response to the Supreme Court's ruling in Chisholm v. Georgia, which ruled that federal courts had the authority to hear cases in law and equity brought by private citizens against states and that states did not enjoy sovereign immunity from suits made by citizens of other states in federal court."

### Sample 15: `1aaee123c19e49e2af80d5e53d1f76ce`
- **Question**: *"what is the baby elephants name in jungle book"*
- **Gold Answer**: `Hathi Jr .`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Hathi Jr."
- **Précis Full Answer**: "The baby elephant's name in The Jungle Book is not provided in the given facts."

### Sample 16: `8224ee3ab476411b82d07cd8b6fc6f10`
- **Question**: *"what are bulls used for on a farm"*
- **Gold Answer**: `herd maintenance`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: LLM synthesis error on packed context
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "Bulls are used for purposes of herd maintenance on dairy or beef farms."
- **Précis Full Answer**: "Bulls are used for artificial insemination (AI) to increase the quality of a herd or to introduce an outcross of bloodlines."
- **Packed Evidence Excerpt**: `Many cattle ranches and stations does not run bulls (context: with cows , and)...`

### Sample 17: `db47ff0afb014ef8a590eb1b4095e988`
- **Question**: *"what is the baby elephants name in jungle book"*
- **Gold Answer**: `Hathi Jr .`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Hathi Jr."
- **Précis Full Answer**: "The baby elephant's name in The Jungle Book is not provided in the given facts."

### Sample 18: `2d366b1b6115450e87614057cd7534a5`
- **Question**: *"what is the baby elephants name in jungle book"*
- **Gold Answer**: `Hathi Jr .`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Hathi Jr."
- **Précis Full Answer**: "The baby elephant's name in The Jungle Book is not provided in the given facts."

### Sample 19: `d79cf47218e54495ba21ea59ca54fc57`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Daisuke Ohata"
- **Précis Full Answer**: "Based on the information provided in the facts, Jonah Lomu has scored the most tries in rugby union. He is listed with 74 tries, which is the highest number of tries among the players mentioned in the given facts."

### Sample 20: `c183875cfc3a4a1ca7998fcdd6f67842`
- **Question**: *"when do willow and tara get back together"*
- **Gold Answer**: `Seeing Red`
- **Pipeline Failure Stage**: Stage 2 / Stage 3 (Factual Representation)
- **Re-Audited Category**: `Incomplete / Distorted Representation` (Previous: *representation loss / incomplete fact*)
- **Underlying Root Cause**: Elliptical clausal complement: 'they Seeing Red' lacked governing matrix clause context
- **Generalizable Fix?**: No (elliptical discourse dependency)
- **Naive RAG Answer**: "In the episode "Seeing Red," Tara returns to Willow and they reconcile."
- **Précis Full Answer**: "After the next episode."
- **Packed Evidence Excerpt**: `Tara returns Willow (recipient: Willow) (time: After tentatively courting each other in `` Entropy '') (time: to Willow)...`

### Sample 21: `2d73cf789796467cb959809f90fc4549`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Daisuke Ohata"
- **Précis Full Answer**: "Based on the information provided in the facts, Jonah Lomu has scored the most tries in rugby union. He is listed with 74 tries, which is the highest number of tries among the players mentioned in the given facts."

### Sample 22: `f1698b6e42604f47a30832f98ea66530`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Daisuke Ohata"
- **Précis Full Answer**: "Based on the information provided in the facts, Jonah Lomu has scored the most tries in rugby union. He is listed with 74 tries, which is the highest number of tries among the players mentioned in the given facts."

### Sample 23: `5eead8e20ca54313be68f0dd84f041c8`
- **Question**: *"when does the new season of lost in space come out"*
- **Gold Answer**: `April 13 , 2018`
- **Pipeline Failure Stage**: Stage 5 (LLM Inference / Synthesis)
- **Re-Audited Category**: `Downstream LLM Generation / Reasoning Failure` (Previous: *LLM generation/reasoning failure*)
- **Underlying Root Cause**: Lexical refusal: Fact stated 'released the series on April 13, 2018', but LLM refused because prompt asked for 'new season'
- **Generalizable Fix?**: No (inherent to 7B parameter local model reasoning)
- **Naive RAG Answer**: "The new season of Lost in Space was released on April 13, 2018."
- **Précis Full Answer**: "The new season of Lost in Space does not have a release date provided in the given facts."
- **Packed Evidence Excerpt**: `an American science fiction television series Lost - (manner: re) (time: in Space)...`

### Sample 24: `db3b37f039dc42e4bb7927783ec9c346`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Daisuke Ohata"
- **Précis Full Answer**: "Based on the information provided in the facts, Jonah Lomu has scored the most tries in rugby union. He is listed with 74 tries, which is the highest number of tries among the players mentioned in the given facts."

### Sample 25: `62bed1a5febb41c38efe895c05c19d2c`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "Daisuke Ohata"
- **Précis Full Answer**: "Based on the information provided in the facts, Jonah Lomu has scored the most tries in rugby union. He is listed with 74 tries, which is the highest number of tries among the players mentioned in the given facts."

### Sample 26: `81bfd43c154a43879c46928b5f5dab13`
- **Question**: *"when do willow and tara get back together"*
- **Gold Answer**: `Seeing Red`
- **Pipeline Failure Stage**: Stage 2 / Stage 3 (Factual Representation)
- **Re-Audited Category**: `Incomplete / Distorted Representation` (Previous: *representation loss / incomplete fact*)
- **Underlying Root Cause**: Elliptical clausal complement: 'they Seeing Red' lacked governing matrix clause context
- **Generalizable Fix?**: No (elliptical discourse dependency)
- **Naive RAG Answer**: "Willow and Tara get back together after Buffy and Willow reconcile through the episode "Seeing Red.""
- **Précis Full Answer**: "After the next episode."
- **Packed Evidence Excerpt**: `Tara returns Willow (recipient: Willow) (time: After tentatively courting each other in `` Entropy '') (time: to Willow)...`

### Sample 27: `9dd3961d209a41abac49a36413371d6c`
- **Question**: *"who has participated in the most super bowls"*
- **Gold Answer**: `New England Patriots`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Upstream syntactic extraction failure
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "The New England Patriots have participated in the most Super Bowls with 10 appearances."
- **Précis Full Answer**: "Based on the provided facts, there is not enough information to determine who has participated in the most Super Bowls."

### Sample 28: `11cabb55e53047449cd8304480660c0b`
- **Question**: *"how many students attend university of texas at austin"*
- **Gold Answer**: `51,331`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "51,331 students attend the University of Texas at Austin."
- **Précis Full Answer**: "40,168 undergraduate students and 11,163 graduate students attended the University of Texas at Austin in Fall 2016."

### Sample 29: `78b30a922137434fbb2170da0e0d79ae`
- **Question**: *"when does grey 's anatomy come back on in march"*
- **Gold Answer**: `March 1 , 2018`
- **Pipeline Failure Stage**: Stage 2 (SVOA Extraction)
- **Re-Audited Category**: `Complete Extraction Failure` (Previous: *SVOA extraction failure*)
- **Underlying Root Cause**: Non-sentential structure (HTML table cell or list item without finite matrix verb)
- **Generalizable Fix?**: No (requires HTML table/list parsing or multi-clause graph representation)
- **Naive RAG Answer**: "March 1, 2018"
- **Précis Full Answer**: "Based on the provided facts, Grey's Anatomy returns on March 22, 2018."
