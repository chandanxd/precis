import uuid

import pytest
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.packer import (
    PackResult,
    compute_pack_score,
    estimate_fact_tokens,
    filter_by_modality,
    pack_context,
    render_context,
)
from precis.pipeline.sdh import score_facts


@pytest.fixture
def mem_store():
    col_name = f"test_pack_{uuid.uuid4().hex[:12]}"
    store = FactStore(in_memory=True, collection_name=col_name)
    yield store
    store._client.delete_collection(col_name)


class TestTokenEstimation:
    def test_basic_token_estimation(self):
        fact = Fact(subject="Einstein", verb="developed", object="relativity")
        tokens = estimate_fact_tokens(fact)

        assert tokens >= 3
        assert isinstance(tokens, int)

    def test_token_growth_with_adjuncts_and_negation(self):
        atomic = Fact(
            subject="Government",
            verb="passed",
            object="bill",
        )
        rich = Fact(
            subject="Government",
            verb="passed",
            object="bill",
            negated=True,
            adjuncts={
                "time": ["yesterday"],
                "loc": ["parliament"],
            },
            modality="attributed",
            attributed_to="Reuters",
        )

        assert estimate_fact_tokens(rich) > estimate_fact_tokens(atomic)

    def test_token_estimation_matches_rendered_structure(self):
        fact = Fact(
            subject="Officials",
            verb="confirmed",
            object="outbreak",
            negated=True,
            adjuncts={"time": ["yesterday"]},
            modality="attributed",
            attributed_to="WHO",
        )

        rendered = render_context([fact])

        assert estimate_fact_tokens(fact) >= len(rendered.split())


class TestPackScore:
    def test_pack_score_formula(self):
        fact = Fact(
            subject="A",
            verb="did",
            object="B",
            sdh_score=0.80,
        )
        sim = 0.50

        ps = compute_pack_score(fact, sim)

        assert abs(ps - 0.40) < 1e-4

    def test_pack_score_bounds(self):
        fact = Fact(
            subject="A",
            verb="did",
            object="B",
            sdh_score=1.5,
        )
        ps = compute_pack_score(fact, 1.2)

        assert 0.0 <= ps <= 1.0

    def test_pack_score_clamps_negative_values(self):
        fact = Fact(
            subject="A",
            verb="did",
            object="B",
            sdh_score=-0.5,
        )

        ps = compute_pack_score(fact, -0.5)

        assert ps == 0.0

    def test_pack_score_zero_when_sdh_is_zero(self):
        fact = Fact(
            subject="A",
            verb="did",
            object="B",
            sdh_score=0.0,
        )

        assert compute_pack_score(fact, 1.0) == 0.0

    def test_pack_score_zero_when_similarity_is_zero(self):
        fact = Fact(
            subject="A",
            verb="did",
            object="B",
            sdh_score=1.0,
        )

        assert compute_pack_score(fact, 0.0) == 0.0


class TestModalityFiltering:
    def test_default_excludes_hypothetical(self):
        facts = [
            Fact(
                subject="A",
                verb="did",
                object="B",
                modality="asserted",
            ),
            Fact(
                subject="C",
                verb="did",
                object="D",
                modality="attributed",
            ),
            Fact(
                subject="E",
                verb="did",
                object="F",
                modality="hypothetical",
            ),
        ]

        filtered = filter_by_modality(facts)

        assert len(filtered) == 2
        assert all(f.modality != "hypothetical" for f in filtered)

    def test_custom_exclusion(self):
        facts = [
            Fact(
                subject="A",
                verb="did",
                object="B",
                modality="asserted",
            ),
            Fact(
                subject="C",
                verb="did",
                object="D",
                modality="conditional",
            ),
        ]

        filtered = filter_by_modality(
            facts,
            exclude_modalities={"conditional"},
        )

        assert len(filtered) == 1
        assert filtered[0].modality == "asserted"

    def test_empty_exclusion_keeps_all_modalities(self):
        facts = [
            Fact(
                subject="A",
                verb="did",
                object="B",
                modality="asserted",
            ),
            Fact(
                subject="C",
                verb="did",
                object="D",
                modality="hypothetical",
            ),
        ]

        filtered = filter_by_modality(
            facts,
            exclude_modalities=set(),
        )

        assert len(filtered) == 2


class TestContextRendering:
    def test_render_empty(self):
        assert render_context([]) == ""

    def test_render_full_fact(self):
        facts = [
            Fact(
                subject="Dr. Fleming",
                verb="discovered",
                object="penicillin",
                adjuncts={
                    "location": ["London"],
                    "time": ["in 1928"],
                },
                negated=False,
                modality="asserted",
            ),
            Fact(
                subject="Officials",
                verb="confirmed",
                object="outbreak",
                negated=True,
                modality="attributed",
                attributed_to="WHO",
            ),
        ]

        rendered = render_context(facts)

        assert "Fact 1: Dr. Fleming discovered penicillin" in rendered
        assert "(location: London)" in rendered
        assert "(time: in 1928)" in rendered
        assert "Fact 2: Officials NOT confirmed outbreak" in rendered
        assert "[attributed to WHO]" in rendered

    def test_negation_marker_not_doubled_when_verb_already_negated(self):
        facts = [
            Fact(subject="The framework", verb="does not subsidize", object="fossil fuels", negated=True),
            Fact(subject="Gordon", verb="does n't help", object="Bruce", negated=True),
            Fact(subject="Officials", verb="confirmed", object="outbreak", negated=True),
        ]

        rendered = render_context(facts)

        assert "Fact 1: The framework does not subsidize fossil fuels" in rendered
        assert "NOT does not" not in rendered
        assert "Fact 2: Gordon does n't help Bruce" in rendered
        assert "Fact 3: Officials NOT confirmed outbreak" in rendered

    def test_render_conditional_fact(self):
        fact = Fact(
            subject="The system",
            verb="fails",
            object="under heavy load",
            modality="conditional",
        )

        rendered = render_context([fact])

        assert "Fact 1: The system fails under heavy load" in rendered
        assert "[conditional]" in rendered

    def test_render_hypothetical_fact(self):
        fact = Fact(
            subject="Researchers",
            verb="might discover",
            object="alien life",
            modality="hypothetical",
        )

        rendered = render_context([fact])

        assert "Fact 1: Researchers might discover alien life" in rendered
        assert "[hypothetical]" in rendered

    def test_render_multiple_adjunct_values(self):
        fact = Fact(
            subject="Researchers",
            verb="conducted",
            object="study",
            adjuncts={
                "location": ["London", "Cambridge"],
            },
        )

        rendered = render_context([fact])

        assert "(location: London)" in rendered
        assert "(location: Cambridge)" in rendered


class TestPackContextIntegration:
    @pytest.fixture
    def populated_store(self, mem_store):
        facts = [
            Fact(
                subject="Alexander Fleming",
                verb="discovered",
                object="penicillin",
                adjuncts={
                    "location": ["London"],
                    "time": ["in 1928"],
                },
                raw_sentence=(
                    "In 1928, Dr. Alexander Fleming discovered penicillin "
                    "at St. Mary's Hospital in London."
                ),
                source_doc="penicillin.txt",
            ),
            Fact(
                subject="Penicillin",
                verb="kills",
                object="bacteria",
                raw_sentence=(
                    "Penicillin actively kills susceptible gram-positive "
                    "bacteria by disrupting cell wall synthesis."
                ),
                source_doc="penicillin.txt",
            ),
            Fact(
                subject="Astronomers",
                verb="discovered",
                object="distant exoplanet",
                raw_sentence=(
                    "Astronomers discovered an Earth-sized distant "
                    "exoplanet orbiting Proxima Centauri."
                ),
                source_doc="space.txt",
            ),
            Fact(
                subject="Researchers",
                verb="might discover",
                object="alien life",
                modality="hypothetical",
                raw_sentence=(
                    "Researchers might discover alien life within the next century."
                ),
                source_doc="space.txt",
            ),
        ]

        score_facts(facts)
        mem_store.add_facts(facts)

        return mem_store

    def test_pack_context_relevance(self, populated_store):
        res = pack_context(
            query="Who discovered penicillin and what does it kill?",
            store=populated_store,
            token_ceiling=500,
        )

        assert isinstance(res, PackResult)
        assert res.facts_packed >= 2

        subjects = [f.subject for f in res.packed_facts]

        assert "Alexander Fleming" in subjects
        assert "Penicillin" in subjects
        assert all(f.modality != "hypothetical" for f in res.packed_facts)
        assert res.tokens_used <= 500
        assert res.compression_rate > 0.0

    def test_token_ceiling_budget_constraint(self, populated_store):
        res = pack_context(
            query="penicillin discovery",
            store=populated_store,
            token_ceiling=6,
        )

        assert res.facts_packed == 1
        assert res.tokens_used <= 6

    def test_ablation_include_hypothetical(self, populated_store):
        res = pack_context(
            query="alien life discovery",
            store=populated_store,
            token_ceiling=500,
            exclude_modalities=set(),
        )

        modalities = [f.modality for f in res.packed_facts]

        assert "hypothetical" in modalities

    def test_custom_exclusion_is_applied(self, populated_store):
        res = pack_context(
            query="penicillin discovery",
            store=populated_store,
            token_ceiling=500,
            exclude_modalities={"asserted"},
        )

        assert all(fact.modality != "asserted" for fact in res.packed_facts)

    def test_empty_query_returns_empty_result(self, populated_store):
        res = pack_context(
            query="   ",
            store=populated_store,
            token_ceiling=500,
        )

        assert res.packed_facts == []
        assert res.tokens_used == 0
        assert res.naive_rag_tokens == 0
        assert res.compression_rate == 0.0
        assert res.avg_sdh_score == 0.0
        assert res.facts_considered == 0
        assert res.facts_packed == 0

    def test_zero_token_ceiling_returns_empty_result(self, populated_store):
        res = pack_context(
            query="penicillin",
            store=populated_store,
            token_ceiling=0,
        )

        assert res.packed_facts == []
        assert res.tokens_used == 0
        assert res.naive_rag_tokens == 0
        assert res.compression_rate == 0.0

    def test_non_positive_top_k_returns_empty_result(self, populated_store):
        res = pack_context(
            query="penicillin",
            store=populated_store,
            token_ceiling=500,
            top_k=0,
        )

        assert res.packed_facts == []
        assert res.tokens_used == 0
        assert res.naive_rag_tokens == 0
        assert res.facts_considered == 0

    def test_compression_rate_is_bounded(self, populated_store):
        res = pack_context(
            query="penicillin discovery",
            store=populated_store,
            token_ceiling=500,
        )

        assert 0.0 <= res.compression_rate <= 1.0

    def test_modality_priority_breaks_score_ties(self, mem_store):
        facts = [
            Fact(
                subject="Asserted",
                verb="is",
                object="important",
                modality="asserted",
                sdh_score=1.0,
                raw_sentence="Asserted is important.",
            ),
            Fact(
                subject="Attributed",
                verb="is",
                object="important",
                modality="attributed",
                sdh_score=1.0,
                raw_sentence="Attributed is important.",
            ),
        ]

        score_facts(facts)
        mem_store.add_facts(facts)

        res = pack_context(
            query="important",
            store=mem_store,
            token_ceiling=6,
            top_k=2,
        )

        assert res.facts_packed == 1
        assert res.packed_facts[0].modality == "asserted"

    def test_all_candidates_filtered(self, populated_store):
        res = pack_context(
            query="alien life discovery",
            store=populated_store,
            token_ceiling=500,
            exclude_modalities={
                "asserted",
                "attributed",
                "conditional",
                "hypothetical",
            },
        )

        assert res.packed_facts == []
        assert res.tokens_used == 0
        assert res.facts_considered == 0
        assert res.facts_packed == 0
        assert res.naive_rag_tokens > 0
        assert res.compression_rate == 1.0
