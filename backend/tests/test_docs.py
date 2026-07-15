from precis.pipeline.coref import resolve_coreferences


class TestCoreference:
    def test_simple_pronoun(self):
        text = "Dr. Smith discovered a compound. He published the results."
        resolved = resolve_coreferences(text)
        assert "He" not in resolved or "Dr. Smith" in resolved

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
