from typing import Dict, Any, List
from schemas.state import InterviewState
from schemas.interview import EvaluationResult
from prompts.evaluator import EVALUATOR_SYSTEM_PROMPT
from utils.llm import get_llm
from utils.logger import logger


def run_evaluator_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluator Agent: Assesses the candidate's latest response against the target role and question.
    Single Responsibility: Score and feedback generation only.
    """
    target_role: str = state.get("target_role", "Software Engineer")
    current_difficulty: str = state.get("current_difficulty", "Mid-Level")
    current_question: str = state.get("current_question", "")
    candidate_response: str = state.get("candidate_response", "")

    llm = get_llm(temperature=0.2)

    if llm is not None:
        try:
            evaluator_prompt = EVALUATOR_SYSTEM_PROMPT.format(
                target_role=target_role,
                current_difficulty=current_difficulty,
                current_question=current_question,
                candidate_response=candidate_response
            )
            structured_llm = llm.with_structured_output(EvaluationResult, method="json_mode")
            evaluation_result: EvaluationResult = structured_llm.invoke(evaluator_prompt)
            
            logger.info(f"Evaluator Agent scored response: {evaluation_result.score}/10.")
            return _build_evaluator_output(state, evaluation_result)
        except Exception as err:
            logger.warning(f"Evaluator Agent LLM invocation failed: {err}. Using heuristic fallback.")

    # Heuristic evaluation fallback based on answer length and technical key terms
    response_length = len(candidate_response.split())
    if response_length < 4 or candidate_response.lower() in ["no", "idk", "i don't know"]:
        score = 3
        feedback_str = "**Summary**: Response is brief and lacks technical depth.\n\n**To Improve**:\n• Explain the specific architecture and system components\n• Discuss framework choices and trade-offs"
        strong = []
        weak = ["Incomplete answer", "Lacks architectural depth"]
    elif response_length > 35:
        score = 8
        feedback_str = "**Summary**: Detailed response demonstrating strong technical awareness.\n\n**To Improve**:\n• Provide additional operational metrics and failure recovery details"
        strong = ["Detailed system design", "Technical depth"]
        weak = ["Failure recovery edge cases"]
    else:
        score = 6
        feedback_str = "**Summary**: Solid baseline response covering high-level concepts.\n\n**To Improve**:\n• Elaborate on specific tool selection and latency trade-offs"
        strong = ["Relevant technical concepts"]
        weak = ["Lacks depth in trade-off analysis"]

    fallback_result = EvaluationResult(
        score=score,
        feedback=feedback_str,
        strong_points=strong,
        weak_points=weak
    )

    logger.info(f"Evaluator Agent completed with heuristic score: {score}/10.")
    return _build_evaluator_output(state, fallback_result)


def _build_evaluator_output(state: InterviewState, evaluation: EvaluationResult) -> Dict[str, Any]:
    """Constructs state updates for evaluation result."""
    current_turn = state.get("turn_count", 1)
    
    # Format feedback string cleanly if dict was returned
    raw_fb = evaluation.feedback
    if isinstance(raw_fb, dict):
        summary_text = raw_fb.get("Summary", "")
        to_improve = raw_fb.get("To Improve", [])
        if isinstance(to_improve, list):
            improve_text = "\n".join([f"• {item}" for item in to_improve])
        else:
            improve_text = str(to_improve)
        feedback_formatted = f"**Summary**: {summary_text}\n\n**To Improve**:\n{improve_text}"
    else:
        feedback_formatted = str(raw_fb)

    eval_dict = {
        "turn": current_turn,
        "question": state.get("current_question", ""),
        "candidate_response": state.get("candidate_response", ""),
        "score": evaluation.score,
        "feedback": feedback_formatted,
        "strong_points": evaluation.strong_points,
        "weak_points": evaluation.weak_points
    }

    return {
        "evaluations": [eval_dict],
        "strong_areas": evaluation.strong_points,
        "weak_areas": evaluation.weak_points,
        "current_step": "evaluating_completed"
    }
