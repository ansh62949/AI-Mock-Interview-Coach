import operator
from typing import Annotated, Dict, List, Optional, TypedDict, Any
from schemas.interview import DifficultyLevel, ReflectionDecisionType


class InterviewState(TypedDict):
    """Comprehensive LangGraph state container passed between graph nodes."""

    session_id: Optional[str]
    
    # Candidate & Job Context
    target_role: str
    resume_summary: str
    focus_area: str
    
    candidate_profile: Optional[Dict[str, Any]]
    job_profile: Optional[Dict[str, Any]]
    match_analysis: Optional[Dict[str, Any]]
    cold_email: Optional[Dict[str, Any]]
    interview_plan: Optional[Dict[str, Any]]

    # Blueprint & Level Calibration
    interview_blueprint: Optional[Dict[str, Any]]
    candidate_level: Optional[str]
    job_level: Optional[str]
    interview_level: Optional[str]

    # ReAct Tool Execution Trace
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]

    # Strategy & RAG Context
    interview_strategy: Optional[Dict[str, Any]]
    rag_context: Annotated[List[str], operator.add]

    # Execution Transcript
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    current_question: Optional[str]
    candidate_response: Optional[str]
    current_difficulty: DifficultyLevel

    # Multi-dimensional Evaluations & Topic Tracking
    evaluations: Annotated[List[Dict[str, Any]], operator.add]
    weak_areas: Annotated[List[str], operator.add]
    strong_areas: Annotated[List[str], operator.add]
    current_topic: Optional[str]

    # Dynamic Routing State
    reflection_decision: Optional[ReflectionDecisionType]
    reflection_reasoning: Optional[str]
    suggested_followup_topic: Optional[str]
    follow_up_goal: Optional[str]
    follow_up_type: Optional[str]
    probe_count: int

    turn_count: int
    max_turns: int
    current_step: str

    # Final Coaching Output
    final_report: Optional[Dict[str, Any]]
