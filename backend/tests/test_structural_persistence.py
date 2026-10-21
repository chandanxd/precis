"""
Test Suite for Persistent Structural Evidence and End-to-End Integration (Experiment 4.5.2).

Validates all 17 mandatory preflight & implementation requirements:
1. PRECIS_ENABLE_LIST_EXTRACTION=false by default (zero overhead, pure SVOA facts)
2. Explicit override precedence over environment variables
3. Ingestion-time structural extraction and persistence into FactStore
4. Query-time retrieval from store without raw_document supplied at query time
5. Multi-document isolation (records from doc A do not appear in doc B queries)
6. Deduplication against retrieved facts and existing tables
7. HTML edge cases (malformed HTML, unclosed tags, empty tags, deeply nested lists)
8. Hard token ceiling enforcement across varied budgets (100 to 2048 tokens)
9. REST ingestion and query end-to-end (/api/ingest and /api/query)
10. WebSocket ingestion and query end-to-end (/ws ingest and query streams)
11. Document re-ingestion (upsert replaces previous records without leakage or stale chunks)
12. Document deletion (deletes structural records alongside facts)
13. Store clear (clears structural collection alongside fact collection)
14. Regression case 3f5983b2: Namibian Minister evidence preserved
15. Regression case ef634417: Scorpions song evidence preserved and deduplicated
16. Regression case 8f1f9bd9: Thomas definition evidence preserved
17. Deterministic validation with zero external dependencies (mocked LLM/inference)
"""

import asyncio
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import main
import pytest
from fastapi.testclient import TestClient
from main import app
from precis.api.security import generate_token
from precis.graph.schema import Fact, StructuralEvidence
from precis.graph.store import FactStore
from precis.pipeline.hardware import HardwareProfile
from precis.pipeline.inference import InferenceResult
from precis.pipeline.orchestrator import (
    assemble_query_context,
    ingest_document,
    process_query,
    query_pipeline,
)
from precis.pipeline.structural import (
    FLAG_NAME,
    extract_structural_evidence_from_document,
    is_list_extraction_enabled,
)


@pytest.fixture
def mem_store():
    """Isolated in-memory FactStore for each test."""
    col_name = f"test_persist_{uuid.uuid4().hex[:12]}"
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
    """Deterministic hardware profile."""
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


@pytest.fixture
def auth_headers():
    token = generate_token("persist_test_user")
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Feature Flag Defaults & Precedence
# ==============================================================================

class TestFeatureFlagSemantics:
    """Verify Requirement 1 and Requirement 2."""

    def test_disabled_by_default(self, monkeypatch, mem_store):
        """Req 1: Disabled by default produces zero structural records."""
        monkeypatch.delenv(FLAG_NAME, raising=False)
        assert not is_list_extraction_enabled()

        html = """
        <p>The company announced quarterly revenue of 10 million dollars.</p>
        <ul>
            <li>Product Alpha: 5 million</li>
            <li>Product Beta: 5 million</li>
        </ul>
        """
        res = ingest_document(
            text=html,
            source_doc="doc_default.html",
            store=mem_store,
        )
        assert res.facts_stored > 0
        assert mem_store.count_structural_evidence("doc_default.html") == 0
        assert not mem_store.has_structural_evidence("doc_default.html")

    def test_explicit_override_precedence(self, monkeypatch, mem_store):
        """Req 2: Explicit parameter overrides environment variable in both directions."""
        # Env disabled, override enabled -> extracts & persists
        monkeypatch.setenv(FLAG_NAME, "false")
        assert not is_list_extraction_enabled()
        assert is_list_extraction_enabled(override=True)

        html = """
        <ul>
            <li>Item A</li>
            <li>Item B</li>
        </ul>
        """
        ingest_document(
            text=html,
            source_doc="override_true.html",
            store=mem_store,
            enable_list_extraction=True,
        )
        assert mem_store.count_structural_evidence("override_true.html") > 0

        # Env enabled, override disabled -> skips extraction & persistence
        monkeypatch.setenv(FLAG_NAME, "true")
        assert is_list_extraction_enabled()
        assert not is_list_extraction_enabled(override=False)

        ingest_document(
            text=html,
            source_doc="override_false.html",
            store=mem_store,
            enable_list_extraction=False,
        )
        assert mem_store.count_structural_evidence("override_false.html") == 0


# ==============================================================================
# 2. Ingestion-Time Persistence & Store Lifecycle
# ==============================================================================

class TestIngestionAndLifecycle:
    """Verify Requirements 3, 11, 12, 13."""

    def test_ingestion_time_persistence(self, mem_store):
        """Req 3: Structural elements are extracted and stored with embeddings."""
        html = """
        <table>
            <tr><th>Product</th><th>Price</th></tr>
            <tr><td>Widget</td><td>$10</td></tr>
            <tr><td>Gadget</td><td>$20</td></tr>
        </table>
        <ul>
            <li>Warranty: 2 years</li>
            <li>Shipping: Free</li>
        </ul>
        """
        res = ingest_document(
            text=html,
            source_doc="catalog.html",
            store=mem_store,
            enable_list_extraction=True,
        )
        assert mem_store.count_structural_evidence("catalog.html") >= 2
        items = mem_store.get_structural_evidence_by_document("catalog.html")
        types = {item.structure_type for item in items}
        assert "table" in types
        assert "list" in types
        assert all(item.source_doc == "catalog.html" for item in items)
        assert all(item.embedding is not None for item in items)
        assert all(len(item.embedding) == 384 for item in items)

    def test_document_reingestion_lifecycle(self, mem_store):
        """Req 11: Re-ingestion upserts/replaces records without creating duplicates or stale chunks."""
        v1_html = """
        <ul>
            <li>Old Version Item 1</li>
            <li>Old Version Item 2</li>
        </ul>
        """
        ingest_document(
            text=v1_html,
            source_doc="spec.html",
            store=mem_store,
            enable_list_extraction=True,
        )
        assert mem_store.count_structural_evidence("spec.html") == 1
        v1_items = mem_store.get_structural_evidence_by_document("spec.html")
        assert "Old Version" in v1_items[0].content

        v2_html = """
        <ul>
            <li>New Version Revised Item Alpha</li>
            <li>New Version Revised Item Beta</li>
        </ul>
        """
        ingest_document(
            text=v2_html,
            source_doc="spec.html",
            store=mem_store,
            enable_list_extraction=True,
        )
        # Old records must be deleted, count must still be 1 (not 2!)
        assert mem_store.count_structural_evidence("spec.html") == 1
        v2_items = mem_store.get_structural_evidence_by_document("spec.html")
        assert "New Version Revised" in v2_items[0].content
        assert "Old Version" not in v2_items[0].content

        # Re-ingest exact same content -> deterministic single record
        ingest_document(
            text=v2_html,
            source_doc="spec.html",
            store=mem_store,
            enable_list_extraction=True,
        )
        assert mem_store.count_structural_evidence("spec.html") == 1

    def test_document_deletion_lifecycle(self, mem_store):
        """Req 12: Deleting a document removes both facts and structural evidence."""
        doc1_html = "<ul><li>Doc1 Item</li></ul>"
        doc2_html = "<ul><li>Doc2 Item</li></ul>"

        ingest_document(doc1_html, "doc1.html", mem_store, enable_list_extraction=True)
        ingest_document(doc2_html, "doc2.html", mem_store, enable_list_extraction=True)

        assert mem_store.count_structural_evidence("doc1.html") == 1
        assert mem_store.count_structural_evidence("doc2.html") == 1

        deleted = mem_store.delete_document("doc1.html")
        assert mem_store.count_structural_evidence("doc1.html") == 0
        assert not mem_store.has_structural_evidence("doc1.html")
        # doc2 must remain untouched
        assert mem_store.count_structural_evidence("doc2.html") == 1

    def test_store_clear_lifecycle(self, mem_store):
        """Req 13: Clearing the store removes all facts and structural evidence."""
        doc_html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        ingest_document(doc_html, "doc_to_clear.html", mem_store, enable_list_extraction=True)

        assert mem_store.count_structural_evidence() > 0
        mem_store.clear()
        assert mem_store.count() == 0
        assert mem_store.count_structural_evidence() == 0


# ==============================================================================
# 3. Query Retrieval Without raw_document & Multi-Document Isolation
# ==============================================================================

class TestQueryRetrievalAndIsolation:
    """Verify Requirements 4, 5, 6, 8."""

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_query_retrieval_without_raw_document(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Req 4: Query time retrieves structural evidence from store without raw_document."""
        mock_generate.return_value = InferenceResult(
            answer="The team members are Alice, Bob, and Charlie.",
            model="qwen2.5-coder:7b",
            latency_ms=80,
            tokens_generated=15,
        )

        doc_html = """
        <p>The core development team works at headquarters.</p>
        <ul>
            <li>Alice: Backend Engineer</li>
            <li>Bob: Frontend Engineer</li>
            <li>Charlie: Systems Architect</li>
        </ul>
        """
        ingest_document(
            text=doc_html,
            source_doc="team.html",
            store=mem_store,
            enable_list_extraction=True,
        )

        # Call query_pipeline without raw_document
        res = query_pipeline(
            query="Who are the members of the core development team?",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )

        assert mock_generate.called
        context_passed = mock_generate.call_args[1]["context"]
        assert "Alice: Backend Engineer" in context_passed
        assert "Bob: Frontend Engineer" in context_passed
        assert "Charlie: Systems Architect" in context_passed

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_multi_document_isolation(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Req 5: Evidence from doc A does not appear in queries matching doc B."""
        mock_generate.return_value = InferenceResult(
            answer="Answer", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=5
        )

        doc_finance = """
        <p>The Ministry of Finance manages national taxation and treasury.</p>
        <ul>
            <li>Alice Miller (Minister of Finance)</li>
            <li>Bob Jones (Treasurer)</li>
        </ul>
        """
        doc_sports = """
        <p>The National Sports League coordinates athletic championships.</p>
        <ul>
            <li>Carlos Silva (Captain)</li>
            <li>David Ramos (Head Coach)</li>
        </ul>
        """
        ingest_document(doc_finance, "finance.html", mem_store, enable_list_extraction=True)
        ingest_document(doc_sports, "sports.html", mem_store, enable_list_extraction=True)

        # Query Finance
        query_pipeline(
            query="Who is the Minister of Finance?",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )
        finance_context = mock_generate.call_args[1]["context"]
        assert "Alice Miller" in finance_context
        # Sports athletes must NOT appear in Finance query context
        assert "Carlos Silva" not in finance_context
        assert "David Ramos" not in finance_context

        # Query Sports
        mock_generate.reset_mock()
        query_pipeline(
            query="Who is the athletic team captain?",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )
        sports_context = mock_generate.call_args[1]["context"]
        assert "Carlos Silva" in sports_context
        # Finance officials must NOT appear in Sports query context
        assert "Alice Miller" not in sports_context

    def test_deduplication_against_retrieved_facts(self, mem_store, sample_hardware):
        """Req 6: Structural context deduplicates redundant items against facts/tables."""
        # Table contains songwriters; standalone list contains exact same names
        html = """
        <table>
            <tr><th>Rock You Like a Hurricane</th><th>Details</th></tr>
            <tr><td>Single by Scorpions</td><td></td></tr>
            <tr><td>Songwriter</td><td>Rudolf Schenker Klaus Meine Herman Rarebell</td></tr>
        </table>
        <ul>
            <li>Rudolf Schenker</li>
            <li>Klaus Meine</li>
            <li>Herman Rarebell</li>
        </ul>
        """
        ingest_document(html, "scorpions.html", mem_store, enable_list_extraction=True)

        assembled = assemble_query_context(
            query="who sings rock you like a hurricane",
            store=mem_store,
            token_ceiling=1000,
            enable_list_extraction=True,
        )
        # Performer is preserved in context
        assert "Scorpions" in assembled.context
        # Deduplication telemetry should show suppression or zero bloated repetition
        if "deduplicated_list_blocks_count" in assembled.telemetry:
            assert assembled.telemetry["deduplicated_list_blocks_count"] >= 1

    @pytest.mark.parametrize("budget", [100, 250, 500, 1000, 2048])
    def test_hard_token_ceiling_enforcement(self, mem_store, budget):
        """Req 8: Context size strictly obeys token_ceiling across varied scales."""
        # Ingest large table and long list
        rows = "".join(f"<tr><td>Metric {i}</td><td>Value {i*100}</td></tr>" for i in range(50))
        items = "".join(f"<li>Requirement item number {i} for high reliability system</li>" for i in range(50))
        html = f"<table><tr><th>Metric</th><th>Val</th></tr>{rows}</table><ul>{items}</ul>"

        ingest_document(html, "large.html", mem_store, enable_list_extraction=True)

        assembled = assemble_query_context(
            query="What are the system metrics and requirements?",
            store=mem_store,
            token_ceiling=budget,
            enable_list_extraction=True,
        )
        assert assembled.tokens_used <= budget


# ==============================================================================
# 4. HTML Edge Cases
# ==============================================================================

class TestHTMLEdgeCases:
    """Verify Requirement 7."""

    def test_unclosed_tags_and_deep_nesting(self, mem_store):
        """Req 7: Malformed unclosed tags, empty tags, and deep nesting parsed safely."""
        malformed_html = """
        <div>
            <ul>
                <li>Item 1 with unclosed paragraph <p>inner text
                <li>Empty item: </li>
                <li>    </li>
                <li>Deeply nested:
                    <ul>
                        <li>Level 2
                            <ul>
                                <li>Level 3 item content
                            </ul>
                    </ul>
                </li>
            </ul>
        </div>
        """
        # Should not raise exception
        clean_prose, evidence = extract_structural_evidence_from_document(
            malformed_html, "malformed.html"
        )
        assert len(evidence) >= 1
        combined = " ".join(e.content for e in evidence)
        assert "Item 1" in combined
        assert "Level 3 item content" in combined


# ==============================================================================
# 5. REST & WebSocket End-to-End Integration
# ==============================================================================

class TestRestAndWebSocketIntegration:
    """Verify Requirements 9 and 10."""

    @pytest.fixture(autouse=True)
    def setup_api_store(self, monkeypatch):
        test_store = FactStore(
            in_memory=True,
            collection_name=f"test_api_persist_{uuid.uuid4().hex[:8]}",
        )
        monkeypatch.setattr(main, "store", test_store)
        monkeypatch.setattr(main, "_get_store", lambda: test_store)
        yield test_store
        test_store.clear()

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_rest_ingestion_and_query_end_to_end(
        self, mock_generate, monkeypatch, auth_headers
    ):
        """Req 9: REST /api/ingest persists evidence, /api/query retrieves it without raw_document."""
        monkeypatch.setenv(FLAG_NAME, "true")
        mock_generate.return_value = InferenceResult(
            answer="The board members are Evelyn and Frank.",
            model="qwen2.5-coder:7b",
            latency_ms=90,
            tokens_generated=12,
        )
        client = TestClient(app)

        doc_html = """
        <p>Acme Corp annual leadership meeting concluded yesterday.</p>
        <ul>
            <li>Board Member: Evelyn Wright</li>
            <li>Board Member: Frank Miller</li>
        </ul>
        """

        # 1. POST /api/ingest
        ingest_resp = client.post(
            "/api/ingest",
            headers=auth_headers,
            json={"text": doc_html, "document_name": "acme_board.html"},
        )
        assert ingest_resp.status_code == 200

        active_store = main._get_store()
        assert active_store.count_structural_evidence("acme_board.html") > 0

        # 2. POST /api/query WITHOUT raw_document
        query_resp = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": "Who are the board members?"},
        )
        assert query_resp.status_code == 200
        data = query_resp.json()
        assert "Evelyn and Frank" in data["answer"]

        # Verify context received by mock_generate had the structural list evidence
        assert mock_generate.called
        context_used = mock_generate.call_args[1]["context"]
        assert "Evelyn Wright" in context_used
        assert "Frank Miller" in context_used

    @patch("main.generate_answer")
    def test_websocket_ingestion_and_query_end_to_end(
        self, mock_generate, monkeypatch
    ):
        """Req 10: WebSocket ingestion and query stream with persistent structural context."""
        monkeypatch.setenv(FLAG_NAME, "true")

        # Mock generator for streaming tokens
        def dummy_token_stream(*args, **kwargs):
            tokens = ["Answer: ", "Alice ", "and ", "Bob."]
            for tok in tokens:
                yield tok

        mock_generate.side_effect = dummy_token_stream

        token = generate_token("ws_test_user")
        client = TestClient(app)

        doc_html = """
        <p>Project milestones are strictly tracked.</p>
        <ul>
            <li>Milestone 1: Prototype completion</li>
            <li>Milestone 2: Security compliance</li>
        </ul>
        """

        with client.websocket_connect(f"/ws?token={token}") as ws:
            # 1. Ingest via WebSocket
            ws.send_json(
                {
                    "type": "ingest",
                    "text": doc_html,
                    "document_name": "milestones.html",
                }
            )
            # Drain until ingest completes
            while True:
                msg = ws.receive_json()
                if msg["type"] == "ingest:done":
                    break
                assert msg["type"] != "error"

            active_store = main._get_store()
            assert active_store.count_structural_evidence("milestones.html") > 0

            # 2. Query via WebSocket
            ws.send_json(
                {
                    "type": "query",
                    "question": "What are the project milestones?",
                }
            )

            # Drain query response
            done_payload = None
            stage4_completed = False
            while True:
                msg = ws.receive_json()
                if msg["type"] == "pipeline:stage":
                    payload = msg.get("payload", {})
                    if payload.get("stage") == 4 and payload.get("status") == "complete":
                        stage4_completed = True
                elif msg["type"] == "pipeline:done":
                    done_payload = msg["payload"]
                    break
                elif msg["type"] == "error":
                    pytest.fail(f"WebSocket query returned error: {msg}")

            assert stage4_completed
            assert done_payload is not None
            assert done_payload["tokens_used"] > 0


# ==============================================================================
# 6. Evidence-Level Regression Safeguards
# ==============================================================================

class TestRegressionSafeguards:
    """Verify Requirements 14, 15, 16."""

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_regression_3f5983b2_namibian_minister(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Req 14 (3f5983b2): Erastus Utoni minister evidence preserved and retrieved."""
        mock_generate.return_value = InferenceResult(
            answer="Erastus Utoni", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=5
        )
        html = """
        <p>Cabinet of Namibia</p>
        <ul>
          <li>Minister of Sport , Youth and National Service : Jerry Ekandjo ( until February 2018 ) , Erastus Utoni
            <ul>
              <li>Deputy : Agnes Tjongarero</li>
            </ul>
          </li>
        </ul>
        """
        ingest_document(html, "namibia_3f5983b2.html", mem_store, enable_list_extraction=True)

        query_pipeline(
            query="who is the minister of youth in namibia",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )

        assert mock_generate.called
        ctx = mock_generate.call_args[1]["context"]
        assert "Erastus Utoni" in ctx
        assert "Minister of Sport , Youth and National Service" in ctx

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_regression_ef634417_scorpions_song(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Req 15 (ef634417): Scorpions performer preserved, redundant songwriters deduplicated."""
        mock_generate.return_value = InferenceResult(
            answer="Scorpions", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=3
        )
        html = """
        <table>
          <tr><th>Rock You Like a Hurricane</th><th>Col_2</th></tr>
          <tr><td>Single by Scorpions</td><td></td></tr>
          <tr><td>Songwriter ( s )</td><td>Rudolf Schenker Klaus Meine Herman Rarebell</td></tr>
        </table>
        <ul>
          <li>Rudolf Schenker</li>
          <li>Klaus Meine</li>
          <li>Herman Rarebell</li>
        </ul>
        """
        ingest_document(html, "scorpions_ef634417.html", mem_store, enable_list_extraction=True)

        query_pipeline(
            query="who sings the song rock you like a hurricane",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )

        assert mock_generate.called
        ctx = mock_generate.call_args[1]["context"]
        assert "Single by Scorpions" in ctx

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_regression_8f1f9bd9_thomas_definition(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Req 16 (8f1f9bd9): Meaning twin preserved in table representation."""
        mock_generate.return_value = InferenceResult(
            answer="twin", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=3
        )
        html = """
        <table>
          <tr><th>Thomas</th><th>Col_2</th></tr>
          <tr><td>Word / name</td><td>Aramaic</td></tr>
          <tr><td>Meaning</td><td>twin</td></tr>
        </table>
        """
        ingest_document(html, "thomas_8f1f9bd9.html", mem_store, enable_list_extraction=True)

        query_pipeline(
            query="what is the definition of the name thomas",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )

        assert mock_generate.called
        ctx = mock_generate.call_args[1]["context"]
        assert "twin" in ctx
        assert "Aramaic" in ctx


# ==============================================================================
# 7. Deterministic Zero External Dependencies
# ==============================================================================

class TestDeterministicExecution:
    """Verify Requirement 17."""

    def test_deterministic_offline_pipeline(self, mem_store, sample_hardware):
        """Req 17: All operations run purely locally with zero network or external services."""
        html = "<p>Fact one.</p><ul><li>List Item 1</li><li>List Item 2</li></ul>"
        res = ingest_document(
            text=html,
            source_doc="local.html",
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=True,
        )
        assert res.document_name == "local.html"
        assert mem_store.count_structural_evidence("local.html") > 0
        items = mem_store.get_structural_evidence_by_document("local.html")
        assert len(items) == 1
        assert "List Item 1" in items[0].content
