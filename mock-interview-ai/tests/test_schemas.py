import pytest
from schemas.interview import CandidateProfile, InterviewStrategy, EvaluationResult, ReflectionOutput, FinalReport


def test_candidate_profile_schema():
    profile = CandidateProfile(
        target_role="Senior AI Engineer",
        resume_summary="Python & LangGraph",
        focus_area="Technical"
    )
    assert profile.target_role == "Senior AI Engineer"
    assert profile.focus_area == "Technical"


def test_evaluation_result_schema():
    eval_res = EvaluationResult(
        score=8,
        feedback="Great answer",
        strong_points=["Clear explanation"],
        weak_points=["Metrics missing"]
    )
    assert eval_res.score == 8
    assert len(eval_res.strong_points) == 1


def test_reflection_output_schema():
    ref = ReflectionOutput(
        decision="increase_difficulty",
        reasoning="Score 9/10"
    )
    assert ref.decision == "increase_difficulty"
