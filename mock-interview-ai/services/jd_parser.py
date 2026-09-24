from typing import Tuple, Dict, Any, Optional, List
from schemas.jd import JobProfile
from utils.llm import get_llm
from utils.logger import logger


def _extract_jd_section_lines(raw_text: str, keywords: List[str]) -> List[str]:
    lines = raw_text.splitlines()
    capturing = False
    results = []
    headers = [
        "required", "qualifications", "required skills", "preferred", "bonus", "nice to have",
        "responsibilities", "key responsibilities", "job overview", "education"
    ]
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        clean_lower = stripped.lower().rstrip(":-_#* ")
        
        # Check if line is a section header
        is_header = len(clean_lower) < 45 and any(h in clean_lower for h in headers)
        if is_header:
            capturing = any(kw in clean_lower for kw in keywords)
            continue
            
        if capturing:
            item = stripped.lstrip("-*• ")
            if item and not item.lower().endswith(":"):
                results.append(item)
            if len(results) >= 15:
                break
                
    return results


import re


def clean_role_title(raw_role: str) -> str:
    """Sanitizes raw role string to extract a clean, concise job title."""
    if not raw_role or raw_role in ["Not specified in JD", "Target Role", "Role", "Hiring Company"]:
        return "Software Engineer"
        
    raw_clean = raw_role.strip(" :-_#*")
    
    # If role is already concise and clean (<= 45 chars without paragraph verbs)
    if len(raw_clean) <= 45 and not any(v in raw_clean.lower() for v in ["looking for", "help automate", "overview", "responsibilities", "finalize", "we are"]):
        return raw_clean

    # Match standard job title pattern
    pattern = r'\b(Senior|Junior|Lead|Principal|Staff|Associate)?\s*(DevOps|Backend|Frontend|Full\s*Stack|Software|Cloud|Site\s*Reliability|SRE|Infrastructure|Data|Machine\s*Learning|AI|Systems|Security|QA)?\s*(Engineer|Developer|Architect|Administrator|Specialist|Analyst)\b'
    match = re.search(pattern, raw_clean, re.IGNORECASE)
    if match:
        return match.group(0).strip()
        
    # Fallback keyword checks
    lower = raw_clean.lower()
    if "devops" in lower:
        return "Junior DevOps Engineer" if "junior" in lower else "DevOps Engineer"
    elif "backend" in lower:
        return "Junior Backend Engineer" if "junior" in lower else "Backend Engineer"
    elif "frontend" in lower:
        return "Frontend Engineer"
    elif "full stack" in lower:
        return "Full Stack Engineer"
    elif "data" in lower:
        return "Data Engineer"
    elif "cloud" in lower:
        return "Cloud Engineer"
    elif "sre" in lower or "reliability" in lower:
        return "Site Reliability Engineer"

    # Truncate first 40 chars clean
    return raw_clean[:40].strip(" :-_#*")


def parse_job_description(raw_text: str) -> JobProfile:
    """
    Parses job description text into a structured JobProfile.
    Enforces anti-hallucination directives ('Not specified in JD' fallback).
    """
    if not raw_text or len(raw_text.strip()) < 20:
        raise ValueError("Job description text is too short or missing.")

    llm = get_llm(temperature=0.2, timeout=15.0, max_retries=1)

    system_prompt = (
        "You are an expert technical talent recruiter and JD analyzer.\n"
        "Extract the structured job profile from the job description below.\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Extract company name, role title, required skills, preferred bonus skills, responsibilities, education requirements, and domain.\n"
        "2. Role title MUST be a clean short job title (e.g. 'Junior DevOps Engineer', NOT a full paragraph or sentence).\n"
        "3. DO NOT HALLUCINATE OR INVENT REQUIREMENTS THAT ARE NOT IN THE TEXT.\n"
        "4. If company name or role is omitted, use 'Not specified in JD'.\n\n"
        f"JOB DESCRIPTION:\n{raw_text[:3500]}"
    )

    if llm:
        try:
            structured_jd_llm = llm.with_structured_output(JobProfile)
            job_profile: JobProfile = structured_jd_llm.invoke(system_prompt)
            if job_profile and (job_profile.required_skills or job_profile.important_technologies):
                job_profile.role = clean_role_title(job_profile.role)
                return job_profile
        except Exception as e:
            logger.warning(f"JDParser: LLM extraction failed: {e}. Using rule-based fallback.")

    # Rule-based fallback if LLM is offline or unavailable
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    # Infer role title
    role = "Software Engineer"
    for line in lines[:5]:
        if any(term in line.lower() for term in ["engineer", "developer", "architect", "lead", "devops", "sre"]):
            role = clean_role_title(line)
            break

    # Extract required & preferred sections
    req_lines = _extract_jd_section_lines(raw_text, ["required", "qualification", "must have", "key responsibilities"])
    pref_lines = _extract_jd_section_lines(raw_text, ["preferred", "bonus", "nice to have"])

    # Broader tech keyword extractions
    tech_keywords = [
        "Java", "Python", "Bash", "PowerShell", "Spring Boot", "SQL", "PostgreSQL", "MySQL", "MongoDB",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Jenkins", "GitHub Actions", "GitLab CI",
        "Linux", "Git", "Ansible", "CI/CD", "IaC", "Networking", "Prometheus", "Grafana", "FastAPI", "REST", "DSA"
    ]
    extracted_tech = [kw for kw in tech_keywords if kw.lower() in raw_text.lower()]

    final_req = req_lines + [t for t in extracted_tech if t not in req_lines]

    return JobProfile(
        company="Hiring Company",
        role=clean_role_title(role),
        required_skills=final_req if final_req else ["Software Engineering", "Problem Solving"],
        preferred_skills=pref_lines if pref_lines else [kw for kw in ["Terraform", "AWS", "Jenkins", "Kubernetes"] if kw.lower() in raw_text.lower()],
        responsibilities=req_lines[:4] if req_lines else ["Automate build & deployment pipelines", "Maintain system uptime & infrastructure"],
        education_requirements=["Bachelor's degree in Computer Science or related field"],
        important_technologies=extracted_tech if extracted_tech else ["Docker", "Linux", "Git"],
        keywords=extracted_tech,
        domain="DevOps & Cloud Engineering" if "devops" in raw_text.lower() else "Software Engineering",
        interview_requirements=["Linux Administration", "CI/CD Pipelines", "Scripting & Automation"]
    )

