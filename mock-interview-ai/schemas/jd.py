from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class JobProfile(BaseModel):
    """Structured job profile extracted from job description."""
    company: str = Field(default="Not specified in JD", description="Hiring company name")
    role: str = Field(default="Target Role", description="Job title / target role")
    required_skills: List[str] = Field(default_factory=list, description="Must-have skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills")
    responsibilities: List[str] = Field(default_factory=list, description="Key job responsibilities")
    education_requirements: List[str] = Field(default_factory=list, description="Education requirements")
    important_technologies: List[str] = Field(default_factory=list, description="Required tech stack & tools")
    keywords: List[str] = Field(default_factory=list, description="Industry/Domain keywords")
    domain: str = Field(default="Software Engineering", description="Technical domain")
    interview_requirements: List[str] = Field(default_factory=list, description="Role specific interview focus areas")


class MatchBreakdown(BaseModel):
    """Transparent scoring breakdown across core dimensions."""
    required_skills_score: float = Field(..., ge=0.0, le=100.0, description="Required skill coverage % (Weight: 40%)")
    evidence_strength_score: float = Field(default=80.0, ge=0.0, le=100.0, description="Evidence strength % (Weight: 25%)")
    preferred_skills_score: float = Field(..., ge=0.0, le=100.0, description="Preferred skill coverage % (Weight: 20%)")
    role_alignment_score: float = Field(default=75.0, ge=0.0, le=100.0, description="Role alignment % (Weight: 10%)")
    project_relevance_score: float = Field(default=75.0, ge=0.0, le=100.0, description="Project relevance %")
    experience_relevance_score: float = Field(default=75.0, ge=0.0, le=100.0, description="Experience relevance %")
    education_score: float = Field(default=80.0, ge=0.0, le=100.0, description="Education match %")


class MatchAnalysis(BaseModel):
    """Explainable Evidence-First Resume-to-JD match analysis."""
    match_score: int = Field(..., ge=0, le=100, description="Overall explainable match percentage (0-100%)")
    breakdown: MatchBreakdown = Field(..., description="Explainable scoring breakdown")
    strong_matches: List[str] = Field(default_factory=list, description="Skills/experiences directly matching JD")
    partial_matches: List[str] = Field(default_factory=list, description="Related or transferable skills")
    skill_gaps: List[str] = Field(default_factory=list, description="Required skills missing from resume")
    project_relevance: List[str] = Field(default_factory=list, description="Project relevance notes")
    focus_recommendations: List[str] = Field(default_factory=list, description="Recommended interview preparation topics")
    requirement_evidences: List[Dict[str, Any]] = Field(default_factory=list, description="Requirement-level evidence breakdown")
