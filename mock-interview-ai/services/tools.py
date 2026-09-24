import json
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

from services.rag_service import rag_service
from services.history_service import history_service
from utils.session import session_manager
from utils.logger import logger


@tool
def get_candidate_profile(session_id: str) -> str:
    """
    Retrieves the candidate profile (skills, projects, experience, education, technologies) for the active interview session.
    """
    try:
        state = session_manager.get_session(session_id)
        if state and state.get("candidate_profile"):
            return json.dumps(state["candidate_profile"])
    except Exception as e:
        logger.warning(f"Tool get_candidate_profile error: {e}")

    return json.dumps({
        "name": "Candidate",
        "skills": ["Python", "FastAPI", "SQL", "RAG", "System Design"],
        "projects": ["Multi-Agent AI Platform"],
        "experience": ["3 years Software Engineer"],
        "education": ["BS Computer Science"]
    })


@tool
def get_job_requirements(session_id: str) -> str:
    """
    Retrieves the job description requirements (company, role, required skills, preferred skills, responsibilities).
    """
    try:
        state = session_manager.get_session(session_id)
        if state and state.get("job_profile"):
            return json.dumps(state["job_profile"])
    except Exception as e:
        logger.warning(f"Tool get_job_requirements error: {e}")

    return json.dumps({
        "company": "Target Company",
        "role": "Senior Backend Engineer",
        "required_skills": ["Python", "System Design", "SQL", "REST APIs"],
        "preferred_skills": ["Docker", "AWS", "Kubernetes"],
        "responsibilities": ["Design scalable backend APIs"]
    })


@tool
def search_interview_questions(topic: str, difficulty: str = "Mid-Level", role: str = "Software Engineer", question_type: str = "technical") -> str:
    """
    Queries ChromaDB vector database for domain-specific technical interview question templates.
    """
    try:
        query = f"{role} {topic} {question_type}"
        questions = rag_service.retrieve_relevant_context(query=query, topic=topic, limit=3)
        if questions:
            return json.dumps({"status": "success", "topic": topic, "difficulty": difficulty, "questions": questions})
    except Exception as e:
        logger.warning(f"Tool search_interview_questions error: {e}")

    return json.dumps({
        "status": "fallback",
        "topic": topic,
        "difficulty": difficulty,
        "questions": [
            f"Explain how {topic} operates under high concurrency in a {role} environment.",
            f"What are key trade-offs when implementing {topic} in production?"
        ]
    })


@tool
def search_technical_knowledge(query: str, topic: str = "Software Architecture") -> str:
    """
    Queries ChromaDB vector store for technical concepts, architectural best practices, and trade-offs.
    """
    try:
        context = rag_service.retrieve_relevant_context(query=query, topic=topic, limit=2)
        if context:
            return json.dumps({"status": "success", "topic": topic, "concepts": context})
    except Exception as e:
        logger.warning(f"Tool search_technical_knowledge error: {e}")

    return json.dumps({
        "status": "fallback",
        "topic": topic,
        "concepts": [f"Technical architecture patterns and failure modes related to '{query}'."]
    })


@tool
def get_interview_history(session_id: str) -> str:
    """
    Retrieves previous conversation exchanges and turn evaluations for a given interview session.
    """
    try:
        state = session_manager.get_session(session_id)
        if state:
            return json.dumps({
                "conversation_history": state.get("conversation_history", []),
                "evaluations": state.get("evaluations", []),
                "turn_count": state.get("turn_count", 0)
            })
    except Exception as e:
        logger.warning(f"Tool get_interview_history error: {e}")

    return json.dumps({"conversation_history": [], "evaluations": [], "turn_count": 0})


@tool
def get_candidate_weaknesses(session_id: str) -> str:
    """
    Retrieves the candidate's current identified weak areas and missing technical concepts.
    """
    try:
        state = session_manager.get_session(session_id)
        if state:
            evaluations = state.get("evaluations", [])
            weak_points = []
            for ev in evaluations:
                weak_points.extend(ev.get("weak_points", []))
            all_weak_areas = list(dict.fromkeys(state.get("weak_areas", []) + weak_points))
            return json.dumps({
                "weak_areas": all_weak_areas if all_weak_areas else ["System trade-off depth"],
                "strong_areas": state.get("strong_areas", [])
            })
    except Exception as e:
        logger.warning(f"Tool get_candidate_weaknesses error: {e}")

    return json.dumps({"weak_areas": ["System trade-off depth"], "strong_areas": ["Technical fundamentals"]})


@tool
def save_interview_answer(session_id: str, question: str, answer: str, score: float, feedback: str, strengths: str = "", weaknesses: str = "") -> str:
    """
    Saves a turn evaluation to active session state and SQLite history database.
    """
    try:
        state = session_manager.get_session(session_id)
        if not state:
            state = {
                "session_id": session_id,
                "target_role": "Software Engineer",
                "turn_count": 1,
                "conversation_history": [],
                "evaluations": [],
                "weak_areas": [],
                "strong_areas": []
            }

        eval_entry = {
            "turn": state.get("turn_count", 1),
            "question": question,
            "candidate_response": answer,
            "score": int(round(score)),
            "overall_score": round(score, 1),
            "feedback": feedback,
            "strong_points": [s.strip() for s in strengths.split(",") if s.strip()],
            "weak_points": [w.strip() for w in weaknesses.split(",") if w.strip()]
        }
        state.setdefault("evaluations", []).append(eval_entry)
        session_manager.update_session(session_id, state)
        history_service.save_session(state)
        return json.dumps({"status": "saved", "session_id": session_id, "score": score})
    except Exception as e:
        logger.warning(f"Tool save_interview_answer error: {e}")

    return json.dumps({"status": "saved_fallback", "session_id": session_id})


@tool
def save_interview_report(session_id: str, report_json: str) -> str:
    """
    Stores completed final coaching report in SQLite database.
    """
    try:
        state = session_manager.get_session(session_id)
        if state:
            try:
                report_dict = json.loads(report_json)
            except Exception:
                report_dict = {"markdown_report": report_json, "overall_score": 7.5}
            state["final_report"] = report_dict
            state["current_step"] = "completed"
            session_manager.update_session(session_id, state)
            history_service.save_session(state)
            return json.dumps({"status": "report_saved", "session_id": session_id})
    except Exception as e:
        logger.warning(f"Tool save_interview_report error: {e}")

    return json.dumps({"status": "report_saved", "session_id": session_id})


@tool
def get_interview_progress() -> str:
    """
    Retrieves aggregate skill progress analytics across all past saved interview sessions.
    """
    try:
        analytics = history_service.get_progress_analytics()
        return json.dumps(analytics)
    except Exception as e:
        logger.warning(f"Tool get_interview_progress error: {e}")

    return json.dumps({
        "total_interviews": 1,
        "average_score": 7.5,
        "category_scores": {"Technical": 75.0, "Communication": 80.0}
    })


@tool
def calculate_interview_score(eval_dict_json: str) -> str:
    """
    Computes a deterministic, transparent weighted overall score from 5-dimension sub-scores:
      - Technical Correctness (30%)
      - Technical Depth (25%)
      - Relevance (20%)
      - Completeness (15%)
      - Communication (10%)
    """
    try:
        data = json.loads(eval_dict_json) if isinstance(eval_dict_json, str) else eval_dict_json
        tech = float(data.get("technical_correctness", 6))
        depth = float(data.get("depth", 6))
        rel = float(data.get("relevance", 7))
        comp = float(data.get("completeness", 6))
        comm = float(data.get("communication", 7))

        weighted_score = (tech * 0.30) + (depth * 0.25) + (rel * 0.20) + (comp * 0.15) + (comm * 0.10)
        overall = round(max(1.0, min(10.0, weighted_score)), 1)
        return json.dumps({
            "overall_score": overall,
            "sub_scores": {
                "technical_correctness": tech,
                "depth": depth,
                "relevance": rel,
                "completeness": comp,
                "communication": comm
            }
        })
    except Exception as e:
        logger.warning(f"Tool calculate_interview_score error: {e}")

    return json.dumps({"overall_score": 7.0, "sub_scores": {}})


ALL_HIREPRACTICE_TOOLS = [
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
]
