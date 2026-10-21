# SVOA Representation Loss Audit (v3 Frozen Benchmark)

**Audit Scope**: All 23 complete extraction failures across the 200-sample benchmark dataset  
**Benchmark Baseline**: Natural Questions MRQA (`qwen2.5-coder:7b`, deterministic greedy decoding)  
**Authoritative Evidence**: `results/nq_benchmark_svoa_enhanced_v3/per_question_results.jsonl`, `nq_dev.jsonl`, `failure_analysis.jsonl`  

---

## 1. Aggregate Taxonomy of Extraction Failures (N = 23)

| Failure Category | Count | % of Extraction Failures | Primary Epistemic Status | General Fixability | Architectural Change Required? |
| :--- | :---: | :---: | :--- | :--- | :---: |
| **NON_SENTENTIAL_STRUCTURE** | 12 | 52.2% | Source-format mismatch | NOT_FIXABLE_WITH_CURRENT_REPRESENTATION | Yes (Table/List parsing) |
| **MULTI_CLAUSE_REPRESENTATION_LIMIT** | 3 | 13.0% | Representation limitation | NOT_FIXABLE_WITH_CURRENT_REPRESENTATION | Yes (Discourse/clausal graphs) |
| **DOMAIN_SPECIFIC_STRUCTURE** | 3 | 13.0% | Representation limitation | DOMAIN_SPECIFIC_HEURISTIC | No (Domain pattern) |
| **IMPLEMENTATION_DEFECT** | 2 | 8.7% | Implementation defect | SAFE_GENERIC_FIX / GENERALIZATION | No |
| **QUALIFIER_OR_ARGUMENT_LOSS** | 2 | 8.7% | Implementation defect | SAFE_GENERIC_FIX | No |
| **EVALUATION_OR_ANNOTATION_ARTIFACT** | 1 | 4.3% | Evaluation artifact | NOT_FIXABLE_WITH_CURRENT_REPRESENTATION | No |
| **Total** | **23** | **100.0%** | | | |

---

## 2. Case-by-Case Deep Audit (23 Samples)

### Case 01: `cde724cb582f43b4956b1bdae72860ec`
- **Question**: *"where did the last name keith come from"*
- **Gold Answer**: `a nickname , derived from the Middle High German kīt , a word meaning `` sprout '' , `` offspring ''`
- **Source Snippet**: `In other cases the surname is originated from a nickname , derived from the Middle High German kīt , a word meaning `` sprout '' , `` offspring '' .`
- **Source Structure Type**: Complex sentence with appositive and participle clause
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=originated (VERB, passive); nickname (pobj of from); derived (acl of nickname); word (appos of nickname).
- **Why No Fact Produced**: The 21-word compound gold answer spans multiple appositives and participle phrases ('a nickname, derived from..., a word meaning...'). SVOA decomposes this into 4 atomic propositions, none of which spans the full 21-word string.
- **Exact Information Lost**: Global multi-clause syntactic span linkage across appositives.
- **Failure Category**: `MULTI_CLAUSE_REPRESENTATION_LIMIT`
- **Epistemic Classification**: `representation_limitation`
- **Fix Classification**: `NOT_FIXABLE_WITH_CURRENT_REPRESENTATION`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 02: `99cc99558fde44128f06b5d3d3b6abb2`
- **Question**: *"in order to prove disparate impact you first must establish"*
- **Gold Answer**: `practices in employment , housing , and other areas that adversely affect one group of people of a protected characteristic more than another , even though rules applied by employers or landlords are formally neutral`
- **Source Snippet**: `<P> Disparate impact in United States labor law refers to practices in employment , housing , and other areas that adversely affect one group of people of a protected characteristic more than another , even though rules applied by employers or landlords are formally neutral .`
- **Source Structure Type**: Complex legal definition with prepositional complement and relative clause
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=refers (VERB); impact (nsubj); to (prep); practices (pobj); affect (relcl of practices).
- **Why No Fact Produced**: Matrix verb 'refers to' is intransitive with prepositional object 'practices', which SVOA does not extract as S-V-O. Furthermore, the relative clause 'that adversely affect' is nested inside the PP and was not resolved.
- **Exact Information Lost**: Propositional link between subject 'Disparate impact' and prepositional complement 'practices...'.
- **Failure Category**: `IMPLEMENTATION_DEFECT`
- **Epistemic Classification**: `implementation_defect`
- **Fix Classification**: `GENERALIZATION_REQUIRED`
- **Regression Risk**: `MEDIUM`
- **Requires Architectural Change?**: No

### Case 03: `ef5ae1bfbf4a4f8e8388d076236a4069`
- **Question**: *"where are the mitochondria located in the sperm"*
- **Gold Answer**: `midpiece ( at the base of the sperm head )`
- **Source Snippet**: `This takes place in the mitochondria located in the sperm 's midpiece ( at the base of the sperm head ) .`
- **Source Structure Type**: Sentence with prepositional phrase and clarifying parenthetical
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=takes (VERB); place (dobj); in (prep); mitochondria (pobj); located (acl); in (prep); midpiece (pobj); at (prep, attached to takes).
- **Why No Fact Produced**: Fact 2 correctly extracted 'the mitochondria located in the sperm's midpiece', but the benchmark gold annotation required the trailing parenthetical explanation '( at the base of the sperm head )', causing exact string containment to fail.
- **Exact Information Lost**: Parenthetical anatomical clarification retained only as separate clause adjunct.
- **Failure Category**: `EVALUATION_OR_ANNOTATION_ARTIFACT`
- **Epistemic Classification**: `evaluation_artifact`
- **Fix Classification**: `NOT_FIXABLE_WITH_CURRENT_REPRESENTATION`
- **Regression Risk**: `LOW`
- **Requires Architectural Change?**: No

### Case 04: `86f8340e3a63483a88037ed369de403d`
- **Question**: *"how dose the poet present death as a voyage in crossing the bar"*
- **Gold Answer**: `uses an extended metaphor to compare death with crossing the `` sandbar '' between river of life , with its outgoing `` flood '' , and the ocean that lies beyond ( death ) , the `` boundless deep '' , to which we return`
- **Source Snippet**: `It is considered that Tennyson wrote it in elegy ; the poem has a tone of finality and the narrator uses an extended metaphor to compare death with crossing the `` sandbar '' between river of life , with its outgoing `` flood '' , and the ocean that lies beyond ( death ) , the `` boundless deep '' , to which we return .`
- **Source Structure Type**: Multi-clause literary analysis sentence (42-word narrative explanation)
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=has (VERB); considered (ccomp); wrote (ccomp); uses (conj); to compare (advcl).
- **Why No Fact Produced**: The 42-word gold answer is an extended literary essay explanation spanning 4 clauses and multiple prepositional metaphors. SVOA decomposes it into 7 discrete propositions, none of which can encompass the full 42-word prose span.
- **Exact Information Lost**: Narrative discourse-level thematic explanation.
- **Failure Category**: `MULTI_CLAUSE_REPRESENTATION_LIMIT`
- **Epistemic Classification**: `representation_limitation`
- **Fix Classification**: `NOT_FIXABLE_WITH_CURRENT_REPRESENTATION`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 05: `4309a135fbc449798138df78adbc928f`
- **Question**: *"what is the meaning of the name comanche"*
- **Gold Answer**: ``` Comanche '' is from the Ute name for them , kɨmantsi ( enemy )`
- **Source Snippet**: `<P> The name `` Comanche '' is from the Ute name for them , kɨmantsi ( enemy ) .`
- **Source Structure Type**: Copular sentence with prepositional complement and HTML prefix
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=is (AUX); P (nsubj); name (nsubj); from (prep); name (pobj).
- **Why No Fact Produced**: Sentence has copular verb 'is' with PP complement 'from the Ute name...'. SVOA copula extraction requires nominal/adjectival complements (attr/acomp) and drops copular prepositional complements. Furthermore, leading '<P>' was parsed as a spurious subject.
- **Exact Information Lost**: Copular origin relation 'The name Comanche is from the Ute name for them'.
- **Failure Category**: `IMPLEMENTATION_DEFECT`
- **Epistemic Classification**: `implementation_defect`
- **Fix Classification**: `SAFE_GENERIC_FIX`
- **Regression Risk**: `LOW`
- **Requires Architectural Change?**: No

### Case 06: `2fbb37774d444fed82d252192c539e37`
- **Question**: *"what event provoked congress to propose the eleventh amendment and the states to ratify it"*
- **Gold Answer**: `the U.S. Supreme Court 's decision in Chisholm v. Georgia , 2 U.S. 419 ( 1793 )`
- **Source Snippet**: `The Eleventh Amendment ( Amendment XI ) to the United States Constitution , which was passed by Congress on March 4 , 1794 , and ratified by the states on February 7 , 1795 , deals with each state 's sovereign immunity and was adopted to overrule the U.S. Supreme Court 's decision in Chisholm v. Georgia , 2 U.S. 419 ( 1793 ) .`
- **Source Structure Type**: Complex sentence with legal case name and formal legal citation
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=deals (VERB); was adopted (conj); to overrule (advcl); decision (dobj); in (prep); Chisholm (pobj); v. (prep); Georgia (pobj); 2 (nummod); U.S. (appos).
- **Why No Fact Produced**: The case name 'Chisholm v. Georgia' was captured in context adjunct, but the formal legal reporter citation ', 2 U.S. 419 ( 1793 )' was parsed as parenthetical/appositive and omitted from the core proposition.
- **Exact Information Lost**: Formal legal reporter citation volume and page numbers.
- **Failure Category**: `DOMAIN_SPECIFIC_STRUCTURE`
- **Epistemic Classification**: `representation_limitation`
- **Fix Classification**: `DOMAIN_SPECIFIC_HEURISTIC`
- **Regression Risk**: `MEDIUM`
- **Requires Architectural Change?**: No

### Case 07: `9725b91f0cda4a17b70c6d11044df156`
- **Question**: *"what event provoked congress to propose the eleventh amendment and the states to ratify it"*
- **Gold Answer**: `the Supreme Court 's ruling in Chisholm v. Georgia , 2 U.S. 419 ( 1793 )`
- **Source Snippet**: `The amendment was adopted following the Supreme Court 's ruling in Chisholm v. Georgia , 2 U.S. 419 ( 1793 ) .`
- **Source Structure Type**: Passive sentence with legal case name and formal legal citation
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=adopted (VERB, passive); following (prep); ruling (pobj); in (prep); Chisholm (pobj); v. (prep); Georgia (pobj); 2 U.S. 419 (appos).
- **Why No Fact Produced**: The extracted fact captured 'The amendment was adopted following the Supreme Court ruling in Chisholm v. Georgia', but the legal citation '2 U.S. 419 (1793)' was split into manner adjunct 'U.S.', failing exact containment.
- **Exact Information Lost**: Formal legal volume and page reporter citation.
- **Failure Category**: `DOMAIN_SPECIFIC_STRUCTURE`
- **Epistemic Classification**: `representation_limitation`
- **Fix Classification**: `DOMAIN_SPECIFIC_HEURISTIC`
- **Regression Risk**: `MEDIUM`
- **Requires Architectural Change?**: No

### Case 08: `b93c70b859eb45479dd2605e12fb6671`
- **Question**: *"what event provoked congress to propose the eleventh amendment and the states to ratify it"*
- **Gold Answer**: `the U.S. Supreme Court 's decision in Chisholm v. Georgia , 2 U.S. 419 ( 1793 )`
- **Source Snippet**: `The Eleventh Amendment ( Amendment XI ) to the United States Constitution , which was passed by Congress on March 4 , 1794 , and ratified by the states on February 7 , 1795 , deals with each state 's sovereign immunity and was adopted to overrule the U.S. Supreme Court 's decision in Chisholm v. Georgia , 2 U.S. 419 ( 1793 ) .`
- **Source Structure Type**: Complex sentence with legal case name and formal legal citation
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=deals (VERB); was adopted (conj); to overrule (advcl); decision (dobj); in (prep); Chisholm (pobj); v. (prep); Georgia (pobj); 2 U.S. 419 (appos).
- **Why No Fact Produced**: The case name 'Chisholm v. Georgia' was extracted in context adjunct, but the formal legal reporter citation ', 2 U.S. 419 ( 1793 )' was omitted from the core proposition.
- **Exact Information Lost**: Formal legal volume and page reporter citation.
- **Failure Category**: `DOMAIN_SPECIFIC_STRUCTURE`
- **Epistemic Classification**: `representation_limitation`
- **Fix Classification**: `DOMAIN_SPECIFIC_HEURISTIC`
- **Regression Risk**: `MEDIUM`
- **Requires Architectural Change?**: No

### Case 09: `1aaee123c19e49e2af80d5e53d1f76ce`
- **Question**: *"what is the baby elephants name in jungle book"*
- **Gold Answer**: `Hathi Jr .`
- **Source Snippet**: `<Li> Hathi Jr . -`
- **Source Structure Type**: HTML list item (<Li> tag in bulleted character list)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Jr (PROPN); Hathi (compound); Li (nmod); no verb exists.
- **Why No Fact Produced**: Snippet is a bulleted HTML list entry '<Li> Hathi Jr . -'. It contains no verb or sentential clause. SVOA requires Subject-Verb-Object syntax and extracts 0 facts.
- **Exact Information Lost**: Character identity in non-sentential HTML bullet list.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 10: `db47ff0afb014ef8a590eb1b4095e988`
- **Question**: *"what is the baby elephants name in jungle book"*
- **Gold Answer**: `Hathi Jr .`
- **Source Snippet**: `<Li> Hathi Jr . -`
- **Source Structure Type**: HTML list item (<Li> tag in bulleted character list)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Jr (PROPN); Hathi (compound); Li (nmod); no verb exists.
- **Why No Fact Produced**: Snippet is a bulleted HTML list entry '<Li> Hathi Jr . -'. Contains no finite verb. SVOA extracts 0 facts.
- **Exact Information Lost**: Character identity in non-sentential HTML bullet list.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 11: `2d366b1b6115450e87614057cd7534a5`
- **Question**: *"what is the baby elephants name in jungle book"*
- **Gold Answer**: `Hathi Jr .`
- **Source Snippet**: `<Li> Hathi Jr . -`
- **Source Structure Type**: HTML list item (<Li> tag in bulleted character list)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Jr (PROPN); Hathi (compound); Li (nmod); no verb exists.
- **Why No Fact Produced**: Snippet is a bulleted HTML list entry '<Li> Hathi Jr . -'. Contains no finite verb. SVOA extracts 0 facts.
- **Exact Information Lost**: Character identity in non-sentential HTML bullet list.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 12: `b98f6e8089e245789007186bfe8c9c12`
- **Question**: *"what degree is a crock pot on low"*
- **Gold Answer**: `71 -- 74 ° C ( 160 -- 165 ° F )`
- **Source Snippet**: `Some cookers automatically switch from cooking to warming ( maintaining the temperature at 71 -- 74 ° C ( 160 -- 165 ° F ) after a fixed time or after the internal temperature of the food , as determined by a probe , reaches a specified value .`
- **Source Structure Type**: Complex sentence with parenthetical temperature specification
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=switch (VERB); cookers (nsubj); warming (pobj); maintaining (advcl); temperature (dobj); at (prep); 71 (pobj); -- (punct); 74 (nummod).
- **Why No Fact Produced**: The adjunct extractor truncated the parenthetical temperature span at the double hyphen '--': 'maintaining the temperature at 71 --', losing '74 ° C ( 160 -- 165 ° F )'.
- **Exact Information Lost**: Numeric temperature range span truncated at punctuation token.
- **Failure Category**: `QUALIFIER_OR_ARGUMENT_LOSS`
- **Epistemic Classification**: `implementation_defect`
- **Fix Classification**: `SAFE_GENERIC_FIX`
- **Regression Risk**: `LOW`
- **Requires Architectural Change?**: No

### Case 13: `a92bbe5aee024b93ae575aac3e28ac86`
- **Question**: *"how long prime minister stay in office canada"*
- **Gold Answer**: `until he or she resigns , is dismissed , or dies`
- **Source Snippet**: `Once appointed and sworn in by the governor general , the prime minister remains in office until he or she resigns , is dismissed , or dies .`
- **Source Structure Type**: Sentence with coordinated temporal subordinate clause
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=remains (VERB); minister (nsubj); until (mark); resigns (advcl); dismissed (conj); dies (conj).
- **Why No Fact Produced**: The gold answer is the complete coordinated temporal clause 'until he or she resigns , is dismissed , or dies'. SVOA decomposed this into 3 separate facts (Fact 1: remains until resigns; Fact 2: she resigns; Fact 3: is dismissed), losing the composite tripartite conditional condition.
- **Exact Information Lost**: Coordinated disjunctive condition in subordinate clause.
- **Failure Category**: `MULTI_CLAUSE_REPRESENTATION_LIMIT`
- **Epistemic Classification**: `representation_limitation`
- **Fix Classification**: `NOT_FIXABLE_WITH_CURRENT_REPRESENTATION`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 14: `d79cf47218e54495ba21ea59ca54fc57`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Source Snippet**: `<Td> Daisuke Ohata <`
- **Source Structure Type**: HTML table cell (<Td> tag in rugby statistics table)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Ohata (PROPN); Td (nmod); no predicate or sentence relation exists.
- **Why No Fact Produced**: Snippet is an isolated table cell '<Td> Daisuke Ohata <' inside an HTML table. Contains no finite verb or clausal structure.
- **Exact Information Lost**: Entity identity and record attribute in HTML table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 15: `2d73cf789796467cb959809f90fc4549`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Source Snippet**: `<Td> Daisuke Ohata <`
- **Source Structure Type**: HTML table cell (<Td> tag in rugby statistics table)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Ohata (PROPN); Td (nmod); no predicate or sentence relation exists.
- **Why No Fact Produced**: Snippet is an isolated table cell '<Td> Daisuke Ohata <' inside an HTML table. Contains no finite verb or clausal structure.
- **Exact Information Lost**: Entity identity and record attribute in HTML table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 16: `f1698b6e42604f47a30832f98ea66530`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Source Snippet**: `<Td> Daisuke Ohata <`
- **Source Structure Type**: HTML table cell (<Td> tag in rugby statistics table)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Ohata (PROPN); Td (nmod); no predicate or sentence relation exists.
- **Why No Fact Produced**: Snippet is an isolated table cell '<Td> Daisuke Ohata <' inside an HTML table. Contains no finite verb or clausal structure.
- **Exact Information Lost**: Entity identity and record attribute in HTML table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 17: `db3b37f039dc42e4bb7927783ec9c346`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Source Snippet**: `<Td> Daisuke Ohata <`
- **Source Structure Type**: HTML table cell (<Td> tag in rugby statistics table)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Ohata (PROPN); Td (nmod); no predicate or sentence relation exists.
- **Why No Fact Produced**: Snippet is an isolated table cell '<Td> Daisuke Ohata <' inside an HTML table. Contains no finite verb or clausal structure.
- **Exact Information Lost**: Entity identity and record attribute in HTML table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 18: `62bed1a5febb41c38efe895c05c19d2c`
- **Question**: *"who has scored the most tries in rugby union"*
- **Gold Answer**: `Daisuke Ohata`
- **Source Snippet**: `<Td> Daisuke Ohata <`
- **Source Structure Type**: HTML table cell (<Td> tag in rugby statistics table)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Ohata (PROPN); Td (nmod); no predicate or sentence relation exists.
- **Why No Fact Produced**: Snippet is an isolated table cell '<Td> Daisuke Ohata <' inside an HTML table. Contains no finite verb or clausal structure.
- **Exact Information Lost**: Entity identity and record attribute in HTML table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 19: `2ec7c62e2fe547f0802d8cf34e5e9be0`
- **Question**: *"who plays the characters in yo gabba gabba"*
- **Gold Answer**: `DJ Lance Rock -- ( Portrayed by Lance Robertson U.S. , voice dubbed by Ortis Deley in the UK )`
- **Source Snippet**: `<Ul> <Li> DJ Lance Rock -- ( Portrayed by Lance Robertson U.S. , voice dubbed by Ortis Deley in the UK )`
- **Source Structure Type**: HTML bullet list with parenthetical role credits (<Ul> <Li>)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=Rock (PROPN); Portrayed (acl); by (agent); no finite matrix verb exists.
- **Why No Fact Produced**: Lines are bulleted HTML cast credits: '<Ul> <Li> DJ Lance Rock -- ( Portrayed by Lance Robertson... )'. Non-sentential dash format lacks matrix predicate.
- **Exact Information Lost**: Actor/voice-actor attribution in non-sentential HTML credit list.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 20: `9dd3961d209a41abac49a36413371d6c`
- **Question**: *"who has participated in the most super bowls"*
- **Gold Answer**: `New England Patriots`
- **Source Snippet**: `<Li> New England Patriots XX , XXXI , XXXVI , XXXVIII , XXXIX , XLII , XLVI , XLIX , LI , LII </Li>`
- **Source Structure Type**: HTML list with team name and Roman numerals (<Li>)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=< (X); Li (npadvmod); Patriots (compound); no verbs in document.
- **Why No Fact Produced**: Document is an HTML list of team names followed by Roman numeral game identifiers: '<Li> New England Patriots XX , XXXI... </Li>'. Zero verbs exist in the document.
- **Exact Information Lost**: Super Bowl participation records in non-sentential HTML list.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 21: `3425eab641a540ff98c7c6337fefd267`
- **Question**: *"who starred in the remake of true grit"*
- **Gold Answer**: `Hailee Steinfeld as Mattie Ross and Jeff Bridges as Deputy U.S. Marshal Reuben J. `` Rooster '' Cogburn , along with Matt Damon , Josh Brolin , and Barry Pepper`
- **Source Snippet**: `This version stars Hailee Steinfeld as Mattie Ross and Jeff Bridges as Deputy U.S. Marshal Reuben J. `` Rooster '' Cogburn , along with Matt Damon , Josh Brolin , and Barry Pepper .`
- **Source Structure Type**: Sentence with complex multi-entity cast conjunction and compound preposition
- **Grammatical Prose?**: Yes
- **Relevant spaCy Dependency Structure**: ROOT=stars (VERB); version (nsubj); Steinfeld (dobj); as (prep); Ross (pobj); along (advmod); with (prep).
- **Why No Fact Produced**: Compound preposition 'along with Matt Damon, Josh Brolin, and Barry Pepper' was truncated to 'manner: along'. The gold answer is a 28-word conjunction of 5 actors and roles.
- **Exact Information Lost**: Subordinate cast members in compound preposition 'along with'.
- **Failure Category**: `QUALIFIER_OR_ARGUMENT_LOSS`
- **Epistemic Classification**: `implementation_defect`
- **Fix Classification**: `SAFE_GENERIC_FIX`
- **Regression Risk**: `LOW`
- **Requires Architectural Change?**: No

### Case 22: `11cabb55e53047449cd8304480660c0b`
- **Question**: *"how many students attend university of texas at austin"*
- **Gold Answer**: `51,331`
- **Source Snippet**: `<Td> 51,331 ( Fall 2016 )`
- **Source Structure Type**: HTML table cell (<Td> tag in university infobox)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=< (X); Td (npadvmod); 51,331 (nummod); no predicate exists.
- **Why No Fact Produced**: Snippet is an isolated table cell '<Td> 51,331 ( Fall 2016 )' from an infobox table. Contains no finite verb.
- **Exact Information Lost**: Student enrollment number in HTML infobox table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes

### Case 23: `78b30a922137434fbb2170da0e0d79ae`
- **Question**: *"when does grey 's anatomy come back on in march"*
- **Gold Answer**: `March 1 , 2018`
- **Source Snippet**: `<Td> March 1 , 2018 ( 2018 - 03 - 01 )`
- **Source Structure Type**: HTML table cell (<Td> tag in episode air-date schedule)
- **Grammatical Prose?**: No
- **Relevant spaCy Dependency Structure**: ROOT=< (X); Td (npadvmod); March (npadvmod); no predicate exists.
- **Why No Fact Produced**: Snippet is an episode schedule table cell '<Td> March 1 , 2018 ( 2018 - 03 - 01 )'. Contains no finite verb.
- **Exact Information Lost**: Broadcast return date in HTML TV schedule table cell.
- **Failure Category**: `NON_SENTENTIAL_STRUCTURE`
- **Epistemic Classification**: `source_format_mismatch`
- **Fix Classification**: `ARCHITECTURAL_CHANGE`
- **Regression Risk**: `HIGH_REGRESSION_RISK`
- **Requires Architectural Change?**: Yes
