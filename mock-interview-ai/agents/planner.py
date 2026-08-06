from typing import Dict, Any
from schemas.state import InterviewState
from schemas.interview import InterviewStrategy
from prompts.planner import PLANNER_SYSTEM_PROMPT
from utils.llm import get_llm
from utils.logger import logger


def run_planner_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Planner Agent: Analyzes candidate profile and produces interview strategy.
    Single Responsibility: Strategic planning only.
    """
    target_role: str = state.get("target_role", "Software Engineer")
    resume_summary: str = state.get("resume_summary", "General engineering background")
    focus_area: str = state.get("focus_area", "Mixed")

    llm = get_llm(temperature=0.3)

    if llm is not None:
        try:
            planner_prompt = PLANNER_SYSTEM_PROMPT.format(
                target_role=target_role,
                resume_summary=resume_summary,
                focus_area=focus_area
            )
            structured_llm = llm.with_structured_output(InterviewStrategy, method="json_mode")
            strategy_result: InterviewStrategy = structured_llm.invoke(planner_prompt)
            
            logger.info(f"Planner Agent generated strategy with {len(strategy_result.key_topics)} key topics.")
            return {
                "interview_strategy": strategy_result.model_dump(),
                "current_difficulty": strategy_result.initial_difficulty,
                "current_step": "planning_completed"
            }
        except Exception as err:
            logger.warning(f"Planner Agent LLM invocation failed: {err}. Using default strategy.")

    # Standard fallback strategy when offline or API call fails
    default_strategy = InterviewStrategy(
        key_topics=[
            f"Core {target_role} Competencies",
            f"{focus_area} Problem Solving & Architecture",
            "System Scalability & Performance"
        ],
        initial_difficulty="Mid-Level",
        focus_summary=f"Structured {focus_area} evaluation tailored for candidate's target role: {target_role}."
    )

    logger.info("Planner Agent completed using default strategy.")
    return {
        "interview_strategy": default_strategy.model_dump(),
        "current_difficulty": default_strategy.initial_difficulty,
        "current_step": "planning_completed"
    }
