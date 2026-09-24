import json
import pytest
from services.tools import (
    get_candidate_profile,
    get_job_requirements,
    search_interview_questions,
    search_technical_knowledge,
    get_interview_history,
    get_candidate_weaknesses,
    save_interview_answer,
    save_interview_report,
    get_interview_progress,
    calculate_interview_score
)


def test_tool_get_candidate_profile():
    res = get_candidate_profile.invoke({"session_id": "test_session"})
    data = json.loads(res)
    assert "skills" in data or "name" in data


def test_tool_get_job_requirements():
    res = get_job_requirements.invoke({"session_id": "test_session"})
    data = json.loads(res)
    assert "role" in data or "company" in data


def test_tool_search_interview_questions():
    res = search_interview_questions.invoke({"topic": "Java", "difficulty": "Mid-Level", "role": "Backend Engineer"})
    data = json.loads(res)
    assert "questions" in data
    assert len(data["questions"]) > 0


def test_tool_search_technical_knowledge():
    res = search_technical_knowledge.invoke({"query": "System Architecture", "topic": "Distributed Systems"})
    data = json.loads(res)
    assert "concepts" in data


def test_tool_get_interview_history():
    res = get_interview_history.invoke({"session_id": "test_session"})
    data = json.loads(res)
    assert "conversation_history" in data


def test_tool_get_candidate_weaknesses():
    res = get_candidate_weaknesses.invoke({"session_id": "test_session"})
    data = json.loads(res)
    assert "weak_areas" in data


def test_tool_save_interview_answer():
    res = save_interview_answer.invoke({
        "session_id": "test_session",
        "question": "What is RAG?",
        "answer": "Retrieval Augmented Generation combines search with LLMs.",
        "score": 8.5,
        "feedback": "Great explanation",
        "strengths": "RAG, Vector Search",
        "weaknesses": "None"
    })
    data = json.loads(res)
    assert data.get("status") in ["saved", "saved_fallback"]


def test_tool_save_interview_report():
    report_json = json.dumps({"overall_score": 8.5, "markdown_report": "Executive summary report"})
    res = save_interview_report.invoke({"session_id": "test_session", "report_json": report_json})
    data = json.loads(res)
    assert data.get("status") == "report_saved"


def test_tool_get_interview_progress():
    res = get_interview_progress.invoke({})
    data = json.loads(res)
    assert "average_score" in data or "total_interviews" in data


def test_tool_calculate_interview_score():
    eval_payload = json.dumps({
        "technical_correctness": 9,
        "depth": 8,
        "relevance": 9,
        "completeness": 8,
        "communication": 9
    })
    res = calculate_interview_score.invoke({"eval_dict_json": eval_payload})
    data = json.loads(res)
    assert "overall_score" in data
    assert data["overall_score"] >= 8.0


def test_langsmith_disabled_mode(monkeypatch):
    import os
    from utils.llm import setup_langsmith_tracing
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "")
    setup_langsmith_tracing()
    assert os.getenv("LANGCHAIN_TRACING_V2") == "false"


def test_langsmith_enabled_mode_failsafe(monkeypatch):
    import os
    from utils.llm import setup_langsmith_tracing
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "mock_key_12345")
    setup_langsmith_tracing()
    assert os.getenv("LANGCHAIN_TRACING_V2") == "true"
    assert os.getenv("LANGCHAIN_PROJECT") == "HirePractice-AI"


def test_adaptive_weakness_lifecycle():
    session_id = "test_adaptive_session"
    save_interview_answer.invoke({
        "session_id": session_id,
        "question": "Explain Kafka consumer groups.",
        "answer": "I don't know how consumer groups rebalance.",
        "score": 3.0,
        "feedback": "Needs work on Kafka partition rebalancing.",
        "strengths": "",
        "weaknesses": "Kafka consumer groups"
    })
    res = get_candidate_weaknesses.invoke({"session_id": session_id})
    data = json.loads(res)
    assert "Kafka consumer groups" in data.get("weak_areas", [])

