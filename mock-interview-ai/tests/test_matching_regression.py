import pytest
from schemas.candidate import CandidateProfile
from schemas.jd import JobProfile
from services.skill_taxonomy import normalize_skill_name
from services.evidence_engine import RequirementEvidenceEngine
from services.match_engine import calculate_match_analysis


ANSH_RESUME_TEXT = """
Ansh Pathak
Email: ansh.pathak@example.com | Phone: +919984130195
LinkedIn: linkedin.com/in/anshpathak | GitHub: github.com/anshpathak

SUMMARY
Software Engineer specializing in Java, Spring Boot, Microservices, Event-Driven Architectures, and AI integration with LangGraph and RAG.

SKILLS
Languages: Java (Java 21), Python, C, JavaScript
Frameworks: Spring Boot 3.5, Spring Security, FastAPI, LangGraph
Databases & Cache: PostgreSQL, MySQL, MongoDB, Redis (incl. GEO), pgvector
Messaging & Streaming: Apache Kafka, RabbitMQ, WebSockets (STOMP)
DevOps & Infrastructure: Docker, Docker Compose, Linux, Prometheus, Grafana, Git, Maven
Concepts: RAG, Microservices, Event-Driven Architecture, REST APIs, Data Structures & Algorithms, OOP

PROJECTS
1. Smart Vehicle Tracking & Dispatching System
- Built with Java 21, Spring Boot 3.5, Apache Kafka, Redis GEO, PostgreSQL.
- Implemented real-time tracking via WebSockets and microservice event distribution.
- Containerized services with Docker and Docker Compose. Monitored metrics using Prometheus and Grafana.

2. AI Mock Interview Coach
- Developed multi-agent stateful graph using Python, FastAPI, LangGraph, RAG, and pgvector.
- Implemented adaptive interview loops and domain context vector retrieval.
"""


DEVOPS_JD_TEXT = """
Job Title: Junior DevOps Engineer
Company: CloudScale Systems

We are looking for a Junior DevOps Engineer to maintain cloud infrastructure and deployment pipelines.

Required Skills & Qualifications:
- Hands-on experience with Kubernetes and container orchestration
- Infrastructure as Code using Terraform or CloudFormation
- Cloud platform experience (AWS or GCP)
- Building CI/CD pipelines using GitHub Actions or Jenkins
- System monitoring with Prometheus and Grafana
- Containerization with Docker
- Linux administration and Bash scripting
"""


BACKEND_JAVA_JD_TEXT = """
Job Title: Senior Backend Java Engineer
Company: Enterprise FinTech Inc.

We are seeking a Backend Engineer to design scalable microservices.

Required Skills & Qualifications:
- Strong proficiency in Java 17+ and Spring Boot
- Microservices architecture and RESTful API design
- Message queues and streaming with Apache Kafka or RabbitMQ
- Relational databases (PostgreSQL or MySQL) and Redis caching
- Containerization with Docker and Git version control
- Distributed system monitoring and logging
"""


AI_ENGINEER_JD_TEXT = """
Job Title: AI / ML Systems Engineer
Company: Generative AI Labs

Seeking an AI Engineer to build LLM agents and RAG pipelines.

Required Skills & Qualifications:
- Proficiency in Python and FastAPI web frameworks
- Experience building AI agents using LangChain or LangGraph
- Knowledge of RAG architectures and Vector Databases (pgvector, ChromaDB)
- Deep learning frameworks (PyTorch or TensorFlow)
- Model fine-tuning and evaluation pipelines
"""


def test_taxonomy_canonicalization():
    assert normalize_skill_name("k8s") == "Kubernetes"
    assert normalize_skill_name("docker compose") == "Docker Compose"
    assert normalize_skill_name("postgres") == "PostgreSQL"
    assert normalize_skill_name("spring") == "Spring Boot"
    assert normalize_skill_name("kafka") == "Apache Kafka"


def test_devops_vs_backend_matching():
    from services.resume_parser import parse_resume_content
    from services.jd_parser import parse_job_description

    candidate_profile, _ = parse_resume_content(ANSH_RESUME_TEXT)
    devops_jd = parse_job_description(DEVOPS_JD_TEXT)
    backend_jd = parse_job_description(BACKEND_JAVA_JD_TEXT)
    ai_jd = parse_job_description(AI_ENGINEER_JD_TEXT)

    devops_analysis = calculate_match_analysis(candidate_profile, devops_jd)
    backend_analysis = calculate_match_analysis(candidate_profile, backend_jd)
    ai_analysis = calculate_match_analysis(candidate_profile, ai_jd)

    # Truthful Score Hierarchy: Backend Java Match > DevOps Match
    assert backend_analysis.match_score > devops_analysis.match_score, (
        f"Backend Java score ({backend_analysis.match_score}) must be strictly higher than DevOps score ({devops_analysis.match_score})"
    )

    # DevOps Gaps: Kubernetes, Terraform, AWS must be in skill_gaps or requirement evidences missing
    devops_gaps_str = " ".join(devops_analysis.skill_gaps).lower()
    assert "kubernetes" in devops_gaps_str or "terraform" in devops_gaps_str or "aws" in devops_gaps_str, (
        f"Expected missing DevOps skills in gaps, got {devops_analysis.skill_gaps}"
    )

    # Backend Matches: Java, Spring Boot, Kafka, PostgreSQL, Docker must be strong matches
    backend_matches_str = " ".join(backend_analysis.strong_matches).lower()
    assert "java" in backend_matches_str
    assert "spring boot" in backend_matches_str or "kafka" in backend_matches_str

    # AI Matches: Python, LangGraph, RAG, FastAPI, pgvector
    ai_matches_str = " ".join(ai_analysis.strong_matches).lower()
    assert "python" in ai_matches_str or "fastapi" in ai_matches_str or "langgraph" in ai_matches_str


def test_no_false_positive_skill_grants():
    """Ensure Linux does NOT grant Kubernetes, and Docker does NOT grant AWS/Terraform."""
    candidate = CandidateProfile(
        name="Test Candidate",
        skills=["Linux", "Docker", "Prometheus", "Grafana"]
    )
    req_engine = RequirementEvidenceEngine()

    # Evaluate Kubernetes requirement
    k8s_ev = req_engine.evaluate_requirement("Hands-on experience with Kubernetes and container orchestration", "required", candidate)
    assert k8s_ev.status in ["missing", "related_evidence", "partial_match"]
    assert k8s_ev.status != "strong_match"

    # Evaluate AWS requirement
    aws_ev = req_engine.evaluate_requirement("Cloud platform experience (AWS or GCP)", "required", candidate)
    assert aws_ev.status in ["missing", "related_evidence", "partial_match"]
    assert aws_ev.status != "strong_match"

    # Evaluate Docker requirement
    docker_ev = req_engine.evaluate_requirement("Containerization with Docker", "required", candidate)
    assert docker_ev.status == "strong_match"
    assert docker_ev.matched_skill == "Docker"


def test_specific_resume_jd_matcher():
    """
    User Test Case:
    JD Required: Python, Linux, Git, Bash, PowerShell, DNS, SSH, CS/IT degree
    JD Preferred: AWS, Azure, GCP, Docker, Kubernetes, Terraform, Jenkins, GitHub Actions
    Resume contains: Python, Linux, Git, Docker, Computer Networks, CS degree
    System MUST NOT report all as matched.
    """
    candidate = CandidateProfile(
        name="Test Candidate",
        skills=["Python", "Linux", "Git", "Docker", "Computer Networks"],
        education=["B.S. Computer Science"]
    )
    job = JobProfile(
        company="Test Co",
        role="DevOps Specialist",
        required_skills=["Python", "Linux", "Git", "Bash", "PowerShell", "DNS", "SSH", "CS/IT degree"],
        preferred_skills=["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins", "GitHub Actions"]
    )
    analysis = calculate_match_analysis(candidate, job)

    strong_str = " ".join(analysis.strong_matches).lower()
    assert "python" in strong_str
    assert "linux" in strong_str
    assert "git" in strong_str
    assert "docker" in strong_str

    gaps_str = " ".join(analysis.skill_gaps).lower()
    assert "kubernetes" in gaps_str or "aws" in gaps_str or "terraform" in gaps_str or "bash" in gaps_str

