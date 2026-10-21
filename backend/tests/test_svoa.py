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

    def test_attributed_complement(self):
        facts = extract_facts("Alice claimed that the results were false.")
        complement_fact = next(f for f in facts if "were" in f.verb)
        assert complement_fact.modality == "attributed"
        assert complement_fact.attributed_to is not None
        assert "Alice" in complement_fact.attributed_to

    def test_reporting_verb_testify(self):
        facts = extract_facts("The witness testified that the driver fled.")
        assert len(facts) >= 2
        testify_fact = next(f for f in facts if "testified" in f.verb)
        assert testify_fact.modality == "attributed"
        assert "witness" in (testify_fact.attributed_to or "").lower()
        fled_fact = next(f for f in facts if "fled" in f.verb)
        assert fled_fact.modality == "attributed"
        assert "witness" in (fled_fact.attributed_to or "").lower()

    def test_hypothetical(self):
        facts = extract_facts("The plan might fail.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_conditional(self):
        facts = extract_facts("If it rains, the match will be cancelled.")
        # The conditional clause fact should be marked conditional
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_future_assertion_will(self):
        facts = extract_facts("The company will release the product.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"

    def test_capability_assertion_can(self):
        facts = extract_facts("The system can process large documents.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"

    def test_obligation_assertion_must(self):
        facts = extract_facts("The system must authenticate users.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"

    def test_hypothetical_might(self):
        facts = extract_facts("The system might fail under heavy load.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_hypothetical_may(self):
        facts = extract_facts("The system may fail under heavy load.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_hypothetical_could(self):
        facts = extract_facts("The system could fail under heavy load.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_explicit_conditional(self):
        facts = extract_facts("The match will proceed if weather permits.")
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_attributed_statement(self):
        facts = extract_facts("The spokesperson announced that the merger completed.")
        assert any(f.modality == "attributed" for f in facts)

    def test_mixed_conditional_and_epistemic_modal(self):
        facts = extract_facts("If the server overheats, the system might restart.")
        restart_facts = [f for f in facts if "restart" in f.verb]
        assert len(restart_facts) >= 1
        assert restart_facts[0].modality == "conditional"

    def test_mixed_attribution_and_epistemic_modal(self):
        facts = extract_facts("Analysts suggest that inflation might decline.")
        decline_facts = [f for f in facts if "decline" in f.verb]
        assert len(decline_facts) >= 1
        assert decline_facts[0].modality == "attributed"
        assert decline_facts[0].attributed_to == "Analysts"

    def test_mixed_future_assertion_with_separate_conditional(self):
        text = "The company will release the product, but if demand falls, prices might drop."
        facts = extract_facts(text)
        release_facts = [f for f in facts if "release" in f.verb]
        assert len(release_facts) >= 1
        assert release_facts[0].modality == "asserted"
        drop_facts = [f for f in facts if "drop" in f.verb]
        assert len(drop_facts) >= 1
        assert drop_facts[0].modality == "conditional"

    def test_mixed_capability_with_separate_conditional(self):
        text = (
            "The system can process documents because it is fast, "
            "but if the network fails, it might retry."
        )
        facts = extract_facts(text)
        process_facts = [f for f in facts if "process" in f.verb]
        assert len(process_facts) >= 1
        assert process_facts[0].modality == "asserted"
        retry_facts = [f for f in facts if "retry" in f.verb]
        assert len(retry_facts) >= 1
        assert retry_facts[0].modality == "conditional"


class TestContextDependentModals:
    """Targeted adversarial and validation tests for 'could' and 'would'.

    Tests the context-dependent behavior of 'could' and 'would', verifying
    that conditional and attributed clauses take precedence, that hypothetical
    uncertainties are properly tagged, and explicitly documenting the lightweight
    heuristic's conservative classification on unconditioned capability/habitual uses.
    """

    def test_could_hypothetical_possibility(self):
        """Uncertainty with 'could' must be classified as hypothetical."""
        facts = extract_facts("The system could fail under heavy load.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_could_adversarial_vulnerability(self):
        """Speculative exploit statements must be classified as hypothetical."""
        facts = extract_facts(
            "An attacker could bypass authentication without valid credentials."
        )
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_could_unconditioned_capability_heuristic_limitation(self):
        """Document heuristic behavior: unconditioned 'could' is treated as hypothetical.

        Without explicit condition markers or tense framing, 'could' is conservatively
        treated as epistemic possibility to prevent speculative claims from entering the
        asserted fact store. (Unambiguous capability should use 'can').
        """
        facts = extract_facts("The system could process 10,000 requests per second.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_would_hypothetical_counterfactual(self):
        """Counterfactual/hypothetical apodosis with 'would' is classified as hypothetical."""
        facts = extract_facts("The model would perform better with more training data.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_would_hypothetical_projection(self):
        """Projected impact with 'would' is classified as hypothetical."""
        facts = extract_facts("Adopting microservices would increase deployment latency.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_would_unconditioned_descriptive_heuristic_limitation(self):
        """Document heuristic behavior: unconditioned 'would' is treated as hypothetical.

        Without overt present or past tense verbs, isolated 'would' is conservatively
        treated as hypothetical/counterfactual rather than asserted ground truth.
        """
        facts = extract_facts("The system would process requests sequentially.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_would_past_framing_heuristic_limitation(self):
        """Document heuristic: past framing without past tense verbs remains hypothetical."""
        facts = extract_facts(
            "The model would process larger batches in the previous implementation."
        )
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_could_with_preceding_conditional_clause(self):
        """Explicit conditional clause takes precedence over 'could' modal."""
        facts = extract_facts("If the service fails, it could restart automatically.")
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_could_with_postposed_conditional_clause(self):
        """Post-posed conditional clause takes precedence over 'could' modal."""
        facts = extract_facts("The service could restart automatically if it fails.")
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_would_with_preceding_conditional_clause(self):
        """Explicit conditional clause takes precedence over 'would' modal."""
        facts = extract_facts(
            "If additional memory were available, the model would process larger batches."
        )
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_would_with_postposed_conditional_clause(self):
        """Post-posed conditional clause takes precedence over 'would' modal."""
        facts = extract_facts(
            "The model would process larger batches if additional memory were available."
        )
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_could_with_unless_condition(self):
        """Condition marker 'unless' takes precedence over 'could' modal."""
        facts = extract_facts(
            "Unless maintenance is scheduled, the service could remain active."
        )
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_would_with_provided_condition(self):
        """Condition marker 'provided' takes precedence over 'would' modal."""
        facts = extract_facts(
            "Provided that resources permit, the system would scale horizontally."
        )
        conditional_facts = [f for f in facts if f.modality == "conditional"]
        assert len(conditional_facts) >= 1

    def test_could_with_attribution(self):
        """Attribution takes precedence over 'could' modal."""
        facts = extract_facts(
            "The engineers stated that the system could handle higher traffic."
        )
        attributed_facts = [f for f in facts if f.modality == "attributed"]
        assert len(attributed_facts) >= 1
        assert any("engineers" in (f.attributed_to or "").lower() for f in attributed_facts)

    def test_would_with_attribution(self):
        """Attribution takes precedence over 'would' modal."""
        facts = extract_facts(
            "The report suggested that the algorithm would converge faster."
        )
        attributed_facts = [f for f in facts if f.modality == "attributed"]
        assert len(attributed_facts) >= 1
        assert any("report" in (f.attributed_to or "").lower() for f in attributed_facts)

    def test_baseline_may_hypothetical(self):
        """Verify baseline 'may' remains hypothetical."""
        facts = extract_facts("The service may become unavailable.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_baseline_might_hypothetical(self):
        """Verify baseline 'might' remains hypothetical."""
        facts = extract_facts("The service might become unavailable.")
        assert len(facts) >= 1
        assert facts[0].modality == "hypothetical"

    def test_baseline_can_capability(self):
        """Verify baseline 'can' remains asserted capability."""
        facts = extract_facts("The service can process requests asynchronously.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"

    def test_baseline_must_obligation(self):
        """Verify baseline 'must' remains asserted obligation."""
        facts = extract_facts("The service must authenticate every request.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"

    def test_baseline_will_future(self):
        """Verify baseline 'will' remains asserted future assertion."""
        facts = extract_facts("The service will restart automatically.")
        assert len(facts) >= 1
        assert facts[0].modality == "asserted"


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
        text = (
            "The Plaintiff filed a formal legal motion on March 5. "
            "The Supreme Court reviewed it."
        )
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


class TestAdversarialSVOA:
    """Adversarial SVOA tests covering attribution and boundary edge cases."""

    def test_reporting_verb_ccomp(self):
        text = "Dr. Vance stated that the reactor will operate tomorrow."
        facts = extract_facts(text)
        assert len(facts) >= 2
        comp_facts = [f for f in facts if "reactor" in f.subject.lower()]
        assert len(comp_facts) >= 1
        assert comp_facts[0].modality == "attributed"
        assert comp_facts[0].attributed_to == "Dr. Vance"

    def test_non_reporting_matrix_verb(self):
        text = "The engineer wanted the motor to run."
        facts = extract_facts(text)
        assert len(facts) >= 1
        for f in facts:
            assert f.modality == "asserted"
            assert f.attributed_to is None

    def test_passive_reporting_construction(self):
        text = "It was reported that the merger was finalized."
        facts = extract_facts(text)
        assert len(facts) >= 1
        for f in facts:
            assert f.modality == "attributed"

    def test_ordinary_asserted_fact(self):
        text = "The catalyst accelerates the chemical reaction."
        facts = extract_facts(text)
        assert len(facts) == 1
        assert facts[0].modality == "asserted"
        assert facts[0].attributed_to is None
        assert facts[0].negated is False


class TestEnhancedSVOAExtraction:
    def test_simple_copular(self):
        facts = extract_facts("Alice is a scientist.")
        assert len(facts) == 1
        fact = facts[0]
        assert fact.subject == "Alice"
        assert fact.verb == "is"
        assert fact.object == "a scientist"
        assert fact.modality == "asserted"
        assert not fact.negated

    def test_past_copular(self):
        facts = extract_facts("Alice was the director.")
        assert len(facts) == 1
        fact = facts[0]
        assert fact.subject == "Alice"
        assert fact.verb == "was"
        assert fact.object == "the director"
        assert fact.modality == "asserted"
        assert not fact.negated

    def test_copular_with_descriptive_complement(self):
        facts = extract_facts("The city is the capital of France.")
        assert len(facts) == 1
        fact = facts[0]
        assert fact.subject == "The city"
        assert fact.verb == "is"
        assert fact.object == "the capital of France"
        assert fact.modality == "asserted"

    def test_appositive(self):
        text = "Patrick Brown, leader of the Ontario PC Party, announced the decision."
        facts = extract_facts(text)
        appos_fact = next(
            (f for f in facts if f.subject == "Patrick Brown" and f.verb == "is"),
            None,
        )
        assert appos_fact is not None
        assert "leader of the Ontario PC Party" in appos_fact.object
        assert appos_fact.modality == "asserted"

        matrix_fact = next(
            (f for f in facts if f.verb == "announced"),
            None,
        )
        assert matrix_fact is not None
        assert matrix_fact.subject == "Patrick Brown"
        assert matrix_fact.object == "the decision"

    def test_appositive_with_determiner(self):
        text = "John Smith, the founder of the company, resigned."
        facts = extract_facts(text)
        appos_fact = next(
            (f for f in facts if f.subject == "John Smith" and f.verb == "is"),
            None,
        )
        assert appos_fact is not None
        assert "founder of the company" in appos_fact.object
        assert appos_fact.modality == "asserted"

        matrix_fact = next(
            (f for f in facts if f.verb == "resigned"),
            None,
        )
        assert matrix_fact is not None
        assert matrix_fact.subject == "John Smith"

    def test_list_item_role(self):
        facts = extract_facts("Jason Marsden as Max Goof")
        assert len(facts) == 1
        fact = facts[0]
        assert fact.subject == "Jason Marsden"
        assert fact.verb == "plays"
        assert fact.object == "Max Goof"
        assert fact.modality == "asserted"

    def test_html_like_list_item(self):
        facts = extract_facts("<Li> Jason Marsden as Max Goof </Li>")
        assert len(facts) == 1
        fact = facts[0]
        assert fact.subject == "Jason Marsden"
        assert fact.verb == "plays"
        assert fact.object == "Max Goof"
        assert fact.modality == "asserted"

    def test_html_like_paragraph(self):
        facts = extract_facts("<P> Patrick Brown is the leader of the Ontario PC Party. </P>")
        assert len(facts) >= 1
        fact = facts[0]
        assert fact.subject == "Patrick Brown"
        assert fact.verb == "is"
        assert "leader of the Ontario PC Party" in fact.object
        assert fact.modality == "asserted"

    def test_negative_ambiguous_as_constructions(self):
        for sent, expected_verb in [
            ("He worked as a clerk.", "worked"),
            ("She described him as talented.", "described"),
            ("He ran as fast as possible.", "ran"),
        ]:
            facts = extract_facts(sent)
            assert len(facts) >= 1
            assert not any(f.verb in {"plays", "serves as"} for f in facts)
            assert any(f.verb == expected_verb for f in facts)

        for frag in [
            "Such as apples and oranges.",
            "As soon as possible.",
            "As of 2020.",
        ]:
            facts = extract_facts(frag)
            assert not any(f.verb in {"plays", "serves as"} for f in facts)

    def test_existing_svoa_behavior_preserved(self):
        facts = extract_facts("The company acquired the startup in 2021.")
        assert len(facts) == 1
        assert facts[0].subject == "The company"
        assert facts[0].verb == "acquired"
        assert facts[0].object == "the startup"
        assert "in 2021" in facts[0].adjuncts.get("time", [])


class TestPassiveCoordination:
    """Test passive coordination agent resolution and preservation."""

    def test_shared_passive_agent_coordination(self):
        text = "The theme was written and composed by Argentine composer Lalo Schifrin."
        facts = extract_facts(text)
        assert len(facts) >= 2
        objs = [f.object for f in facts]
        assert any("Lalo Schifrin" in o for o in objs)
        written_facts = [f for f in facts if "written" in f.verb]
        composed_facts = [f for f in facts if "composed" in f.verb]
        assert len(written_facts) >= 1
        assert "Lalo Schifrin" in written_facts[0].object
        assert len(composed_facts) >= 1
        assert "Lalo Schifrin" in composed_facts[0].object

    def test_distinct_passive_agents_coordination(self):
        text = "The film was directed by Ridley Scott and produced by Jerry Bruckheimer."
        facts = extract_facts(text)
        assert len(facts) >= 2
        directed = [f for f in facts if "directed" in f.verb]
        produced = [f for f in facts if "produced" in f.verb]
        assert len(directed) >= 1
        assert "Ridley Scott" in directed[0].object
        assert len(produced) >= 1
        assert "Jerry Bruckheimer" in produced[0].object

    def test_shared_passive_agent_in_relative_clause(self):
        text = "The theme which was written and composed by Lalo Schifrin won an award."
        facts = extract_facts(text)
        assert any("Lalo Schifrin" in f.subject or "Lalo Schifrin" in f.object for f in facts)

    def test_passive_coordination_negative_active(self):
        text = "The team reviewed and approved the document."
        facts = extract_facts(text)
        # Should NOT treat "the document" as an agent of reviewed
        reviewed = [f for f in facts if "reviewed" in f.verb]
        assert len(reviewed) >= 1
        assert reviewed[0].object == ""

    def test_passive_coordination_negative_unrelated_prep(self):
        text = "John cooked and ate with Mary."
        facts = extract_facts(text)
        assert len(facts) >= 1
        for f in facts:
            assert "Mary" not in f.object


class TestStage2ExtractionEnhancements:
    """Regression and adversarial tests for Stage 2 SVOA extraction fixes."""

    def test_introductory_pp_subject_misattachment_positive(self):
        text = (
            "On January 17 , 1899 , under orders from President William McKinley , "
            "Commander Edward D. Taussig of USS Bennington landed on Wake and formally "
            "took possession of the island for the United States ."
        )
        facts = extract_facts(text)
        assert len(facts) >= 2
        landed_facts = [f for f in facts if "landed" in f.verb]
        assert len(landed_facts) >= 1
        assert "Taussig" in landed_facts[0].subject
        assert "On January 17 , 1899" in landed_facts[0].adjuncts.get("time", [])

        took_facts = [f for f in facts if "took" in f.verb]
        assert len(took_facts) >= 1
        assert "Taussig" in took_facts[0].subject
        assert "possession" in took_facts[0].object

    def test_introductory_pp_subject_misattachment_negative_coordination(self):
        # When explicit 'and' is present inside the PP, Taussig must NOT be treated as subject
        text = "Under orders from President McKinley and General Taussig , the troops retreated ."
        facts = extract_facts(text)
        assert len(facts) >= 1
        retreated = [f for f in facts if "retreated" in f.verb]
        assert len(retreated) >= 1
        assert "the troops" in retreated[0].subject
        assert "Taussig" not in retreated[0].subject

    def test_introductory_pp_subject_misattachment_negative_overt_subject(self):
        # When an overt subject already exists, fallback must not interfere
        text = "Under orders from President McKinley , the general ordered a retreat ."
        facts = extract_facts(text)
        assert len(facts) >= 1
        assert facts[0].subject == "the general"

    def test_coordinated_clausal_complements_positive(self):
        text = "The manager met the client and claimed that the contract was signed."
        facts = extract_facts(text)
        signed_facts = [f for f in facts if "signed" in f.verb]
        assert len(signed_facts) >= 1
        assert "the contract" in signed_facts[0].subject
        assert signed_facts[0].modality == "attributed"
        assert signed_facts[0].attributed_to == "The manager"

    def test_coordinated_clausal_complements_xcomp(self):
        text = "They returned home and agreed to finish the project."
        facts = extract_facts(text)
        project_facts = [f for f in facts if "finish" in f.verb or "project" in f.object]
        assert len(project_facts) >= 1

    def test_coordinated_clausal_complements_negative_no_complement(self):
        text = "The manager met the client and signed the contract."
        facts = extract_facts(text)
        # No extra embedded proposition should be hallucinated
        assert len(facts) == 2
        verbs = {f.verb for f in facts}
        assert verbs == {"met", "signed"}

    def test_multiple_direct_objects_positive(self):
        text = (
            "Most dairy or beef farms traditionally had at least one , "
            "if not several , bulls for purposes of herd maintenance ."
        )
        facts = extract_facts(text)
        assert len(facts) >= 2
        objs = [f.object for f in facts]
        assert any("bulls for purposes of herd maintenance" in o for o in objs)

    def test_multiple_direct_objects_negative_ditransitive(self):
        text = "The company gave Alice a promotion."
        facts = extract_facts(text)
        # Should not duplicate a second proposition for the recipient
        assert len(facts) == 1
        assert facts[0].subject == "The company"
        assert facts[0].object == "a promotion"
        assert facts[0].adjuncts.get("recipient") == ["Alice"]

    def test_restrictive_appositive_preserved_in_subject(self):
        text = "The name Comanche is from the Ute language."
        facts = extract_facts(text)
        assert len(facts) >= 1
        assert "Comanche" in facts[0].subject

    def test_non_restrictive_appositive_trimmed_from_subject(self):
        text = "Patrick Brown, leader of the Ontario PC Party, announced the decision."
        facts = extract_facts(text)
        announced = [f for f in facts if f.verb == "announced"][0]
        assert announced.subject == "Patrick Brown"
