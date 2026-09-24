import json
from typing import Dict, Any, List
from schemas.state import InterviewState
from schemas.interview import MultiDimEvaluation
from prompts.evaluator import EVALUATOR_SYSTEM_PROMPT
from tools.interview_tools import calculate_interview_score, save_interview_answer, search_technical_knowledge, set_current_interview_state
from utils.llm import get_llm
from utils.logger import logger


def run_evaluator_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Evaluator Agent: Evaluates candidate answer across 5 core dimensions using real tool execution
    and classifies answer state into one of 5 distinct states: unknown, incorrect, partial, correct, off_topic.
    """
    set_current_interview_state(state)

    session_id: str = state.get("session_id") or "session_default"
    target_role: str = state.get("target_role", "Software Engineer")
    current_difficulty: str = state.get("current_difficulty", "Mid-Level")
    current_question: str = state.get("current_question", "")
    candidate_response: str = state.get("candidate_response", "")
    cand_resp_lower = candidate_response.lower().strip()

    # Fast-path detection for explicit unknown responses
    is_unknown_expression = any(p in cand_resp_lower for p in ["i don't know", "dont know", "not sure", "idk", "no idea", "can't recall", "no experience", "haven't used"])

    if is_unknown_expression:
        eval_result = MultiDimEvaluation(
            answer_status="unknown",
            technical_correctness=1,
            depth=1,
            relevance=1,
            completeness=1,
            communication=4,
            overall_score=1.6,
            confidence=0.98,
            knowledge_gaps=[state.get("current_topic") or "Target Concept"],
            misconceptions=[],
            needs_followup=True,
            followup_strategy="teach_then_probe",
            recommended_topic=state.get("current_topic") or "Core Fundamentals",
            feedback="Candidate explicitly indicated unfamiliarity with the topic.",
            strengths=[],
            weaknesses=[f"Unfamiliar with {state.get('current_topic', 'target domain')}"],
            missing_concepts=["Foundational principles", "Architectural concepts"],
            suggested_improvement="Break down the concept into a simpler scenario before probing trade-offs."
        )

        save_interview_answer.invoke({
            "question_id": f"q_{state.get('turn_count', 1)}",
            "answer": candidate_response,
            "metadata": {
                "question": current_question,
                "score": 1.6,
                "answer_status": "unknown"
            }
        })
        logger.info(f"Evaluator Agent: Classified response as 'unknown'. Followup strategy: teach_then_probe.")
        return _build_evaluator_output(state, eval_result)

    # Optional Technical Grounding Verification via search_technical_knowledge
    tech_knowledge_context = ""
    if any(k in candidate_response.lower() for k in ["kafka", "redis", "postgres", "sql", "rag", "langgraph", "docker", "k8s", "aws", "ecs", "lambda"]):
        try:
            chunks = search_technical_knowledge.invoke({"query": candidate_response[:100], "top_k": 2})
            if isinstance(chunks, list) and chunks:
                tech_knowledge_context = "\n- ".join([c.get("content", "") for c in chunks if isinstance(c, dict)])
        except Exception as tex:
            logger.warning(f"Evaluator search_technical_knowledge exception: {tex}")

    llm = get_llm(temperature=0.2)

    if llm is not None:
        try:
            base_eval_prompt = EVALUATOR_SYSTEM_PROMPT.format(
                target_role=target_role,
                current_difficulty=current_difficulty,
                current_question=current_question,
                candidate_response=candidate_response
            )
            evaluator_prompt = (
                f"{base_eval_prompt}\n\n"
                f"FACTUAL TECHNICAL GROUNDING REFERENCE:\n{tech_knowledge_context if tech_knowledge_context else 'Standard technical concepts'}\n\n"
                f"STRICT INSTRUCTION: Classify `answer_status` (unknown, incorrect, partial, correct, off_topic) "
                f"and provide sub-scores out of 10 for:\n"
                f"- technical_correctness\n- depth\n- relevance\n- completeness\n- communication\n"
                f"Identify `knowledge_gaps`, `misconceptions`, and set `followup_strategy`."
            )
            structured_llm = llm.with_structured_output(MultiDimEvaluation)
            eval_result: MultiDimEvaluation = structured_llm.invoke(evaluator_prompt)
            
            # Deterministic scoring calculation via tool call
            score_res = calculate_interview_score.invoke({
                "technical_correctness": float(eval_result.technical_correctness),
                "depth": float(eval_result.depth),
                "relevance": float(eval_result.relevance),
                "completeness": float(eval_result.completeness),
                "communication": float(eval_result.communication)
            })
            deterministic_overall = score_res.get("overall_score", eval_result.overall_score) if isinstance(score_res, dict) else eval_result.overall_score
            eval_result.overall_score = deterministic_overall

            # Save answer via tool call
            save_interview_answer.invoke({
                "question_id": f"q_{state.get('turn_count', 1)}",
                "answer": candidate_response,
                "metadata": {
                    "question": current_question,
                    "score": deterministic_overall,
                    "answer_status": eval_result.answer_status,
                    "verdict": score_res.get("verdict") if isinstance(score_res, dict) else "Evaluated"
                }
            })

            logger.info(f"Evaluator Agent: answer_status='{eval_result.answer_status}', score={deterministic_overall}/10.")
            return _build_evaluator_output(state, eval_result)
        except Exception as err:
            logger.warning(f"Evaluator Agent LLM invocation failed: {err}. Using heuristic fallback.")

    # Heuristic evaluation fallback
    response_length = len(candidate_response.split())
    if response_length < 4 or cand_resp_lower in ["no", "idk", "i don't know"]:
        status_val = "unknown"
        tech_corr = 2.0
        depth = 1.0
        rel = 2.0
        comp = 1.0
        comm = 4.0
        strat = "teach_then_probe"
        feedback_str = "Response is brief and indicates unfamiliarity or missing detail."
        suggested = "Break down the concept into simpler building blocks."
        strong = []
        weak = ["Incomplete technical explanation"]
        missing = ["Core concepts"]
        gaps = ["Foundational knowledge"]
        miscons = []
    elif response_length > 35:
        status_val = "correct"
        tech_corr = 8.0
        depth = 8.0
        rel = 9.0
        comp = 8.0
        comm = 9.0
        strat = "increase_depth"
        feedback_str = "Detailed response demonstrating solid technical awareness."
        suggested = "Elaborate on production failure modes and specific monitoring metrics."
        strong = ["Detailed system design", "Strong communication"]
        weak = ["Edge cases under peak load"]
        missing = ["Latency SLAs"]
        gaps = []
        miscons = []
    else:
        status_val = "partial"
        tech_corr = 6.0
        depth = 6.0
        rel = 7.0
        comp = 6.0
        comm = 7.0
        strat = "probe_missing_concept"
        feedback_str = "Solid baseline response covering key high-level concepts."
        suggested = "Elaborate on tool selection rationale and quantitative trade-offs."
        strong = ["Relevant technical concepts"]
        weak = ["Lacks quantitative trade-offs"]
        missing = ["Performance benchmarking"]
        gaps = ["Quantitative trade-offs"]
        miscons = []

    # Deterministic scoring calculation via tool call
    score_res = calculate_interview_score.invoke({
        "technical_correctness": tech_corr,
        "depth": depth,
        "relevance": rel,
        "completeness": comp,
        "communication": comm
    })
    overall = score_res.get("overall_score", 6.5) if isinstance(score_res, dict) else 6.5

    multi_result = MultiDimEvaluation(
        answer_status=status_val,
        technical_correctness=int(tech_corr),
        depth=int(depth),
        relevance=int(rel),
        completeness=int(comp),
        communication=int(comm),
        overall_score=overall,
        knowledge_gaps=gaps,
        misconceptions=miscons,
        needs_followup=True,
        followup_strategy=strat,
        feedback=feedback_str,
        strengths=strong,
        weaknesses=weak,
        missing_concepts=missing,
        suggested_improvement=suggested
    )

    save_interview_answer.invoke({
        "question_id": f"q_{state.get('turn_count', 1)}",
        "answer": candidate_response,
        "metadata": {
            "question": current_question,
            "score": overall,
            "answer_status": status_val
        }
    })

    return _build_evaluator_output(state, multi_result)


def _build_evaluator_output(state: InterviewState, evaluation: MultiDimEvaluation) -> Dict[str, Any]:
    """Constructs state updates for evaluation result."""
    current_turn = state.get("turn_count", 1)
    
    eval_dict = {
        "turn": current_turn,
        "question": state.get("current_question", ""),
        "candidate_response": state.get("candidate_response", ""),
        "answer_status": evaluation.answer_status,
        "confidence": evaluation.confidence,
        "score": int(round(evaluation.overall_score)),
        "overall_score": round(evaluation.overall_score, 1),
        "technical_correctness": evaluation.technical_correctness,
        "depth": evaluation.depth,
        "relevance": evaluation.relevance,
        "completeness": evaluation.completeness,
        "communication": evaluation.communication,
        "knowledge_gaps": evaluation.knowledge_gaps,
        "misconceptions": evaluation.misconceptions,
        "needs_followup": evaluation.needs_followup,
        "followup_strategy": evaluation.followup_strategy,
        "recommended_topic": evaluation.recommended_topic,
        "feedback": f"**Summary**: {evaluation.feedback}\n\n**Actionable Improvement**: {evaluation.suggested_improvement}",
        "strong_points": evaluation.strengths,
        "weak_points": evaluation.weaknesses,
        "missing_concepts": evaluation.missing_concepts
    }

    new_weak_areas = list(set(evaluation.weaknesses + evaluation.knowledge_gaps + evaluation.misconceptions))

    return {
        "evaluations": [eval_dict],
        "strong_areas": evaluation.strengths,
        "weak_areas": new_weak_areas if new_weak_areas else evaluation.weaknesses,
        "current_step": "evaluating_completed"
    }

