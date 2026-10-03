from precis.graph.schema import Fact
from precis.pipeline.sdh import (
    ABLATION_DROP_ALPHA,
    ABLATION_DROP_BETA,
    ABLATION_DROP_DELTA,
    ABLATION_DROP_GAMMA,
    DEFAULT_WEIGHTS,
    adjunct_density,
    canonical_fact_text,
    cosine_similarity,
    embed_text,
    embed_texts,
    entity_relatedness,
    score_fact,
    score_facts,
    score_facts_with_store,
    uniqueness,
    verb_informativeness,
)


class TestEmbeddingAndSimilarity:
    def test_embed_text_dimensions(self):
        emb = embed_text("Alexander Fleming discovered penicillin.")
        assert len(emb) == 384
        assert isinstance(emb[0], float)

    def test_embed_empty_text(self):
        emb = embed_text("")
        assert len(emb) == 384
        assert all(x == 0.0 for x in emb)

    def test_embed_texts_batch(self):
        texts = ["Text one", "Text two", "Text three"]
        embs = embed_texts(texts)
        assert len(embs) == 3
        assert all(len(e) == 384 for e in embs)

    def test_cosine_similarity_identical(self):
        v = embed_text("quantum physics")
        sim = cosine_similarity(v, v)
        assert abs(sim - 1.0) < 1e-4

    def test_cosine_similarity_orthogonal_or_zero(self):
        sim = cosine_similarity([0.0] * 384, [1.0] * 384)
        assert sim == 0.0


class TestCanonicalFactText:
    def test_canonical_text_formatting(self):
        fact = Fact(
            subject="parliament",
            verb="approved",
            object="climate bill",
            adjuncts={"time": ["on Friday"], "location": ["in London"]},
            negated=True,
            modality="attributed",
            attributed_to="BBC",
        )
        text = canonical_fact_text(fact)
        assert "parliament does not approved climate bill" in text
        assert "(time: on Friday)" in text
        assert "(location: in London)" in text
        assert "[attributed: BBC]" in text


class TestEntityRelatedness:
    def test_empty_entities(self):
        fact_no_sub = Fact(subject="", verb="approved", object="bill")
        assert entity_relatedness(fact_no_sub) == 0.0

        fact_no_obj = Fact(subject="government", verb="approved", object="")
        assert entity_relatedness(fact_no_obj) == 0.0

    def test_related_entities(self):
        fact = Fact(subject="physician", verb="prescribed", object="medication")
        score = entity_relatedness(fact)
        assert 0.0 <= score <= 1.0
        assert score > 0.30

    def test_generic_pronoun_penalty(self):
        fact_specific = Fact(subject="scientist", verb="tested", object="vaccine")
        fact_generic = Fact(subject="it", verb="tested", object="something")

        score_spec = entity_relatedness(fact_specific)
        score_gen = entity_relatedness(fact_generic)
        assert score_spec > score_gen


class TestVerbInformativeness:
    def test_copular_light_verbs(self):
        fact_be = Fact(subject="water", verb="is", object="liquid")
        fact_have = Fact(subject="company", verb="has", object="assets")

        score_be = verb_informativeness(fact_be)
        score_have = verb_informativeness(fact_have)

        assert 0.15 <= score_be <= 0.35
        assert 0.15 <= score_have <= 0.35

    def test_multi_word_verb_phrases(self):
        # Multi-word verbs should decompose to their head verb and not collapse to default OOV
        fact_future = Fact(subject="senate", verb="will approve", object="treaty")
        fact_neg = Fact(subject="team", verb="did not discover", object="cure")
        fact_pass = Fact(subject="bill", verb="was ratified by", object="parliament")

        score_future = verb_informativeness(fact_future)
        score_neg = verb_informativeness(fact_neg)
        score_pass = verb_informativeness(fact_pass)

        # All of approve, discover, ratify are substantive verbs
        assert score_future > 0.50
        assert score_neg > 0.50
        assert score_pass > 0.60

    def test_specific_domain_verbs(self):
        fact_domain = Fact(subject="chemist", verb="synthesized", object="compound")
        fact_light = Fact(subject="chemist", verb="made", object="compound")

        score_domain = verb_informativeness(fact_domain)
        score_light = verb_informativeness(fact_light)

        assert score_domain > score_light
        assert score_domain >= 0.70

    def test_empty_verb(self):
        fact = Fact(subject="a", verb="", object="b")
        assert verb_informativeness(fact) == 0.10


class TestUniqueness:
    def test_cold_start_uniqueness(self):
        fact = Fact(subject="government", verb="approved", object="climate bill")
        assert uniqueness(fact, existing_embeddings=[]) == 1.0
        assert uniqueness(fact, existing_embeddings=None) == 1.0

    def test_near_duplicate_penalty(self):
        fact1 = Fact(subject="NASA", verb="launched", object="James Webb Telescope")
        emb1 = embed_text(canonical_fact_text(fact1))

        fact_duplicate = Fact(
            subject="NASA", verb="launched", object="James Webb Telescope"
        )
        u_score = uniqueness(fact_duplicate, existing_embeddings=[emb1])
        assert u_score < 0.10

    def test_novel_fact_high_uniqueness(self):
        fact1 = Fact(subject="astronomers", verb="discovered", object="exoplanet")
        emb1 = embed_text(canonical_fact_text(fact1))

        fact2 = Fact(subject="baker", verb="baked", object="sourdough bread")
        u_score = uniqueness(fact2, existing_embeddings=[emb1])
        assert u_score > 0.85

    def test_temporal_variants_distinguished(self):
        fact2021 = Fact(
            subject="company",
            verb="reported",
            object="record profits",
            adjuncts={"time": ["in 2021"]},
        )
        fact2022 = Fact(
            subject="company",
            verb="reported",
            object="record profits",
            adjuncts={"time": ["in 2022"]},
        )

        emb2021 = embed_text(canonical_fact_text(fact2021))
        emb2022 = embed_text(canonical_fact_text(fact2022))

        # Because canonical text includes the adjunct, embeddings differ
        sim = cosine_similarity(emb2021, emb2022)
        assert sim < 1.0


class TestAdjunctDensity:
    def test_empty_adjuncts_baseline(self):
        fact = Fact(subject="x", verb="y", object="z", adjuncts={})
        assert adjunct_density(fact) == 0.20

    def test_single_adjunct(self):
        fact = Fact(subject="x", verb="y", object="z", adjuncts={"time": ["Friday"]})
        score = adjunct_density(fact)
        assert score > 0.20
        assert score <= 1.0

    def test_weighted_adjuncts(self):
        fact_cause = Fact(
            subject="x", verb="y", object="z", adjuncts={"cause": ["due to inflation"]}
        )
        fact_manner = Fact(
            subject="x", verb="y", object="z", adjuncts={"manner": ["quickly"]}
        )

        score_cause = adjunct_density(fact_cause)
        score_manner = adjunct_density(fact_manner)
        assert score_cause > score_manner

    def test_density_capped_at_one(self):
        fact = Fact(
            subject="x",
            verb="y",
            object="z",
            adjuncts={
                "time": ["on Friday", "at noon"],
                "loc": ["in Berlin"],
                "cause": ["due to rain"],
            },
        )
        assert adjunct_density(fact) == 1.0


class TestCompositeSDHScoring:
    def test_score_fact_range(self):
        fact = Fact(
            subject="researchers",
            verb="published",
            object="paper",
            adjuncts={"time": ["yesterday"]},
        )
        score = score_fact(fact)
        assert 0.0 <= score <= 1.0
        assert fact.sdh_score == score

    def test_ablation_weights(self):
        fact = Fact(
            subject="Alexander Fleming",
            verb="discovered",
            object="penicillin",
            adjuncts={"time": ["in 1928"]},
        )

        score_default = score_fact(fact, weights=DEFAULT_WEIGHTS)
        score_drop_alpha = score_fact(fact, weights=ABLATION_DROP_ALPHA)
        score_drop_beta = score_fact(fact, weights=ABLATION_DROP_BETA)
        score_drop_gamma = score_fact(fact, weights=ABLATION_DROP_GAMMA)
        score_drop_delta = score_fact(fact, weights=ABLATION_DROP_DELTA)

        for s in [
            score_default,
            score_drop_alpha,
            score_drop_beta,
            score_drop_gamma,
            score_drop_delta,
        ]:
            assert 0.0 <= s <= 1.0

    def test_score_facts_batch(self):
        facts = [
            Fact(subject="Dr. Smith", verb="discovered", object="compound A"),
            Fact(
                subject="Dr. Smith", verb="discovered", object="compound A"
            ),  # Near duplicate
            Fact(subject="Astronomers", verb="observed", object="supernova"),
        ]

        scored = score_facts(facts)
        assert len(scored) == 3

        # Every fact must have an sdh_score and a cached 384-d embedding
        for f in scored:
            assert 0.0 <= f.sdh_score <= 1.0
            assert len(f.embedding) == 384

        # The duplicate fact (index 1) should have a lower uniqueness and thus lower SDH score than index 0
        assert scored[0].sdh_score > scored[1].sdh_score

    def test_score_facts_with_store(self):
        class MockStore:
            def __init__(self):
                self.embeddings = []

            def get_all_embeddings(self):
                return self.embeddings

        mock_store = MockStore()
        fact1 = Fact(subject="Team", verb="ratified", object="agreement")
        score_facts_with_store([fact1], mock_store)

        assert 0.0 <= fact1.sdh_score <= 1.0
        assert len(fact1.embedding) == 384
