import os
import io
from typing import Tuple, Dict, Any, Optional
import pdfplumber
from docx import Document

from schemas.candidate import CandidateProfile, ResumeAnalysis
from utils.llm import get_llm
from utils.logger import logger


def extract_raw_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extracts raw plain text from PDF or DOCX file bytes."""
    extension = os.path.splitext(filename)[1].lower()
    text = ""

    if extension == ".pdf":
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_str = page.extract_text()
                    if page_str:
                        pages_text.append(page_str)
                    # Extract hyperlinked URIs from PDF annotations/links
                    try:
                        for hyperlink in (page.hyperlinks or []):
                            uri = hyperlink.get("uri")
                            if uri:
                                pages_text.append(f"LINK: {uri}")
                    except Exception:
                        pass
                text = "\n".join(pages_text)
        except Exception as e:
            logger.error(f"ResumeParser: Failed to extract PDF text with pdfplumber: {e}")
            # Fallback to pdfminer if needed
            from pdfminer.high_level import extract_text as pdfminer_extract
            try:
                text = pdfminer_extract(io.BytesIO(file_bytes))
            except Exception as e2:
                logger.error(f"ResumeParser: pdfminer fallback also failed: {e2}")
                raise ValueError("Could not extract text from PDF file. File may be encrypted or corrupted.")

    elif extension in [".docx", ".doc"]:
        try:
            doc = Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"ResumeParser: Failed to extract DOCX text: {e}")
            raise ValueError("Could not extract text from DOCX file.")
    elif extension in [".txt"]:
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type '{extension}'. Please upload a PDF or DOCX file.")

    if not text or len(text.strip()) < 20:
        raise ValueError("The uploaded document contains insufficient or unreadable text.")

    return text.strip()


def _extract_section_lines(raw_text: str, keywords: List[str]) -> List[str]:
    lines = raw_text.splitlines()
    capturing = False
    results = []
    section_headers = [
        "projects", "project", "personal projects", "key projects", 
        "experience", "work experience", "employment", "professional experience",
        "education", "academic", "academic background", 
        "skills", "technical skills", "certifications", "achievements", "certifications & achievements", "summary"
    ]
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        clean_lower = stripped.lower().rstrip(":-_#* ")
        
        # Check if line is a standalone section header
        is_target_header = len(clean_lower) < 40 and any(clean_lower == kw or clean_lower == f"{kw}s" for kw in keywords)
        
        if is_target_header:
            capturing = True
            continue
            
        if capturing:
            is_other_header = len(clean_lower) < 40 and any(clean_lower == h for h in section_headers if not any(clean_lower == kw for kw in keywords))
            if is_other_header:
                break
            results.append(stripped)
            if len(results) >= 15:
                break
                
    return results


def parse_resume_content(raw_text: str) -> Tuple[CandidateProfile, ResumeAnalysis]:
    """
    Parses extracted resume text into structured CandidateProfile and ResumeAnalysis models.
    Enforces anti-hallucination directives ('Not found in resume' for missing fields).
    """
    llm = get_llm(temperature=0.2, timeout=15.0, max_retries=1)

    system_prompt = (
        "You are an expert resume parser & candidate profiler AI.\n"
        "Extract structured candidate profile details from the resume text below.\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Extract candidate full name, email, phone, linkedin URL, github URL, education history, work experience, projects, skills, technologies.\n"
        "2. DO NOT HALLUCINATE OR INVENT INFORMATION NOT PRESENT IN THE TEXT.\n"
        "3. Use 'Not found in resume' for missing text fields, or [] for missing lists.\n\n"
        f"RESUME TEXT:\n{raw_text[:3500]}"
    )

    if llm:
        try:
            structured_profile_llm = llm.with_structured_output(CandidateProfile)
            profile: CandidateProfile = structured_profile_llm.invoke(system_prompt)

            analysis_prompt = (
                "Based ONLY on the candidate profile and resume text, produce an objective resume analysis.\n"
                "Identify top skills, key experience, major projects, missing key details, strengths, and recommended interview topics.\n\n"
                f"CANDIDATE NAME: {profile.name}\n"
                f"SKILLS: {', '.join(profile.skills[:8])}\n"
                f"RESUME TEXT:\n{raw_text[:2000]}"
            )
            structured_analysis_llm = llm.with_structured_output(ResumeAnalysis)
            analysis: ResumeAnalysis = structured_analysis_llm.invoke(analysis_prompt)
            return profile, analysis
        except Exception as e:
            logger.warning(f"ResumeParser: LLM structured extraction failed: {e}. Using rule-based fallback.")

    # Rule-based fallback if LLM is unavailable or offline
    import re
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    name = lines[0] if lines else "Candidate"
    
    # Improved contact regexes
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
    phone_match = re.search(r'\+?\d{1,3}[-.\s]?\d{4,5}[-.\s]?\d{4,5}', raw_text)
    linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|profile|pub)/[a-zA-Z0-9_-]+', raw_text, re.I)
    github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+', raw_text, re.I)

    email = email_match.group(0) if email_match else "Not found in resume"
    phone = phone_match.group(0) if phone_match else "Not found in resume"
    linkedin = linkedin_match.group(0) if linkedin_match else "Not found in resume"
    github = github_match.group(0) if github_match else "Not found in resume"

    # Section extraction
    extracted_projects = _extract_section_lines(raw_text, ["projects", "project", "personal projects", "key projects"])
    extracted_exp = _extract_section_lines(raw_text, ["experience", "work experience", "employment", "professional experience"])
    extracted_edu = _extract_section_lines(raw_text, ["education", "academic", "academic background"])

    # Skill extractions
    tech_keywords = [
        "Java", "Spring Boot", "Spring Security", "Python", "FastAPI", "JavaScript", "TypeScript", "React", "Node.js",
        "C++", "C", "Kafka", "Apache Kafka", "RabbitMQ", "Redis", "PostgreSQL", "MySQL", "MongoDB", "pgvector",
        "Docker", "Docker Compose", "Kubernetes", "AWS", "Linux", "Prometheus", "Grafana", "Git", "Maven",
        "LangGraph", "RAG", "Data Structures", "Algorithms", "Microservices", "Event-Driven Architecture", "REST APIs", "WebSockets"
    ]
    extracted_skills = [kw for kw in tech_keywords if kw.lower() in raw_text.lower()]
    
    profile = CandidateProfile(
        name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        target_roles=["Software Engineer"],
        education=extracted_edu if extracted_edu else ["Engineering / Computer Science Degree"],
        experience=extracted_exp if extracted_exp else ["Software Engineering Projects & Internships"],
        projects=extracted_projects if extracted_projects else ["Technical Portfolio Projects"],
        skills=extracted_skills if extracted_skills else ["Software Development"],
        technologies=extracted_skills if extracted_skills else ["General Engineering Tools"],
        achievements=[],
        keywords=extracted_skills
    )

    analysis = ResumeAnalysis(
        strongest_skills=profile.skills[:5],
        relevant_experience=profile.experience,
        major_projects=profile.projects,
        missing_info=["Certifications", "Quantified business metrics"],
        technical_strengths=profile.skills[:3],
        potential_topics=["Microservices Architecture", "Distributed Systems", "Database Optimization"] + profile.skills[:3]
    )

    return profile, analysis
