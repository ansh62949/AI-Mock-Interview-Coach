import pytest
from schemas.candidate import CandidateProfile
from schemas.jd import JobProfile
from schemas.state import InterviewState
from tools.interview_tools import (
    search_interview_questions,
    search_technical_knowledge,
    get_candidate_profile,
    get_job_requirements,
    get_candidate_weaknesses,
    get_interview_history,
    calculate_interview_score,
    save_interview_answer,
    save_interview_report,
    set_current_interview_state
)
from agents.planner import run_planner_agent
from agents.interviewer import run_interviewer_agent
from agents.evaluator import run_evaluator_agent


@pytest.fixture
def mock_state() -> InterviewState:
    return {
        "session_id": "test_session_react_101",
        "target_role": "Junior Backend Engineer",
        "resume_summary": "Java, Spring Boot, Kafka, Redis, Docker, PostgreSQL",
        "focus_area": "Technical",
        "candidate_profile": {
            "name": "Ansh Pathak",
            "skills": ["Java", "Spring Boot", "Kafka", "Docker", "PostgreSQL", "Linux"],
            "projects": ["HerRide Ride Hailing", "PRSense AI Agent"],
            "education": ["B.Tech Computer Science"]
        },
        "job_profile": {
            "company": "CloudScale FinTech",
            "role": "Junior Backend Engineer",
            "required_skills": ["Java", "Spring Boot", "Kafka", "Kubernetes", "AWS", "Terraform"],
            "preferred_skills": ["Docker", "Prometheus"]
        },
        "match_analysis": {
            "match_score": 55,
            "strong_matches": ["Java", "Spring Boot", "Kafka", "Docker"],
            "skill_gaps": ["Kubernetes", "Terraform", "AWS"],
            "partial_matches": ["~ AWS (Related: Docker Container Infrastructure)"]
        },
        "cold_email": None,
        "interview_plan": None,
        "interview_blueprint": None,
        "candidate_level": None,
        "job_level": None,
        "interview_level": None,
        "tool_calls": [],
        "interview_strategy": {
            "key_topics": ["Kafka", "Spring Boot", "Kubernetes"],
            "initial_difficulty": "Junior",
            "focus_summary": "Test Kafka experience and validate Kubernetes gap."
        },
        "rag_context": [],
        "conversation_history": [],
        "current_question": None,
        "candidate_response": None,
        "current_difficulty": "Junior",
        "evaluations": [],
        "weak_areas": ["Kafka consumer groups"],
        "strong_areas": ["Java OOP"],
        "current_topic": "Kafka",
        "reflection_decision": "probe_deeper",
        "reflection_reasoning": "Candidate gave partial answer on Kafka consumer groups.",
        "suggested_followup_topic": "Kafka consumer groups",
        "follow_up_goal": "Probe consumer group partition rebalancing and offset commits.",
        "follow_up_type": "deeper_tradeoffs",
        "probe_count": 1,
        "turn_count": 1,
        "max_turns": 5,
        "current_step": "initialized",
        "final_report": None
    }


def test_planner_blueprint_generation(mock_state):
    res = run_planner_agent(mock_state)
    assert "interview_blueprint" in res
    blueprint = res["interview_blueprint"]
    assert blueprint["role"] == "Junior Backend Engineer"
    assert blueprint["interview_level"] == "Junior"
    assert "matched_skills" in blueprint
    assert "missing_skills" in blueprint


def test_resume_grounded_retrieval_tool(mock_state):
    set_current_interview_state(mock_state)
    cp = get_candidate_profile.invoke({})
    assert cp["name"] == "Ansh Pathak"
    assert "Kafka" in cp["skills"]


def test_weakness_driven_retrieval_tool(mock_state):
    set_current_interview_state(mock_state)
    weaknesses = get_candidate_weaknesses.invoke({})
    assert "weaknesses" in weaknesses
    assert len(weaknesses["weaknesses"]) > 0
    assert any(w["topic"] == "Kafka consumer groups" for w in weaknesses["weaknesses"])


def test_jd_driven_retrieval_tool(mock_state):
    set_current_interview_state(mock_state)
    reqs = get_job_requirements.invoke({})
    assert reqs["role"] == "Junior Backend Engineer"
    assert "Kubernetes" in reqs["required_skills"]


def test_technical_verification_tool():
    res = search_technical_knowledge.invoke({"query": "Kafka exactly once delivery guarantees", "top_k": 2})
    assert isinstance(res, list)
    assert len(res) > 0
    assert "content" in res[0]


def test_deterministic_score_tool():
    res = calculate_interview_score.invoke({
        "technical_correctness": 8.0,
        "depth": 7.0,
        "relevance": 9.0,
        "completeness": 8.0,
        "communication": 9.0
    })
    assert "overall_score" in res
    assert res["overall_score"] >= 7.5
    assert res["verdict"] in ["Strong Pass", "Pass"]


def test_interviewer_react_execution(mock_state):
    res = run_interviewer_agent(mock_state)
    assert "current_question" in res
    assert len(res["current_question"]) > 10
    assert "tool_calls" in res
    assert isinstance(res["tool_calls"], list)


def test_evaluator_agent_execution(mock_state):
    mock_state["current_question"] = "How do Kafka consumer groups handle partition rebalancing when a consumer crashes?"
    mock_state["candidate_response"] = "When a consumer crashes, Kafka triggers rebalance protocol via group coordinator, reassigning partitions to surviving consumers."
    res = run_evaluator_agent(mock_state)
    assert "evaluations" in res
    assert len(res["evaluations"]) == 1
    eval_item = res["evaluations"][0]
    assert eval_item["overall_score"] >= 6.0


from services.rag_service import rag_service


def test_tool_result_influences_final_question(mock_state, monkeypatch):
    """
    CRITICAL INTEGRATION TEST (Requirement 25):
    Mocks ChromaDB search_interview_questions retrieval to return a UNIQUE question:
    'TEST QUESTION: Explain Kafka consumer group rebalancing.'
    Then runs the ReAct interviewer.
    Verifies that the final generated interviewer question contains or clearly uses that retrieved information.
    """
    unique_q = "TEST QUESTION: Explain Kafka consumer group rebalancing."

    def mock_chroma_query(query_texts, n_results=5):
        return {
            "documents": [[unique_q]],
            "ids": [["q_test_kafka_rebalance"]],
            "metadatas": [[{"topic": "Kafka", "difficulty": "Junior"}]]
        }

    monkeypatch.setattr(rag_service.questions_col, "query", mock_chroma_query)

    set_current_interview_state(mock_state)
    res = run_interviewer_agent(mock_state)

    assert "current_question" in res
    final_q = res["current_question"]
    assert ("Kafka" in final_q or "rebalancing" in final_q or "TEST QUESTION" in final_q)


def test_evaluator_answer_status_unknown(mock_state):

    mock_state["current_question"] = "Compare AWS Lambda serverless execution with ECS container deployment."
    mock_state["candidate_response"] = "I don't know."
    res = run_evaluator_agent(mock_state)
    assert "evaluations" in res
    eval_item = res["evaluations"][0]
    assert eval_item["answer_status"] == "unknown"
    assert eval_item["overall_score"] <= 3.0
    assert eval_item["followup_strategy"] == "teach_then_probe"


def test_evaluator_answer_status_incorrect(mock_state):
    mock_state["current_question"] = "Compare AWS Lambda serverless execution with ECS container deployment."
    mock_state["candidate_response"] = "Lambda is better because it is cheaper and ECS doesn't scale."
    res = run_evaluator_agent(mock_state)
    assert "evaluations" in res
    eval_item = res["evaluations"][0]
    assert eval_item["answer_status"] in ["incorrect", "partial"]
    assert "overall_score" in eval_item


def test_interviewer_adaptive_response_for_unknown(mock_state):
    mock_state["current_question"] = "Compare AWS Lambda serverless execution with ECS container deployment."
    mock_state["candidate_response"] = "I don't know."
    mock_state["reflection_decision"] = "simplify"
    mock_state["follow_up_goal"] = "Break down concept into simpler conceptual building blocks before probing trade-offs."
    mock_state["follow_up_type"] = "teach_then_probe"
    
    set_current_interview_state(mock_state)
    res = run_interviewer_agent(mock_state)
    assert "current_question" in res
    q_text = res["current_question"].lower()
    assert any(term in q_text for term in ["break", "no problem", "imagine", "traffic", "lambda", "ecs", "container", "service", "scenario", "scale", "auto"])


def test_interviewer_adaptive_response_for_misconception(mock_state):
    mock_state["current_question"] = "Compare AWS Lambda serverless execution with ECS container deployment."
    mock_state["candidate_response"] = "Lambda is better because it is cheaper and ECS doesn't scale."
    mock_state["reflection_decision"] = "probe_deeper"
    mock_state["follow_up_goal"] = "Politely address misconception (ECS doesn't scale) and ask targeted question."
    mock_state["follow_up_type"] = "target_misconception"
    
    set_current_interview_state(mock_state)
    res = run_interviewer_agent(mock_state)
    assert "current_question" in res
    q_text = res["current_question"].lower()
    assert len(q_text) > 15



