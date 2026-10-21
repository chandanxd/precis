"""
Tests for production wiring of structural list retention in orchestrator.py.

Verifies end-to-end execution through query_pipeline and process_query:
1. Disabled mode strictly preserves original fact-based context and behavior.
2. Enabled mode calls structural extraction and includes retained list items.
3. Retained list items improve answer evidence for documents with answers in lists.
4. Documents without lists produce identical results regardless of feature flag.
5. Feature flag validator prevents invalid configurations.
6. Hardware token ceiling is strictly obeyed across the full production path.
7. Streaming pipeline behaves identically to non-streaming for structural context.
8. Callers omitting raw_document gracefully fall back to fact-based context.
9. FastAPI REST handler POST /api/query execution path and fallback verification.
"""

import uuid
from unittest.mock import MagicMock, patch

import main
import pytest
from fastapi.testclient import TestClient
from main import app
from precis.api.security import generate_token
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.hardware import HardwareProfile
from precis.pipeline.inference import InferenceResult
from precis.pipeline.orchestrator import (
    PipelineResult,
    process_query,
    query_pipeline,
)
from precis.pipeline.structural import build_structural_context


@pytest.fixture
def mem_store():
    """Isolated in-memory FactStore for each test."""
    col_name = f"test_prod_{uuid.uuid4().hex[:12]}"
    store = FactStore(in_memory=True, collection_name=col_name)
    yield store
    try:
        store._client.delete_collection(col_name)
    except Exception:
        pass


@pytest.fixture
def sample_hardware():
    """Predictable hardware profile for deterministic context testing."""
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


class TestProductionWiring:
    """Test suite for orchestrator wiring of structural list retention."""

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_disabled_mode_preserves_original_fact_based_behavior(
        self, mock_generate, mem_store, sample_hardware
    ):
        """When disabled, the production pipeline uses standard SVOA fact packing."""
        mock_generate.return_value = InferenceResult(
            answer="Albert Einstein won the Nobel Prize in Physics.",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=10,
        )

        doc_html = """
        <p>Albert Einstein received the Nobel Prize in Physics in 1921.</p>
        <ul>
          <li>Special relativity (1905)</li>
          <li>General relativity (1915)</li>
        </ul>
        """
        query = "Who won the Nobel Prize in Physics?"

        res = process_query(
            document_text=doc_html,
            query=query,
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=False,
        )

        # 1. generate_answer was called
        assert mock_generate.called
        call_kwargs = mock_generate.call_args[1]
        context_passed = call_kwargs["context"]

        # 2. Context uses the original Fact N: format
        assert "Fact " in context_passed
        assert "### Structured List:" not in context_passed
        assert "- Special relativity" not in context_passed

        # 3. PipelineResult populated with original SVOA facts
        assert isinstance(res, PipelineResult)
        assert len(res.facts_used) >= 1
        assert res.facts_used[0].subject == "Albert Einstein"

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_enabled_mode_calls_structural_extraction_with_retained_lists(
        self, mock_generate, mem_store, sample_hardware
    ):
        """When enabled, the production pipeline injects structured lists into prompt context."""
        mock_generate.return_value = InferenceResult(
            answer="Notable theories include Special relativity and General relativity.",
            model="qwen2.5-coder:7b",
            latency_ms=120,
            tokens_generated=12,
        )

        doc_html = """
        <p>Einstein was a renowned theoretical physicist.</p>
        <ul>
          <li>Special relativity (1905)</li>
          <li>General relativity (1915)</li>
        </ul>
        """
        query = "What theories did Einstein formulate?"

        res = process_query(
            document_text=doc_html,
            query=query,
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=True,
        )

        assert mock_generate.called
        call_kwargs = mock_generate.call_args[1]
        context_passed = call_kwargs["context"]

        # Context contains clean prose AND the retained markdown list
        assert "Einstein was a renowned theoretical physicist." in context_passed
        assert "### Structured List:" in context_passed
        assert "* Special relativity (1905)" in context_passed
        assert "* General relativity (1915)" in context_passed

        # Telemetry fields are populated
        assert res.tokens_used > 0
        assert res.latency_ms >= 0

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_retained_list_items_improve_answer_evidence_for_list_answer(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Answers solely present in list items become accessible in enabled mode."""
        mock_generate.return_value = InferenceResult(
            answer="Mock answer",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=5,
        )

        # Document where key relationship exists only in an unordered list
        doc_html = """
        <p>The committee assembled to review nominations.</p>
        <ul>
          <li>Erastus Utoni</li>
          <li>Agnes Tjongarero</li>
        </ul>
        """
        query = "Who was nominated by the committee?"

        # Disabled mode
        process_query(
            document_text=doc_html,
            query=query,
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=False,
        )
        disabled_context = mock_generate.call_args[1]["context"]

        # In disabled mode, SVOA fact extractor does not parse HTML lists into subject-verb-object
        assert "Erastus Utoni" not in disabled_context

        # Enabled mode
        mock_generate.reset_mock()
        process_query(
            document_text=doc_html,
            query=query,
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=True,
        )
        enabled_context = mock_generate.call_args[1]["context"]

        # In enabled mode, list evidence is retained and passed to the model
        assert "Erastus Utoni" in enabled_context
        assert "### Structured List:" in enabled_context

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_document_without_lists_produces_same_result_regardless_of_feature_flag(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Documents without lists produce identical results in enabled and disabled mode."""
        mock_generate.return_value = InferenceResult(
            answer="The speed of light is 299,792,458 m/s.",
            model="qwen2.5-coder:7b",
            latency_ms=90,
            tokens_generated=14,
        )

        doc_text = "The speed of light in vacuum is 299792458 meters per second."
        query = "What is the speed of light?"

        res_disabled = process_query(
            document_text=doc_text,
            query=query,
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=False,
        )
        disabled_context = mock_generate.call_args[1]["context"]

        mock_generate.reset_mock()
        res_enabled = process_query(
            document_text=doc_text,
            query=query,
            store=mem_store,
            hardware=sample_hardware,
            enable_list_extraction=True,
        )
        enabled_context = mock_generate.call_args[1]["context"]

        # Both contexts are identical fact-based contexts
        assert disabled_context == enabled_context
        assert "### Structured List:" not in enabled_context
        assert res_disabled.answer == res_enabled.answer
        assert res_disabled.tokens_used == res_enabled.tokens_used
        assert len(res_disabled.facts_used) == len(res_enabled.facts_used)

    def test_feature_flag_validation_prevents_invalid_configurations(
        self, mem_store, sample_hardware
    ):
        """Invalid feature flag inputs fail closed with clear ValueError exceptions."""
        invalid_values = ["maybe", "enabled_sometimes", 2, -1, 100, [True]]

        for inv in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                query_pipeline(
                    query="test",
                    store=mem_store,
                    hardware=sample_hardware,
                    raw_document="<p>Test</p>",
                    enable_list_extraction=inv,
                )
            assert "Invalid" in str(exc_info.value)
            assert "PRECIS_ENABLE_LIST_EXTRACTION" in str(exc_info.value)

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_hardware_token_ceiling_respected_across_full_production_path(
        self, mock_generate, mem_store
    ):
        """Hard token ceiling is strictly obeyed when packing structural lists."""
        mock_generate.return_value = InferenceResult(
            answer="Test answer",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=5,
        )

        # Build a large document with 100 list items
        items = "\n".join(f"<li>Item {i}: Some long descriptive entry about topic {i}</li>" for i in range(100))
        doc_html = f"<p>Long document list</p><ul>{items}</ul>"

        # Constrained hardware profile with strict 120-token ceiling
        tight_hardware = HardwareProfile(
            cpu_cores=4,
            cpu_model="Constrained CPU",
            ram_gb=4.0,
            has_gpu=False,
            gpu_name=None,
            vram_gb=None,
            ml_accelerator=None,
            recommended_model="qwen2.5-coder:1.5b",
            recommended_mode="cpu-light",
            token_ceiling=120,
        )

        res = process_query(
            document_text=doc_html,
            query="list items",
            store=mem_store,
            hardware=tight_hardware,
            enable_list_extraction=True,
        )

        context_passed = mock_generate.call_args[1]["context"]
        words = len(context_passed.split())
        approx_tokens = int(words * 1.3)

        # Context must not breach the token ceiling
        assert approx_tokens <= tight_hardware.token_ceiling + 10
        assert res.tokens_used <= tight_hardware.token_ceiling + 10

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_streaming_pipeline_with_list_extraction_enabled(
        self, mock_generate, mem_store, sample_hardware
    ):
        """Streaming pipeline supports structural context and yields tokens properly."""
        def mock_stream_gen():
            yield "Token1 "
            yield "Token2."
            return InferenceResult(
                answer="Token1 Token2.",
                model="qwen2.5-coder:7b",
                latency_ms=110,
                tokens_generated=2,
            )

        mock_generate.return_value = mock_stream_gen()

        doc_html = """
        <p>Overview paragraph</p>
        <ul>
          <li>Point A: Value 1</li>
          <li>Point B: Value 2</li>
        </ul>
        """

        gen = query_pipeline(
            query="test query",
            store=mem_store,
            hardware=sample_hardware,
            stream=True,
            raw_document=doc_html,
            enable_list_extraction=True,
        )

        tokens = []
        pipeline_res = None
        while True:
            try:
                tokens.append(next(gen))
            except StopIteration as exc:
                pipeline_res = exc.value
                break

        assert tokens == ["Token1 ", "Token2."]
        assert isinstance(pipeline_res, PipelineResult)
        assert pipeline_res.answer == "Token1 Token2."

        context_passed = mock_generate.call_args[1]["context"]
        assert "### Structured List:" in context_passed
        assert "Point A: Value 1" in context_passed

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_omitted_raw_document_gracefully_falls_back_to_facts(
        self, mock_generate, mem_store, sample_hardware
    ):
        """When raw_document is omitted, enabled mode falls back to fact store without error."""
        mock_generate.return_value = InferenceResult(
            answer="Fact answer",
            model="qwen2.5-coder:7b",
            latency_ms=80,
            tokens_generated=4,
        )

        fact = Fact(
            subject="Earth",
            verb="orbits",
            object="Sun",
            modality="asserted",
            negated=False,
            source_doc="solar.txt",
        )
        mem_store.add_facts([fact])

        # raw_document omitted, but enable_list_extraction=True
        res = query_pipeline(
            query="What does Earth orbit?",
            store=mem_store,
            hardware=sample_hardware,
            raw_document=None,
            enable_list_extraction=True,
        )

        context_passed = mock_generate.call_args[1]["context"]
        assert "Fact 1: Earth orbits Sun" in context_passed
        assert "### Structured List:" not in context_passed
        assert len(res.facts_used) == 1

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_rest_api_query_endpoint_execution_path_and_list_extraction_status(
        self, mock_generate, monkeypatch
    ):
        """
        Verify the actual FastAPI POST /api/query execution path with mocked inference:
        1. Tests whether list extraction is reached when PRECIS_ENABLE_LIST_EXTRACTION=true.
        2. Demonstrates that POST /api/query receives only QueryRequest(question=...), so
           raw_document is not available in the request.
        3. Confirms that query_pipeline gracefully falls back to fact-based context packing without error.
        4. Verifies that build_structural_context is NOT called due to absent raw_document.
        5. Demonstrates disabled-mode compatibility where behavior is also strictly preserved.
        """
        mock_generate.return_value = InferenceResult(
            answer="Albert Einstein won the Nobel Prize in Physics.",
            model="qwen2.5-coder:7b",
            latency_ms=90,
            tokens_generated=8,
        )

        test_store = FactStore(
            in_memory=True,
            collection_name=f"test_rest_wiring_{uuid.uuid4().hex[:8]}",
        )
        fact = Fact(
            subject="Albert Einstein",
            verb="won",
            object="Nobel Prize in Physics",
            modality="asserted",
            negated=False,
            source_doc="physics.txt",
        )
        test_store.add_facts([fact])
        monkeypatch.setattr(main, "store", test_store)
        monkeypatch.setattr(main, "_get_store", lambda: test_store)

        token = generate_token("rest_test_user")
        headers = {"Authorization": f"Bearer {token}"}
        client = TestClient(app)

        # Case A: Feature flag enabled (PRECIS_ENABLE_LIST_EXTRACTION=true)
        monkeypatch.setenv("PRECIS_ENABLE_LIST_EXTRACTION", "true")

        with patch(
            "precis.pipeline.orchestrator.build_structural_context",
            wraps=build_structural_context,
        ) as spy_structural:
            response = client.post(
                "/api/query",
                headers=headers,
                json={"question": "Who won the Nobel Prize in Physics?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "Albert Einstein" in data["answer"]
            assert len(data["facts_used"]) >= 1

            # Verify generate_answer was called
            assert mock_generate.called
            context_passed = mock_generate.call_args[1]["context"]

            # Fact-based context is packed
            assert "Fact 1: Albert Einstein won Nobel Prize in Physics" in context_passed
            assert "### Structured List:" not in context_passed

            # Structural list extraction was NOT reached because raw_document was None
            assert spy_structural.call_count == 0

        # Case B: Feature flag disabled (PRECIS_ENABLE_LIST_EXTRACTION=false)
        mock_generate.reset_mock()
        monkeypatch.setenv("PRECIS_ENABLE_LIST_EXTRACTION", "false")

        with patch(
            "precis.pipeline.orchestrator.build_structural_context",
            wraps=build_structural_context,
        ) as spy_structural:
            response = client.post(
                "/api/query",
                headers=headers,
                json={"question": "Who won the Nobel Prize in Physics?"},
            )

            assert response.status_code == 200
            context_passed = mock_generate.call_args[1]["context"]
            assert "Fact 1: Albert Einstein won Nobel Prize in Physics" in context_passed
            assert "### Structured List:" not in context_passed
            assert spy_structural.call_count == 0
