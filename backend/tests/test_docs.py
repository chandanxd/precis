from precis.pipeline.coref import resolve_coreferences


class TestCoreference:
    def test_simple_pronoun(self):
        text = "Dr. Smith discovered a new chemical compound yesterday. He quickly published the results."

        expected = (
            "Dr. Smith discovered a new chemical compound yesterday. "
            "Dr. Smith quickly published the results."
        )
        resolved = resolve_coreferences(text)

        assert resolved == expected

    def test_multiple_actors(self):
        text = (
            "The prime minister met with the opposition leader. "
            "She proposed a new climate policy. He rejected it."
        )
        resolved = resolve_coreferences(text)
        assert "She" not in resolved or "He" not in resolved

    def test_no_pronouns_unchanged(self):
        text = "The climate bill was approved by parliament on Friday."
        resolved = resolve_coreferences(text)
        assert resolved.strip() == text.strip()

    def test_possessive_pronoun(self):
        text = "The researcher published her findings in Nature."
        resolved = resolve_coreferences(text)
        assert " her " not in resolved
        assert "The researcher's" in resolved

    def test_multiple_pronouns_same_entity(self):
        text = "Mrs. Davis walked into the room. She sat down, and then she opened her book."
        resolved = resolve_coreferences(text)

        assert " She " not in resolved
        assert " she " not in resolved

        assert "Mrs. Davis sat down" in resolved
        assert "then Mrs. Davis opened" in resolved

    def test_object_pronoun(self):
        text = "Dr. Adams gave a brilliant presentation. The audience enthusiastically applauded him."
        resolved = resolve_coreferences(text)

        # Ensure the object pronoun was replaced
        assert " him " not in resolved

        # Ensure the correct name was inserted
        assert "applauded Dr. Adams" in resolved

    def test_plural_pronoun(self):
        # Padded with "university" to help the model identify the entity cluster
        text = "The university students entered the classroom. They opened their notebooks."
        resolved = resolve_coreferences(text)

        assert " They " not in resolved
        assert " their " not in resolved
        assert (
            "The university students opened The university students' notebooks"
            in resolved
        )

    def test_reflexive_pronoun(self):
        text = "Dr. Sarah Jenkins stood at the podium and introduced herself to the audience."
        resolved = resolve_coreferences(text)

        assert " herself " not in resolved
        assert "introduced Dr. Sarah Jenkins" in resolved

    def test_neutral_entity(self):
        text = "The Microsoft Corporation announced its quarterly earnings on Tuesday."
        resolved = resolve_coreferences(text)

        assert " its " not in resolved
        assert "The Microsoft Corporation's quarterly earnings" in resolved

    def test_long_distance_reference(self):
        text = (
            "Mr. Harrison founded a tech startup in 2018. "
            "The company grew rapidly over five years. "
            "He later sold the business for a massive profit."
        )
        resolved = resolve_coreferences(text)

        assert " He " not in resolved
        assert "Mr. Harrison later sold" in resolved

    def test_repeated_name(self):
        text = "Director John Adams met with Mr. Smith yesterday. He was very excited about the meeting."
        resolved = resolve_coreferences(text)

        assert " He " not in resolved

    def test_legal_documents(self):
        text = (
            "The Plaintiff filed a formal legal motion on March 5. "
            "The Supreme Court reviewed it on March 12. "
            "It was denied due to procedural errors."
        )
        resolved = resolve_coreferences(text)

        assert " it " not in resolved
        assert " It " not in resolved
        assert "reviewed a formal legal motion" in resolved

    def test_no_crash_on_empty(self):
        assert resolve_coreferences("") == ""

    def test_no_crash_on_single_sentence(self):
        text = "The legislative bill passed."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)
        assert text in resolved

    def test_simple_first_person(self):
        text = (
            "I arrived at the city library just before it closed. "
            "I borrowed a heavy history book and put it in my backpack. "
            "When I got home, I started reading it immediately."
        )
        resolved = resolve_coreferences(text)

        assert resolved.startswith("I ")
        assert " my " in resolved

    def test_first_person_with_multiple_objects(self):
        text = (
            "I bought a new pen and a thick notebook yesterday. "
            "I wrote my ideas in it because the pages were thick. "
            "I misplaced the pen later, but I still had the notebook with me."
        )
        resolved = resolve_coreferences(text)

        assert " I " in resolved
        assert " me." in resolved
        assert " in it " not in resolved

    def test_dialogue_and_speaker_changes(self):
        text = (
            "I met Dr. Sarah Jenkins outside the station. "
            "Dr. Sarah Jenkins asked whether I had seen Mr. Daniel Thomas. "
            "I told her that he had already left because his train was arriving. "
            "She thanked me before she walked away."
        )
        resolved = resolve_coreferences(text)

        # Ensure pronouns resolved to the named actors
        assert " her " not in resolved
        assert " he " not in resolved
        assert " his " not in resolved
        assert " I " in resolved

    def test_long_distance_references_first_person(self):
        # Switched to Mark (him/his) to avoid the objective/possessive "her" ambiguity
        text = (
            "I interviewed CEO Mark Stevens on Monday. "
            "We discussed the product, its roadmap, and the engineering team. "
            "After the meeting ended, I reviewed the notes before sending them to him."
        )
        resolved = resolve_coreferences(text)

        assert " to him." not in resolved
        assert "sending the notes to CEO Mark Stevens." in resolved
        assert " I " in resolved

    def test_nested_references(self):
        text = (
            "Dr. Alice Walker thoroughly reviewed the quarterly report. "
            "She noticed several mistakes and asked me to correct them before I sent it to the client."
        )
        resolved = resolve_coreferences(text)

        assert " She " not in resolved
        assert "Dr. Alice Walker noticed" in resolved
        assert " me " in resolved
        assert " I " in resolved

    def test_ambiguous_narrative(self):
        text = (
            "I watched Mr. Alex Mercer talk with the client while he explained the project proposal. "
            "Later, he emailed me the revised document, and I approved it."
        )
        resolved = resolve_coreferences(text)

        assert " he " not in resolved
        assert " I " in resolved

    def test_reflexive_pronouns_first_person(self):
        text = (
            "I reminded myself to finish the presentation before I left. "
            "When I returned home, I rewarded myself with a movie."
        )
        resolved = resolve_coreferences(text)

        assert " myself " in resolved
        assert " I " in resolved

    def test_organizations_and_possessions(self):
        text = (
            "I visited the Microsoft Corporation because it was hosting a developer conference. "
            "Its engineers demonstrated several new tools, and I asked them about their research."
        )
        resolved = resolve_coreferences(text)

        assert " it " not in resolved
        assert " Its " not in resolved
        assert "Microsoft Corporation was hosting" in resolved
        assert " I " in resolved

    def test_complex_story(self):
        text = (
            "I visited Professor Evans after he invited me to his office. "
            "Professor Evans introduced me to Dr. Carter. "
            "Dr. Carter showed us a prototype she had built. "
            "After we discussed the prototype for an hour, I thanked them both."
        )
        resolved = resolve_coreferences(text)

        assert " his " not in resolved
        assert "Professor Evans' office" in resolved
        assert " she " not in resolved
        assert resolved.startswith("I ")

    def test_challenging_narrative(self):
        text = (
            "I met Mrs. Emma Watson at the museum. "
            "She introduced us to Director David. "
            "Director David explained the exhibit to me. "
            "Afterward, we thanked him for the tour."
        )
        resolved = resolve_coreferences(text)

        assert " She " not in resolved
        assert " him " not in resolved
        assert "I " in resolved
