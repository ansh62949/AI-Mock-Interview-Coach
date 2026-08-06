import pytest
from agents.planner import run_planner_agent
from agents.interviewer import run_interviewer_agent
from agents.evaluator import run_evaluator_agent
from agents.reflection import run_reflection_agent
from agents.difficulty import run_difficulty_controller
from agents.coach import run_coach_agent


def test_planner_agent():
    state = {
        "target_role": "Senior AI Engineer",
        "resume_summary": "Built RAG systems",
        "focus_area": "Technical"
    }
    update = run_planner_agent(state)
    assert "interview_strategy" in update
    assert update["current_difficulty"] in ["Junior", "Mid-Level", "Senior", "Staff"]


def test_interviewer_agent():
    state = {
        "target_role": "Senior AI Engineer",
        "resume_summary": "Python",
        "focus_area": "Technical",
        "current_difficulty": "Senior",
        "interview_strategy": {"key_topics": ["LLMs"], "focus_summary": "Tech"},
        "turn_count": 0
    }
    update = run_interviewer_agent(state)
    assert "current_question" in update
    assert update["turn_count"] == 1


def test_evaluator_agent():
    state = {
        "target_role": "AI Engineer",
        "current_difficulty": "Mid-Level",
        "current_question": "What is RAG?",
        "candidate_response": "Retrieval Augmented Generation combines vector search with LLMs.",
        "turn_count": 1
    }
    update = run_evaluator_agent(state)
    assert "evaluations" in update
    assert len(update["evaluations"]) == 1
    assert "score" in update["evaluations"][0]


def test_reflection_agent_increase():
    state = {
        "turn_count": 1,
        "max_turns": 5,
        "evaluations": [{"score": 9, "feedback": "Great"}]
    }
    update = run_reflection_agent(state)
    assert update["reflection_decision"] == "increase_difficulty"


def test_reflection_agent_finish():
    state = {
        "turn_count": 5,
        "max_turns": 5,
        "evaluations": [{"score": 7, "feedback": "Solid"}]
    }
    update = run_reflection_agent(state)
    assert update["reflection_decision"] == "finish"


def test_difficulty_controller():
    state = {
        "current_difficulty": "Mid-Level",
        "reflection_decision": "increase_difficulty"
    }
    update = run_difficulty_controller(state)
    assert update["current_difficulty"] == "Senior"


def test_coach_agent():
    state = {
        "target_role": "AI Engineer",
        "focus_area": "Technical",
        "resume_summary": "Resume text",
        "evaluations": [{"turn": 1, "score": 8, "feedback": "Good"}],
        "strong_areas": ["RAG"],
        "weak_areas": ["Caching"]
    }
    update = run_coach_agent(state)
    assert "final_report" in update
    assert update["final_report"]["overall_score"] == 8.0
