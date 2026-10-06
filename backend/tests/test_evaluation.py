"""
Unit and integration tests for the evaluation harness, naive RAG baseline,
and evaluation metrics.
"""

import json
from unittest.mock import patch

import fastcoref.spacy_component  # noqa: F401
import pytest
from precis.evaluation.harness import (
    AggregateResult,
    EvalSample,
    format_ablation_table,
    format_results_table,
    load_natural_questions,
    pack_svoa_similarity,
    run_ablation,
    run_evaluation,
)
from precis.evaluation.metrics import (
    DEFAULT_BERTSCORE_MODEL,
    compute_bert_score,
    compute_exact_match,
    compute_minilm_cosine,
    compute_rouge_l,
    compute_token_f1,
    is_bertscore_model_cached,
    normalize_answer,
)
from precis.evaluation.naive_rag import (
    chunk_document,
    naive_rag_answer,
    naive_rag_retrieve,
)
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.inference import InferenceResult


class TestMetrics:
    def test_normalize_answer(self):
        raw = "  The Doctor, Alexander Fleming.  "

        assert normalize_answer(raw) == "doctor alexander fleming"

    def test_normalize_answer_rejects_non_string(self):
        with pytest.raises(TypeError):
            normalize_answer(None)  # type: ignore[arg-type]

    def test_exact_match(self):
        gold = "Dr. Alexander Fleming"
        pred_match = "dr alexander fleming"
        pred_mismatch = "Howard Florey"

        assert (
            compute_exact_match(
                pred_match,
                gold,
            )
            is True
        )

        assert (
            compute_exact_match(
                pred_mismatch,
                gold,
            )
            is False
        )

    def test_exact_match_empty_strings(self):
        assert compute_exact_match("", "") is True
        assert compute_exact_match("", "answer") is False
        assert compute_exact_match("answer", "") is False

    def test_token_f1(self):
        gold = "Alexander Fleming discovered penicillin"
        pred = "penicillin was discovered by Fleming"

        f1 = compute_token_f1(
            pred,
            gold,
        )

        assert 0.0 < f1 <= 1.0

    def test_token_f1_identical(self):
        assert (
            compute_token_f1(
                "Alexander Fleming",
                "Alexander Fleming",
            )
            == 1.0
        )

    def test_token_f1_no_overlap(self):
        assert (
            compute_token_f1(
                "Alexander Fleming",
                "Howard Florey",
            )
            == 0.0
        )

    def test_rouge_l(self):
        gold = "Alexander Fleming discovered penicillin in 1928."
        pred = "Fleming discovered penicillin in 1928."

        score = compute_rouge_l(
            pred,
            gold,
        )

        assert score > 0.80

    @patch("bert_score.score")
    @patch("precis.evaluation.metrics.is_bertscore_model_cached", return_value=True)
    def test_bert_score(self, mock_cached, mock_bert):
        import torch

        mock_bert.return_value = (
            torch.tensor([0.90]),
            torch.tensor([0.92]),
            torch.tensor([0.91]),
        )

        gold = "Penicillin destroys bacterial cell walls."
        pred = "Penicillin kills bacteria by inhibiting cell wall synthesis."

        score = compute_bert_score(
            pred,
            gold,
            model_type=DEFAULT_BERTSCORE_MODEL,
            device="cpu",
            batch_size=4,
        )

        assert score == 0.91
        mock_bert.assert_called_once_with(
            [pred],
            [gold],
            lang="en",
            model_type=DEFAULT_BERTSCORE_MODEL,
            device="cpu",
            batch_size=4,
            verbose=False,
        )

    def test_bert_score_offline_missing_model_raises(self, monkeypatch):
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")
        with patch(
            "precis.evaluation.metrics.is_bertscore_model_cached",
            return_value=False,
        ):
            with pytest.raises(FileNotFoundError, match="not cached locally"):
                compute_bert_score(
                    "predicted answer",
                    "gold answer",
                    model_type="microsoft/deberta-large-mnli",
                )

    def test_bert_score_missing_library_raises(self):
        with patch.dict("sys.modules", {"bert_score": None}):
            with pytest.raises(RuntimeError, match="requires the 'bert-score' package"):
                compute_bert_score(
                    "predicted answer",
                    "gold answer",
                )

    def test_bert_score_empty_input(self):
        assert (
            compute_bert_score(
                "",
                "answer",
            )
            == 0.0
        )

        assert (
            compute_bert_score(
                "answer",
                "",
            )
            == 0.0
        )

    def test_minilm_cosine(self):
        gold = "Penicillin destroys bacterial cell walls."
        pred = "Penicillin kills bacteria by inhibiting cell wall synthesis."

        score = compute_minilm_cosine(
            pred,
            gold,
        )

        assert 0.0 <= score <= 1.0
        assert score > 0.60

    def test_minilm_cosine_empty_input(self):
        assert compute_minilm_cosine("", "answer") == 0.0
        assert compute_minilm_cosine("answer", "") == 0.0

    def test_minilm_and_bertscore_are_distinct(self):
        gold = "Dr. Alexander Fleming discovered penicillin in London."
        pred = "Penicillin was discovered by Alexander Fleming."

        minilm_sim = compute_minilm_cosine(pred, gold)
        assert 0.0 <= minilm_sim <= 1.0

        # Verify compute_bert_score does NOT call compute_minilm_cosine
        with patch("precis.evaluation.metrics.compute_minilm_cosine") as mock_minilm:
            with patch("bert_score.score") as mock_bert:
                import torch

                mock_bert.return_value = (
                    torch.tensor([0.85]),
                    torch.tensor([0.88]),
                    torch.tensor([0.865]),
                )
                with patch(
                    "precis.evaluation.metrics.is_bertscore_model_cached",
                    return_value=True,
                ):
                    b_score = compute_bert_score(pred, gold)
                    assert b_score == 0.865
                    mock_minilm.assert_not_called()

    def test_is_bertscore_model_cached(self):
        assert is_bertscore_model_cached("nonexistent_model_xyz_123") is False


class TestNaiveRAG:
    def test_chunk_document(self):
        text = "word " * 1200

        chunks = chunk_document(
            text,
            chunk_size=512,
            overlap=128,
        )

        assert len(chunks) >= 3
        assert len(chunks[0].split()) == 512

    def test_chunk_document_short_text(self):
        text = "one two three four"

        chunks = chunk_document(
            text,
            chunk_size=512,
            overlap=128,
        )

        assert chunks == ["one two three four"]

    def test_chunk_document_empty_text(self):
        assert chunk_document("") == []
        assert chunk_document("   ") == []

    def test_chunk_document_invalid_chunk_size(self):
        with pytest.raises(ValueError):
            chunk_document(
                "some text",
                chunk_size=0,
            )

    def test_chunk_document_negative_overlap(self):
        with pytest.raises(ValueError):
            chunk_document(
                "some text",
                chunk_size=10,
                overlap=-1,
            )

    def test_chunk_document_overlap_too_large(self):
        with pytest.raises(ValueError):
            chunk_document(
                "some text",
                chunk_size=10,
                overlap=10,
            )

    def test_naive_rag_retrieve(self):
        doc = (
            "Section 1: Quantum mechanics describes particles. "
            "Section 2: Alexander Fleming discovered penicillin "
            "in 1928 at St. Mary's Hospital. "
            "Section 3: Medieval castle architecture in Europe."
        )

        query = "Who discovered penicillin?"

        top_chunks, context_words = naive_rag_retrieve(
            doc,
            query,
            top_k=1,
            chunk_size=15,
            overlap=5,
        )

        assert len(top_chunks) == 1
        assert "penicillin" in top_chunks[0].lower()
        assert context_words > 0

    def test_naive_rag_retrieve_invalid_top_k(self):
        with pytest.raises(ValueError):
            naive_rag_retrieve(
                "some document",
                "some query",
                top_k=0,
            )

    def test_naive_rag_retrieve_empty_document(self):
        chunks, context_words = naive_rag_retrieve(
            "",
            "some query",
        )

        assert chunks == []
        assert context_words == 0

    @patch("precis.evaluation.naive_rag.generate_answer")
    def test_naive_rag_answer(
        self,
        mock_generate,
    ):
        mock_generate.return_value = InferenceResult(
            answer="Alexander Fleming.",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=3,
        )

        doc = "Alexander Fleming discovered penicillin."

        answer, context_words = naive_rag_answer(
            doc,
            "Who discovered penicillin?",
        )

        assert answer == "Alexander Fleming."
        assert context_words > 0

        mock_generate.assert_called_once()

        call_kwargs = mock_generate.call_args.kwargs

        assert call_kwargs["model"] == "qwen2.5-coder:7b"
        assert call_kwargs["stream"] is False


class TestHarness:
    def test_load_natural_questions(
        self,
        tmp_path,
    ):
        jsonl_path = tmp_path / "test_nq.jsonl"

        data = [
            {
                "question": "Q1?",
                "answer": "A1",
                "document": "D1",
                "doc_id": "1",
            },
            {
                "question": "Q2?",
                "answer": "A2",
                "document": "D2",
                "doc_id": "2",
            },
        ]

        with open(
            jsonl_path,
            "w",
            encoding="utf-8",
        ) as f:
            f.writelines(json.dumps(item) + "\n" for item in data)

        samples = load_natural_questions(
            str(jsonl_path),
            limit=1,
        )

        assert len(samples) == 1
        assert samples[0].question == "Q1?"
        assert samples[0].gold_answer == "A1"
        assert samples[0].document == "D1"

    def test_load_natural_questions_counts_valid_samples(
        self,
        tmp_path,
    ):
        jsonl_path = tmp_path / "test_nq.jsonl"

        lines = [
            "",
            json.dumps(
                {
                    "question": "Q1?",
                    "answer": "A1",
                    "document": "D1",
                }
            ),
            "",
            json.dumps(
                {
                    "question": "Q2?",
                    "answer": "A2",
                    "document": "D2",
                }
            ),
        ]

        jsonl_path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        samples = load_natural_questions(
            str(jsonl_path),
            limit=2,
        )

        assert len(samples) == 2
        assert samples[0].question == "Q1?"
        assert samples[1].question == "Q2?"

    def test_load_natural_questions_missing_file(
        self,
        tmp_path,
    ):
        missing_path = tmp_path / "missing.jsonl"

        with pytest.raises(FileNotFoundError):
            load_natural_questions(str(missing_path))

    def test_load_natural_questions_invalid_limit(
        self,
        tmp_path,
    ):
        jsonl_path = tmp_path / "test_nq.jsonl"

        jsonl_path.write_text(
            json.dumps(
                {
                    "question": "Q?",
                    "answer": "A",
                    "document": "D",
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            load_natural_questions(
                str(jsonl_path),
                limit=0,
            )

    def test_load_natural_questions_non_object(
        self,
        tmp_path,
    ):
        jsonl_path = tmp_path / "test_nq.jsonl"

        jsonl_path.write_text(
            json.dumps(["not", "an", "object"]),
            encoding="utf-8",
        )

        with pytest.raises(TypeError):
            load_natural_questions(str(jsonl_path))

    def test_load_natural_questions_invalid_json(
        self,
        tmp_path,
    ):
        jsonl_path = tmp_path / "test_nq.jsonl"

        jsonl_path.write_text(
            "{invalid json}\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError):
            load_natural_questions(str(jsonl_path))

    def test_format_results_table(self):
        results = {
            "naive_rag": AggregateResult(
                condition="naive_rag",
                num_samples=10,
                avg_em=0.5,
                avg_rouge_l=0.6,
                avg_bert_score=0.7,
                avg_context_words=400,
                avg_generated_tokens=20,
                avg_compression_rate=0.0,
                avg_latency_ms=200,
            ),
            "svoa_similarity": AggregateResult(
                condition="svoa_similarity",
                num_samples=10,
                avg_em=0.52,
                avg_rouge_l=0.62,
                avg_bert_score=0.71,
                avg_context_words=90,
                avg_generated_tokens=18,
                avg_compression_rate=0.75,
                avg_latency_ms=130,
            ),
            "svoa_no_modality": AggregateResult(
                condition="svoa_no_modality",
                num_samples=10,
                avg_em=0.53,
                avg_rouge_l=0.63,
                avg_bert_score=0.71,
                avg_context_words=88,
                avg_generated_tokens=18,
                avg_compression_rate=0.76,
                avg_latency_ms=125,
            ),
            "precis_full": AggregateResult(
                condition="precis_full",
                num_samples=10,
                avg_em=0.55,
                avg_rouge_l=0.65,
                avg_bert_score=0.72,
                avg_context_words=85,
                avg_generated_tokens=18,
                avg_compression_rate=0.78,
                avg_latency_ms=120,
            ),
        }

        table = format_results_table(results)

        assert "| Condition | EM | ROUGE-L |" in table
        assert "Baseline A" in table
        assert "Baseline B (SVOA Pure Similarity)" in table
        assert "Baseline C (SVOA w/o Modality)" in table
        assert "Précis (Full 6-Stage)" in table
        assert "Context Words" in table
        assert "Generated Tokens" in table
        assert "Compression Rate" in table
        assert "78.0%" in table
        assert "BERTScore (DeBERTa)" in table

    def test_format_results_table_with_both_metrics(self):
        results = {
            "naive_rag": AggregateResult(
                condition="naive_rag",
                num_samples=2,
                avg_em=0.5,
                avg_rouge_l=0.6,
                avg_bert_score=0.75,
                avg_context_words=400,
                avg_generated_tokens=20,
                avg_compression_rate=0.0,
                avg_latency_ms=200,
                avg_minilm_cosine=0.71,
            ),
            "precis_full": AggregateResult(
                condition="precis_full",
                num_samples=2,
                avg_em=0.55,
                avg_rouge_l=0.65,
                avg_bert_score=0.82,
                avg_context_words=85,
                avg_generated_tokens=18,
                avg_compression_rate=0.78,
                avg_latency_ms=120,
                avg_minilm_cosine=0.79,
            ),
        }

        table = format_results_table(results)

        assert "BERTScore (DeBERTa)" in table
        assert "MiniLM Cosine" in table
        assert "0.750" in table
        assert "0.710" in table
        assert "0.820" in table
        assert "0.790" in table

    def test_format_ablation_table(self):
        results = {
            "full": AggregateResult(
                condition="full",
                num_samples=5,
                avg_em=0.6,
                avg_rouge_l=0.7,
                avg_bert_score=0.8,
                avg_context_words=80,
                avg_generated_tokens=20,
                avg_compression_rate=0.75,
                avg_latency_ms=100,
            ),
            "drop_E": AggregateResult(
                condition="drop_E",
                num_samples=5,
                avg_em=0.5,
                avg_rouge_l=0.62,
                avg_bert_score=0.75,
                avg_context_words=80,
                avg_generated_tokens=20,
                avg_compression_rate=0.75,
                avg_latency_ms=100,
            ),
        }

        table = format_ablation_table(results)

        assert "| Configuration | Dropped Term |" in table
        assert "drop_E" in table
        assert "-0.080" in table
        assert "Compression Rate" in table
        assert "75.0%" in table

    @patch("precis.evaluation.harness.generate_answer")
    @patch("precis.evaluation.naive_rag.generate_answer")
    def test_run_evaluation(
        self,
        mock_naive_inf,
        mock_precis_inf,
    ):
        mock_naive_inf.return_value = InferenceResult(
            answer="Dr. Alexander Fleming.",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=4,
        )

        mock_precis_inf.return_value = InferenceResult(
            answer="Dr. Alexander Fleming.",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=4,
        )

        sample = EvalSample(
            question=("Who discovered penicillin in 1928?"),
            gold_answer="Dr. Alexander Fleming",
            document=(
                "In 1928, Dr. Alexander Fleming "
                "discovered penicillin in London. "
                "Fleming was a Scottish physician "
                "who worked at St. Mary's Hospital. "
                "His discovery revolutionized modern "
                "medicine and saved millions of lives "
                "worldwide."
            ),
            doc_id="sample_0",
        )

        results = run_evaluation(
            [sample],
            token_ceiling=35,
        )

        assert "naive_rag" in results
        assert "svoa_similarity" in results
        assert "svoa_no_modality" in results
        assert "precis_no_modality" in results
        assert "precis_full" in results

        assert results["precis_full"].avg_em == 1.0

        assert results["precis_full"].avg_rouge_l > 0.80

        assert results["precis_full"].avg_compression_rate > 0.0

        assert results["precis_full"].avg_generated_tokens == 4

        assert results["svoa_similarity"].avg_em == 1.0

        assert results["svoa_no_modality"].avg_em == 1.0

        assert results["naive_rag"].avg_generated_tokens == 0

        assert results["naive_rag"].avg_context_words > 0

        assert results["precis_full"].avg_bert_score is None

        assert results["precis_full"].avg_minilm_cosine is not None

        assert results["precis_full"].avg_minilm_cosine > 0.80

    @patch("bert_score.score")
    @patch("precis.evaluation.metrics.is_bertscore_model_cached", return_value=True)
    @patch("precis.evaluation.harness.generate_answer")
    @patch("precis.evaluation.naive_rag.generate_answer")
    def test_run_evaluation_with_bertscore(
        self,
        mock_naive_inf,
        mock_precis_inf,
        mock_cached,
        mock_bert,
    ):
        import torch

        mock_bert.return_value = (
            torch.tensor([0.90]),
            torch.tensor([0.92]),
            torch.tensor([0.91]),
        )
        mock_naive_inf.return_value = InferenceResult(
            answer="Dr. Alexander Fleming.",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=4,
        )
        mock_precis_inf.return_value = InferenceResult(
            answer="Dr. Alexander Fleming.",
            model="qwen2.5-coder:7b",
            latency_ms=100,
            tokens_generated=4,
        )

        sample = EvalSample(
            question="Who discovered penicillin in 1928?",
            gold_answer="Dr. Alexander Fleming",
            document="In 1928, Dr. Alexander Fleming discovered penicillin in London.",
            doc_id="sample_bert_eval",
        )

        results = run_evaluation(
            [sample],
            token_ceiling=35,
            use_bertscore=True,
        )

        assert results["precis_full"].avg_bert_score == 0.91
        assert results["precis_full"].avg_minilm_cosine is not None
        assert mock_bert.call_count >= 1

    def test_pack_svoa_similarity(self):
        col_name = "test_svoa_sim_harness"
        store = FactStore(in_memory=True, collection_name=col_name)
        try:
            facts = [
                Fact(
                    subject="Alexander Fleming",
                    verb="discovered",
                    object="penicillin",
                    modality="asserted",
                    sdh_score=0.1,
                ),
                Fact(
                    subject="Alien civilization",
                    verb="might inhabit",
                    object="distant galaxies",
                    modality="hypothetical",
                    sdh_score=0.9,
                ),
            ]
            store.add_facts(facts)

            # Test invalid inputs
            assert pack_svoa_similarity("", store, 500).facts_packed == 0
            assert pack_svoa_similarity("penicillin", store, 0).facts_packed == 0

            # Test packing
            res = pack_svoa_similarity("penicillin", store, token_ceiling=500)
            assert res.facts_packed >= 1

            # Modality filtering is bypassed: hypothetical facts are retained
            res_all = pack_svoa_similarity(
                "alien civilization distant galaxies",
                store,
                token_ceiling=500,
            )
            assert any(f.modality == "hypothetical" for f in res_all.packed_facts)
        finally:
            store.clear()

    @patch("precis.evaluation.harness.generate_answer")
    def test_run_ablation(
        self,
        mock_inf,
    ):
        mock_inf.return_value = InferenceResult(
            answer="Fleming in 1928.",
            model="qwen2.5-coder:7b",
            latency_ms=80,
            tokens_generated=4,
        )

        sample = EvalSample(
            question=("When was penicillin discovered?"),
            gold_answer="1928",
            document=("Dr. Fleming discovered penicillin in 1928."),
            doc_id="sample_abl",
        )

        results = run_ablation([sample])

        assert "full" in results
        assert "drop_E" in results
        assert "drop_I" in results
        assert "drop_U" in results
        assert "drop_A" in results

        assert results["full"].num_samples == 1

        assert results["full"].avg_generated_tokens == 4
