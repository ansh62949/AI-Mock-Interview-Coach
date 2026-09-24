from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from schemas.state import InterviewState
from schemas.candidate import CandidateProfile, ResumeAnalysis
from schemas.jd import JobProfile, MatchAnalysis
from schemas.interview import FocusAreaType, DifficultyLevel, ColdEmailOutput, InterviewPlan
from graph.interview_graph import (
    planner_node,
    interviewer_node,
    evaluator_node,
    reflection_node,
    difficulty_controller_node,
    coach_node
)
from services.resume_parser import extract_raw_text_from_bytes, parse_resume_content
from services.jd_parser import parse_job_description
from services.match_engine import calculate_match_analysis
from services.cold_email import generate_personalized_cold_email
from services.history_service import history_service
from services.rag_service import rag_service
from utils.session import session_manager
from utils.logger import logger

app = FastAPI(
    title="HirePractice AI API",
    description="Production Multi-Agent LangGraph SaaS Platform for Resume Analysis, JD Matching, Cold Email & Adaptive AI Mock Interviews.",
    version="2.0.0"
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
    target_role: str = Field(..., json_schema_extra={"example": "Senior Backend Engineer"})
    resume_summary: Optional[str] = Field(default="", description="Resume text summary")
    candidate_profile: Optional[Dict[str, Any]] = Field(default=None)
    job_profile: Optional[Dict[str, Any]] = Field(default=None)
    match_analysis: Optional[Dict[str, Any]] = Field(default=None)
    focus_area: FocusAreaType = Field(default="Mixed")
    max_turns: int = Field(default=5, ge=1, le=10)


class StartInterviewResponse(BaseModel):
    session_id: str
    target_role: str
    current_difficulty: DifficultyLevel
    initial_question: str
    interview_strategy: Dict[str, Any]
    interview_plan: Optional[Dict[str, Any]] = None
    interview_blueprint: Optional[Dict[str, Any]] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


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
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class TextParseRequest(BaseModel):
    text: str = Field(..., min_length=10)


class JDParseRequest(BaseModel):
    jd_text: str = Field(..., min_length=10)


class MatchRequest(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile


class DebugMatchRequest(BaseModel):
    resume_text: Optional[str] = Field(default=None)
    jd_text: Optional[str] = Field(default=None)
    candidate_profile: Optional[CandidateProfile] = Field(default=None)
    job_profile: Optional[JobProfile] = Field(default=None)


class ColdEmailRequest(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile


# Endpoints
@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, str]:
    """Health check endpoint confirming API service status."""
    return {"status": "healthy", "service": "HirePractice AI API", "version": "2.0.0"}


# STEP 1: RESUME PARSING
@app.post("/api/resume/upload", tags=["Resume Service"])
async def upload_resume(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Uploads resume file (PDF or DOCX), extracts text, and returns Candidate Profile + Analysis."""
    try:
        contents = await file.read()
        raw_text = extract_raw_text_from_bytes(contents, file.filename)
        profile, analysis = parse_resume_content(raw_text)
        return {
            "status": "success",
            "filename": file.filename,
            "raw_text": raw_text,
            "candidate_profile": profile.model_dump(),
            "resume_analysis": analysis.model_dump()
        }
    except Exception as e:
        logger.error(f"API Resume Upload Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/resume/parse-text", tags=["Resume Service"])
def parse_resume_text(req: TextParseRequest) -> Dict[str, Any]:
    """Parses raw text resume into Candidate Profile + Analysis."""
    try:
        profile, analysis = parse_resume_content(req.text)
        return {
            "status": "success",
            "candidate_profile": profile.model_dump(),
            "resume_analysis": analysis.model_dump()
        }
    except Exception as e:
        logger.error(f"API Resume Text Parse Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# STEP 2: JOB DESCRIPTION PARSING
@app.post("/api/jd/analyze", tags=["Job Description Service"])
def analyze_job_description(req: JDParseRequest) -> Dict[str, Any]:
    """Parses text job description into structured Job Profile."""
    try:
        job_profile = parse_job_description(req.jd_text)
        return {
            "status": "success",
            "job_profile": job_profile.model_dump()
        }
    except Exception as e:
        logger.error(f"API JD Parse Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# STEP 3: MATCH ANALYSIS & DEBUG DIAGNOSTIC
@app.post("/api/match/analyze", tags=["Match Engine"])
def analyze_match(req: MatchRequest) -> Dict[str, Any]:
    """Calculates explainable Resume-to-JD Match Score and gap breakdown."""
    try:
        analysis = calculate_match_analysis(req.candidate_profile, req.job_profile)
        return {
            "status": "success",
            "match_analysis": analysis.model_dump()
        }
    except Exception as e:
        logger.error(f"API Match Analysis Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/matching/debug", tags=["Match Engine"])
@app.post("/api/match/debug", tags=["Match Engine"])
def debug_match(req: DebugMatchRequest) -> Dict[str, Any]:
    """Diagnostic endpoint returning step-by-step evidence extraction, taxonomy mapping, and score calculation details."""
    try:
        cand_prof = req.candidate_profile
        if not cand_prof and req.resume_text:
            cand_prof, _ = parse_resume_content(req.resume_text)

        job_prof = req.job_profile
        if not job_prof and req.jd_text:
            job_prof = parse_job_description(req.jd_text)

        if not cand_prof or not job_prof:
            raise HTTPException(status_code=400, detail="Provide either candidate_profile & job_profile OR resume_text & jd_text")

        analysis = calculate_match_analysis(cand_prof, job_prof)

        return {
            "status": "success",
            "candidate_name": cand_prof.name,
            "target_role": job_prof.role,
            "overall_match_score": analysis.match_score,
            "breakdown": analysis.breakdown.model_dump(),
            "strong_matches": analysis.strong_matches,
            "partial_matches": analysis.partial_matches,
            "skill_gaps": analysis.skill_gaps,
            "requirement_evidences": analysis.requirement_evidences,
            "focus_recommendations": analysis.focus_recommendations
        }
    except Exception as e:
        logger.error(f"API Debug Match Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# STEP 4: COLD EMAIL GENERATION
@app.post("/api/cold-email/generate", tags=["Cold Email Service"])
def generate_cold_email_endpoint(req: ColdEmailRequest) -> Dict[str, Any]:
    """Generates personalized cold outreach email based strictly on Candidate Profile & Job Profile."""
    try:
        email_output = generate_personalized_cold_email(req.candidate_profile, req.job_profile)
        return {
            "status": "success",
            "cold_email": email_output.model_dump()
        }
    except Exception as e:
        logger.error(f"API Cold Email Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# STEP 5 & 6: INTERVIEW SESSION MANAGEMENT
@app.post(
    "/api/interview/start",
    response_model=StartInterviewResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Interview Engine"]
)
def start_interview(request_data: StartInterviewRequest) -> StartInterviewResponse:
    """Initializes interview session, runs Planner Agent, indexes RAG context, and generates first question."""
    logger.info(f"API: Received start interview request for role '{request_data.target_role}'.")

    initial_state: InterviewState = {
        "session_id": None,
        "target_role": request_data.target_role,
        "resume_summary": request_data.resume_summary or "",
        "focus_area": request_data.focus_area,
        "candidate_profile": request_data.candidate_profile,
        "job_profile": request_data.job_profile,
        "match_analysis": request_data.match_analysis,
        "cold_email": None,
        "interview_plan": None,
        "interview_strategy": None,
        "rag_context": [],
        "conversation_history": [],
        "current_question": None,
        "candidate_response": None,
        "current_difficulty": "Mid-Level",
        "evaluations": [],
        "weak_areas": [],
        "strong_areas": [],
        "current_topic": None,
        "reflection_decision": None,
        "reflection_reasoning": None,
        "suggested_followup_topic": None,
        "follow_up_goal": None,
        "follow_up_type": None,
        "probe_count": 0,
        "turn_count": 0,
        "max_turns": request_data.max_turns,
        "current_step": "initialized",
        "final_report": None
    }

    # Step 1: Execute Planner Agent
    planner_update = planner_node(initial_state)
    state = {**initial_state, **planner_update}

    # Step 2: Execute Interviewer Agent for initial question with ChromaDB RAG
    interviewer_update = interviewer_node(state)
    state = {**state, **interviewer_update}

    session_id = session_manager.create_session(state)
    state["session_id"] = session_id
    session_manager.update_session(session_id, state)

    # Index candidate session context in ChromaDB
    context_str = f"Role: {request_data.target_role} | Resume: {request_data.resume_summary}"
    rag_service.store_candidate_context(session_id, context_str)

    logger.info(f"API: Interview session started successfully. Session ID: {session_id}.")

    return StartInterviewResponse(
        session_id=session_id,
        target_role=state["target_role"],
        current_difficulty=state["current_difficulty"],
        initial_question=state["current_question"],
        interview_strategy=state["interview_strategy"],
        interview_plan=state.get("interview_plan"),
        interview_blueprint=state.get("interview_blueprint"),
        tool_calls=state.get("tool_calls", [])
    )


@app.post(
    "/api/interview/respond",
    response_model=SubmitResponseResponse,
    status_code=status.HTTP_200_OK,
    tags=["Interview Engine"]
)
def respond_to_interview(request_data: SubmitResponseRequest) -> SubmitResponseResponse:
    """Processes candidate response through Evaluator -> Reflection -> Difficulty Controller -> Interviewer/Coach."""
    state = session_manager.get_session(request_data.session_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{request_data.session_id}' not found."
        )

    if state.get("current_step") == "completed":
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

    # Update transcript
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
        state["current_step"] = "completed"
        session_manager.update_session(request_data.session_id, state)
        
        # Persist completed session to SQLite database
        history_service.save_session(state)

        logger.info(f"API: Interview finished and saved to DB for session {request_data.session_id}.")
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
        final_report=None,
        tool_calls=state.get("tool_calls", [])
    )


@app.get("/api/interview/status/{session_id}", tags=["Interview Engine"])
def get_interview_status(session_id: str) -> Dict[str, Any]:
    """Retrieves full active interview state by session ID."""
    state = session_manager.get_session(session_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session '{session_id}' not found."
        )
    return state


# HISTORY & PROGRESS ANALYTICS
@app.get("/api/history", tags=["History & Progress"])
def get_interview_history() -> Dict[str, Any]:
    """Retrieves list of past completed interview sessions."""
    sessions = history_service.get_sessions()
    return {"status": "success", "sessions": sessions}


@app.get("/api/history/{session_id}", tags=["History & Progress"])
def get_interview_history_record(session_id: str) -> Dict[str, Any]:
    """Retrieves detailed record of a single past interview attempt."""
    record = history_service.get_session_by_id(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Interview record not found.")
    return {"status": "success", "session": record}


@app.get("/api/progress", tags=["History & Progress"])
def get_progress_analytics_endpoint() -> Dict[str, Any]:
    """Retrieves aggregate progress analytics and skill trends across all interview attempts."""
    analytics = history_service.get_progress_analytics()
    return {"status": "success", "analytics": analytics}
