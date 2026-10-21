"""
Focused tests for casual conversation, intent routing, and conversation history in Précis.
"""

import uuid
from unittest.mock import patch

import main
import pytest
from fastapi.testclient import TestClient
from main import app
from precis.api.security import generate_token
from precis.graph.schema import Fact
from precis.graph.store import FactStore
from precis.pipeline.history import ChatMessage, SessionManager, session_manager
from precis.pipeline.inference import (
    InferenceResult,
    build_conversational_prompt,
)
from precis.pipeline.routing import QueryIntent, classify_query_intent


@pytest.fixture(autouse=True)
def clean_store(monkeypatch):
    """Ensure a clean, isolated in-memory fact store and session store for each test."""
    test_store = FactStore(
        in_memory=True,
        collection_name=f"test_conv_{uuid.uuid4().hex[:8]}",
    )
    monkeypatch.setattr(main, "store", test_store)
    monkeypatch.setattr(main, "_get_store", lambda: test_store)
    session_manager._sessions.clear()
    session_manager._last_accessed.clear()
    main.query_limiter._requests.clear()
    yield test_store
    test_store.clear()
    main.query_limiter._requests.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = generate_token("conv_test_user")
    return {"Authorization": f"Bearer {token}"}


class TestIntentRouting:
    def test_casual_greetings_classified_conversational(self):
        assert classify_query_intent("Hello!") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Hi there") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("How are you?") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Good morning") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Who are you?") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("what's your name?") == QueryIntent.CONVERSATIONAL

    def test_gratitude_and_pleasantries_classified_conversational(self):
        assert classify_query_intent("Thanks, that helped.") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Thank you very much") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Goodbye!") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Got it, thanks") == QueryIntent.CONVERSATIONAL

    def test_general_knowledge_classified_correctly(self):
        assert classify_query_intent("Explain how a neural network works.") == QueryIntent.GENERAL_KNOWLEDGE
        assert classify_query_intent("What is the difference between a list and a tuple in Python?") == QueryIntent.GENERAL_KNOWLEDGE
        assert classify_query_intent("How do I sort a list in Python?") == QueryIntent.GENERAL_KNOWLEDGE
        assert classify_query_intent("What is photosynthesis? How does gravity work?") == QueryIntent.GENERAL_KNOWLEDGE

    def test_document_explicit_markers(self):
        assert classify_query_intent("What is stated in the document?") == QueryIntent.DOCUMENT_GROUNDED
        assert classify_query_intent("According to the report, what is revenue?", has_documents=True) == QueryIntent.DOCUMENT_GROUNDED
        assert classify_query_intent("What does the table show?") == QueryIntent.DOCUMENT_GROUNDED
        assert classify_query_intent("What was revenue in 2021? And what about expenses in 2022 according to the report?", has_documents=True) == QueryIntent.DOCUMENT_GROUNDED

    def test_ambiguous_queries_routing(self):
        # Without documents, ambiguous queries route to conversational
        assert classify_query_intent("What do you think about this?", has_documents=False) == QueryIntent.CONVERSATIONAL
        # With documents and no history, ambiguous query is marked AMBIGUOUS
        assert classify_query_intent("What do you think about this?", has_documents=True) == QueryIntent.AMBIGUOUS

        # With history referencing document, follow-up resolves to DOCUMENT_GROUNDED
        doc_history = [ChatMessage("user", "What is in the document?", 1.0)]
        assert classify_query_intent("What about it?", has_documents=True, conversation_history=doc_history) == QueryIntent.DOCUMENT_GROUNDED

        # With history being conversational, follow-up resolves to CONVERSATIONAL
        conv_history = [ChatMessage("user", "I like machine learning", 1.0)]
        assert classify_query_intent("What do you think about this?", has_documents=True, conversation_history=conv_history) == QueryIntent.CONVERSATIONAL


class TestConversationalPrompts:
    def test_build_conversational_prompt_without_history(self):
        prompt = build_conversational_prompt("Hello!")
        assert "You are Précis" in prompt
        assert "USER:\nHello!" in prompt
        assert "FACTS FROM DOCUMENT" not in prompt

    def test_build_conversational_prompt_with_history(self):
        history = [
            ChatMessage(role="user", content="My name is Alice", timestamp=1.0),
            ChatMessage(role="assistant", content="Hello Alice!", timestamp=2.0),
        ]
        prompt = build_conversational_prompt("What is my name?", history=history)
        assert "CONVERSATION HISTORY:" in prompt
        assert "User: My name is Alice" in prompt
        assert "Assistant: Hello Alice!" in prompt
        assert "USER:\nWhat is my name?" in prompt


class TestSessionManager:
    def test_add_and_get_history(self):
        sm = SessionManager(max_turns_per_session=5)
        sm.add_message("session_1", "user", "Hi")
        sm.add_message("session_1", "assistant", "Hello!")

        history = sm.get_history("session_1")
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hi"
        assert history[1].role == "assistant"
        assert history[1].content == "Hello!"

    def test_turn_pruning(self):
        sm = SessionManager(max_turns_per_session=2)
        sm.add_message("s1", "user", "turn 1")
        sm.add_message("s1", "assistant", "turn 2")
        sm.add_message("s1", "user", "turn 3")

        history = sm.get_history("s1")
        assert len(history) == 2
        assert history[0].content == "turn 2"
        assert history[1].content == "turn 3"

    def test_clear_session(self):
        sm = SessionManager()
        sm.add_message("s1", "user", "hi")
        assert sm.clear_session("s1") is True
        assert sm.get_history("s1") == []


class TestCasualConversationEndpoints:
    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_casual_greeting_without_documents(self, mock_inf, client, auth_headers):
        mock_inf.return_value = InferenceResult(
            answer="Hello! How can I assist you today?",
            model="qwen3.5:4b",
            latency_ms=80,
            tokens_generated=8,
        )

        resp = client.post(
            "/api/query",
            headers={**auth_headers},
            json={"question": "Hello!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Hello! How can I assist you today?"
        assert data["facts_used"] == []
        assert data["tokens_used"] == 0
        assert data["compression_rate"] == 0.0

        # Verify generate_answer was called with prompt_type='conversational'
        assert mock_inf.call_args.kwargs.get("prompt_type") == "conversational"

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_casual_greeting_with_uploaded_documents_bypasses_retrieval(
        self, mock_inf, client, auth_headers, clean_store
    ):
        mock_inf.return_value = InferenceResult(
            answer="I am doing well, thank you!",
            model="qwen3.5:4b",
            latency_ms=90,
            tokens_generated=7,
        )

        # Ingest a document
        fact = Fact(
            subject="Company",
            verb="reported",
            object="high revenue",
            source_doc="financials.txt",
        )
        clean_store.add_facts([fact])
        assert clean_store.count() > 0

        # Ask a casual question
        resp = client.post(
            "/api/query",
            headers={**auth_headers},
            json={"question": "How are you?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "I am doing well, thank you!"
        assert data["facts_used"] == []
        assert data["tokens_used"] == 0
        assert mock_inf.call_args.kwargs.get("prompt_type") == "conversational"

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_general_knowledge_without_documents(self, mock_inf, client, auth_headers):
        mock_inf.return_value = InferenceResult(
            answer="A neural network is a computational model inspired by the human brain.",
            model="qwen3.5:4b",
            latency_ms=150,
            tokens_generated=14,
        )

        resp = client.post(
            "/api/query",
            headers={**auth_headers},
            json={"question": "Explain how a neural network works."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "neural network" in data["answer"].lower()
        assert data["facts_used"] == []

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_document_grounded_question_uses_retrieval_pipeline(
        self, mock_inf, client, auth_headers, clean_store
    ):
        mock_inf.return_value = InferenceResult(
            answer="The legislation does not include fossil fuel subsidies.",
            model="qwen3.5:4b",
            latency_ms=110,
            tokens_generated=10,
        )

        fact = Fact(
            subject="legislation",
            verb="include",
            object="fossil fuel subsidies",
            negated=True,
            modality="asserted",
            source_doc="climate.txt",
        )
        clean_store.add_facts([fact])

        resp = client.post(
            "/api/query",
            headers={**auth_headers},
            json={"question": "Does the legislation include fossil fuel subsidies?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["facts_used"]) > 0
        assert data["facts_used"][0]["negated"] is True
        assert data["answer_source"] == "document"
        assert mock_inf.call_args.kwargs.get("prompt_type") == "document_chat"

    def test_document_question_with_empty_store_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/query",
            headers={**auth_headers},
            json={"question": "What is stated in the document regarding the revenue?"},
        )
        assert resp.status_code == 400
        assert "No documents ingested" in resp.json()["detail"]

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_session_history_tracking_across_turns(
        self, mock_inf, client, auth_headers
    ):
        mock_inf.side_effect = [
            InferenceResult(
                answer="I like Python programming.",
                model="qwen3.5:4b",
                latency_ms=50,
                tokens_generated=5,
            ),
            InferenceResult(
                answer="Python is widely used for AI and data science.",
                model="qwen3.5:4b",
                latency_ms=60,
                tokens_generated=8,
            ),
        ]

        sid = "user_session_123"

        # Turn 1
        resp1 = client.post(
            "/api/query",
            headers={**auth_headers},
            json={
                "question": "What is your favorite programming language?",
                "session_id": sid,
            },
        )
        assert resp1.status_code == 200
        assert resp1.json()["session_id"] == sid

        # Turn 2
        resp2 = client.post(
            "/api/query",
            headers={**auth_headers},
            json={
                "question": "Why do you like it?",
                "session_id": sid,
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == sid

        # Check that history was passed to turn 2
        history_arg = mock_inf.call_args_list[1].kwargs.get("history")
        assert history_arg is not None
        assert len(history_arg) >= 2
        assert history_arg[0].content == "What is your favorite programming language?"
        assert history_arg[1].content == "I like Python programming."

    def test_websocket_conversational_query_without_documents(self, client):
        token = generate_token("ws_conv_user")
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_json(
                {
                    "type": "query",
                    "question": "Hello!",
                    "session_id": "ws_session_1",
                }
            )

            # Receive pipeline stage / token events
            events = []
            while True:
                msg = ws.receive_json()
                events.append(msg)
                if msg.get("type") == "pipeline:done" or msg.get("type") == "error":
                    break

            done_event = events[-1]
            assert done_event["type"] == "pipeline:done"
            assert done_event["payload"]["facts_used"] == []
            assert done_event["payload"]["session_id"] == "ws_session_1"


class TestRoutingDocumentSafety:
    def test_greeting_with_real_question_goes_to_documents(self):
        q = "Hi, what did the report say about revenue?"
        assert classify_query_intent(q, has_documents=True) == QueryIntent.DOCUMENT_GROUNDED
        q = "Thanks, now what does it say about expenses?"
        assert classify_query_intent(q, has_documents=True) == QueryIntent.DOCUMENT_GROUNDED

    def test_short_greeting_tails_still_conversational(self):
        assert classify_query_intent("Hi there") == QueryIntent.CONVERSATIONAL
        assert classify_query_intent("Thank you very much") == QueryIntent.CONVERSATIONAL

    def test_what_is_goes_to_documents_when_ingested(self):
        assert classify_query_intent("What is the revenue?", has_documents=True) == QueryIntent.DOCUMENT_GROUNDED
        assert classify_query_intent("Who is the CEO?", has_documents=True) == QueryIntent.DOCUMENT_GROUNDED
        assert classify_query_intent("What is photosynthesis?", has_documents=False) == QueryIntent.GENERAL_KNOWLEDGE

    def test_mixed_query_not_general(self):
        q = "What is a CPU? What was revenue in 2021"
        assert classify_query_intent(q, has_documents=True) == QueryIntent.DOCUMENT_GROUNDED

    def test_followup_to_grounded_answer_keeps_retrieval(self):
        history = [
            ChatMessage("user", "Tell me about revenue", 1.0),
            ChatMessage("assistant", "Revenue rose.", 2.0, grounded=True),
        ]
        assert (
            classify_query_intent("Tell me more", has_documents=True, conversation_history=history)
            == QueryIntent.DOCUMENT_GROUNDED
        )


class TestChatRouting:
    """Chat-app routing: casual and general turns in document chats,
    no-document chats, relevance gating and follow-up rewriting."""

    def test_casual_requests_stay_conversational_with_documents(self):
        for q in [
            "Tell me a joke",
            "Can you write me a poem about the sea?",
            "Help me write an email to my landlord",
            "What can you do?",
            "lol",
            "I'm bored",
        ]:
            assert classify_query_intent(q, has_documents=True) == QueryIntent.CONVERSATIONAL, q

    def test_without_documents_unmarked_questions_use_general_knowledge(self):
        for q in ["tell me something interesting", "explain how transformers work", "recommend a good book"]:
            assert classify_query_intent(q, has_documents=False) == QueryIntent.GENERAL_KNOWLEDGE, q

    def test_explicit_document_reference_without_documents_stays_document(self):
        q = "What does the report say about revenue?"
        assert classify_query_intent(q, has_documents=False) == QueryIntent.DOCUMENT_GROUNDED

    def test_unrelated_question_with_documents_routes_to_general(self, clean_store):
        from precis.pipeline.orchestrator import route_chat_query

        clean_store.add_facts([
            Fact(subject="Acme Corp", verb="reported", object="revenue of 5 million dollars in 2022", source_doc="r.txt"),
        ])
        route = route_chat_query("Who won the 2018 FIFA World Cup?", clean_store, True, [], "m")
        assert route.answer_source == "general"
        assert route.intent == QueryIntent.GENERAL_KNOWLEDGE

    def test_related_question_with_documents_routes_to_documents(self, clean_store):
        from precis.pipeline.orchestrator import route_chat_query

        clean_store.add_facts([
            Fact(subject="Acme Corp", verb="reported", object="revenue of 5 million dollars in 2022", source_doc="r.txt"),
        ])
        route = route_chat_query("What revenue did Acme Corp report in 2022?", clean_store, True, [], "m")
        assert route.answer_source == "document"

    def test_explicit_marker_skips_relevance_gate(self, clean_store):
        from precis.pipeline.orchestrator import route_chat_query

        clean_store.add_facts([Fact(subject="Acme", verb="sells", object="widgets", source_doc="r.txt")])
        route = route_chat_query("What does the document say about the weather on Mars?", clean_store, True, [], "m")
        assert route.answer_source == "document"

    def test_followup_is_rewritten_for_retrieval(self, clean_store):
        from precis.pipeline.orchestrator import route_chat_query

        clean_store.add_facts([Fact(subject="Acme", verb="reported", object="revenue growth", source_doc="r.txt")])
        history = [
            ChatMessage("user", "What was Acme's revenue in 2022?", 1.0),
            ChatMessage("assistant", "5 million dollars.", 2.0, grounded=True),
        ]
        with patch(
            "precis.pipeline.orchestrator.rewrite_followup_query",
            return_value="What was Acme's revenue in 2021?",
        ) as rw:
            route = route_chat_query("What about 2021?", clean_store, True, history, "m")
        rw.assert_called_once()
        assert route.retrieval_query == "What was Acme's revenue in 2021?"
        assert route.answer_source == "document"

    def test_followup_rewrite_falls_back_without_ollama(self, clean_store):
        from precis.pipeline.inference import OllamaConnectionError
        from precis.pipeline.orchestrator import route_chat_query

        clean_store.add_facts([Fact(subject="Acme", verb="reported", object="revenue growth", source_doc="r.txt")])
        history = [
            ChatMessage("user", "What was Acme's revenue in 2022?", 1.0),
            ChatMessage("assistant", "5 million dollars.", 2.0, grounded=True),
        ]
        with patch(
            "precis.pipeline.orchestrator.rewrite_followup_query",
            side_effect=OllamaConnectionError("down"),
        ):
            route = route_chat_query("What about 2021?", clean_store, True, history, "m")
        assert route.retrieval_query == "What was Acme's revenue in 2022? What about 2021?"

    def test_standalone_question_is_not_rewritten(self, clean_store):
        from precis.pipeline.orchestrator import route_chat_query

        clean_store.add_facts([Fact(subject="Acme", verb="reported", object="revenue growth", source_doc="r.txt")])
        history = [ChatMessage("user", "Hi", 1.0), ChatMessage("assistant", "Hello!", 2.0)]
        with patch("precis.pipeline.orchestrator.rewrite_followup_query") as rw:
            route_chat_query("Which company reported revenue growth last year?", clean_store, True, history, "m")
        rw.assert_not_called()


class TestDocumentChatPrompt:
    def test_document_chat_prompt_has_facts_history_and_fallback_rule(self):
        from precis.pipeline.inference import build_document_chat_prompt

        prompt = build_document_chat_prompt(
            "Acme reported revenue of 5 million.",
            "What about 2021?",
            history=[ChatMessage("user", "Acme revenue in 2022?", 1.0)],
        )
        assert "Acme reported revenue of 5 million." in prompt
        assert "User: Acme revenue in 2022?" in prompt
        assert "general knowledge" in prompt
        assert prompt.rstrip().endswith("ASSISTANT:")

    def test_long_history_turns_are_truncated(self):
        prompt = build_conversational_prompt("next", history=[ChatMessage("assistant", "x" * 5000, 1.0)])
        assert "x" * 1000 in prompt
        assert "x" * 1001 not in prompt

    def test_evaluated_grounded_prompt_is_unchanged(self):
        from precis.pipeline.inference import STANDARD_PROMPT_TEMPLATE, build_prompt

        prompt = build_prompt("fact", "question", prompt_style="standard")
        assert prompt == STANDARD_PROMPT_TEMPLATE.format(context="fact", query="question")
        assert "Do not use outside knowledge" in prompt


class TestChatEndpoints:
    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_unrelated_question_in_document_chat_answers_from_general_knowledge(
        self, mock_inf, client, auth_headers, clean_store
    ):
        mock_inf.return_value = InferenceResult(
            answer="France won the 2018 World Cup.", model="m", latency_ms=10, tokens_generated=6
        )
        clean_store.add_facts([
            Fact(subject="legislation", verb="include", object="fossil fuel subsidies", negated=True, source_doc="c.txt"),
        ])
        resp = client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": "Who won the 2018 FIFA World Cup?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer_source"] == "general"
        assert data["facts_used"] == []
        assert mock_inf.call_args.kwargs.get("prompt_type") == "conversational"

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_casual_request_without_documents_is_answered(self, mock_inf, client, auth_headers):
        mock_inf.return_value = InferenceResult(
            answer="Why did the scarecrow win an award?", model="m", latency_ms=10, tokens_generated=8
        )
        resp = client.post("/api/query", headers=auth_headers, json={"question": "Tell me a joke"})
        assert resp.status_code == 200
        assert resp.json()["answer_source"] == "conversation"

    @patch("precis.pipeline.orchestrator.generate_answer")
    def test_document_answer_receives_history(self, mock_inf, client, auth_headers, clean_store):
        mock_inf.return_value = InferenceResult(answer="ok", model="m", latency_ms=10, tokens_generated=1)
        clean_store.add_facts([
            Fact(subject="legislation", verb="include", object="fossil fuel subsidies", negated=True, source_doc="c.txt"),
        ])
        sid = "doc_session"
        client.post("/api/query", headers=auth_headers, json={"question": "Hello!", "session_id": sid})
        client.post(
            "/api/query",
            headers=auth_headers,
            json={"question": "Does the legislation include fossil fuel subsidies?", "session_id": sid},
        )
        kwargs = mock_inf.call_args.kwargs
        assert kwargs.get("prompt_type") == "document_chat"
        assert [m.content for m in kwargs.get("history")] == ["Hello!", "ok"]


class TestThinkingDisabledForChat:
    @pytest.mark.parametrize(
        ("prompt_type", "expect_think_off"),
        [("conversational", True), ("document_chat", True), ("grounded", False)],
    )
    def test_think_flag_by_prompt_type(self, prompt_type, expect_think_off):
        from precis.pipeline.inference import generate_answer

        with patch("precis.pipeline.inference.requests.post") as post:
            post.return_value.json.return_value = {"response": "ok", "eval_count": 1}
            generate_answer("q", context="fact", model="m", prompt_type=prompt_type)
        payload = post.call_args.kwargs["json"]
        if expect_think_off:
            assert payload["think"] is False
        else:
            assert "think" not in payload

    def test_greeting_with_how_are_you_is_conversational(self):
        for q in ["hi! how are you?", "Hello, how are you doing today?", "hey there, what's up?"]:
            assert classify_query_intent(q, has_documents=True) == QueryIntent.CONVERSATIONAL, q
