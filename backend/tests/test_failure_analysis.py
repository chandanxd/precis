"""
Unit tests for the Précis benchmark failure analysis diagnostic tool.
"""

from precis.graph.schema import Fact
from scripts.analyze_benchmark_failures import (
    CLASS_CORRECT,
    CLASS_EXTRACTION_FAILURE,
    CLASS_GENERATION_FAILURE,
    CLASS_PACKING_FAILURE,
    CLASS_RETRIEVAL_FAILURE,
    CLASS_UNCERTAIN,
    categorize_answer_length,
    categorize_question_type,
    classify_failure,
    contains_answer,
    fact_contains_answer,
    is_answer_correct,
)


def _make_fact(subject: str, verb: str = "is", obj: str = "", modality: str = "asserted") -> Fact:
    return Fact(
        subject=subject,
        verb=verb,
        object=obj,
        modality=modality,
    )


class TestAnswerNormalizationAndMatching:
    def test_answer_normalization_exact_and_case(self) -> None:
        assert contains_answer("Dr. Alexander Fleming", "Alexander Fleming")
        assert contains_answer("dr alexander fleming", "Dr. Alexander Fleming")
        assert contains_answer("The 23 episodes", "23")

    def test_word_boundary_enforcement(self) -> None:
        assert contains_answer("season had 23 episodes", "23")
        assert not contains_answer("season had 123 episodes", "23")
        assert contains_answer("the red house", "red")
        assert not contains_answer("ordered house", "red")

    def test_empty_and_whitespace_inputs(self) -> None:
        assert not contains_answer("", "Neil Armstrong")
        assert not contains_answer("Neil Armstrong", "")
        assert not contains_answer("   ", "   ")

    def test_fact_contains_answer(self) -> None:
        fact1 = _make_fact("Jason Marsden", "voiced", "Max Goof")
        assert fact_contains_answer(fact1, "Jason Marsden")
        assert fact_contains_answer(fact1, "Max Goof")
        assert not fact_contains_answer(fact1, "Donald Duck")

        # Test alternative answers
        assert fact_contains_answer(fact1, "wrong", ["Max Goof", "other"])


class TestFailureClassification:
    def test_correct_answer_exact_match(self) -> None:
        res = classify_failure(
            gold_answer="Alan Turing",
            precis_predicted="Alan Turing",
            precis_exact_match=True,
            naive_predicted="Alan Turing",
            naive_exact_match=True,
            source_text="Alan Turing introduced the concept in 1936.",
            extracted_facts=[_make_fact("Alan Turing", "introduced", "concept")],
            retrieved_facts=[_make_fact("Alan Turing", "introduced", "concept")],
            packed_facts=[_make_fact("Alan Turing", "introduced", "concept")],
        )
        assert res.primary_failure_class == CLASS_CORRECT
        assert res.confidence == "high"
        assert res.precis_correct is True

    def test_correct_answer_substring_containment(self) -> None:
        res = classify_failure(
            gold_answer="23",
            precis_predicted="Season 4 had 23 episodes.",
            precis_exact_match=False,
            naive_predicted="23 episodes",
            naive_exact_match=False,
            source_text="The season contained 23 episodes.",
            extracted_facts=[_make_fact("season", "contained", "23 episodes")],
            retrieved_facts=[_make_fact("season", "contained", "23 episodes")],
            packed_facts=[_make_fact("season", "contained", "23 episodes")],
        )
        assert res.primary_failure_class == CLASS_CORRECT
        assert res.precis_correct is True

    def test_extraction_failure(self) -> None:
        # Source contains answer, but SVOA representation dropped it
        source = "<Li> Jason Marsden as Max Goof </Li>"
        res = classify_failure(
            gold_answer="Jason Marsden",
            precis_predicted="No relevant facts retrieved.",
            precis_exact_match=False,
            naive_predicted="Jason Marsden as Max Goof",
            naive_exact_match=True,
            source_text=source,
            extracted_facts=[_make_fact("The movie", "released in", "1995")],
            retrieved_facts=[],
            packed_facts=[],
        )
        assert res.primary_failure_class == CLASS_EXTRACTION_FAILURE
        assert res.confidence == "high"
        assert "EXTRACTION" in res.failure_stages
        assert res.source_has_answer is True
        assert res.svoa_has_answer is False

    def test_retrieval_failure(self) -> None:
        # SVOA extracted the fact, but query similarity did not retrieve it
        source = "Neil Armstrong walked on the Moon. Buzz Aldrin followed him."
        bearing_fact = _make_fact("Neil Armstrong", "walked on", "the Moon")
        other_fact = _make_fact("Buzz Aldrin", "followed", "him")
        res = classify_failure(
            gold_answer="Neil Armstrong",
            precis_predicted="Buzz Aldrin",
            precis_exact_match=False,
            naive_predicted="Neil Armstrong",
            naive_exact_match=True,
            source_text=source,
            extracted_facts=[bearing_fact, other_fact],
            retrieved_facts=[other_fact],
            packed_facts=[other_fact],
        )
        assert res.primary_failure_class == CLASS_RETRIEVAL_FAILURE
        assert res.confidence == "high"
        assert "RETRIEVAL" in res.failure_stages
        assert res.svoa_has_answer is True
        assert res.retrieval_has_answer is False

    def test_packing_failure_due_to_modality(self) -> None:
        # Fact retrieved but filtered by modality
        source = "The system might deploy the update next week."
        hyp_fact = _make_fact(
            "system", "might deploy", "update next week", modality="hypothetical"
        )
        res = classify_failure(
            gold_answer="next week",
            precis_predicted="Unknown",
            precis_exact_match=False,
            naive_predicted="next week",
            naive_exact_match=True,
            source_text=source,
            extracted_facts=[hyp_fact],
            retrieved_facts=[hyp_fact],
            packed_facts=[],  # Filtered by modality in precis_full
        )
        assert res.primary_failure_class == CLASS_PACKING_FAILURE
        assert res.confidence == "high"
        assert "PACKING" in res.failure_stages
        assert res.evidence["filtered_by_modality_count"] == 1

    def test_generation_failure(self) -> None:
        # Packed context contains fact, but LLM hallucinates or produces wrong answer
        source = "The fourth season of Chicago Fire contained 23 episodes."
        bearing_fact = _make_fact("season", "contained", "23 episodes")
        res = classify_failure(
            gold_answer="23",
            precis_predicted="The season had 16 episodes.",
            precis_exact_match=False,
            naive_predicted="23",
            naive_exact_match=True,
            source_text=source,
            extracted_facts=[bearing_fact],
            retrieved_facts=[bearing_fact],
            packed_facts=[bearing_fact],
        )
        assert res.primary_failure_class == CLASS_GENERATION_FAILURE
        assert res.confidence == "high"
        assert "GENERATION" in res.failure_stages
        assert res.packing_has_answer is True
        assert res.precis_correct is False

    def test_uncertain_classification_when_not_in_source(self) -> None:
        # Source text does not even contain the answer
        source = "The concert was held in London."
        res = classify_failure(
            gold_answer="Paris",
            precis_predicted="London",
            precis_exact_match=False,
            naive_predicted="London",
            naive_exact_match=False,
            source_text=source,
            extracted_facts=[_make_fact("concert", "held in", "London")],
            retrieved_facts=[_make_fact("concert", "held in", "London")],
            packed_facts=[_make_fact("concert", "held in", "London")],
        )
        assert res.primary_failure_class == CLASS_UNCERTAIN
        assert res.source_has_answer is False

    def test_uncertain_classification_on_empty_gold(self) -> None:
        res = classify_failure(
            gold_answer="",
            precis_predicted="something",
            precis_exact_match=False,
            naive_predicted="something",
            naive_exact_match=False,
            source_text="source text",
            extracted_facts=[],
            retrieved_facts=[],
            packed_facts=[],
        )
        assert res.primary_failure_class == CLASS_UNCERTAIN
        assert res.confidence == "low"

    def test_missing_optional_evidence(self) -> None:
        res = classify_failure(
            gold_answer="something",
            precis_predicted="something else",
            precis_exact_match=False,
            naive_predicted="something else",
            naive_exact_match=False,
            source_text=None,
            extracted_facts=[],
            retrieved_facts=[],
            packed_facts=[],
        )
        assert res.primary_failure_class == CLASS_UNCERTAIN
        assert res.confidence == "low"
        assert "not provided" in res.evidence["reason"]

    def test_multiple_candidate_failure_stages(self) -> None:
        # Two facts extracted, one retrieved, none packed
        source = "Fact A has answer 10. Fact B has answer 10."
        fact_a = _make_fact("A", "has", "10")
        fact_b = _make_fact("B", "has", "10")
        res = classify_failure(
            gold_answer="10",
            precis_predicted="unknown",
            precis_exact_match=False,
            naive_predicted="10",
            naive_exact_match=True,
            source_text=source,
            extracted_facts=[fact_a, fact_b],
            retrieved_facts=[fact_a],
            packed_facts=[],  # dropped in packing
        )
        assert res.primary_failure_class == CLASS_PACKING_FAILURE
        assert "PACKING" in res.failure_stages
        assert "PARTIAL_RETRIEVAL" in res.failure_stages


class TestCategorizations:
    def test_question_type_categorization(self) -> None:
        assert categorize_question_type("Who was the first president?") == "WHO"
        assert categorize_question_type("What is non controlling interest?") == "WHAT"
        assert categorize_question_type("When was penicillin discovered?") == "WHEN"
        assert categorize_question_type("Where did the last name come from?") == "WHERE"
        assert categorize_question_type("Why do leaves change color?") == "WHY"
        assert categorize_question_type("How many episodes in season 4?") == "HOW"
        assert categorize_question_type("Which team won the championship?") == "WHICH"
        assert categorize_question_type("Converting stereo to mono is called?") == "OTHER"

    def test_answer_length_categorization(self) -> None:
        assert categorize_answer_length("23") == "SHORT (1-2 words)"
        assert categorize_answer_length("Neil Armstrong") == "SHORT (1-2 words)"
        assert categorize_answer_length("James Watson Francis Crick") == "MEDIUM (3-5 words)"
        assert categorize_answer_length("the portion of a subsidiary corporation stock") == (
            "LONG (>5 words)"
        )

    def test_is_answer_correct(self) -> None:
        assert is_answer_correct("Neil Armstrong", "Neil Armstrong", exact_match=True)
        assert is_answer_correct("American astronaut Neil Armstrong", "Neil Armstrong")
        assert not is_answer_correct("Buzz Aldrin", "Neil Armstrong")
        assert is_answer_correct("Wrong but Max Goof", "Jason", ["Max Goof"])
