from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from schemas.state import InterviewState
from schemas.interview import FocusAreaType, DifficultyLevel
from graph.interview_graph import (
    planner_node,
    interviewer_node,
    evaluator_node,
    reflection_node,
    difficulty_controller_node,
    coach_node
)
from utils.session import session_manager
from utils.logger import logger

app = FastAPI(
    title="AI Mock Interview Coach API",
    description="Multi-Agent LangGraph Backend API for Adaptive Job Mock Interviews",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Schemas
class StartInterviewRequest(BaseModel):
    target_role: str = Field(..., json_schema_extra={"example": "Senior AI Engineer"})
    resume_summary: str = Field(..., json_schema_extra={"example": "5 years Python, LangChain, RAG architecture"})
    focus_area: FocusAreaType = Field(default="Mixed")
    max_turns: int = Field(default=5, ge=1, le=10)


class StartInterviewResponse(BaseModel):
    session_id: str
    target_role: str
    current_difficulty: DifficultyLevel
    initial_question: str
    interview_strategy: Dict[str, Any]


class SubmitResponseRequest(BaseModel):
    session_id: str
    candidate_response: str = Field(..., min_length=1)


class SubmitResponseResponse(BaseModel):
    session_id: str
    turn_count: int
    latest_evaluation: Dict[str, Any]
    reflection_decision: str
    current_difficulty: DifficultyLevel
    next_question: Optional[str] = None
    is_completed: bool = False
    final_report: Optional[Dict[str, Any]] = None


# Endpoints
@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, str]:
    """Health check endpoint confirming API service status."""
    return {"status": "healthy", "service": "AI Mock Interview Coach API"}


@app.post(
    "/api/interview/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Interview"]
)
def start_interview(request_data: StartInterviewRequest) -> StartInterviewResponse:
    """Initializes interview session, runs Planner Agent, and generates first question."""
    logger.info(f"API: Received start interview request for role '{request_data.target_role}'.")

    initial_state: InterviewState = {
        "target_role": request_data.target_role,
        "resume_summary": request_data.resume_summary,
        "focus_area": request_data.focus_area,
        "interview_strategy": None,
        "conversation_history": [],
        "current_question": None,
        "candidate_response": None,
        "current_difficulty": "Mid-Level",
        "evaluations": [],
        "weak_areas": [],
        "strong_areas": [],
        "reflection_decision": None,
        "reflection_reasoning": None,
        "turn_count": 0,
        "max_turns": request_data.max_turns,
        "current_step": "initialized",
        "final_report": None
    }

    # Step 1: Execute Planner Agent
    planner_update = planner_node(initial_state)
    state = {**initial_state, **planner_update}

    # Step 2: Execute Interviewer Agent for initial question
    interviewer_update = interviewer_node(state)
    state = {**state, **interviewer_update}

    session_id = session_manager.create_session(state)
    logger.info(f"API: Interview session started successfully. Session ID: {session_id}.")

    return StartInterviewResponse(
        session_id=session_id,
        target_role=state["target_role"],
        current_difficulty=state["current_difficulty"],
        initial_question=state["current_question"],
        interview_strategy=state["interview_strategy"]
    )


@app.post(
    "/api/interview/respond",
    response_model=SubmitResponseResponse,
    status_code=status.HTTP_200_OK,
    tags=["Interview"]
)
def respond_to_interview(request_data: SubmitResponseRequest) -> SubmitResponseResponse:
    """Processes candidate response through Evaluator -> Reflection -> Difficulty Controller -> Interviewer/Coach."""
    state = session_manager.get_session(request_data.session_id)
    if not state:
        logger.error(f"API: Session {request_data.session_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{request_data.session_id}' not found."
        )

    if state.get("current_step") == "completed":
        logger.info(f"API: Session {request_data.session_id} is already completed.")
        return SubmitResponseResponse(
            session_id=request_data.session_id,
            turn_count=state.get("turn_count", 0),
            latest_evaluation=state.get("evaluations", [])[-1] if state.get("evaluations") else {},
            reflection_decision="finish",
            current_difficulty=state.get("current_difficulty", "Mid-Level"),
            next_question=None,
            is_completed=True,
            final_report=state.get("final_report")
        )

    # Update state with candidate response and append to conversation history transcript
    state["candidate_response"] = request_data.candidate_response
    candidate_message = {"role": "candidate", "content": request_data.candidate_response}
    state["conversation_history"] = state.get("conversation_history", []) + [candidate_message]


    # Execute Evaluator Agent
    evaluator_update = evaluator_node(state)
    state = {**state, **evaluator_update}

    # Execute Reflection Agent
    reflection_update = reflection_node(state)
    state = {**state, **reflection_update}

    reflection_decision = state.get("reflection_decision", "next_topic")

    # Handle completion routing
    if reflection_decision == "finish" or state.get("turn_count", 0) >= state.get("max_turns", 5):
        coach_update = coach_node(state)
        state = {**state, **coach_update}
        session_manager.update_session(request_data.session_id, state)
        
        logger.info(f"API: Interview finished for session {request_data.session_id}.")
        return SubmitResponseResponse(
            session_id=request_data.session_id,
            turn_count=state.get("turn_count", 0),
            latest_evaluation=state["evaluations"][-1] if state["evaluations"] else {},
            reflection_decision="finish",
            current_difficulty=state["current_difficulty"],
            next_question=None,
            is_completed=True,
            final_report=state["final_report"]
        )

    # Execute Difficulty Controller Agent if modifying difficulty or topic
    if reflection_decision in ["increase_difficulty", "decrease_difficulty", "next_topic"]:
        difficulty_update = difficulty_controller_node(state)
        state = {**state, **difficulty_update}

    # Execute Interviewer Agent for next question
    interviewer_update = interviewer_node(state)
    state = {**state, **interviewer_update}
    
    session_manager.update_session(request_data.session_id, state)

    return SubmitResponseResponse(
        session_id=request_data.session_id,
        turn_count=state["turn_count"],
        latest_evaluation=state["evaluations"][-1] if state["evaluations"] else {},
        reflection_decision=reflection_decision,
        current_difficulty=state["current_difficulty"],
        next_question=state["current_question"],
        is_completed=False,
        final_report=None
    )


@app.get(
    "/api/interview/status/{session_id}",
    status_code=status.HTTP_200_OK,
    tags=["Interview"]
)
def get_interview_status(session_id: str) -> Dict[str, Any]:
    """Retrieves full active interview state by session ID."""
    state = session_manager.get_session(session_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{session_id}' not found."
        )
    return state
