"""
Unit and integration tests for the ChromaDB FactStore layer.
"""

import uuid

import pytest
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.sdh import score_facts, score_facts_with_store


@pytest.fixture
def mem_store():
    """Provides a fresh, isolated in-memory FactStore for each test."""
    col_name = f"test_{uuid.uuid4().hex[:12]}"
    store = FactStore(in_memory=True, collection_name=col_name)
    yield store
    store._client.delete_collection(col_name)


class TestFactStoreInit:
    def test_store_creation(self, mem_store):
        assert mem_store.count() == 0
        assert mem_store.collection is not None
        assert mem_store.stats()["total_facts"] == 0

    def test_persistent_init(self, tmp_path):
        persist_dir = str(tmp_path / "chroma_test")
        store = FactStore(persist_dir=persist_dir, in_memory=False)
        assert store.count() == 0
        assert store.persist_dir == persist_dir


class TestAddAndRetrieveFacts:
    def test_add_empty_list(self, mem_store):
        added = mem_store.add_facts([])
        assert added == 0
        assert mem_store.count() == 0

    def test_reingestion_is_stable_when_fact_order_changes(self, mem_store):
        fact_a = Fact(
            subject="Alice",
            verb="discovered",
            object="X",
            source_doc="doc.txt",
            sentence_id=1,
        )
        fact_b = Fact(
            subject="Bob",
            verb="created",
            object="Y",
            source_doc="doc.txt",
            sentence_id=2,
        )
        mem_store.add_facts([fact_a, fact_b])
        assert mem_store.count() == 2
        # Re-ingest the same facts in a different order.
        mem_store.add_facts([fact_b, fact_a])
        # Reordering must not create duplicates.
        assert mem_store.count() == 2

    def test_add_and_preserve_metadata(self, mem_store):
        fact = Fact(
            subject="Alexander Fleming",
            verb="discovered",
            object="penicillin",
            adjuncts={"location": ["London"], "time": ["in 1928"]},
            negated=False,
            modality="asserted",
            attributed_to=None,
            sdh_score=0.825,
            source_doc="history.txt",
            sentence_id=1,
            raw_sentence="In 1928, Alexander Fleming discovered penicillin in London.",
        )
        added = mem_store.add_facts([fact])
        assert added == 1
        assert mem_store.count() == 1
        # Query back
        results = mem_store.query_similar("Who discovered penicillin?", n_results=1)
        assert len(results) == 1
        retrieved_fact, sim = results[0]
        assert retrieved_fact.subject == "Alexander Fleming"
        assert retrieved_fact.verb == "discovered"
        assert retrieved_fact.object == "penicillin"
        assert retrieved_fact.adjuncts == {"location": ["London"], "time": ["in 1928"]}
        assert retrieved_fact.negated is False
        assert retrieved_fact.modality == "asserted"
        assert retrieved_fact.attributed_to is None
        assert retrieved_fact.source_doc == "history.txt"
        assert retrieved_fact.sentence_id == 1
        assert abs(retrieved_fact.sdh_score - 0.825) < 1e-4
        assert len(retrieved_fact.embedding) == 384
        assert sim > 0.50

    def test_reuse_existing_embedding(self, mem_store):
        precomputed_emb = [0.05] * 384
        fact = Fact(
            subject="Alpha",
            verb="created",
            object="Beta",
            embedding=precomputed_emb,
            source_doc="test.txt",
        )
        mem_store.add_facts([fact])
        stored_embs = mem_store.get_all_embeddings()
        assert len(stored_embs) == 1
        # ChromaDB normalizes embeddings under cosine distance
        assert len(stored_embs[0]) == 384

    def test_identical_facts_get_distinct_ids(self, mem_store):
        fact_a = Fact(
            subject="Alice",
            verb="discovered",
            object="X",
            source_doc="doc.txt",
            sentence_id=1,
        )
        fact_b = Fact(
            subject="Alice",
            verb="discovered",
            object="X",
            source_doc="doc.txt",
            sentence_id=1,
        )
        mem_store.add_facts([fact_a, fact_b])
        assert mem_store.count() == 2


class TestQuerySimilar:
    @pytest.fixture(autouse=True)
    def populate_store(self, mem_store):
        facts = [
            Fact(
                subject="astronomers",
                verb="discovered",
                object="exoplanet",
                modality="asserted",
                source_doc="space.txt",
                sdh_score=0.75,
            ),
            Fact(
                subject="biologists",
                verb="isolated",
                object="novel virus",
                modality="asserted",
                source_doc="biology.txt",
                sdh_score=0.70,
            ),
            Fact(
                subject="spokesperson",
                verb="claimed",
                object="revenue tripled",
                modality="attributed",
                attributed_to="CEO",
                source_doc="finance.txt",
                sdh_score=0.60,
            ),
            Fact(
                subject="author",
                verb="may release",
                object="sequel",
                modality="hypothetical",
                source_doc="arts.txt",
                sdh_score=0.40,
            ),
        ]
        score_facts(facts)
        mem_store.add_facts(facts)

    def test_query_relevance(self, mem_store):
        results = mem_store.query_similar(
            "telescope astronomical discovery of new planet", n_results=2
        )
        assert len(results) >= 1
        top_fact, score = results[0]
        assert top_fact.subject == "astronomers"
        assert top_fact.object == "exoplanet"
        assert score > 0.40

    def test_query_with_single_modality_filter(self, mem_store):
        results = mem_store.query_similar(
            "company revenue", modality_filter="attributed"
        )
        assert len(results) == 1
        assert results[0][0].modality == "attributed"
        assert results[0][0].subject == "spokesperson"

    def test_query_with_multi_modality_filter(self, mem_store):
        results = mem_store.query_similar(
            "anything", modality_filter=["asserted", "attributed"]
        )
        modalities = {f.modality for f, _ in results}
        assert "hypothetical" not in modalities
        assert modalities.issubset({"asserted", "attributed"})

    def test_query_with_source_doc_filter(self, mem_store):
        results = mem_store.query_similar("discovery", source_doc="biology.txt")
        assert len(results) == 1
        assert results[0][0].source_doc == "biology.txt"
        assert results[0][0].subject == "biologists"


class TestFilteringAndStats:
    def test_get_by_modality(self, mem_store):
        facts = [
            Fact(subject="A", verb="did", object="B", modality="conditional"),
            Fact(subject="C", verb="did", object="D", modality="conditional"),
            Fact(subject="E", verb="did", object="F", modality="asserted"),
        ]
        mem_store.add_facts(facts)
        conditionals = mem_store.get_by_modality("conditional")
        assert len(conditionals) == 2
        assert all(f.modality == "conditional" for f in conditionals)

    def test_get_by_document(self, mem_store):
        facts = [
            Fact(subject="A", verb="did", object="B", source_doc="doc1.txt"),
            Fact(subject="C", verb="did", object="D", source_doc="doc2.txt"),
        ]
        mem_store.add_facts(facts)
        doc1_facts = mem_store.get_by_document("doc1.txt")
        assert len(doc1_facts) == 1
        assert doc1_facts[0].subject == "A"

    def test_stats_and_documents(self, mem_store):
        facts = [
            Fact(
                subject="A",
                verb="did",
                object="B",
                negated=True,
                modality="asserted",
                sdh_score=0.8,
                source_doc="docA.txt",
            ),
            Fact(
                subject="C",
                verb="did",
                object="D",
                negated=False,
                modality="attributed",
                sdh_score=0.6,
                source_doc="docB.txt",
            ),
        ]
        mem_store.add_facts(facts)
        stats = mem_store.stats()
        assert stats["total_facts"] == 2
        assert stats["negated_count"] == 1
        assert stats["modality_breakdown"] == {"asserted": 1, "attributed": 1}
        assert abs(stats["avg_sdh_score"] - 0.7) < 1e-4
        assert stats["document_count"] == 2
        assert stats["documents"] == ["docA.txt", "docB.txt"]
        docs = mem_store.get_all_documents()
        assert docs == ["docA.txt", "docB.txt"]


class TestDeletionAndClearing:
    def test_delete_document(self, mem_store):
        facts = [
            Fact(subject="A", verb="did", object="B", source_doc="delete_me.txt"),
            Fact(subject="C", verb="did", object="D", source_doc="delete_me.txt"),
            Fact(subject="E", verb="did", object="F", source_doc="keep_me.txt"),
        ]
        mem_store.add_facts(facts)
        assert mem_store.count() == 3
        deleted = mem_store.delete_document("delete_me.txt")
        assert deleted == 2
        assert mem_store.count() == 1
        assert mem_store.get_all_documents() == ["keep_me.txt"]

    def test_clear_store(self, mem_store):
        facts = [Fact(subject="A", verb="did", object="B", source_doc="doc.txt")]
        mem_store.add_facts(facts)
        assert mem_store.count() == 1
        cleared = mem_store.clear()
        assert cleared == 1
        assert mem_store.count() == 0
        assert mem_store.stats()["total_facts"] == 0


class TestStoreSDHIntegration:
    def test_score_facts_with_store_uniqueness(self, mem_store):
        # 1. Ingest an initial fact into store
        initial_fact = Fact(
            subject="NASA", verb="launched", object="James Webb Space Telescope"
        )
        score_facts([initial_fact])
        mem_store.add_facts([initial_fact])
        # 2. Score a duplicate fact against the store
        duplicate_fact = Fact(
            subject="NASA", verb="launched", object="James Webb Space Telescope"
        )
        score_facts_with_store([duplicate_fact], mem_store)
        # 3. Score a completely novel fact against the store
        novel_fact = Fact(subject="Chemist", verb="synthesized", object="aspirin")
        score_facts_with_store([novel_fact], mem_store)
        # Duplicate must have a lower SDH score than novel fact due to U(t, G)
        assert duplicate_fact.sdh_score < novel_fact.sdh_score
