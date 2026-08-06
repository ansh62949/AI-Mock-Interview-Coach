from typing import Dict, Any, List
from schemas.state import InterviewState
from schemas.interview import DifficultyLevel
from utils.logger import logger


DIFFICULTY_LEVEL_ORDER: List[DifficultyLevel] = ["Junior", "Mid-Level", "Senior", "Staff"]


def run_difficulty_controller(state: InterviewState) -> Dict[str, Any]:
    """
    Difficulty Controller Agent: Manages state transitions for candidate difficulty level.
    Single Responsibility: Difficulty state adjustments only.
    """
    current_difficulty: DifficultyLevel = state.get("current_difficulty", "Mid-Level")
    reflection_decision: str = state.get("reflection_decision", "next_topic")

    try:
        current_index = DIFFICULTY_LEVEL_ORDER.index(current_difficulty)
    except ValueError:
        current_index = 1

    target_index = current_index

    if reflection_decision == "increase_difficulty":
        if current_index < len(DIFFICULTY_LEVEL_ORDER) - 1:
            target_index = current_index + 1
    elif reflection_decision == "decrease_difficulty":
        if current_index > 0:
            target_index = current_index - 1

    updated_difficulty: DifficultyLevel = DIFFICULTY_LEVEL_ORDER[target_index]

    if updated_difficulty != current_difficulty:
        logger.info(f"Difficulty Controller: Adjusted level from {current_difficulty} to {updated_difficulty}.")
    else:
        logger.info(f"Difficulty Controller: Maintained difficulty level at {current_difficulty}.")

    return {
        "current_difficulty": updated_difficulty,
        "current_step": "difficulty_adjusted"
    }
