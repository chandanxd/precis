import requests
import json
import asyncio
import websockets

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000/ws"

def run_smoke_tests():
    print("--- Starting Live API & WebSocket Smoke Test ---")
    
    # 1. Health & Auth
    health = requests.get(f"{API_BASE}/api/health").json()
    print(f"1. Health check: {health}")
    assert health["status"] == "ok"

    token_res = requests.post(f"{API_BASE}/api/auth/token")
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]
    print(f"2. JWT Token acquired successfully.")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingestion
    doc_text = "Dr. Elena Rostova won the Renewable Energy Innovation Award at the global energy summit in Berlin on May 12, 2028."
    ingest_res = requests.post(
        f"{API_BASE}/api/ingest",
        json={"text": doc_text, "document_name": "smoke_test.html"},
        headers=headers
    )
    print(f"3. Ingestion response: {ingest_res.status_code} {ingest_res.json()}")
    assert ingest_res.status_code == 200

    # 3. Grounded Query
    query_res = requests.post(
        f"{API_BASE}/api/query",
        json={"question": "Who won the renewable energy innovation award?", "session_id": "smoke-session-1"},
        headers=headers
    )
    print(f"4. Grounded Query response: {query_res.status_code} {query_res.json()}")
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert "Elena Rostova" in q_data["answer"] or len(q_data.get("facts_used", [])) > 0
    print(f"   Model used: {q_data.get('model')}, Tokens: {q_data.get('tokens_used')}, Compression: {q_data.get('compression_rate')}")

    # 4. Casual Conversation ('hi' and 'who are you?')
    for q in ["hi", "who are you?"]:
        conv_res = requests.post(
            f"{API_BASE}/api/query",
            json={"question": q, "session_id": "smoke-session-1"},
            headers=headers
        )
        print(f"5. Conversational Query ('{q}') response: {conv_res.status_code} {conv_res.json()}")
        assert conv_res.status_code == 200
        c_data = conv_res.json()
        print(f"   Answer: {repr(c_data['answer'])} | Inference tokens: {c_data.get('inference_tokens')}")
        assert c_data.get('inference_tokens', 0) > 0
        assert len(c_data['answer']) > 0

    # 5. FactExplorer (/api/facts)
    facts_res = requests.get(f"{API_BASE}/api/facts", headers=headers)
    print(f"6. FactExplorer response: {facts_res.status_code} total facts: {facts_res.json().get('total')}")
    assert facts_res.status_code == 200
    assert facts_res.json().get('total', 0) > 0

    # 6. Error Handling (Missing auth)
    err_res = requests.post(
        f"{API_BASE}/api/query",
        json={"question": "Who won the award?"}
    )
    print(f"7. Unauthenticated query response (expected 401): {err_res.status_code}")
    assert err_res.status_code == 401

    # 7. WebSocket Live Test
    async def test_ws():
        uri = f"{WS_BASE}?token={token}"
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"type": "ping"}))
            pong = await websocket.recv()
            print(f"8. WebSocket ping/pong received: {json.loads(pong)}")
            assert json.loads(pong)["type"] == "pong"

            # Query via WS
            await websocket.send(json.dumps({
                "type": "query",
                "question": "Who won the award?",
                "session_id": "smoke-session-ws"
            }))
            
            while True:
                msg_str = await websocket.recv()
                msg = json.loads(msg_str)
                print(f"   WS message: {msg['type']}")
                if msg["type"] == "pipeline:done":
                    print(f"   WS Done Answer: {msg['payload']['answer']}")
                    break

    asyncio.run(test_ws())

    # Clean up facts
    requests.delete(f"{API_BASE}/api/facts", headers=headers)
    print("--- Smoke Tests Completed Successfully ---")

if __name__ == "__main__":
    run_smoke_tests()
