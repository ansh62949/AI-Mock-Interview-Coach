from typing import List, Optional
from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    """Structured candidate profile extracted from resume."""
    name: str = Field(default="Not found in resume", description="Candidate full name")
    email: str = Field(default="Not found in resume", description="Contact email address")
    phone: str = Field(default="Not found in resume", description="Contact phone number")
    linkedin: Optional[str] = Field(default="Not found in resume", description="LinkedIn profile URL or handle")
    github: Optional[str] = Field(default="Not found in resume", description="GitHub profile URL or handle")
    target_roles: List[str] = Field(default_factory=list, description="Target or detected roles")
    target_role: Optional[str] = Field(default=None, description="Legacy target role alias")
    resume_summary: Optional[str] = Field(default=None, description="Legacy resume summary alias")
    focus_area: Optional[str] = Field(default="Mixed", description="Legacy focus area alias")
    education: List[str] = Field(default_factory=list, description="Degrees, institutions, graduation dates")
    experience: List[str] = Field(default_factory=list, description="Work history, roles, companies")
    projects: List[str] = Field(default_factory=list, description="Notable projects & key details")
    languages: List[str] = Field(default_factory=list, description="Programming languages")
    frameworks: List[str] = Field(default_factory=list, description="Frameworks and libraries")
    databases: List[str] = Field(default_factory=list, description="Databases and storage engines")
    cloud: List[str] = Field(default_factory=list, description="Cloud infrastructure providers")
    devops: List[str] = Field(default_factory=list, description="DevOps and IaC tools")
    containers: List[str] = Field(default_factory=list, description="Containerization and orchestration")
    ci_cd: List[str] = Field(default_factory=list, description="CI/CD platforms")
    networking: List[str] = Field(default_factory=list, description="Networking protocols and tools")
    os: List[str] = Field(default_factory=list, description="Operating systems")
    messaging: List[str] = Field(default_factory=list, description="Message brokers and distributed systems")
    ai_ml: List[str] = Field(default_factory=list, description="AI, ML, and RAG frameworks")
    skills: List[str] = Field(default_factory=list, description="Core technical & soft skills")
    technologies: List[str] = Field(default_factory=list, description="Tools, frameworks, platforms, databases")
    achievements: List[str] = Field(default_factory=list, description="Certifications, awards, metrics")
    keywords: List[str] = Field(default_factory=list, description="Extracted domain keywords")


class ResumeAnalysis(BaseModel):
    """AI analysis of candidate's technical profile."""
    strongest_skills: List[str] = Field(default_factory=list, description="Top technical capabilities")
    relevant_experience: List[str] = Field(default_factory=list, description="Key work experience summary")
    major_projects: List[str] = Field(default_factory=list, description="High-impact portfolio projects")
    missing_info: List[str] = Field(default_factory=list, description="Information missing from resume")
    technical_strengths: List[str] = Field(default_factory=list, description="Standout engineering strengths")
    potential_topics: List[str] = Field(default_factory=list, description="Recommended interview topics")
