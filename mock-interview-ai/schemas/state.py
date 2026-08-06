import operator
from typing import Annotated, Dict, List, Optional, TypedDict, Any
from schemas.interview import DifficultyLevel, ReflectionDecisionType


class InterviewState(TypedDict):
    """LangGraph state container passed between graph nodes."""

    target_role: str
    resume_summary: str
    focus_area: str

    interview_strategy: Optional[Dict[str, Any]]

    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    current_question: Optional[str]
    candidate_response: Optional[str]
    current_difficulty: DifficultyLevel

    evaluations: Annotated[List[Dict[str, Any]], operator.add]
    weak_areas: Annotated[List[str], operator.add]
    strong_areas: Annotated[List[str], operator.add]

    reflection_decision: Optional[ReflectionDecisionType]
    reflection_reasoning: Optional[str]
    suggested_followup_topic: Optional[str]
    follow_up_goal: Optional[str]
    follow_up_type: Optional[str]
    probe_count: int

    turn_count: int
    max_turns: int
    current_step: str

    final_report: Optional[Dict[str, Any]]
