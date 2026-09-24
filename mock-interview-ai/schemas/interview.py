from typing import Any, Dict, List, Literal, Optional, Union
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from schemas.candidate import CandidateProfile


FocusAreaType = Literal["Technical", "Behavioral", "Mixed", "Case", "System Design", "AI & ML"]
DifficultyLevel = Literal["Junior", "Mid-Level", "Senior", "Staff"]
ReflectionDecisionType = Literal["probe_deeper", "next_topic", "increase_difficulty", "decrease_difficulty", "simplify", "finish"]


class InterviewStrategy(BaseModel):
    """Interview strategy produced by Planner Agent."""
    key_topics: List[str] = Field(..., min_length=1, description="Selected interview topics")
    initial_difficulty: DifficultyLevel = Field(default="Mid-Level", description="Starting difficulty level")
    focus_summary: str = Field(..., description="Strategy plan summary")


AnswerStatusType = Literal["unknown", "incorrect", "partial", "correct", "off_topic"]
FollowupStrategyType = Literal["teach_then_probe", "target_misconception", "probe_missing_concept", "increase_depth", "redirect"]


class MultiDimEvaluation(BaseModel):
    """Grounded evaluation across 5 core dimensions with 5-state classification and adaptive strategy."""
    answer_status: AnswerStatusType = Field(default="partial", description="Classification of candidate answer: unknown, incorrect, partial, correct, off_topic")
    technical_correctness: int = Field(..., ge=1, le=10, description="Technical accuracy (1-10)")
    depth: int = Field(..., ge=1, le=10, description="Technical depth and detail (1-10)")
    relevance: int = Field(..., ge=1, le=10, description="Direct relevance to the question (1-10)")
    completeness: int = Field(..., ge=1, le=10, description="Completeness of response (1-10)")
    communication: int = Field(..., ge=1, le=10, description="Clarity and communication structure (1-10)")
    overall_score: float = Field(..., ge=1.0, le=10.0, description="Calculated overall score out of 10")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Classification confidence")
    knowledge_gaps: List[str] = Field(default_factory=list, description="Specific technical knowledge gaps identified")
    misconceptions: List[str] = Field(default_factory=list, description="Specific candidate misconceptions identified")
    needs_followup: bool = Field(default=True, description="Whether adaptive follow-up probing is required")
    followup_strategy: Optional[FollowupStrategyType] = Field(default="probe_missing_concept", description="Targeted follow-up strategy")
    recommended_topic: Optional[str] = Field(None, description="Recommended specific concept or subtopic for next question")
    feedback: str = Field(..., description="Actionable, grounded feedback without fluff")
    strengths: List[str] = Field(default_factory=list, description="Demonstrated response strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Response weaknesses")
    missing_concepts: List[str] = Field(default_factory=list, description="Key concepts or trade-offs omitted")
    suggested_improvement: str = Field(..., description="Specific recommendation for answer enhancement")



class ColdEmailOutput(BaseModel):
    """Personalized outreach email for candidates."""
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Formatted email body text")
    candidate_name: str = Field(..., description="Candidate name")
    candidate_email: str = Field(..., description="Candidate email")
    target_company: str = Field(..., description="Company name")
    target_role: str = Field(..., description="Target role title")


class InterviewPlanRound(BaseModel):
    """Individual round in the personalized interview plan."""
    round_number: int = Field(..., description="Round number (1-6)")
    title: str = Field(..., description="Round title (e.g. Java/OOP, SQL/DBMS, RAG Fundamentals)")
    focus: str = Field(..., description="Specific technical focus and skills tested")


class InterviewPlan(BaseModel):
    """Personalized multi-round interview strategy plan."""
    target_role: str = Field(..., description="Target role title")
    company: str = Field(..., description="Target company")
    rounds: List[InterviewPlanRound] = Field(default_factory=list, description="Interview rounds roadmap")
    focus_summary: str = Field(..., description="Overview strategy summary")


CandidateSeniorityLevel = Literal["Internship", "Entry-Level", "Junior", "Mid-Level", "Senior", "Staff"]


class SkillCoverageItem(BaseModel):
    """Specific skill coverage objective in the Interview Blueprint."""
    skill: str = Field(..., description="Skill name")
    importance: str = Field(default="required", description="required or preferred")
    resume_evidence: bool = Field(default=True, description="Whether present in resume")
    coverage_objective: str = Field(default="validate", description="validate, deep_validate, gap_check, optional")


class InterviewBlueprint(BaseModel):
    """Explicit, pre-generated structured interview roadmap and level calibration."""
    role: str = Field(..., description="Target job title")
    candidate_level: CandidateSeniorityLevel = Field(default="Junior", description="Inferred candidate experience level")
    job_level: DifficultyLevel = Field(default="Junior", description="Inferred job posting seniority level")
    interview_level: DifficultyLevel = Field(default="Junior", description="Auto-calibrated target interview difficulty")
    level_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Calibration confidence score")
    level_reason: str = Field(..., description="Rationale for auto-calibrated interview level")
    
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both Resume and JD")
    missing_skills: List[str] = Field(default_factory=list, description="Mandatory JD skills missing from Resume")
    partial_skills: List[str] = Field(default_factory=list, description="Related or unproven skills needing validation")
    
    skill_coverage: List[SkillCoverageItem] = Field(default_factory=list, description="Detailed per-skill evaluation targets")
    rounds_plan: List[InterviewPlanRound] = Field(default_factory=list, description="Round-by-round roadmap")
    difficulty_progression: List[str] = Field(default_factory=list, description="Progression sequence")
    focus_summary: str = Field(..., description="Overall interview strategy summary")


class EvaluationResult(BaseModel):
    """Evaluation output model maintained for backward compatibility."""
    score: int = Field(..., ge=1, le=10)
    feedback: Union[str, Dict[str, Any]]
    strong_points: List[str] = Field(default_factory=list)
    weak_points: List[str] = Field(default_factory=list)


class ReflectionOutput(BaseModel):
    """Routing decision from Reflection Agent."""
    decision: ReflectionDecisionType = Field(..., description="Routing decision")
    reasoning: str = Field(..., description="Decision rationale")
    follow_up_goal: Optional[str] = Field(None, description="Probing objective")
    follow_up_type: Optional[str] = Field(default="deeper_tradeoffs", description="Probing style")


class CategoryScore(BaseModel):
    """Category specific performance score."""
    category: str
    score: float
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    """Executive coaching report generated by Coach Agent."""
    overall_score: float = Field(..., ge=1.0, le=10.0, description="Overall score out of 10")
    category_scores: List[CategoryScore] = Field(default_factory=list, description="Scores by topic category")
    executive_summary: str = Field(..., description="Performance summary")
    top_strengths: List[str] = Field(default_factory=list, description="Top 5 candidate strengths")
    top_weaknesses: List[str] = Field(default_factory=list, description="Top 5 areas for growth")
    questions_answered_well: List[str] = Field(default_factory=list, description="Questions with high score")
    questions_answered_poorly: List[str] = Field(default_factory=list, description="Questions needing improvement")
    recommended_study_plan: List[str] = Field(default_factory=list, description="Actionable 3-step study roadmap")
    next_difficulty_recommendation: DifficultyLevel = Field(default="Mid-Level", description="Recommended difficulty level")
    markdown_report: str = Field(..., description="Full formatted markdown report")
