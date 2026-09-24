import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from schemas.candidate import CandidateProfile
from services.skill_taxonomy import normalize_skill_name, CANONICAL_SKILL_ALIASES, SKILL_TAXONOMY


@dataclass
class RequirementEvidence:
    requirement: str
    importance: str  # "required" or "preferred"
    status: str      # "strong_match", "partial_match", "related_evidence", "missing"
    confidence: float
    matched_skill: Optional[str] = None
    source_section: Optional[str] = None
    evidence_text: Optional[str] = None


class RequirementEvidenceEngine:
    """
    Evidence-First Requirement-Level Matching Engine.
    Evaluates candidate profile evidence against each JD requirement individually.
    Zero hallucination rule: Related skills (e.g. Computer Networks) contribute to
    'related_evidence', but MUST NOT become 'strong_match' for unproven requirements like DNS/SSH.
    """

    def evaluate_requirement(
        self, req_text: str, importance: str, candidate: CandidateProfile
    ) -> RequirementEvidence:
        req_lower = req_text.lower()
        req_canonical = normalize_skill_name(req_text)

        # Build candidate skill corpus with normalization
        all_cand_skills = set([normalize_skill_name(s) for s in candidate.skills + candidate.technologies + candidate.keywords])
        cand_skills_raw_lower = set([s.lower() for s in candidate.skills + candidate.technologies + candidate.keywords])

        # 1. Exact / Canonical Match in Technical Skills & Technologies
        if req_canonical in all_cand_skills:
            # Find evidence in Projects or Experience
            source_section, evidence_str = self._find_resume_evidence(req_canonical, candidate)
            return RequirementEvidence(
                requirement=req_text,
                importance=importance,
                status="strong_match",
                confidence=1.0 if source_section else 0.9,
                matched_skill=req_canonical,
                source_section=source_section or "Technical Skills",
                evidence_text=evidence_str or f"Extracted skill: {req_canonical}"
            )

        # 2. Check for Alias or Exact Substring Match in Skills
        for skill in all_cand_skills:
            skill_lower = skill.lower()
            if skill_lower == req_lower or (len(skill_lower) >= 3 and skill_lower in req_lower):
                source_section, evidence_str = self._find_resume_evidence(skill, candidate)
                return RequirementEvidence(
                    requirement=req_text,
                    importance=importance,
                    status="strong_match",
                    confidence=0.95,
                    matched_skill=skill,
                    source_section=source_section or "Technical Skills",
                    evidence_text=evidence_str or f"Extracted skill: {skill}"
                )

        # 3. Project / Experience Evidence Search for Requirement Keyword
        source_section, evidence_str = self._find_phrase_evidence(req_lower, candidate)
        if evidence_str:
            return RequirementEvidence(
                requirement=req_text,
                importance=importance,
                status="strong_match",
                confidence=0.9,
                matched_skill=req_canonical,
                source_section=source_section,
                evidence_text=evidence_str
            )

        # 4. Partial Match Check (e.g. Docker for Containerization, Python for Scripting)
        if "container" in req_lower and "Docker" in all_cand_skills:
            return RequirementEvidence(
                requirement=req_text,
                importance=importance,
                status="partial_match",
                confidence=0.8,
                matched_skill="Docker",
                source_section="Technical Skills",
                evidence_text="Candidate possesses Docker containerization skills"
            )
        if "scripting" in req_lower and ("Python" in all_cand_skills or "JavaScript" in all_cand_skills):
            matched_script = "Python" if "Python" in all_cand_skills else "JavaScript"
            return RequirementEvidence(
                requirement=req_text,
                importance=importance,
                status="strong_match" if "Python" in all_cand_skills else "partial_match",
                confidence=0.85,
                matched_skill=matched_script,
                source_section="Technical Skills",
                evidence_text=f"Scripting evidence via {matched_script}"
            )

        # 5. Related Evidence Check (e.g. Computer Networks for DNS/SSH, Linux for Operating Systems)
        related_topic = self._check_related_evidence(req_lower, all_cand_skills, candidate)
        if related_topic:
            return RequirementEvidence(
                requirement=req_text,
                importance=importance,
                status="related_evidence",
                confidence=0.5,
                matched_skill=related_topic,
                source_section="General CS Fundamentals",
                evidence_text=f"Related baseline knowledge in {related_topic}, but specific requirement ({req_canonical}) is unproven"
            )

        # 6. Otherwise: Missing
        return RequirementEvidence(
            requirement=req_text,
            importance=importance,
            status="missing",
            confidence=1.0,
            matched_skill=None,
            source_section=None,
            evidence_text=f"No direct or partial evidence found in candidate profile for '{req_text}'"
        )

    def _find_resume_evidence(self, skill: str, candidate: CandidateProfile) -> Tuple[Optional[str], Optional[str]]:
        skill_lower = skill.lower()

        # Search Projects
        for proj in candidate.projects:
            if skill_lower in proj.lower():
                return "Projects Portfolio", proj[:120]

        # Search Experience
        for exp in candidate.experience:
            if skill_lower in exp.lower():
                return "Work Experience", exp[:120]

        # Search Education
        for edu in candidate.education:
            if skill_lower in edu.lower():
                return "Education", edu[:120]

        return None, None

    def _find_phrase_evidence(self, req_lower: str, candidate: CandidateProfile) -> Tuple[Optional[str], Optional[str]]:
        tokens = [t for t in re.findall(r'\b[a-zA-Z0-9+#\.]+\b', req_lower) if len(t) > 3 and t not in ["with", "from", "for", "using", "such"]]

        for proj in candidate.projects:
            proj_lower = proj.lower()
            if any(t in proj_lower for t in tokens):
                return "Projects Portfolio", proj[:120]

        for exp in candidate.experience:
            exp_lower = exp.lower()
            if any(t in exp_lower for t in tokens):
                return "Work Experience", exp[:120]

        return None, None

    def _check_related_evidence(self, req_lower: str, cand_skills: set, candidate: CandidateProfile) -> Optional[str]:
        if any(term in req_lower for term in ["dns", "ssh", "ip addressing", "http"]) and "Computer Networks" in candidate.skills:
            return "Computer Networks"
        if any(term in req_lower for term in ["bash", "shell", "powershell"]) and ("Linux" in cand_skills or "Operating Systems" in candidate.skills):
            return "Linux / Operating Systems"
        if "ci/cd" in req_lower and "Docker" in cand_skills:
            return "Docker Containerization"
        if any(term in req_lower for term in ["aws", "azure", "gcp", "cloud"]) and "Docker" in cand_skills:
            return "Docker Container Infrastructure"
        return None
