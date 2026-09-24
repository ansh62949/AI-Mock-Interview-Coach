import pytest
from schemas.candidate import CandidateProfile
from schemas.jd import JobProfile
from services.resume_parser import parse_resume_content
from services.jd_parser import parse_job_description
from services.match_engine import calculate_match_analysis
from services.cold_email import generate_personalized_cold_email


def test_resume_parser():
    raw_text = """
    John Doe
    Email: john@example.com
    Skills: Java, Spring Boot, SQL, Docker, AWS, REST APIs
    Experience: 3 years Software Engineer at TechCorp
    Projects: HerRide backend service built with Java and Spring Boot
    Education: BS Computer Science
    """
    profile, analysis = parse_resume_content(raw_text)
    assert profile.name != ""
    assert "Java" in profile.skills or "Java" in profile.technologies or len(profile.skills) > 0
    assert len(analysis.strongest_skills) > 0


def test_jd_parser():
    raw_text = """
    Senior Backend Engineer - Acme Inc
    We are looking for a Senior Backend Engineer with expertise in Java, Spring Boot, SQL, and Docker.
    Responsibilities include designing microservices and maintaining databases.
    """
    job_profile = parse_job_description(raw_text)
    assert job_profile.role != ""
    assert len(job_profile.required_skills) > 0


def test_match_engine():
    candidate = CandidateProfile(
        name="Alice",
        skills=["Java", "Spring Boot", "SQL", "REST"],
        technologies=["Git", "Maven"],
        projects=["E-commerce Microservices"],
        experience=["2 years Backend Dev"],
        education=["BS CS"]
    )
    jd = JobProfile(
        company="TechCorp",
        role="Backend Engineer",
        required_skills=["Java", "Spring Boot", "SQL"],
        preferred_skills=["Docker", "AWS"],
        responsibilities=["Build APIs"],
        education_requirements=["BS CS"]
    )
    analysis = calculate_match_analysis(candidate, jd)
    assert analysis.match_score >= 50
    assert "Java" in analysis.strong_matches


def test_cold_email():
    candidate = CandidateProfile(
        name="Bob",
        email="bob@example.com",
        skills=["Python", "FastAPI", "PostgreSQL"],
        projects=["AI Search Engine"]
    )
    jd = JobProfile(
        company="AI Startup",
        role="AI Engineer",
        required_skills=["Python", "FastAPI"]
    )
    email = generate_personalized_cold_email(candidate, jd)
    assert "Bob" in email.subject or "Bob" in email.body
    assert "AI Startup" in email.body or "AI Engineer" in email.body


def test_jd_parser_role_cleaning():
    raw_text = """
    Job OverviewWe are looking for a driven Junior DevOps Engineer to help automate, build, and maintain our cloud infrastructure and deployment pipelines. In this role, you will work closely with senior DevOps engineers and development teams to ensure software is delivered quickly, reliably, and securely.
    Required Skills & Qualifications: Python, Linux, Git, Docker.
    To finalize this DevOps JD, please let me know: Which cloud provider do you use? — Ansh Pathak
    """
    job_profile = parse_job_description(raw_text)
    assert job_profile.role == "Junior DevOps Engineer"

