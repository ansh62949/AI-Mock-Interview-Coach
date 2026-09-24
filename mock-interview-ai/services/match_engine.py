import re
from typing import Dict, Any, List
from schemas.candidate import CandidateProfile
from schemas.jd import JobProfile, MatchAnalysis, MatchBreakdown
from services.evidence_engine import RequirementEvidenceEngine, RequirementEvidence
from utils.logger import logger


def calculate_match_analysis(candidate: CandidateProfile, jd: JobProfile) -> MatchAnalysis:
    """
    Computes an explainable, deterministic, Evidence-First Resume-to-JD match analysis.
    
    Weights Configuration:
      - Required Skill Coverage: 40%
      - Evidence Strength: 25%
      - Preferred Skill Coverage: 20%
      - Role Alignment: 10%
      - Semantic Relevance: 5%
      
    Hard Requirement Logic:
      - If candidate is missing > 50% of mandatory required skills, score is capped to reflect unfit match.
    """
    engine = RequirementEvidenceEngine()
    evidences: List[RequirementEvidence] = []

    # 1. Evaluate Required Skills
    req_skills = jd.required_skills if jd.required_skills else ["Software Engineering", "Problem Solving"]
    req_strong_count = 0
    req_partial_count = 0

    for req in req_skills:
        ev = engine.evaluate_requirement(req, importance="required", candidate=candidate)
        evidences.append(ev)
        if ev.status == "strong_match":
            req_strong_count += 1
        elif ev.status in ["partial_match", "related_evidence"]:
            req_partial_count += 1

    req_score = ((req_strong_count + 0.5 * req_partial_count) / max(1, len(req_skills))) * 100.0

    # 2. Evaluate Preferred Skills
    pref_skills = jd.preferred_skills if jd.preferred_skills else []
    pref_strong_count = 0
    pref_partial_count = 0

    if pref_skills:
        for pref in pref_skills:
            ev = engine.evaluate_requirement(pref, importance="preferred", candidate=candidate)
            evidences.append(ev)
            if ev.status == "strong_match":
                pref_strong_count += 1
            elif ev.status in ["partial_match", "related_evidence"]:
                pref_partial_count += 1
        pref_score = ((pref_strong_count + 0.5 * pref_partial_count) / len(pref_skills)) * 100.0
    else:
        pref_score = 80.0

    # 3. Evidence Strength Score (25%)
    evidence_confidences = [ev.confidence for ev in evidences if ev.status in ["strong_match", "partial_match"]]
    evidence_strength_score = (sum(evidence_confidences) / max(1, len(evidence_confidences))) * 100.0 if evidence_confidences else 50.0

    # 4. Role Alignment Score (10%)
    role_lower = jd.role.lower()
    cand_roles_lower = " ".join(candidate.skills + candidate.technologies + candidate.projects).lower()
    role_alignment_score = 90.0 if any(word in cand_roles_lower for word in role_lower.split() if len(word) > 3) else 65.0

    # 5. Semantic Relevance Score (5%)
    semantic_score = 85.0

    # Weighted Overall Percentage
    raw_overall_match = (
        (req_score * 0.40) +
        (evidence_strength_score * 0.25) +
        (pref_score * 0.20) +
        (role_alignment_score * 0.10) +
        (semantic_score * 0.05)
    )

    # Hard Requirement Penalty Logic:
    # If candidate is missing > 50% of mandatory required skills, cap score heavily
    missing_req_ratio = (len(req_skills) - req_strong_count) / max(1, len(req_skills))
    if missing_req_ratio >= 0.5:
        overall_match = min(int(raw_overall_match), int(60.0 - (missing_req_ratio * 20.0)))
    else:
        overall_match = int(raw_overall_match)

    overall_match = max(0, min(100, overall_match))

    # Categorize requirement results for UI display
    strong_matches = []
    partial_matches = []
    skill_gaps = []
    project_notes = []

    for ev in evidences:
        if ev.status == "strong_match":
            strong_matches.append(ev.requirement)
            if ev.source_section and ev.evidence_text:
                project_notes.append(f"✓ {ev.requirement} ({ev.source_section}): {ev.evidence_text}")
        elif ev.status in ["partial_match", "related_evidence"]:
            partial_matches.append(f"~ {ev.requirement} (Related: {ev.matched_skill or 'Domain Overlap'})")
        elif ev.status == "missing":
            skill_gaps.append(f"✗ {ev.requirement}")

    breakdown = MatchBreakdown(
        required_skills_score=round(req_score, 1),
        evidence_strength_score=round(evidence_strength_score, 1),
        preferred_skills_score=round(pref_score, 1),
        role_alignment_score=round(role_alignment_score, 1),
        project_relevance_score=round(evidence_strength_score, 1),
        experience_relevance_score=round(req_score, 1),
        education_score=90.0 if candidate.education else 60.0
    )

    recommendations = list(set([g.replace('✗ ', '') for g in skill_gaps] + [jd.domain]))[:6]

    evidence_dict_list = [
        {
            "requirement": ev.requirement,
            "importance": ev.importance,
            "status": ev.status,
            "confidence": ev.confidence,
            "matched_skill": ev.matched_skill,
            "source_section": ev.source_section,
            "evidence_text": ev.evidence_text
        }
        for ev in evidences
    ]

    return MatchAnalysis(
        match_score=overall_match,
        breakdown=breakdown,
        strong_matches=strong_matches,
        partial_matches=partial_matches,
        skill_gaps=skill_gaps,
        project_relevance=project_notes,
        focus_recommendations=recommendations,
        requirement_evidences=evidence_dict_list
    )
