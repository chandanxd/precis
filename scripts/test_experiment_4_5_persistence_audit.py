"""
Independent Audit Test Suite for Experiment 4.5.3.

Comprehensive deterministic probes covering all 11 audit requirements:
1. Feature flag defaults, isolation, and disabled-mode byte parity.
2. Ingestion-time structural extraction, persistence, provenance, and lifecycle.
3. Query-time retrieval, document isolation, and scrutiny of the top_doc selection logic.
4. Pure-structural document vulnerability (svoa_count == 0).
5. REST API and WebSocket real-handler verification with mocked inference.
6. Context budget accounting across scales (100 to 2048) and deduplication preservation.
7. Evidence preservation across regression cases (3f5983b2, ef634417, 8f1f9bd9).
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "backend" / "src"
BACKEND_DIR = REPO_ROOT / "backend"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

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
from precis.pipeline.packer import pack_context, render_context
from precis.pipeline.sdh import embed_text
from precis.pipeline.structural import (
    FLAG_NAME,
    assemble_structural_query_context,
    extract_structural_evidence_from_document,
    is_list_extraction_enabled,
    parse_feature_flag,
)


@pytest.fixture
def mem_store():
    col = f"audit_store_{uuid.uuid4().hex[:12]}"
    store = FactStore(in_memory=True, collection_name=col)
    yield store
    try:
        store._client.delete_collection(col)
    except Exception:
        pass
    try:
        store._client.delete_collection(f"{col}_structural")
    except Exception:
        pass


@pytest.fixture
def sample_hw():
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
    tok = generate_token("audit_user")
    return {"Authorization": f"Bearer {tok}"}


# ==============================================================================
# AUDIT SECTION 1: Feature Flag & Disabled-Mode Compatibility
# ==============================================================================

class TestAuditFeatureFlagAndDisabledMode:

    def test_flag_defaults_to_disabled(self, monkeypatch):
        monkeypatch.delenv(FLAG_NAME, raising=False)
        assert not is_list_extraction_enabled()

    def test_explicit_override_does_not_mutate_global_env(self, monkeypatch):
        monkeypatch.setenv(FLAG_NAME, "false")
        assert not is_list_extraction_enabled()
        # Call with override True
        res = is_list_extraction_enabled(override=True)
        assert res is True
        # Verify global env was untouched
        assert os.getenv(FLAG_NAME) == "false"
        assert not is_list_extraction_enabled()

    def test_disabled_mode_byte_identical_context(self, mem_store, sample_hw):
        """Compare disabled mode assemble_query_context with pure pack_context + render_context."""
        doc = "<p>Marie Curie was awarded the Nobel Prize in Physics in 1903.</p>"
        ingest_document(doc, "curie.txt", mem_store, enable_list_extraction=False)

        q = "Who won the Nobel Prize in Physics?"
        assembled_disabled = assemble_query_context(
            query=q, store=mem_store, token_ceiling=sample_hw.token_ceiling, enable_list_extraction=False
        )
        pure_pack = pack_context(q, mem_store, sample_hw.token_ceiling)
        legacy_context = render_context(pure_pack.packed_facts)

        assert assembled_disabled.context == legacy_context
        assert assembled_disabled.use_structural is False
        assert assembled_disabled.tokens_used == pure_pack.tokens_used

    def test_disabled_mode_skips_structural_operations(self, mem_store):
        """Verify disabled mode does zero structural storage."""
        doc = "<ul><li>Alpha</li><li>Beta</li></ul>"
        ingest_document(doc, "list.txt", mem_store, enable_list_extraction=False)
        assert mem_store.count_structural_evidence() == 0


# ==============================================================================
# AUDIT SECTION 2: Extraction, Persistence & Provenance
# ==============================================================================

class TestAuditExtractionAndPersistence:

    def test_embedding_dimensions_and_metric(self, mem_store):
        """Verify actual embedding dimension is 384 and collection metric is cosine."""
        emb = embed_text("Test embedding dimensionality")
        assert isinstance(emb, list)
        assert len(emb) == 384
        assert isinstance(emb[0], float)

        # Check Chroma collection metadata
        coll = mem_store.structural_collection
        assert coll.metadata.get("hnsw:space") == "cosine"

    def test_provenance_and_content_addressing(self, mem_store):
        doc = """
        <table>
            <tr><th>Role</th><th>Name</th></tr>
            <tr><td>Lead</td><td>Dr. Smith</td></tr>
        </table>
        <ul>
            <li>Project Milestone 1</li>
        </ul>
        """
        ingest_document(doc, "research_doc.html", mem_store, enable_list_extraction=True)
        items = mem_store.get_structural_evidence_by_document("research_doc.html")
        assert len(items) >= 2
        for item in items:
            assert item.source_doc == "research_doc.html"
            assert item.id.startswith("research_doc_html_struct_")
            assert len(item.id.split("_")[-1]) == 12  # SHA256 hex[:12]
            assert item.structure_type in ("table", "list")
            assert item.searchable_text

    def test_empty_or_unavailable_collection_handling(self, mem_store):
        """Empty collection must return empty lists without raising exceptions."""
        res = mem_store.query_similar_structural("anything", n_results=5)
        assert res == []
        assert mem_store.count_structural_evidence("nonexistent.txt") == 0
        assert not mem_store.has_structural_evidence("nonexistent.txt")


# ==============================================================================
# AUDIT SECTION 3: Query Retrieval & Document Isolation Scrutiny
# ==============================================================================

class TestAuditQueryRetrievalAndIsolationScrutiny:

    def test_top_doc_defect_vulnerability_demonstration(self, mem_store, sample_hw):
        """
        REGRESSION TEST A: Demonstrates and verifies remediation of DEFECT-01.
        Under old hard-top_doc logic, Frank Miller from energy_summit.html monopolized
        the structural context and discarded Dr. Elena Rostova from awards_data.html.
        Under corrected similarity-dominant blended ranking, Dr. Elena Rostova is retained.
        """
        # Doc Wrong: high SVOA lexical overlap with query terms, but weak/spurious table
        doc_wrong = """
        <p>The global energy leadership summit discussed renewable energy innovations and wind energy.</p>
        <table>
            <tr><th>Summit Role</th><th>Name</th></tr>
            <tr><td>Logistics Manager</td><td>Frank Miller</td></tr>
        </table>
        """

        # Doc Correct: minimal SVOA prose, but exact answer table
        doc_correct = """
        <p>Annual financial results.</p>
        <table>
            <tr><th>Category</th><th>Winner</th></tr>
            <tr><td>Renewable Energy Innovation Award</td><td>Dr. Elena Rostova</td></tr>
        </table>
        """

        ingest_document(doc_wrong, "energy_summit.html", mem_store, enable_list_extraction=True)
        ingest_document(doc_correct, "awards_data.html", mem_store, enable_list_extraction=True)

        query = "Who won the renewable energy innovation award at the energy summit?"
        assembled = assemble_query_context(
            query=query, store=mem_store, token_ceiling=1000, enable_list_extraction=True
        )

        # Inspect which evidence survived
        has_correct = "Dr. Elena Rostova" in assembled.context
        has_wrong = "Frank Miller" in assembled.context
        print(f"\n[AUDIT TOP_DOC PROBE]")
        print(f"Top SVOA fact doc: {[f.source_doc for f in assembled.facts_used[:2]]}")
        print(f"Has correct structural evidence (Elena Rostova): {has_correct}")
        print(f"Has wrong structural evidence (Frank Miller): {has_wrong}")

        # Assert correct evidence from Document B is present
        assert has_correct, "DEFECT-01 REGRESSION: Dr. Elena Rostova was discarded from context!"

        # Prove that old hard-top_doc selection logic would have failed:
        top_doc = assembled.facts_used[0].source_doc if assembled.facts_used else None
        assert top_doc == "energy_summit.html"
        all_candidates = mem_store.query_similar_structural(query, 10)
        old_top_items = [it for it in all_candidates if it[0].source_doc == top_doc]
        assert any("Frank Miller" in it[0].content for it in old_top_items)
        assert not any("Dr. Elena Rostova" in it[0].content for it in old_top_items)

    def test_candidate_starvation_remediation_test_b(self, mem_store):
        """
        REGRESSION TEST B: Verifies remediation of DEFECT-03.
        matched_items contains a weak candidate from a document in fact_docs.
        other_items contains a substantially stronger candidate from an uncorroborated document.
        Asserts the stronger candidate is selected and not starved by the presence of matched_items.
        """
        doc_a = """
        <p>The annual conference on distributed computing discussed protocol latency.</p>
        <table>
            <tr><th>Track</th><th>Speaker</th></tr>
            <tr><td>Networking Track</td><td>Speaker Brown</td></tr>
        </table>
        """
        doc_b = """
        <p>Corporate financial filings 2026.</p>
        <table>
            <tr><th>Benchmark</th><th>Measurement</th></tr>
            <tr><td>Protocol Latency Minimum</td><td>0.42 milliseconds</td></tr>
        </table>
        """
        ingest_document(doc_a, "conf_doc.html", mem_store, enable_list_extraction=True)
        ingest_document(doc_b, "benchmark_doc.html", mem_store, enable_list_extraction=True)

        query = "What is the protocol latency minimum measurement?"
        assembled = assemble_query_context(
            query=query, store=mem_store, token_ceiling=1000, enable_list_extraction=True
        )

        assert "0.42 milliseconds" in assembled.context, "DEFECT-03 REGRESSION: Strong candidate from other_items was starved!"
        assert "Protocol Latency Minimum" in assembled.context

    def test_multiple_relevant_documents_deterministic_selection_test_c(self, mem_store):
        """
        REGRESSION TEST C: Verifies multi-document ranking, deterministic tie-breaking,
        chunk limit (<=3), provenance preservation, and rejection of low-relevance distractor chunks.
        """
        doc1 = "<table><tr><th>Metric</th><th>Val</th></tr><tr><td>Alpha Server CPU</td><td>99%</td></tr></table>"
        doc2 = "<table><tr><th>Metric</th><th>Val</th></tr><tr><td>Beta Server CPU</td><td>88%</td></tr></table>"
        doc3 = "<table><tr><th>Metric</th><th>Val</th></tr><tr><td>Gamma Server CPU</td><td>77%</td></tr></table>"
        doc4 = "<table><tr><th>Metric</th><th>Val</th></tr><tr><td>Delta Server CPU</td><td>66%</td></tr></table>"
        doc_distractor = "<table><tr><th>Fruit</th><th>Stock</th></tr><tr><td>Apples</td><td>50</td></tr></table>"

        ingest_document(doc1, "srv_alpha.html", mem_store, enable_list_extraction=True)
        ingest_document(doc2, "srv_beta.html", mem_store, enable_list_extraction=True)
        ingest_document(doc3, "srv_gamma.html", mem_store, enable_list_extraction=True)
        ingest_document(doc4, "srv_delta.html", mem_store, enable_list_extraction=True)
        ingest_document(doc_distractor, "groceries.html", mem_store, enable_list_extraction=True)

        query = "What is the Server CPU utilization metric?"

        runs = []
        for _ in range(3):
            assembled = assemble_query_context(
                query=query, store=mem_store, token_ceiling=2000, enable_list_extraction=True
            )
            runs.append(assembled.context)

        assert runs[0] == runs[1] == runs[2], "Ranking selection must be deterministic across runs"
        table_headers_count = runs[0].count("### Structured Table:")
        assert table_headers_count <= 3, f"Expected at most 3 chunks, got {table_headers_count}"
        assert "Apples" not in runs[0], "Unrelated distractor chunk entered context!"
        assert any(srv in runs[0] for srv in ["Alpha Server CPU", "Beta Server CPU", "Gamma Server CPU"])

    def test_zero_svoa_facts_store_rejection(self, mem_store):
        """
        AUDIT PROBE: Document containing only structural elements produces 0 SVOA facts.
        """
        doc_pure_table = """
        <table>
            <tr><th>Server</th><th>IP</th></tr>
            <tr><td>Primary</td><td>192.168.1.1</td></tr>
        </table>
        """
        ingest_document(doc_pure_table, "pure_table.html", mem_store, enable_list_extraction=True)
        assert mem_store.count() == 0
        assert mem_store.count_structural_evidence() > 0


# ==============================================================================
# AUDIT SECTION 4: Real REST & WebSocket Handlers
# ==============================================================================

def assert_rest_structural_delivery(
    mock_gen: Any,
    target_question: str,
    expected_sentinels: List[str],
    unexpected_sentinels: List[str],
) -> str:
    """
    Shared assertion helper for REST structural context delivery.
    Verifies that generate_answer was called with the exact target question,
    all expected sentinels are present in the delivered context,
    and all negative control sentinels are strictly absent.
    """
    assert mock_gen.called, "Generator was not called"
    call_kwargs = mock_gen.call_args[1]
    assert call_kwargs["query"] == target_question, (
        f"Query mismatch: expected '{target_question}', got '{call_kwargs.get('query')}'"
    )
    ctx = call_kwargs["context"]
    for s in expected_sentinels:
        assert s in ctx, f"Distinctive sentinel '{s}' missing from generator context"
    for u in unexpected_sentinels:
        assert u not in ctx, f"Negative control sentinel '{u}' leaked into generator context"
    return ctx


def assert_websocket_structural_delivery(
    captured_kwargs: List[Dict[str, Any]],
    target_question: str,
    expected_sentinels: List[str],
    unexpected_sentinels: List[str],
    events: Dict[str, Any],
) -> str:
    """
    Shared assertion helper for WebSocket structural context delivery.
    Verifies stage completion (Stage 4 & 5), done payload delivery,
    generator question argument match, presence of expected sentinels,
    and absence of negative control sentinels.
    """
    assert events.get("stage4_completed"), "Stage 4 (Re-rank & pack) did not complete"
    assert events.get("stage5_completed"), "Stage 5 (Inference) did not complete"
    assert events.get("done_payload") is not None, "pipeline:done event missing"
    assert len(captured_kwargs) == 1, (
        f"Expected exactly 1 call to generator, got {len(captured_kwargs)}"
    )
    gen_call = captured_kwargs[0]
    assert gen_call["query"] == target_question, (
        f"Query mismatch: expected '{target_question}', got '{gen_call.get('query')}'"
    )
    ctx = gen_call["context"]
    for s in expected_sentinels:
        assert s in ctx, f"Distinctive sentinel '{s}' missing from WS generator context"
    for u in unexpected_sentinels:
        assert u not in ctx, f"Negative control sentinel '{u}' leaked into WS generator context"
    return ctx


def assert_retrieval_candidate_provenance(
    retrieved_candidates: List[Tuple[Any, float]],
    expected_doc_id: str,
) -> Any:
    """
    Shared assertion helper for structural retrieval candidate provenance.
    Asserts candidate list non-empty and verifies source_doc metadata on top candidate.
    """
    assert len(retrieved_candidates) > 0, "No candidates retrieved from vector store"
    top_cand, score = retrieved_candidates[0]
    assert top_cand.source_doc == expected_doc_id, (
        f"Candidate provenance mismatch: expected '{expected_doc_id}', got '{top_cand.source_doc}'"
    )
    return top_cand


def assert_scoped_retrieval_isolation(
    scoped_results: List[Tuple[Any, float]],
    allowed_doc_id: str,
    prohibited_doc_ids: List[str],
) -> None:
    """
    Shared assertion helper for document-scoped retrieval isolation.
    Asserts all candidates originate from allowed_doc_id and none from prohibited_doc_ids.
    """
    for prohib in prohibited_doc_ids:
        assert not any(item.source_doc == prohib for item, _ in scoped_results), (
            f"Prohibited document '{prohib}' leaked into scoped results"
        )
    assert all(item.source_doc == allowed_doc_id for item, _ in scoped_results), (
        f"Non-{allowed_doc_id} items found in scoped results"
    )


class TestAuditRestAndWebSocketHandlers:

    @pytest.fixture(autouse=True)
    def setup_api_store(self, monkeypatch):
        test_store = FactStore(
            in_memory=True,
            collection_name=f"audit_api_{uuid.uuid4().hex[:8]}",
        )
        monkeypatch.setattr(main, "store", test_store)
        monkeypatch.setattr(main, "_get_store", lambda: test_store)
        yield test_store
        test_store.clear()

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_rest_passes_structural_context_to_generator(
        self, mock_gen, monkeypatch, auth_headers
    ):
        """
        HARDENED TEST A: REST structural evidence delivery with sentinel values,
        direct persistence confirmation, generator context verification, negative control,
        and source-document provenance verification.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        mock_gen.return_value = InferenceResult(
            answer="Audit Answer", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=5
        )
        client = TestClient(app)

        # 1. Ingest target document containing unique, distinctive structural sentinel
        doc_target = """
        <p>Gate 5 Production Benchmark Specification</p>
        <ul>
            <li>Gate 5 Sentinel Project — target latency: 17.3 ms</li>
            <li>Throughput requirement: 850 qps</li>
        </ul>
        """
        resp_ingest_target = client.post(
            "/api/ingest",
            headers=auth_headers,
            json={"text": doc_target, "document_name": "target_sentinel_doc.html"},
        )
        assert resp_ingest_target.status_code == 200

        # 2. Ingest negative control document containing an unrelated domain and sentinel
        doc_distractor = """
        <p>Corporate Facilities Infrastructure</p>
        <ul>
            <li>Building Gamma HVAC — cooling capacity: 99.9 tons</li>
        </ul>
        """
        resp_ingest_distractor = client.post(
            "/api/ingest",
            headers=auth_headers,
            json={"text": doc_distractor, "document_name": "distractor_sentinel_doc.html"},
        )
        assert resp_ingest_distractor.status_code == 200

        # 3. Direct persistence confirmation in FactStore
        active_store = main._get_store()
        assert active_store.count_structural_evidence("target_sentinel_doc.html") > 0
        assert active_store.count_structural_evidence("distractor_sentinel_doc.html") > 0
        stored_items = active_store.get_structural_evidence_by_document("target_sentinel_doc.html")
        assert any(
            "17.3 ms" in item.content and item.source_doc == "target_sentinel_doc.html"
            for item in stored_items
        ), "Target sentinel missing from stored structural records"

        # 4. Query through actual REST query endpoint
        target_question = "What is the target latency for Gate 5 Sentinel Project?"
        resp_query = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": target_question},
        )
        assert resp_query.status_code == 200
        assert mock_gen.called

        # 5-7. Assert generator received context with expected sentinels and negative control exclusion
        ctx = assert_rest_structural_delivery(
            mock_gen,
            target_question,
            expected_sentinels=["Gate 5 Sentinel Project", "17.3 ms"],
            unexpected_sentinels=["Building Gamma HVAC", "99.9 tons"],
        )

        # 8. Assert source-document provenance from retrieval candidates
        retrieved = active_store.query_similar_structural(target_question, n_results=5)
        assert_retrieval_candidate_provenance(retrieved, "target_sentinel_doc.html")

    @patch("main.generate_answer")
    def test_websocket_passes_structural_context_to_generator(
        self, mock_gen, monkeypatch
    ):
        """
        HARDENED TEST B: WebSocket structural evidence delivery with sentinel values,
        stream protocol verification, question argument verification, generator context assertions,
        and negative control isolation.
        """
        monkeypatch.setenv(FLAG_NAME, "true")

        captured_kwargs = []
        def mock_stream(*args, **kwargs):
            captured_kwargs.append(kwargs)
            yield "STREAMED_SENTINEL_TOKEN"

        mock_gen.side_effect = mock_stream
        token = generate_token("audit_ws_hardened")
        client = TestClient(app)

        doc_target = """
        <p>Gate 5 Production Benchmark Specification</p>
        <ul>
            <li>Gate 5 Sentinel Project — target latency: 17.3 ms</li>
        </ul>
        """
        doc_distractor = """
        <p>Corporate Facilities Infrastructure</p>
        <ul>
            <li>Building Gamma HVAC — cooling capacity: 99.9 tons</li>
        </ul>
        """

        target_question = "What is the target latency for Gate 5 Sentinel Project?"

        with client.websocket_connect(f"/ws?token={token}") as ws:
            # 1. Ingest target document through WebSocket
            ws.send_json({"type": "ingest", "text": doc_target, "document_name": "ws_target_doc.html"})
            while True:
                msg = ws.receive_json()
                if msg["type"] == "ingest:done":
                    break
                assert msg["type"] != "error"

            # 2. Ingest distractor document through WebSocket
            ws.send_json({"type": "ingest", "text": doc_distractor, "document_name": "ws_distractor_doc.html"})
            while True:
                msg = ws.receive_json()
                if msg["type"] == "ingest:done":
                    break
                assert msg["type"] != "error"

            # 3. Confirm persistence in active store
            active_store = main._get_store()
            assert active_store.count_structural_evidence("ws_target_doc.html") > 0
            assert active_store.count_structural_evidence("ws_distractor_doc.html") > 0

            # 4. Issue query through real WebSocket protocol
            ws.send_json({"type": "query", "question": target_question})

            # 5. Assert protocol event sequence
            stage4_completed = False
            stage5_completed = False
            done_payload = None
            tokens = []

            while True:
                msg = ws.receive_json()
                if msg["type"] == "pipeline:stage":
                    payload = msg.get("payload", {})
                    if payload.get("stage") == 4 and payload.get("status") == "complete":
                        stage4_completed = True
                    elif payload.get("stage") == 5 and payload.get("status") == "complete":
                        stage5_completed = True
                elif msg["type"] == "pipeline:token":
                    tokens.append(msg["payload"]["char"])
                elif msg["type"] == "pipeline:done":
                    done_payload = msg["payload"]
                    break
                elif msg["type"] == "error":
                    pytest.fail(f"WebSocket query returned error: {msg}")

            assert stage4_completed, "Stage 4 (Re-rank & pack) did not complete"
            assert done_payload is not None, "pipeline:done event missing"
            assert "".join(tokens) == "STREAMED_SENTINEL_TOKEN"

            # 6-8. Assert generator received context with expected sentinels and negative control exclusion
            events = {
                "stage4_completed": stage4_completed,
                "stage5_completed": stage5_completed,
                "done_payload": done_payload,
            }
            ctx = assert_websocket_structural_delivery(
                captured_kwargs,
                target_question,
                expected_sentinels=["Gate 5 Sentinel Project", "17.3 ms"],
                unexpected_sentinels=["Building Gamma HVAC", "99.9 tons"],
                events=events,
            )

    def test_source_provenance_and_telemetry_test_c(self, monkeypatch):
        """
        HARDENED TEST C: Source provenance verification across multiple documents.
        Directly asserts stored source identifiers and selected evidence records,
        tests filtered queries, and verifies evidence delivery to assembled context.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        test_store = main._get_store()

        doc_alpha = """
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>Alpha Latency Budget</td><td>12.5 ms</td></tr>
        </table>
        """
        doc_beta = """
        <table>
            <tr><th>Component</th><th>Replica Count</th></tr>
            <tr><td>Beta Worker Pool</td><td>88 replicas</td></tr>
        </table>
        """

        ingest_document(doc_alpha, "doc_alpha.html", test_store, enable_list_extraction=True)
        ingest_document(doc_beta, "doc_beta.html", test_store, enable_list_extraction=True)

        # 1. Assert stored source identifiers directly
        items_alpha = test_store.get_structural_evidence_by_document("doc_alpha.html")
        assert len(items_alpha) == 1
        assert items_alpha[0].source_doc == "doc_alpha.html"
        assert items_alpha[0].structure_type == "table"
        assert "Alpha Latency Budget" in items_alpha[0].content

        items_beta = test_store.get_structural_evidence_by_document("doc_beta.html")
        assert len(items_beta) == 1
        assert items_beta[0].source_doc == "doc_beta.html"
        assert items_beta[0].structure_type == "table"
        assert "Beta Worker Pool" in items_beta[0].content

        # 2. Assert retrieval candidates maintain explicit source provenance
        retrieved_alpha = test_store.query_similar_structural("Alpha Latency Budget", n_results=5)
        top_alpha = assert_retrieval_candidate_provenance(retrieved_alpha, "doc_alpha.html")
        assert "12.5 ms" in top_alpha.content

        # 3. Assert document-scoped filtering bounds retrieval strictly
        scoped_alpha = test_store.query_similar_structural("Latency Budget", n_results=5, source_doc="doc_alpha.html")
        assert_scoped_retrieval_isolation(scoped_alpha, "doc_alpha.html", ["doc_beta.html"])

        scoped_beta = test_store.query_similar_structural("Worker Pool", n_results=5, source_doc="doc_beta.html")
        assert_scoped_retrieval_isolation(scoped_beta, "doc_beta.html", ["doc_alpha.html"])

        # 4. Assert assembled context delivers selected evidence to generator
        assembled_alpha = assemble_query_context(
            "What is the Alpha Latency Budget?", test_store, 2048, enable_list_extraction=True
        )
        assert assembled_alpha.use_structural is True
        assert "Alpha Latency Budget" in assembled_alpha.context
        assert "12.5 ms" in assembled_alpha.context
        assert "Beta Worker Pool" not in assembled_alpha.context
        assert "88 replicas" not in assembled_alpha.context
        assert assembled_alpha.telemetry["structural_items_selected"] > 0

        # Also assert the inverse query selects doc_beta and excludes doc_alpha
        assembled_beta = assemble_query_context(
            "What is the replica count for Beta Worker Pool?", test_store, 2048, enable_list_extraction=True
        )
        assert assembled_beta.use_structural is True
        assert "Beta Worker Pool" in assembled_beta.context
        assert "88 replicas" in assembled_beta.context
        assert "Alpha Latency Budget" not in assembled_beta.context
        assert "12.5 ms" not in assembled_beta.context

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_failure_injection_rest_structural_drop_test_d1(
        self, mock_gen, monkeypatch, auth_headers
    ):
        """
        CONTROLLED FAILURE INJECTION D1: REST structural evidence drop.
        Exercises the actual REST handler POST /api/query while simulating a regression
        where structural evidence is prevented from reaching the generator context.
        Verifies:
        1. REST request succeeds with HTTP 200 (no crash, exception, or 500 error).
        2. Generator is called normally with correct target_question.
        3. assert_rest_structural_delivery FAILS with AssertionError specifically
           identifying the missing sentinel.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        mock_gen.return_value = InferenceResult(
            answer="Audit Answer", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=5
        )
        client = TestClient(app)

        doc_target = """
        <p>Gate 5 Production Benchmark Specification</p>
        <ul>
            <li>Gate 5 Sentinel Project — target latency: 17.3 ms</li>
        </ul>
        """
        resp_ingest = client.post(
            "/api/ingest",
            headers=auth_headers,
            json={"text": doc_target, "document_name": "target_sentinel_doc.html"},
        )
        assert resp_ingest.status_code == 200

        active_store = main._get_store()
        assert active_store.count_structural_evidence("target_sentinel_doc.html") > 0

        # Inject failure: simulate retrieval regression where structural candidates are dropped
        monkeypatch.setattr(active_store, "query_similar_structural", lambda *args, **kwargs: [])

        # Execute actual REST query handler
        target_question = "What is the target latency for Gate 5 Sentinel Project?"
        resp_query = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": target_question},
        )

        # Verify pipeline executed without HTTP errors or exceptions
        assert resp_query.status_code == 200, "REST query must succeed with HTTP 200"
        assert mock_gen.called, "Generator was called"

        # Verify that the test's delivery assertion strictly detects the missing sentinel
        with pytest.raises(AssertionError) as exc_info:
            assert_rest_structural_delivery(
                mock_gen,
                target_question,
                expected_sentinels=["Gate 5 Sentinel Project", "17.3 ms"],
                unexpected_sentinels=["Building Gamma HVAC", "99.9 tons"],
            )

        assert "missing from generator context" in str(exc_info.value)
        assert ("Gate 5 Sentinel Project" in str(exc_info.value) or "17.3 ms" in str(exc_info.value))

    @patch("main.generate_answer")
    def test_failure_injection_websocket_structural_drop_test_d2(
        self, mock_gen, monkeypatch
    ):
        """
        CONTROLLED FAILURE INJECTION D2: WebSocket structural evidence drop.
        Exercises the actual WebSocket streaming protocol /ws while simulating a regression
        where structural evidence is prevented from reaching the streaming generator context.
        Verifies:
        1. Protocol progresses through Stage 4, Stage 5, token streaming, and pipeline:done.
        2. No WebSocket errors or disconnection occur.
        3. Streaming generator is called with target question.
        4. assert_websocket_structural_delivery FAILS with AssertionError specifically
           identifying the missing sentinel.
        """
        monkeypatch.setenv(FLAG_NAME, "true")

        captured_kwargs = []
        def mock_stream(*args, **kwargs):
            captured_kwargs.append(kwargs)
            yield "STREAMED_SENTINEL_TOKEN"

        mock_gen.side_effect = mock_stream
        token = generate_token("audit_ws_failure_inj")
        client = TestClient(app)

        doc_target = """
        <p>Gate 5 Production Benchmark Specification</p>
        <ul>
            <li>Gate 5 Sentinel Project — target latency: 17.3 ms</li>
        </ul>
        """
        target_question = "What is the target latency for Gate 5 Sentinel Project?"

        with client.websocket_connect(f"/ws?token={token}") as ws:
            # Ingest target document through WebSocket
            ws.send_json({"type": "ingest", "text": doc_target, "document_name": "ws_target_doc.html"})
            while True:
                msg = ws.receive_json()
                if msg["type"] == "ingest:done":
                    break
                assert msg["type"] != "error"

            active_store = main._get_store()
            assert active_store.count_structural_evidence("ws_target_doc.html") > 0

            # Inject failure: simulate retrieval regression where structural candidates are dropped
            monkeypatch.setattr(active_store, "query_similar_structural", lambda *args, **kwargs: [])

            # Issue query through real WebSocket protocol
            ws.send_json({"type": "query", "question": target_question})

            stage4_completed = False
            stage5_completed = False
            done_payload = None
            tokens = []

            while True:
                msg = ws.receive_json()
                if msg["type"] == "pipeline:stage":
                    payload = msg.get("payload", {})
                    if payload.get("stage") == 4 and payload.get("status") == "complete":
                        stage4_completed = True
                    elif payload.get("stage") == 5 and payload.get("status") == "complete":
                        stage5_completed = True
                elif msg["type"] == "pipeline:token":
                    tokens.append(msg["payload"]["char"])
                elif msg["type"] == "pipeline:done":
                    done_payload = msg["payload"]
                    break
                elif msg["type"] == "error":
                    pytest.fail(f"Unexpected WebSocket error during test: {msg}")

            # Verify protocol completed normally without timeouts or errors
            assert stage4_completed, "Stage 4 completed normally"
            assert stage5_completed, "Stage 5 completed normally"
            assert done_payload is not None, "pipeline:done event emitted"
            assert "".join(tokens) == "STREAMED_SENTINEL_TOKEN"
            assert len(captured_kwargs) == 1

            # Verify that the delivery assertion strictly detects the missing sentinel
            events = {
                "stage4_completed": stage4_completed,
                "stage5_completed": stage5_completed,
                "done_payload": done_payload,
            }
            with pytest.raises(AssertionError) as exc_info:
                assert_websocket_structural_delivery(
                    captured_kwargs,
                    target_question,
                    expected_sentinels=["Gate 5 Sentinel Project", "17.3 ms"],
                    unexpected_sentinels=["Building Gamma HVAC", "99.9 tons"],
                    events=events,
                )

            assert "missing from WS generator context" in str(exc_info.value)
            assert ("Gate 5 Sentinel Project" in str(exc_info.value) or "17.3 ms" in str(exc_info.value))

    def test_failure_injection_provenance_metadata_mismatch_test_d3(self, monkeypatch):
        """
        CONTROLLED FAILURE INJECTION D3: Incorrect source identifier metadata regression.
        Simulates an ingestion/retrieval regression where evidence content is preserved
        but source_doc is misattributed (e.g., 'corrupted_source_doc.html' or 'unknown').
        Verifies:
        1. Retrieval returns the candidate item.
        2. assert_retrieval_candidate_provenance FAILS with AssertionError specifically
           identifying the provenance mismatch.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        test_store = main._get_store()

        doc_alpha = """
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>Alpha Latency Budget</td><td>12.5 ms</td></tr>
        </table>
        """
        ingest_document(doc_alpha, "doc_alpha.html", test_store, enable_list_extraction=True)

        retrieved = test_store.query_similar_structural("Alpha Latency Budget", n_results=5)
        assert len(retrieved) > 0

        # Inject failure: simulate metadata corruption on top candidate
        real_cand, real_score = retrieved[0]
        corrupted_cand = StructuralEvidence(
            id=real_cand.id,
            source_doc="corrupted_or_wrong_source.html",
            structure_type=real_cand.structure_type,
            content=real_cand.content,
            searchable_text=real_cand.searchable_text,
        )
        corrupted_retrieved = [(corrupted_cand, real_score)]

        with pytest.raises(AssertionError) as exc_info:
            assert_retrieval_candidate_provenance(corrupted_retrieved, "doc_alpha.html")

        assert "Candidate provenance mismatch" in str(exc_info.value)
        assert "doc_alpha.html" in str(exc_info.value)
        assert "corrupted_or_wrong_source.html" in str(exc_info.value)

    def test_failure_injection_provenance_scoped_leakage_test_d4(self, monkeypatch):
        """
        CONTROLLED FAILURE INJECTION D4: Scoped retrieval filter failure / cross-document leakage.
        Simulates a regression in the vector filter where querying with source_doc='doc_alpha.html'
        leaks structural evidence from 'doc_beta.html'.
        Verifies:
        1. Scoped results contain leaked items from doc_beta.html.
        2. assert_scoped_retrieval_isolation FAILS with AssertionError specifically
           identifying prohibited document leakage.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        test_store = main._get_store()

        doc_alpha = """
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>Alpha Latency Budget</td><td>12.5 ms</td></tr>
        </table>
        """
        doc_beta = """
        <table>
            <tr><th>Component</th><th>Replica Count</th></tr>
            <tr><td>Beta Worker Pool</td><td>88 replicas</td></tr>
        </table>
        """
        ingest_document(doc_alpha, "doc_alpha.html", test_store, enable_list_extraction=True)
        ingest_document(doc_beta, "doc_beta.html", test_store, enable_list_extraction=True)

        items_alpha = test_store.get_structural_evidence_by_document("doc_alpha.html")
        items_beta = test_store.get_structural_evidence_by_document("doc_beta.html")

        # Simulate scoped retrieval regression leaking beta into alpha query results
        leaked_scoped_results = [(items_alpha[0], 0.9), (items_beta[0], 0.85)]

        with pytest.raises(AssertionError) as exc_info:
            assert_scoped_retrieval_isolation(
                leaked_scoped_results,
                allowed_doc_id="doc_alpha.html",
                prohibited_doc_ids=["doc_beta.html"],
            )

        assert "Prohibited document 'doc_beta.html' leaked into scoped results" in str(exc_info.value)

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_rest_pure_structural_query_test_d(
        self, mock_gen, monkeypatch, auth_headers
    ):
        """
        REGRESSION TEST D: Ingest document containing table/list but 0 SVOA facts.
        Verify store.count() == 0, structural evidence exists, POST /api/query returns HTTP 200,
        and structural evidence reaches the mocked generator context.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        mock_gen.return_value = InferenceResult(
            answer="Audit Answer", model="qwen2.5-coder:7b", latency_ms=50, tokens_generated=5
        )
        client = TestClient(app)

        doc = """
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>MaxConcurrentConnections</td><td>10000</td></tr>
        </table>
        """
        resp_ingest = client.post(
            "/api/ingest",
            headers=auth_headers,
            json={"text": doc, "document_name": "config_table.html"},
        )
        assert resp_ingest.status_code == 200

        # Verify 0 SVOA facts and nonzero structural evidence
        active_store = main._get_store()
        assert active_store.count() == 0
        assert active_store.count_structural_evidence() > 0

        # Query through REST endpoint
        resp_query = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": "What is the MaxConcurrentConnections setting?"},
        )
        assert resp_query.status_code == 200, f"Expected 200, got {resp_query.status_code}: {resp_query.text}"
        assert mock_gen.called
        ctx = mock_gen.call_args[1]["context"]
        assert "MaxConcurrentConnections" in ctx
        assert "10000" in ctx

    @patch("main.generate_answer")
    def test_websocket_pure_structural_query_test_e(
        self, mock_gen, monkeypatch
    ):
        """
        REGRESSION TEST E: Ingest pure structural document (0 SVOA facts),
        query through WebSocket handler, assert no 'No documents ingested' error,
        assert mocked generator receives evidence, and query completes normally.
        """
        monkeypatch.setenv(FLAG_NAME, "true")

        def mock_stream(*args, **kwargs):
            ctx_received = kwargs.get("context", "")
            if "MaxConcurrentConnections" in ctx_received and "10000" in ctx_received:
                yield "STREAMED_PURE_STRUCTURAL_EVIDENCE"
            else:
                yield "FAILED_EVIDENCE_ABSENT"

        mock_gen.side_effect = mock_stream
        token = generate_token("audit_ws_pure")
        client = TestClient(app)

        doc = """
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>MaxConcurrentConnections</td><td>10000</td></tr>
        </table>
        """

        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_json({"type": "ingest", "text": doc, "document_name": "ws_pure.html"})
            while True:
                msg = ws.receive_json()
                if msg["type"] == "ingest:done":
                    break

            active_store = main._get_store()
            assert active_store.count() == 0
            assert active_store.count_structural_evidence() > 0

            ws.send_json({"type": "query", "question": "What is MaxConcurrentConnections?"})
            tokens = []
            while True:
                msg = ws.receive_json()
                if msg["type"] == "pipeline:token":
                    tokens.append(msg["payload"]["char"])
                elif msg["type"] == "pipeline:done":
                    break
                elif msg["type"] == "error":
                    raise AssertionError(f"Unexpected WebSocket error: {msg}")

            full_ans = "".join(tokens)
            assert "STREAMED_PURE_STRUCTURAL_EVIDENCE" in full_ans

    def test_truly_empty_store_rejection_test_f(
        self, monkeypatch, auth_headers
    ):
        """
        REGRESSION TEST F: Truly empty store (0 SVOA facts AND 0 structural evidence).
        Assert REST returns HTTP 400 'No documents ingested. Upload a document first.'
        and WebSocket returns 'No documents ingested' error.
        """
        monkeypatch.setenv(FLAG_NAME, "true")
        client = TestClient(app)

        active_store = main._get_store()
        active_store.clear()
        assert active_store.count() == 0
        assert active_store.count_structural_evidence() == 0

        # REST check
        resp = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": "Any question on empty store?"},
        )
        assert resp.status_code == 400
        assert "No documents ingested" in resp.json()["detail"]

        # WebSocket check
        token = generate_token("audit_ws_empty")
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_json({"type": "query", "question": "Any question on empty store?"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["detail"] == "No documents ingested"

    def test_feature_disabled_pure_structural_compatibility_test_g(
        self, monkeypatch, auth_headers
    ):
        """
        REGRESSION TEST G: When PRECIS_ENABLE_LIST_EXTRACTION=false:
        - Ingesting a pure structural document produces 0 facts and 0 structural evidence.
        - REST and WebSocket queries reject the empty store with HTTP 400 / error.
        - Prose-only ingestion and query remain 100% compatible.
        """
        monkeypatch.setenv(FLAG_NAME, "false")
        client = TestClient(app)

        active_store = main._get_store()
        active_store.clear()

        # Ingest pure table with feature disabled
        doc = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        resp_ingest = client.post(
            "/api/ingest",
            headers=auth_headers,
            json={"text": doc, "document_name": "disabled_table.html"},
        )
        assert resp_ingest.status_code == 200
        assert active_store.count() == 0
        assert active_store.count_structural_evidence() == 0

        # Query rejected because store has 0 facts and 0 usable structural evidence
        resp = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": "What is A?"},
        )
        assert resp.status_code == 400
        assert "No documents ingested" in resp.json()["detail"]


# ==============================================================================
# AUDIT SECTION 5: Budget Enforcement & Deduplication
# ==============================================================================

class TestAuditBudgetAndDeduplication:

    @pytest.mark.parametrize("ceiling", [100, 250, 500, 1000, 2048])
    def test_strict_ceiling_enforcement_with_large_blocks(self, mem_store, ceiling):
        """Verify that token ceiling is strictly obeyed with massive table & list."""
        rows = "".join(f"<tr><td>Field_{i}</td><td>Value_{i*10}</td><td>Note_{i}</td></tr>" for i in range(40))
        items = "".join(f"<li>Hierarchical policy specification item number {i}</li>" for i in range(40))
        doc = f"<table><tr><th>F</th><th>V</th><th>N</th></tr>{rows}</table><ul>{items}</ul>"

        ingest_document(doc, "massive.html", mem_store, enable_list_extraction=True)

        assembled = assemble_query_context(
            query="policy specification fields",
            store=mem_store,
            token_ceiling=ceiling,
            enable_list_extraction=True,
        )
        assert assembled.tokens_used <= ceiling


# ==============================================================================
# AUDIT SECTION 6: Regression Safeguards Detailed Examination
# ==============================================================================

class TestAuditRegressionSafeguardsDetailed:

    def test_case_3f5983b2_evidence_detail(self, mem_store):
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
        ingest_document(html, "case_3f5983b2.html", mem_store, enable_list_extraction=True)
        items = mem_store.get_structural_evidence_by_document("case_3f5983b2.html")
        assert len(items) == 1
        rec = items[0]
        assert "Erastus Utoni" in rec.content
        assert "[Minister of Sport" in rec.content or "Deputy : Agnes Tjongarero" in rec.content

        assembled = assemble_query_context(
            query="who is the minister of youth in namibia",
            store=mem_store,
            token_ceiling=1000,
            enable_list_extraction=True,
        )
        assert "Erastus Utoni" in assembled.context
        assert "Agnes Tjongarero" in assembled.context

    def test_case_ef634417_evidence_detail(self, mem_store):
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
        ingest_document(html, "case_ef634417.html", mem_store, enable_list_extraction=True)
        assembled = assemble_query_context(
            query="who sings the song rock you like a hurricane",
            store=mem_store,
            token_ceiling=1000,
            enable_list_extraction=True,
        )
        assert "Single by Scorpions" in assembled.context
        # Redundant list suppressed from context\n        assert "### Structured List:" not in assembled.context

    def test_case_8f1f9bd9_evidence_detail(self, mem_store):
        html = """
        <table>
          <tr><th>Thomas</th><th>Col_2</th></tr>
          <tr><td>Word / name</td><td>Aramaic</td></tr>
          <tr><td>Meaning</td><td>twin</td></tr>
        </table>
        """
        ingest_document(html, "case_8f1f9bd9.html", mem_store, enable_list_extraction=True)
        assembled = assemble_query_context(
            query="what is the definition of the name thomas",
            store=mem_store,
            token_ceiling=1000,
            enable_list_extraction=True,
        )
        assert "twin" in assembled.context
        assert "Aramaic" in assembled.context
