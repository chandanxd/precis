"""
Deterministic Acceptance Test Suite for Guarded Structural-Priority Context Packing (Experiment 4.7.0.1 Hardened).

Verifies the 10 acceptance test cases (ATP-01 to ATP-10) specified in acceptance_test_plan.md:
- ATP-01: Structural evidence is selected: same-document SVOA facts are suppressed.
- ATP-02: Structural retrieval returns no eligible evidence: safe fallback to standard SVOA facts.
- ATP-03: Structural evidence exceeds budget: safe fallback to SVOA facts, no empty context or ceiling violation.
- ATP-04: Cross-document isolation: Doc A table packed, Doc A facts suppressed, Doc B facts retained.
- ATP-05: Prose-only document: legacy and feature-enabled behavior are byte-for-byte identical.
- ATP-06: Feature flag disabled: legacy behavior remains unchanged.
- ATP-07: Deterministic ranking and tie-breaking across repeated calls.
- ATP-08: Known eligible evidence item survives into context when fallback occurs.
- ATP-09: Budget ceiling strictly enforced across varied scales.
- ATP-10: Verbatim deduplication preserved on retained cross-document facts.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from precis.graph.schema import Fact, StructuralEvidence
from precis.graph.store import FactStore
from precis.pipeline.hardware import HardwareProfile
from precis.pipeline.orchestrator import (
    assemble_query_context,
    ingest_document,
)
from precis.pipeline.structural import (
    assemble_structural_query_context,
    estimate_text_tokens,
)


@pytest.fixture
def mem_store():
    """Isolated in-memory FactStore with structural collection."""
    col_name = f"test_atp_{uuid.uuid4().hex[:12]}"
    store = FactStore(in_memory=True, collection_name=col_name)
    yield store
    try:
        store._client.delete_collection(col_name)
    except Exception:
        pass
    try:
        store._client.delete_collection(f"{col_name}_structural")
    except Exception:
        pass


@pytest.fixture
def sample_hardware():
    """Predictable hardware profile."""
    return HardwareProfile(
        cpu_cores=8,
        cpu_model="Mock CPU",
        ram_gb=16.0,
        has_gpu=False,
        gpu_name=None,
        vram_gb=None,
        ml_accelerator=None,
        recommended_model="qwen2.5-coder:7b",
        recommended_mode="cpu",
        token_ceiling=2048,
    )


class TestStructuralPriorityPackingAcceptance:
    """Suite covering ATP-01 through ATP-10 with hardened assertions."""

    def test_atp_01_suppresses_same_doc_facts_when_structural_packed(self, mem_store):
        """
        ATP-01: When relevant structural evidence from document D is packed,
        same-document SVOA facts are strictly suppressed (facts_packed == 0).
        """
        doc_html = """
        <p>The Supreme Court of the United States is the highest federal court.</p>
        <table>
            <tr><th>Role</th><th>Name</th></tr>
            <tr><td>Incumbent</td><td>John Roberts since September 29, 2005</td></tr>
            <tr><td>Inaugural holder</td><td>John Jay September 26, 1789</td></tr>
        </table>
        <p>John Jay served as inaugural Chief Justice in historical times.</p>
        """
        ingest_document(
            text=doc_html,
            source_doc="supreme_court.html",
            store=mem_store,
            enable_list_extraction=True,
        )

        query = "who is the supreme justice of the supreme court"
        assembled = assemble_query_context(
            query=query,
            store=mem_store,
            token_ceiling=2048,
            enable_list_extraction=True,
        )

        # 1. Structural evidence must be used
        assert assembled.use_structural is True
        assert "John Roberts" in assembled.context
        assert "| Incumbent | John Roberts" in assembled.context

        # 2. Same-document SVOA facts must be strictly suppressed
        assert assembled.facts_packed == 0
        assert len(assembled.facts_used) == 0
        assert "Fact 1:" not in assembled.context
        assert "Fact 2:" not in assembled.context
        assert "served as inaugural Chief Justice" not in assembled.context

        # 3. Telemetry asserts
        telemetry = assembled.telemetry
        assert telemetry.get("structural_priority_active") is True
        assert telemetry.get("suppressed_same_doc_facts", 0) > 0
        assert telemetry.get("retained_cross_doc_facts", 0) == 0
        assert telemetry.get("tables_packed", 0) >= 1

    def test_atp_02_fallback_when_structural_retrieval_below_threshold(self, mem_store):
        """
        ATP-02: When structural records exist but fail retrieval relevance filtering,
        deterministically fall back to standard SVOA fact-based context.
        Uses a controlled test-local mock to force structural candidates to be ineligible (sim < 0.25, no KW match).
        """
        doc_html = """
        <p>The botanical garden has multiple species of flowering plants.</p>
        <table>
            <tr><th>Batch ID</th><th>Reading</th></tr>
            <tr><td>101</td><td>98.6</td></tr>
        </table>
        <p>Dr. Smith discovered the rare alpine orchid in 1995.</p>
        """
        ingest_document(
            text=doc_html,
            source_doc="botany.html",
            store=mem_store,
            enable_list_extraction=True,
        )

        # Confirm structural evidence exists in storage
        assert mem_store.count_structural_evidence("botany.html") > 0

        # Retrieve real structural item from store to construct controlled candidate with low similarity
        struct_items = mem_store.get_structural_evidence_by_document("botany.html")
        assert len(struct_items) > 0

        # Force query_similar_structural to return structural item with ineligible similarity (0.10 < 0.25) and no KW match
        controlled_candidates = [(struct_items[0], 0.10)]
        with patch.object(mem_store, "query_similar_structural", return_value=controlled_candidates):
            query = "who discovered the rare alpine orchid"
            assembled = assemble_query_context(
                query=query,
                store=mem_store,
                token_ceiling=2048,
                enable_list_extraction=True,
            )

            # 1. Structural evidence must be rejected and SVOA fallback exercised
            assert assembled.use_structural is False
            assert "| Batch ID | Reading |" not in assembled.context

            # 2. Assert fallback returns non-empty context with eligible facts
            assert len(assembled.context.strip()) > 0
            assert "Fact 1:" in assembled.context
            assert assembled.facts_packed >= 1
            assert "Dr. Smith discovered the rare alpine orchid" in assembled.context
            assert len(assembled.facts_used) == assembled.facts_packed

            # 3. Assert token limit respected
            assert assembled.tokens_used <= 2048
            assert estimate_text_tokens(assembled.context) <= 2048

    def test_atp_03_fallback_when_structural_evidence_exceeds_budget(self, mem_store):
        """
        ATP-03: When structural evidence exceeds the token budget and cannot fit,
        deterministically fall back to SVOA facts. No empty context or ceiling violation.
        """
        rows = "".join(f"<tr><td>Item_{i}</td><td>Detailed description metric value {i*10}</td></tr>" for i in range(25))
        doc_html = f"""
        <p>Short summary: System operates at 99.9% availability.</p>
        <table>
            <tr><th>Item</th><th>Description</th></tr>
            {rows}
        </table>
        """
        ingest_document(
            text=doc_html,
            source_doc="metrics.html",
            store=mem_store,
            enable_list_extraction=True,
        )

        query = "system availability metrics"
        tiny_budget = 40  # Table is ~200 tokens, cannot fit in 40 tokens

        # Verify table chunk in store exceeds 40 tokens
        struct_items = mem_store.get_structural_evidence_by_document("metrics.html")
        assert len(struct_items) > 0
        assert estimate_text_tokens(struct_items[0].content) > tiny_budget

        assembled = assemble_query_context(
            query=query,
            store=mem_store,
            token_ceiling=tiny_budget,
            enable_list_extraction=True,
        )

        # Table could not fit, so it must fall back to SVOA facts
        assert assembled.use_structural is False
        assert "| Item | Description |" not in assembled.context
        assert assembled.tokens_used <= tiny_budget
        assert estimate_text_tokens(assembled.context) <= tiny_budget
        assert assembled.facts_packed >= 1
        assert "Fact 1:" in assembled.context
        assert "System operates" in assembled.context

    def test_atp_04_cross_document_isolation_and_retention(self, mem_store):
        """
        ATP-04: Multi-document store: Doc A table is packed, Doc A facts are suppressed,
        Doc B facts from non-structural document are retained in remaining budget.
        """
        doc_a_html = """
        <p>The leadership committee coordinates executive decisions.</p>
        <table>
            <tr><th>Role</th><th>Executive</th></tr>
            <tr><td>Chairperson</td><td>Elena Rostova</td></tr>
            <tr><td>Vice-Chair</td><td>Marcus Vance</td></tr>
        </table>
        <p>Elena Rostova was appointed in June 2022.</p>
        """
        doc_b_html = """
        <p>Acme Corporation was founded in 1984 by Arthur Pendelton.</p>
        <p>Acme Corporation manufactures precision measurement tools in Zurich.</p>
        """
        ingest_document(text=doc_a_html, source_doc="leadership.html", store=mem_store, enable_list_extraction=True)
        ingest_document(text=doc_b_html, source_doc="history.html", store=mem_store, enable_list_extraction=True)

        query = "Who is the Chairperson and who founded Acme Corporation?"
        assembled = assemble_query_context(
            query=query,
            store=mem_store,
            token_ceiling=2048,
            enable_list_extraction=True,
        )

        # 1. Structural evidence from doc A is packed
        assert assembled.use_structural is True
        assert "Elena Rostova" in assembled.context
        assert "| Chairperson | Elena Rostova |" in assembled.context

        # 2. Same-doc (Doc A) prose facts must be suppressed
        assert "Elena Rostova was appointed in June 2022" not in assembled.context
        assert not any(f.source_doc == "leadership.html" for f in assembled.facts_used)

        # 3. Cross-doc (Doc B) facts must be retained and packed
        telemetry = assembled.telemetry
        assert telemetry.get("tables_packed", 0) >= 1
        assert telemetry.get("retained_cross_doc_facts", 0) > 0
        assert telemetry.get("suppressed_same_doc_facts", 0) > 0
        assert assembled.facts_packed > 0
        assert any(f.source_doc == "history.html" for f in assembled.facts_used)
        assert "Fact 1:" in assembled.context
        assert ("Arthur Pendelton" in assembled.context) or ("Acme Corporation" in assembled.context)

    def test_atp_05_prose_only_document_behavior_unchanged(self, mem_store):
        """
        ATP-05: Prose-only document produces byte-for-byte identical context and metrics
        between feature-enabled and feature-disabled paths.
        """
        doc_prose = """
        Marie Curie was a physicist and chemist who conducted pioneering research on radioactivity.
        She was the first woman to win a Nobel Prize.
        She was the first person to win Nobel Prizes in two scientific fields.
        """
        ingest_document(text=doc_prose, source_doc="curie.html", store=mem_store, enable_list_extraction=True)

        query = "What did Marie Curie research?"
        ctx_disabled = assemble_query_context(
            query=query,
            store=mem_store,
            token_ceiling=2048,
            enable_list_extraction=False,
        )
        ctx_enabled = assemble_query_context(
            query=query,
            store=mem_store,
            token_ceiling=2048,
            enable_list_extraction=True,
        )

        # Byte-for-byte and property identity
        assert ctx_enabled.context == ctx_disabled.context
        assert ctx_enabled.tokens_used == ctx_disabled.tokens_used
        assert ctx_enabled.facts_packed == ctx_disabled.facts_packed
        assert len(ctx_enabled.facts_used) == len(ctx_disabled.facts_used)
        assert ctx_enabled.use_structural is False
        assert "Marie Curie" in ctx_enabled.context
        assert "Fact 1:" in ctx_enabled.context

    def test_atp_06_feature_flag_disabled_preserves_legacy_packing(self, mem_store):
        """
        ATP-06: When feature flag is disabled, context strictly uses legacy SVOA fact packing
        even when table evidence exists in store.
        """
        doc_html = """
        <table>
            <tr><th>Metric</th><th>Score</th></tr>
            <tr><td>Alpha</td><td>95</td></tr>
        </table>
        <p>System test passed with high confidence.</p>
        """
        ingest_document(text=doc_html, source_doc="flag_test.html", store=mem_store, enable_list_extraction=True)

        query = "System test score"
        assembled = assemble_query_context(
            query=query,
            store=mem_store,
            token_ceiling=2048,
            enable_list_extraction=False,
        )

        assert assembled.use_structural is False
        assert "| Metric | Score |" not in assembled.context
        assert "Fact 1:" in assembled.context
        assert assembled.facts_packed >= 1

    def test_atp_07_deterministic_ranking_and_tie_breaking(self, mem_store):
        """
        ATP-07: Context assembly produces byte-identical context across repeated invocations.
        """
        doc_html = """
        <table>
            <tr><th>City</th><th>Population</th></tr>
            <tr><td>Tokyo</td><td>37400068</td></tr>
            <tr><td>Delhi</td><td>29399141</td></tr>
        </table>
        <p>Urban density metrics are monitored annually.</p>
        """
        ingest_document(text=doc_html, source_doc="cities.html", store=mem_store, enable_list_extraction=True)

        query = "What is the population of Tokyo?"
        res1 = assemble_query_context(query=query, store=mem_store, token_ceiling=2048, enable_list_extraction=True)
        res2 = assemble_query_context(query=query, store=mem_store, token_ceiling=2048, enable_list_extraction=True)

        assert res1.context == res2.context
        assert res1.tokens_used == res2.tokens_used
        assert res1.facts_packed == res2.facts_packed
        assert res1.use_structural == res2.use_structural
        assert [f.fact_id for f in res1.facts_used] == [f.fact_id for f in res2.facts_used]

    def test_atp_08_no_empty_context_when_evidence_exists(self, mem_store):
        """
        ATP-08: When structural relevance fails, known eligible fact evidence survives into
        context rather than returning an empty string.
        Uses a controlled test-local mock to force structural rejection deterministically.
        """
        doc_html = """
        <table>
            <tr><th>Batch ID</th><th>Reading</th></tr>
            <tr><td>001</td><td>42.5</td></tr>
        </table>
        <p>The system verification test confirmed proper operational readiness.</p>
        """
        ingest_document(text=doc_html, source_doc="verify.html", store=mem_store, enable_list_extraction=True)

        # Force structural retrieval rejection via controlled mock (empty candidates)
        with patch.object(mem_store, "query_similar_structural", return_value=[]):
            query = "what did the system verification test confirm"
            assembled = assemble_query_context(query=query, store=mem_store, token_ceiling=500, enable_list_extraction=True)

            assert assembled.use_structural is False
            assert len(assembled.context.strip()) > 0
            assert assembled.facts_packed >= 1
            # Specifically verify the known target entity/assertion survived into context
            assert "The system verification test confirmed proper operational readiness" in assembled.context
            assert "Fact 1:" in assembled.context
            assert assembled.tokens_used <= 500
            assert estimate_text_tokens(assembled.context) <= 500

    @pytest.mark.parametrize("ceiling", [100, 250, 500, 1000, 2048])
    def test_atp_09_budget_ceiling_hard_enforcement_at_all_scales(self, mem_store, ceiling):
        """
        ATP-09: Context size strictly obeys token_ceiling across all scales unconditionally.
        Asserts tokens_used <= token_ceiling and estimate_text_tokens(context) <= token_ceiling.
        Note: For table context, tokens_used and estimate_text_tokens are identical.
        For SVOA fallback context, tokens_used is computed by packer (estimate_fact_tokens sum)
        which is bounded by token_ceiling.
        """
        rows = "".join(f"<tr><td>Item_{i}</td><td>Value_{i}</td></tr>" for i in range(10))
        doc_html = f"<table><tr><th>Item</th><th>Value</th></tr>{rows}</table>"
        ingest_document(text=doc_html, source_doc="tbl.html", store=mem_store, enable_list_extraction=True)

        query = "Item Value"
        assembled = assemble_query_context(query=query, store=mem_store, token_ceiling=ceiling, enable_list_extraction=True)

        # Unconditional budget ceiling assertion
        assert assembled.tokens_used <= ceiling
        assert estimate_text_tokens(assembled.context) <= ceiling
        if assembled.use_structural:
            assert assembled.telemetry.get("ceiling_violation") is False

    def test_atp_10_verbatim_deduplication_on_retained_cross_doc_facts(self, mem_store):
        """
        ATP-10: When cross-document facts are retained, verbatim deduplication
        against the packed structural content is still strictly enforced.
        Asserts both that the duplicate cross-doc fact is absent AND distinct fact is retained.
        Also asserts a distinct AlphaCorp fact is NOT incorrectly suppressed merely because
        it shares the same subject as the duplicate.
        """
        doc_a_html = """
        <table>
            <tr><th>Entity</th><th>Role</th></tr>
            <tr><td>AlphaCorp</td><td>Equipment Supplier</td></tr>
        </table>
        """
        doc_b_html = """
        <p>AlphaCorp is Equipment Supplier.</p>
        <p>AlphaCorp acquired GammaCorp in Berlin.</p>
        <p>BetaCorp operates logistics in Rotterdam.</p>
        """
        ingest_document(text=doc_a_html, source_doc="doc_a.html", store=mem_store, enable_list_extraction=True)
        ingest_document(text=doc_b_html, source_doc="doc_b.html", store=mem_store, enable_list_extraction=True)

        query = "AlphaCorp equipment supplier, GammaCorp acquisition, and BetaCorp logistics"
        assembled = assemble_query_context(query=query, store=mem_store, token_ceiling=2048, enable_list_extraction=True)

        assert assembled.use_structural is True
        # Doc A table is in context
        assert "| AlphaCorp | Equipment Supplier |" in assembled.context

        # 1. Distinct cross-document facts from doc B must be retained in context and facts_used
        assert "BetaCorp operates logistics in Rotterdam" in assembled.context
        assert any(f.subject == "BetaCorp" for f in assembled.facts_used)

        # Distinct AlphaCorp fact sharing the subject must NOT be suppressed
        assert "AlphaCorp acquired GammaCorp" in assembled.context
        assert any(f.subject == "AlphaCorp" and f.object == "GammaCorp" for f in assembled.facts_used)

        # 2. Redundant duplicate cross-document fact from doc B must be absent from context and facts_used
        assert not any(f.subject == "AlphaCorp" and f.object == "Equipment Supplier" for f in assembled.facts_used)
        assert "AlphaCorp is Equipment Supplier" not in assembled.context
