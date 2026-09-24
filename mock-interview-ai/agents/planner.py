from typing import Dict, Any, Tuple
from schemas.state import InterviewState
from schemas.interview import InterviewStrategy, InterviewPlan, InterviewPlanRound, InterviewBlueprint, SkillCoverageItem
from prompts.planner import PLANNER_SYSTEM_PROMPT
from utils.llm import get_llm
from utils.logger import logger


def infer_seniority_levels(target_role: str, job_prof: Dict[str, Any], cand_prof: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Infers job level, candidate level, auto-calibrated interview difficulty, and rationale."""
    role_lower = (target_role + " " + job_prof.get("role", "")).lower()
    reqs_str = " ".join(job_prof.get("required_skills", []) + job_prof.get("responsibilities", [])).lower()
    
    if any(k in role_lower or k in reqs_str for k in ["junior", "entry", "associate", "graduate", "0-2 years", "0-1 years"]):
        job_lvl = "Junior"
        cand_lvl = "Entry-Level"
        cal_lvl = "Junior"
        reason = "JD requests entry-level / junior experience (0-2 years) focusing on implementation and baseline APIs."
    elif any(k in role_lower or k in reqs_str for k in ["senior", "lead", "principal", "5+ years", "architect"]):
        job_lvl = "Senior"
        cand_lvl = "Mid-Level"
        cal_lvl = "Senior"
        reason = "JD specifies Senior role requirements including system design, scalability, and architecture trade-offs."
    elif any(k in role_lower or k in reqs_str for k in ["staff", "principal", "head"]):
        job_lvl = "Staff"
        cand_lvl = "Senior"
        cal_lvl = "Staff"
        reason = "JD specifies Staff/Principal level organizational and system design leadership."
    else:
        job_lvl = "Mid-Level"
        cand_lvl = "Mid-Level"
        cal_lvl = "Mid-Level"
        reason = "Auto-calibrated to Mid-Level based on technical requirements and candidate project evidence."

    return job_lvl, cand_lvl, cal_lvl, reason


def run_planner_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Planner Agent: Analyzes candidate profile, JD, and match analysis to build structured Interview Blueprint.
    """
    target_role: str = state.get("target_role", "Software Engineer")
    resume_summary: str = state.get("resume_summary", "General engineering background")
    focus_area: str = state.get("focus_area", "Mixed")
    job_prof = state.get("job_profile") or {}
    cand_prof = state.get("candidate_profile") or {}
    match_an = state.get("match_analysis") or {}

    company = job_prof.get("company", "Tech Company")
    strong_matches = match_an.get("strong_matches", cand_prof.get("skills", [])[:5])
    skill_gaps = match_an.get("skill_gaps", [])
    partial_matches = match_an.get("partial_matches", [])

    job_lvl, cand_lvl, cal_lvl, reason = infer_seniority_levels(target_role, job_prof, cand_prof)

    # Build Skill Coverage Items
    coverage_items = []
    for s in strong_matches[:4]:
        coverage_items.append(SkillCoverageItem(skill=s, importance="required", resume_evidence=True, coverage_objective="deep_validate"))
    for s in skill_gaps[:3]:
        clean_s = s.lstrip("✗✓~ ").strip()
        coverage_items.append(SkillCoverageItem(skill=clean_s, importance="required", resume_evidence=False, coverage_objective="gap_check"))

    # Build 6-Round Roadmap
    rounds = [
        InterviewPlanRound(round_number=1, title="Resume & Background Overview", focus=f"Candidate experience & strongest projects in {target_role}"),
        InterviewPlanRound(round_number=2, title="Core Technical Stack", focus=", ".join(strong_matches[:3]) if strong_matches else "Core Engineering Fundamentals"),
        InterviewPlanRound(round_number=3, title="Frameworks & Architecture", focus="Component design, REST APIs, and state management"),
        InterviewPlanRound(round_number=4, title="Resume Portfolio Deep Dive", focus=cand_prof.get("projects", ["Key Technical Projects"])[0] if cand_prof.get("projects") else "Project Deep Dive"),
        InterviewPlanRound(round_number=5, title="JD Gap & Missing Skill Validation", focus=", ".join([s.lstrip("✗✓~ ").strip() for s in skill_gaps[:2]]) if skill_gaps else "System Trade-offs & Security"),
        InterviewPlanRound(round_number=6, title="Practical Backend Scenario", focus="Debugging, production edge cases, and performance tuning")
    ]

    llm = get_llm(temperature=0.3)
    focus_summary_text = f"Structured ReAct evaluation tailored for {target_role} ({cal_lvl} Level) at {company}."
    key_topics = strong_matches[:3] + [s.lstrip("✗✓~ ").strip() for s in skill_gaps[:2]]

    if llm is not None:
        try:
            planner_prompt = PLANNER_SYSTEM_PROMPT.format(
                target_role=target_role,
                resume_summary=resume_summary,
                focus_area=focus_area
            )
            structured_llm = llm.with_structured_output(InterviewStrategy, method="json_mode")
            strategy_result: InterviewStrategy = structured_llm.invoke(planner_prompt)
            if strategy_result and strategy_result.key_topics:
                key_topics = strategy_result.key_topics
                focus_summary_text = strategy_result.focus_summary
        except Exception as err:
            logger.warning(f"Planner Agent LLM invocation failed: {err}. Using rule-based blueprint.")

    blueprint = InterviewBlueprint(
        role=target_role,
        candidate_level=cand_lvl,
        job_level=job_lvl,
        interview_level=cal_lvl,
        level_confidence=0.88,
        level_reason=reason,
        matched_skills=strong_matches,
        missing_skills=[s.lstrip("✗✓~ ").strip() for s in skill_gaps],
        partial_skills=[s.lstrip("✗✓~ ").strip() for s in partial_matches],
        skill_coverage=coverage_items,
        rounds_plan=rounds,
        difficulty_progression=["easy", "medium", "medium", "hard"] if cal_lvl == "Junior" else ["medium", "medium", "hard", "system_design"],
        focus_summary=focus_summary_text
    )

    strategy = InterviewStrategy(
        key_topics=key_topics,
        initial_difficulty=cal_lvl,
        focus_summary=focus_summary_text
    )

    interview_plan = InterviewPlan(
        target_role=target_role,
        company=company,
        rounds=rounds,
        focus_summary=focus_summary_text
    )

    logger.info(f"Planner Agent generated Interview Blueprint ({cal_lvl} level, {len(key_topics)} topics).")

    return {
        "interview_blueprint": blueprint.model_dump(),
        "interview_strategy": strategy.model_dump(),
        "interview_plan": interview_plan.model_dump(),
        "candidate_level": cand_lvl,
        "job_level": job_lvl,
        "interview_level": cal_lvl,
        "current_difficulty": cal_lvl,
        "current_step": "planning_completed"
    }
