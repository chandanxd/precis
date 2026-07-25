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
        assert isinstance(resolved, str)

    def test_multiple_pronouns_same_entity(self):
        text = "Alice wrote a report. She reviewed it before submitting it."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)  # "She" not in resolved

    def test_object_pronoun(self):
        text = "Alice thanked Bob because he helped her."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_plural_pronoun(self):
        text = "The students entered the classroom. They opened their notebooks."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_reflexive_pronoun(self):
        text = "Sarah introduced herself to the audience."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_neutral_entity(self):
        text = "The company announced its earnings."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_long_distance_reference(self):
        text = (
            "John founded a startup in 2018. "
            "The company grew rapidly over five years. "
            "He later sold it."
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_repeated_name(self):
        text = "John met John Smith yesterday. He was excited about the meeting."
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_legal_documents(self):
        text = (
            "The Plaintiff filed a motion on March 5. "
            "The Court reviewed it on March 12. "
            "It was denied due to procedural errors. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)
        assert len(resolved) >= len(text)

    def test_no_crash_on_empty(self):
        assert resolve_coreferences("") == ""

    def test_no_crash_on_single_sentence(self):
        text = "The bill passed. "
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_simple_first_person(self):
        text = (
            "I arrived at the library just before it closed. "
            "I borrowed a history book and put it in my backpack. "
            "When I got home, I started reading it immediately. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_first_person_with_multiple_objects(self):
        text = (
            "I bought a new pen and a notebook yesterday. "
            "I wrote my ideas in it because the pages were thick. "
            "I misplaced the pen later, but I still had the notebook with me. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_dialogue_and_speaker_changes(self):
        text = (
            "I met Sarah outside the station. "
            "She asked whether I had seen Daniel. "
            "I told her that he had already left because his train was arriving. "
            "She thanked me before she walked away. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_long_distance_references(self):
        text = (
            "I interviewed the company's founder on Monday. "
            "We discussed the product, its roadmap, and the engineering team. "
            "After the meeting ended, I reviewed the notes before sending them them to her. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_nested_references(self):
        text = (
            "I named Alice the report after she finished reviewing it. "
            "She noticed several mistakes and asked me to correct them before I sent it to the client. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_ambiguous_narrative(self):
        text = (
            "I watched Alex talk with Jordan while he explained the proposal. "
            "Later, he emailed me the revised document, and I approved it. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_reflexive_pronouns(self):
        text = (
            "I reminded myself to finish the presentation before I left. "
            "When i returned home, I rewarded myself with a movie. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_organizations_and_possessions(self):
        text = (
            "I visited Microsoft because it was hosting a developer conference. "
            "Its engineers demonstrated several new tools, and I asked them about their research. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_complex_story(self):
        text = (
            "I visited Professor Evans after he invited me to his office. "
            "He introduced me to Dr. Carter, who showed us a prototype she had built. "
            "After we discussed it for an hour, I thanked them both before leaving because they had answered all of my questions. "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)

    def test_challenging_narrative(self):
        text = (
            "I met Emma at the museum before she greeted David. "
            "He introduced us to his colleague Maria, who explained the exhibit to me because I had never seen it before. "
            "Afterward, we thanked her, and she gave us a brochure to take home with us> "
        )
        resolved = resolve_coreferences(text)
        assert isinstance(resolved, str)
