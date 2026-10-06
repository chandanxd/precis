"""
Unit and integration tests for Stage 5 Local LLM Inference and Pipeline Orchestrator.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
import requests
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.inference import (
    InferenceResult,
    OllamaConnectionError,
    OllamaInferenceError,
    build_prompt,
    check_ollama,
    generate_answer,
)
from precis.pipeline.orchestrator import (
    IngestionResult,
    PipelineResult,
    ingest_document,
    process_query,
    query_pipeline,
)


@pytest.fixture
def mem_store():
    col_name = f"test_inf_{uuid.uuid4().hex[:12]}"
    store = FactStore(in_memory=True, collection_name=col_name)
    yield store
    store._client.delete_collection(col_name)


class TestPromptBuilding:
    def test_build_prompt_formatting(self):
        context = "Fact 1: Alexander Fleming discovered penicillin."
        query = "Who discovered penicillin?"

        prompt = build_prompt(context, query)

        assert "FACTS FROM DOCUMENT:" in prompt
        assert context in prompt
        assert "QUESTION:\nWho discovered penicillin?" in prompt
        assert "GROUNDING RULES:" in prompt
        assert 'A fact containing "NOT"' in prompt
        assert "[attributed to X]" in prompt
        assert "[conditional]" in prompt
        assert "[hypothetical]" in prompt

    def test_build_prompt_empty_context(self):
        prompt = build_prompt("", "What is the capital?")

        assert "(No relevant facts retrieved)" in prompt

    def test_build_prompt_whitespace_context(self):
        prompt = build_prompt("   \n  ", "What happened?")

        assert "(No relevant facts retrieved)" in prompt

    def test_build_prompt_rejects_empty_query(self):
        with pytest.raises(ValueError, match="Query must not be empty"):
            build_prompt("Fact 1: Something happened.", "")

    def test_build_prompt_rejects_whitespace_query(self):
        with pytest.raises(ValueError, match="Query must not be empty"):
            build_prompt("Fact 1: Something happened.", "   ")


class TestOllamaClient:
    @patch("requests.get")
    def test_check_ollama_online(self, mock_get):
        mock_get.return_value.status_code = 200

        assert check_ollama("http://localhost:11434") is True
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=3,
        )

    @patch("requests.get")
    def test_check_ollama_offline(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        assert check_ollama("http://localhost:11434") is False

    @patch("requests.get")
    def test_check_ollama_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout("Timed out")

        assert check_ollama("http://localhost:11434") is False

    @patch("requests.post")
    def test_generate_answer_blocking(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Alexander Fleming discovered penicillin in 1928.",
            "eval_count": 8,
            "prompt_eval_count": 45,
        }
        mock_post.return_value = mock_resp

        res = generate_answer(
            "Who discovered penicillin?",
            "Fact 1: Fleming discovered penicillin.",
            model="qwen2.5-coder:7b",
        )

        assert isinstance(res, InferenceResult)
        assert res.answer == "Alexander Fleming discovered penicillin in 1928."
        assert res.model == "qwen2.5-coder:7b"
        assert res.tokens_generated == 8
        assert res.prompt_tokens == 45
        assert res.latency_ms >= 0

        mock_post.assert_called_once()

    @patch("requests.post")
    def test_generate_answer_blocking_connection_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(OllamaConnectionError, match="Could not connect"):
            generate_answer(
                "Who discovered penicillin?",
                "Fact 1: Fleming discovered penicillin.",
            )

    @patch("requests.post")
    def test_generate_answer_blocking_request_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_resp

        with pytest.raises(
            OllamaInferenceError,
            match="Ollama inference request failed",
        ):
            generate_answer(
                "Who discovered penicillin?",
                "Fact 1: Fleming discovered penicillin.",
            )

    @patch("requests.post")
    def test_generate_answer_streaming(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = [
            b'{"response": "Alexander", "done": false}',
            b'{"response": " Fleming", "done": false}',
            b'{"response": " discovered", "done": false}',
            b'{"response": " penicillin.", "done": true, "eval_count": 4}',
        ]
        mock_post.return_value = mock_resp

        gen = generate_answer(
            "Who discovered penicillin?",
            "Fact 1: Fleming discovered penicillin.",
            model="qwen2.5-coder:7b",
            stream=True,
        )

        tokens = []

        try:
            while True:
                tokens.append(next(gen))
        except StopIteration as exc:
            res: InferenceResult = exc.value

        assert "".join(tokens) == ("Alexander Fleming discovered penicillin.")
        assert res.answer == "Alexander Fleming discovered penicillin."
        assert res.model == "qwen2.5-coder:7b"
        assert res.tokens_generated == 4
        assert res.prompt_tokens == 0
        assert res.latency_ms >= 0

    @patch("requests.post")
    def test_generate_answer_streaming_connection_error(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        gen = generate_answer(
            "Who discovered penicillin?",
            "Fact 1: Fleming discovered penicillin.",
            stream=True,
        )

        with pytest.raises(
            OllamaConnectionError,
            match="Could not connect",
        ):
            next(gen)

    @patch("requests.post")
    def test_generate_answer_streaming_request_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_post.return_value = mock_resp

        gen = generate_answer(
            "Who discovered penicillin?",
            "Fact 1: Fleming discovered penicillin.",
            stream=True,
        )

        with pytest.raises(
            OllamaInferenceError,
            match="Ollama streaming request failed",
        ):
            next(gen)

    def test_generate_answer_rejects_invalid_temperature(self):
        with pytest.raises(
            ValueError,
            match="temperature must be between",
        ):
            generate_answer(
                "Who discovered penicillin?",
                "Fact 1: Fleming discovered penicillin.",
                temperature=-0.1,
            )

    def test_generate_answer_rejects_invalid_top_p(self):
        with pytest.raises(
            ValueError,
            match="top_p must be between",
        ):
            generate_answer(
                "Who discovered penicillin?",
                "Fact 1: Fleming discovered penicillin.",
                top_p=1.1,
            )

    def test_generate_answer_rejects_invalid_max_tokens(self):
        with pytest.raises(
            ValueError,
            match="max_tokens must be greater than 0",
        ):
            generate_answer(
                "Who discovered penicillin?",
                "Fact 1: Fleming discovered penicillin.",
                max_tokens=0,
            )

    def test_generate_answer_rejects_empty_query(self):
        with pytest.raises(ValueError, match="Query must not be empty"):
            generate_answer(
                "",
                "Fact 1: Fleming discovered penicillin.",
            )

    @patch("requests.post")
    def test_generate_answer_uses_environment_model(
        self,
        mock_post,
        monkeypatch,
    ):
        monkeypatch.setenv(
            "PRECIS_OLLAMA_MODEL",
            "deepseek-r1:8b",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": "Answer",
            "eval_count": 1,
            "prompt_eval_count": 10,
        }
        mock_post.return_value = mock_resp

        res = generate_answer(
            "Question?",
            "Fact 1: Answer.",
        )

        assert res.model == "deepseek-r1:8b"

        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "deepseek-r1:8b"


class TestOrchestrator:
    def test_ingest_document(self, mem_store):
        text = (
            "Dr. Alexander Fleming discovered penicillin in London in 1928. "
            "He published his findings later."
        )

        res = ingest_document(
            text=text,
            source_doc="fleming.txt",
            store=mem_store,
        )

        assert isinstance(res, IngestionResult)
        assert res.document_name == "fleming.txt"
        assert res.facts_extracted >= 1
        assert res.facts_stored >= 1
        assert mem_store.count() >= 1
        assert "coreference" in res.stage_timings
        assert "svoa_extraction" in res.stage_timings
        assert "sdh_scoring_and_storage" in res.stage_timings

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_query_pipeline(self, mock_generate, mem_store):
        facts = [
            Fact(
                subject="Fleming",
                verb="discovered",
                object="penicillin",
                adjuncts={"time": ["in 1928"]},
                raw_sentence=(
                    "In 1928, Dr. Alexander Fleming discovered penicillin "
                    "at St. Mary's Hospital in London."
                ),
                sdh_score=0.8,
                source_doc="history.txt",
            ),
            Fact(
                subject="Scientists",
                verb="isolated",
                object="chemical compound",
                raw_sentence=(
                    "Scientists isolated the chemical compound after "
                    "extensive purification trials."
                ),
                sdh_score=0.7,
                source_doc="history.txt",
            ),
        ]

        mem_store.add_facts(facts)

        mock_generate.return_value = InferenceResult(
            answer="Alexander Fleming discovered penicillin in 1928.",
            model="qwen2.5-coder:7b",
            latency_ms=120,
            tokens_generated=8,
        )

        res = query_pipeline(
            "Who discovered penicillin?",
            store=mem_store,
        )

        assert isinstance(res, PipelineResult)
        assert res.answer == "Alexander Fleming discovered penicillin in 1928."
        assert len(res.facts_used) >= 1
        assert res.facts_used[0].subject == "Fleming"
        assert res.tokens_used > 0
        assert res.compression_rate >= 0.0
        assert "rerank_and_pack" in res.stage_timings
        assert "inference" in res.stage_timings

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_process_query_end_to_end(self, mock_generate, mem_store):
        mock_generate.return_value = InferenceResult(
            answer="Penicillin was discovered in 1928.",
            model="qwen2.5-coder:7b",
            latency_ms=150,
            tokens_generated=6,
        )

        doc_text = "Alexander Fleming discovered penicillin in 1928."
        query = "When was penicillin discovered?"

        res = process_query(
            document_text=doc_text,
            query=query,
            store=mem_store,
            source_doc="test_doc.txt",
        )

        assert isinstance(res, PipelineResult)
        assert res.answer == "Penicillin was discovered in 1928."
        assert mem_store.count() >= 1
