from schemas.candidate import CandidateProfile
from schemas.jd import JobProfile
from schemas.interview import ColdEmailOutput
from services.jd_parser import clean_role_title
from utils.llm import get_llm
from utils.logger import logger


def generate_personalized_cold_email(candidate: CandidateProfile, jd: JobProfile) -> ColdEmailOutput:
    """
    Generates a targeted, professional cold outreach email based strictly on
    the extracted Candidate Profile and Job Profile.
    STRICT RULE: Zero hallucination of achievements, metrics, or technologies not in candidate profile.
    """
    llm = get_llm(temperature=0.3)

    cand_name = candidate.name if candidate.name not in ["Not found in resume", "Candidate"] else "Applicant"
    cand_email = candidate.email if candidate.email not in ["Not found in resume", "candidate@example.com"] else ""
    company = jd.company if jd.company not in ["Not specified in JD", "Hiring Company"] else "your engineering team"
    role = clean_role_title(jd.role)

    prompt = (
        "You are an executive talent strategist creating a compelling, personalized cold email for a job candidate.\n"
        "STRICT RULES:\n"
        "1. Base the email ONLY on the provided Candidate Profile and Job Profile.\n"
        "2. DO NOT INVENT or hallucinate past roles, metrics, companies, or projects not mentioned in candidate profile.\n"
        "3. Write a clean, concise, professional email without generic AI buzzwords or raw JD dumps.\n"
        "4. Subject line MUST be clean and concise, e.g. 'Application for Junior DevOps Engineer — Ansh Pathak'.\n\n"
        f"CANDIDATE NAME: {cand_name}\n"
        f"CANDIDATE SKILLS: {', '.join(candidate.skills[:6])}\n"
        f"CANDIDATE PROJECTS: {', '.join(candidate.projects[:2])}\n"
        f"CANDIDATE EXPERIENCE: {', '.join(candidate.experience[:2])}\n\n"
        f"TARGET COMPANY: {company}\n"
        f"TARGET ROLE: {role}\n"
        f"REQUIRED SKILLS IN JD: {', '.join(jd.required_skills[:5])}\n"
    )

    if llm:
        try:
            structured_email_llm = llm.with_structured_output(ColdEmailOutput)
            result: ColdEmailOutput = structured_email_llm.invoke(prompt)
            if result:
                result.target_role = role
                result.subject = f"Application for {role} — {cand_name}"
                return result
        except Exception as e:
            logger.warning(f"ColdEmailService: LLM generation failed: {e}. Using structured template fallback.")


    # Fallback template generator
    skills_text = ", ".join(candidate.skills[:3]) if candidate.skills else "software engineering"
    proj_text = candidate.projects[0] if candidate.projects else "recent technical initiatives"

    subject = f"Application for {role} — {cand_name}"
    body = (
        f"Hi {company} Engineering Team,\n\n"
        f"I am writing to express my strong interest in the {role} position at {company}.\n\n"
        f"With a background in {skills_text}, I have developed hands-on experience building technical solutions "
        f"such as {proj_text}, which closely aligns with your team's requirements for {', '.join(jd.required_skills[:3])}.\n\n"
        f"I would welcome the opportunity to discuss how my technical experience can contribute to {company}.\n\n"
        f"Best regards,\n"
        f"{cand_name}\n"
        f"Email: {cand_email}\n"
    )

    return ColdEmailOutput(
        subject=subject,
        body=body,
        candidate_name=cand_name,
        candidate_email=cand_email,
        target_company=company,
        target_role=role
    )
