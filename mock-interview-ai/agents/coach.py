import json
from typing import Dict, Any, List
from schemas.state import InterviewState
from schemas.interview import FinalReport, CategoryScore
from prompts.coach import COACH_SYSTEM_PROMPT
from tools.interview_tools import save_interview_report, get_interview_history, get_candidate_weaknesses, set_current_interview_state
from utils.llm import get_llm
from utils.logger import logger


def _format_bullet_points(items: List[str]) -> str:
    if not items:
        return "- None noted"
    return "\n".join([f"- {item}" for item in items])


def run_coach_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Coach Agent: Synthesizes turn logs and evaluations into a structured executive report.
    """
    set_current_interview_state(state)

    session_id: str = state.get("session_id") or "session_default"
    target_role: str = state.get("target_role", "Software Engineer")
    focus_area: str = state.get("focus_area", "Mixed")
    resume_summary: str = state.get("resume_summary", "")

    evaluations: List[Dict[str, Any]] = state.get("evaluations", [])
    conversation_history: List[Dict[str, str]] = state.get("conversation_history", [])
    synthesized_strong_areas: List[str] = list(set(state.get("strong_areas", [])))
    synthesized_weak_areas: List[str] = list(set(state.get("weak_areas", [])))

    # Compute overall average score across all turns
    evaluation_scores = [e.get("overall_score", e.get("score", 6.0)) for e in evaluations]
    overall_score = round(sum(evaluation_scores) / len(evaluation_scores), 1) if evaluation_scores else 7.0

    evaluations_summary_text = "\n".join(
        [f"- Turn {e.get('turn')}: Question: '{e.get('question')}' | Score: {e.get('overall_score', e.get('score'))}/10 | Feedback: {e.get('feedback')}"
         for e in evaluations]
    ) if evaluations else "No turn evaluation logs recorded."

    history_summary_text = "\n".join(
        [f"{m.get('role').capitalize()}: {m.get('content')}" for m in conversation_history]
    ) if conversation_history else "No transcript recorded."

    # Identify questions answered well (score >= 7.5) and poorly (score < 7.5)
    questions_well = [e.get("question", "") for e in evaluations if e.get("overall_score", e.get("score", 0)) >= 7.5 and e.get("question")]
    questions_poorly = [e.get("question", "") for e in evaluations if e.get("overall_score", e.get("score", 0)) < 7.5 and e.get("question")]

    category_scores = [
        CategoryScore(category="Technical Correctness", score=round(overall_score, 1), strengths=synthesized_strong_areas[:3], weaknesses=synthesized_weak_areas[:2], recommended_topics=["Deep Dive Architecture"]),
        CategoryScore(category="Communication & Structure", score=round(min(10.0, overall_score + 0.5), 1), strengths=["Clear explanations"], weaknesses=["Add quantitative metrics"], recommended_topics=["STAR Method"]),
        CategoryScore(category="System Design & Scalability", score=round(max(1.0, overall_score - 0.5), 1), strengths=["High-level component design"], weaknesses=["Edge cases under peak load"], recommended_topics=["Kafka Partitioning", "Redis Eviction"])
    ]

    llm = get_llm(temperature=0.3)

    if llm is not None:
        try:
            coach_prompt = COACH_SYSTEM_PROMPT.format(
                target_role=target_role,
                focus_area=focus_area,
                resume_summary=resume_summary,
                history_summary=history_summary_text,
                evaluations_summary=evaluations_summary_text,
                strong_areas=", ".join(synthesized_strong_areas) if synthesized_strong_areas else "Solid technical fundamentals",
                weak_areas=", ".join(synthesized_weak_areas) if synthesized_weak_areas else "Architectural trade-off depth"
            )
            structured_llm = llm.with_structured_output(FinalReport, method="json_mode")
            report_result: FinalReport = structured_llm.invoke(coach_prompt)
            
            # Persist report via tool call
            save_interview_report.invoke({
                "overall_score": report_result.overall_score,
                "strengths": report_result.top_strengths,
                "weaknesses": report_result.top_weaknesses,
                "recommendations": report_result.recommended_study_plan
            })

            logger.info(f"Coach Agent generated final report with score: {report_result.overall_score}/10.")
            return {
                "final_report": report_result.model_dump(),
                "current_step": "completed"
            }
        except Exception as err:
            logger.warning(f"Coach Agent LLM invocation failed: {err}. Using default final report.")

    # Fallback Markdown Report Generator
    recommendation = "Strong Candidate - Recommend Next Round" if overall_score >= 7.5 else "Needs Target Practice"
    formatted_markdown_report = f"""# HirePractice AI — Interview Coaching Report

## Executive Summary
- **Target Role**: {target_role}
- **Overall Score**: **{overall_score} / 10**
- **Recommendation**: {recommendation}

Candidate completed the mock interview for **{target_role}**. Demonstrated good communication and domain concepts, with specific areas identified for growth in technical depth.

---

## Top Strengths
{_format_bullet_points(synthesized_strong_areas[:5] or ["Solid technical fundamentals", "Direct problem-solving approach"])}

## Top Areas for Growth
{_format_bullet_points(synthesized_weak_areas[:5] or ["Elaborate on quantitative metrics", "Address edge cases and failure modes"])}

---

## Recommended Study Roadmap
1. Practice framing responses using the STAR method (Situation, Task, Action, Result).
2. Deep dive into system design failure recovery modes and operational metrics.
3. Prepare concrete trade-off comparisons for key frameworks in target role.
"""

    default_report = FinalReport(
        overall_score=overall_score,
        category_scores=category_scores,
        executive_summary=f"Completed {target_role} evaluation with overall score of {overall_score}/10.",
        top_strengths=synthesized_strong_areas[:5] or ["Solid technical fundamentals"],
        top_weaknesses=synthesized_weak_areas[:5] or ["Architectural trade-offs"],
        questions_answered_well=questions_well,
        questions_answered_poorly=questions_poorly,
        recommended_study_plan=["Deep dive system design", "Review database indexing", "Practice quantitative explanations"],
        next_difficulty_recommendation="Mid-Level",
        markdown_report=formatted_markdown_report
    )

    save_interview_report.invoke({
        "overall_score": overall_score,
        "strengths": default_report.top_strengths,
        "weaknesses": default_report.top_weaknesses,
        "recommendations": default_report.recommended_study_plan
    })

    return {
        "final_report": default_report.model_dump(),
        "current_step": "completed"
    }
