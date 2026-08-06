from typing import Dict, Any, List
from schemas.state import InterviewState
from schemas.interview import FinalReport
from prompts.coach import COACH_SYSTEM_PROMPT
from utils.llm import get_llm
from utils.logger import logger


def run_coach_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Coach Agent: Synthesizes cumulative turn evaluations into a final coaching report.
    Single Responsibility: Coaching report generation only.
    """
    target_role: str = state.get("target_role", "Software Engineer")
    focus_area: str = state.get("focus_area", "Mixed")
    resume_summary: str = state.get("resume_summary", "")

    evaluations: List[Dict[str, Any]] = state.get("evaluations", [])
    conversation_history: List[Dict[str, str]] = state.get("conversation_history", [])
    synthesized_strong_areas: List[str] = list(set(state.get("strong_areas", [])))
    synthesized_weak_areas: List[str] = list(set(state.get("weak_areas", [])))

    # Compute overall average score across all turns
    evaluation_scores = [entry.get("score", 6) for entry in evaluations]
    overall_score = round(sum(evaluation_scores) / len(evaluation_scores), 1) if evaluation_scores else 7.0

    evaluations_summary_text = "\n".join(
        [f"- Turn {e.get('turn')}: Question: '{e.get('question')}' | Score: {e.get('score')}/10 | Feedback: {e.get('feedback')}"
         for e in evaluations]
    ) if evaluations else "No turn evaluation logs recorded."

    history_summary_text = "\n".join(
        [f"{m.get('role').capitalize()}: {m.get('content')}" for m in conversation_history]
    ) if conversation_history else "No transcript recorded."

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

            
            logger.info(f"Coach Agent generated final report with score: {report_result.overall_score}/10.")
            return {
                "final_report": report_result.model_dump(),
                "current_step": "completed"
            }
        except Exception as err:
            logger.warning(f"Coach Agent LLM invocation failed: {err}. Using default final report.")

    # Fallback Markdown Report Generator
    recommendation = "Strong Candidate - Recommend Next Round" if overall_score >= 7.5 else "Needs Target Practice"
    formatted_markdown_report = f"""# AI Mock Interview Coaching Report

## Executive Summary
- **Target Role**: {target_role}
- **Interview Focus**: {focus_area}
- **Overall Rating**: **{overall_score} / 10**
- **Recommendation**: {recommendation}

Candidate completed the mock interview for **{target_role}**. Demonstrated good communication and domain concepts, with areas identified for architectural trade-off depth.

---

## Demonstrated Strengths
{_format_bullet_points(synthesized_strong_areas or ["Solid technical fundamentals", "Direct problem-solving approach"])}

## Key Areas for Growth
{_format_bullet_points(synthesized_weak_areas or ["Elaborate on quantitative metrics", "Address edge cases and failure modes"])}

---

## Turn-by-Turn Evaluation Log
{evaluations_summary_text}

---

## Actionable Study Plan
1. Practice framing responses using the STAR method (Situation, Task, Action, Result).
2. Deep dive into system trade-offs for latency, consistency, and fault tolerance.
"""

    fallback_report = FinalReport(
        overall_score=overall_score,
        executive_summary=f"Candidate achieved an overall performance rating of {overall_score}/10 for {target_role}.",
        strong_areas=synthesized_strong_areas or ["Technical communication"],
        weak_areas=synthesized_weak_areas or ["System scalability details"],
        recommendation=recommendation,
        markdown_report=formatted_markdown_report
    )

    logger.info("Coach Agent completed using fallback final report.")
    return {
        "final_report": fallback_report.model_dump(),
        "current_step": "completed"
    }


def _format_bullet_points(items: List[str]) -> str:
    """Formats a list of string items as Markdown bullet points."""
    return "\n".join([f"- {item}" for item in items])
