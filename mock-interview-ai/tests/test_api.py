import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_full_interview_api_flow():
    # 1. Start Interview
    start_res = client.post("/api/interview/start", json={
        "target_role": "Senior AI Engineer",
        "resume_summary": "Built LangChain and RAG applications",
        "focus_area": "Technical",
        "max_turns": 1
    })
    assert start_res.status_code in [200, 201]
    data = start_res.json()
    session_id = data["session_id"]
    assert "initial_question" in data

    # 2. Respond to Question (turn 1, max 1)
    resp_res = client.post("/api/interview/respond", json={
        "session_id": session_id,
        "candidate_response": "I design RAG pipelines with hybrid BM25 and vector search, cached with Redis."
    })
    assert resp_res.status_code == 200
    resp_data = resp_res.json()
    assert resp_data["is_completed"] is True
    assert "final_report" in resp_data

    # 3. Check status
    status_res = client.get(f"/api/interview/status/{session_id}")
    assert status_res.status_code == 200
    assert status_res.json()["target_role"] == "Senior AI Engineer"
