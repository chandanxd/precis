from precis.pipeline.svoa import extract_facts


class TestBasicSVOA:
    """Test standard Subject-Verb-Object extraction."""

    def test_simple_active(self):
        facts = extract_facts("The cat chased the mouse.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "cat" in fact.subject.lower()
        assert "chased" in fact.verb.lower()
        assert "mouse" in fact.object.lower()

    def test_simple_passive(self):
        facts = extract_facts("The bill was approved by parliament.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "bill" in fact.subject.lower()
        assert "approved" in fact.verb.lower()
        assert "parliament" in fact.object.lower()

    def test_with_auxiliaries(self):
        facts = extract_facts("The government has announced new policies.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "government" in fact.subject.lower()
        assert "has announced" == fact.verb
        assert "policies" in fact.object.lower()

    def test_past_tense(self):
        facts = extract_facts("Dr. Smith discovered a compound.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "Dr. Smith" in fact.subject or "Smith" in fact.subject
        assert "discovered" in fact.verb.lower()
        assert "compound" in fact.object.lower()

    def test_future_tense(self):
        facts = extract_facts("The committee will review the proposal next week.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "committee" in fact.subject.lower()
        assert "will review" == fact.verb
        assert "proposal" in fact.object.lower()

    def test_intransitive_verb(self):
        facts = extract_facts("The president arrived yesterday.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "president" in fact.subject.lower()
        assert "arrived" in fact.verb.lower()

    def test_phrasal_verb(self):
        facts = extract_facts("The police called off the search.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "police" in fact.subject.lower()
        assert "called off" == fact.verb
        assert "search" in fact.object.lower()


class TestCopularExtraction:
    """Test copular / attributive constructions."""

    def test_basic_copular(self):
        facts = extract_facts("The sky is blue.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "sky" in fact.subject.lower()
        assert "is" == fact.verb
        assert "blue" in fact.object.lower()

    def test_copular_with_article(self):
        facts = extract_facts("Dr. Smith is a scientist.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "Dr. Smith" in fact.subject or "Smith" in fact.subject
        assert "is" == fact.verb
        assert "scientist" in fact.object.lower()

    def test_copular_adjective(self):
        facts = extract_facts("The results were significant.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "results" in fact.subject.lower()
        assert "were" == fact.verb
        assert "significant" in fact.object.lower()

    def test_copular_prepositional(self):
        facts = extract_facts("The book is on the table.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "book" in fact.subject.lower()
        assert "is" == fact.verb
        assert "on the table" in fact.object.lower()

    def test_copular_become(self):
        facts = extract_facts("She became the director.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "She" == fact.subject
        assert "became" == fact.verb
        assert "director" in fact.object.lower()

    def test_copular_seem(self):
        facts = extract_facts("The plan seems feasible.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "plan" in fact.subject.lower()
        assert "seems" == fact.verb
        assert "feasible" in fact.object.lower()

    def test_copular_negated(self):
        facts = extract_facts("The claim is not valid.")
        assert len(facts) >= 1
        fact = facts[0]
        assert fact.negated is True
        assert "claim" in fact.subject.lower()
        assert "is" == fact.verb
        assert "valid" in fact.object.lower()


class TestNegation:
    """Test negation detection."""

    def test_simple_negation(self):
        facts = extract_facts("The court did not approve the motion.")
        assert len(facts) >= 1
        fact = facts[0]
        assert fact.negated is True
        assert "court" in fact.subject.lower()
        assert "did not approve" == fact.verb

    def test_nt_contraction(self):
        facts = extract_facts("The defendant hasn't arrived.")
        assert len(facts) >= 1
        fact = facts[0]
        assert fact.negated is True

    def test_never(self):
        facts = extract_facts("The company never disclosed the information.")
        assert len(facts) >= 1
        fact = facts[0]
        assert fact.negated is True

    def test_no_object(self):
        facts = extract_facts("There is no evidence of fraud.")
        assert len(facts) >= 1
        fact = facts[0]
        # "no" as determiner should trigger negation
        assert fact.negated is True


class TestCoordination:
    """Test coordinated subjects, verbs, and objects."""

    def test_coordinated_subjects(self):
        facts = extract_facts("John and Mary submitted the report.")
        assert len(facts) >= 2
        subjects = [f.subject for f in facts]
        assert any("John" in s for s in subjects)
        assert any("Mary" in s for s in subjects)

    def test_coordinated_verbs(self):
        facts = extract_facts("The team reviewed and approved the document.")
        # Should get facts for both "reviewed" and "approved"
        verbs = [f.verb for f in facts]
        assert any("reviewed" in v for v in verbs)
        assert any("approved" in v for v in verbs)

    def test_coordinated_objects(self):
        facts = extract_facts("The manager signed the contract and the letter.")
        # Should get at least one fact per object
        objects = [f.object for f in facts]
        assert any("contract" in o for o in objects)
        assert any("letter" in o for o in objects)


class TestRelativeClauses:
    """Test relative clause extraction."""

    def test_relative_clause_active(self):
        facts = extract_facts(
            "The scientist who discovered penicillin won a Nobel Prize."
        )
        # Should extract: scientist won Prize (main) AND scientist discovered penicillin (relative)
        assert len(facts) >= 2
        verbs = [f.verb for f in facts]
        assert any("discovered" in v for v in verbs)
        assert any("won" in v for v in verbs)

    def test_relative_clause_passive(self):
        facts = extract_facts(
            "The bill that was rejected by the senate caused controversy."
        )
        # Should extract: bill caused controversy (main) AND senate rejected bill (relative)
        assert len(facts) >= 2

    def test_reduced_relative(self):
        facts = extract_facts("The man arrested yesterday was released today.")
        # Should extract facts from "man arrested yesterday" and "man was released today"
        assert len(facts) >= 2


class testClausalComplements:
    """Test clausal complement extraction (reported speech, mental states)."""

    def test_reported_speech(self):
        facts = extract_facts("She said that he left early.")
        # Should extract: She said [something] AND he left early
        assert len(facts) >= 2
        subjects = [f.subject for f in facts]
        assert any("he" in s.lower() for s in subjects)

    def test_mental_state(self):
        facts = extract_facts("He believes the market will crash.")
        # Should extract: He believes [something] AND market will crash
        assert len(facts) >= 2

    def test_want_xcomp(self):
        facts = extract_facts("The CEO wants to expand operations.")
        # Should extract: CEO wants [something] AND CEO to expand operations
        assert len(facts) >= 2


class TestDitransitive:
    """Test ditransitive verb extraction."""

    def test_give_ditransitive(self):
        facts = extract_facts("John gave Mary a book.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "John" in fact.subject
        assert "gave" in fact.verb
        assert "book" in fact.object.lower()
        assert "recipient" in fact.adjuncts
        assert any("Mary" in r for r in fact.adjuncts["recipient"])

    def test_send_ditransitive(self):
        facts = extract_facts("The company sent the client a proposal.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "company" in fact.subject.lower()
        assert "proposal" in fact.object.lower()
        assert "recipient" in fact.adjuncts


class TestAdjuncts:
    """Test adjunct (time, location, manner) extraction."""

    def test_temporal_adjunct(self):
        facts = extract_facts("The meeting occurred on Friday.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "time" in fact.adjuncts
        assert any("Friday" in a for a in fact.adjuncts["time"])

    def test_location_adjunct(self):
        facts = extract_facts("The conference took place in Bangalore.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "location" in fact.adjuncts
        assert any("Bangalore" in a for a in fact.adjuncts["location"])

    def test_multiple_adjuncts(self):
        facts = extract_facts("The event happened in Delhi on Monday.")
        assert len(facts) >= 1
        fact = facts[0]
        assert "location" in fact.adjuncts or "time" in fact.adjuncts


class TestModality:
    """Test modality detection."""

    def test_asserted(self):
        facts = extract_facts("The report confirms the findings.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"

    def test_attributed(self):
        facts = extract_facts("She claimed that the data was incorrect.")
        # The main clause should be attributed
        main_fact = next(f for f in facts if "claimed" in f.verb)
        assert main_fact.modality == "attributed"
        assert main_fact.attributed_to is not None

    def test_hypothetical(self):
        facts = extract_facts("The plan might fail.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_conditional(self):
        facts = extract_facts("If it rains, the match will be cancelled.")
        # The conditional clause fact should be marked conditional
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1


class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_empty_string(self):
        facts = extract_facts("")
        assert facts == []

    def test_whitespace_only(self):
        facts = extract_facts("   \n\t  ")
        assert facts == []

    def test_single_word(self):
        facts = extract_facts("Hello.")
        assert facts == []

    def test_fragment_no_verb(self):
        facts = extract_facts("The old building.")
        assert facts == []

    def test_question(self):
        facts = extract_facts("Did the committee approve the budget?")
        # Should still extract facts from questions
        assert len(facts) >= 1
        assert "committee" in facts[0].subject.lower()

    def test_complex_sentence(self):
        text = (
            "The European Parliament, which represents the citizens of the EU, "
            "voted on the climate bill yesterday and rejected it."
        )
        facts = extract_facts(text)
        assert len(facts) >= 3  # Main + relative + coordination

    def test_very_long_sentence(self):
        text = (
            "After extensive deliberations that lasted for several days and involved "
            "numerous stakeholders from various member states, the council finally "
            "reached a consensus on the controversial proposal."
        )
        facts = extract_facts(text)
        assert len(facts) >= 1
        assert "council" in facts[0].subject.lower()
        assert "reached" in facts[0].verb.lower()


class TestRealWorldExamples:
    """Test on realistic document-style sentences."""

    def test_legal_document(self):
        text = "The Plaintiff filed a formal legal motion on March 5. The Supreme Court reviewed it."
        facts = extract_facts(text)
        assert len(facts) >= 2
        subjects = [f.subject for f in facts]
        assert any("Plaintiff" in s for s in subjects)
        assert any("Supreme Court" in s or "Court" in s for s in subjects)

    def test_news_article(self):
        text = (
            "Prime Minister Modi met with President Biden in Washington. "
            "They discussed bilateral trade agreements."
        )
        facts = extract_facts(text)
        assert len(facts) >= 2
        subjects = [f.subject for f in facts]
        assert any("Modi" in s for s in subjects)
        assert any("Biden" in s for s in subjects) or any("They" in s for s in subjects)

    def test_scientific_text(self):
        text = (
            "The researchers observed that the treatment group showed significant improvement. "
            "The control group exhibited no change."
        )
        facts = extract_facts(text)
        assert len(facts) >= 3  # Main + ccomp + second sentence
        subjects = [f.subject for f in facts]
        assert any("researchers" in s.lower() for s in subjects)
        assert any("treatment group" in s.lower() for s in subjects)
        assert any("control group" in s.lower() for s in subjects)

    def test_multiple_sentences(self):
        text = (
            "Dr. Smith discovered a compound. He published his findings. "
            "The compound was tested in clinical trials."
        )
        facts = extract_facts(text)
        assert len(facts) >= 3
        # Each sentence should produce at least one fact
        assert len({f.sentence_id for f in facts}) >= 3
