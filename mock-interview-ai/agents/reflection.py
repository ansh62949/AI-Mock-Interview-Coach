from typing import Dict, Any, List
from schemas.state import InterviewState
from schemas.interview import ReflectionOutput, ReflectionDecisionType
from prompts.reflection import REFLECTION_SYSTEM_PROMPT
from utils.llm import get_llm
from utils.logger import logger


def run_reflection_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Reflection Agent: Analyzes evaluation history and determines interview trajectory.
    Enforces probe_count fatigue rules:
      probe_count == 0: probe_deeper
      probe_count == 1: simplify
      probe_count >= 2: next_topic (auto-reset)
    """
    turn_count: int = state.get("turn_count", 1)
    max_turns: int = state.get("max_turns", 5)
    current_probe_count: int = state.get("probe_count", 0)

    # Mandatory turn limit rule
    if turn_count >= max_turns:
        logger.info(f"Reflection Agent: Turn count limit ({max_turns}) reached. Decision: finish.")
        return {
            "reflection_decision": "finish",
            "reflection_reasoning": f"Reached maximum turn limit ({max_turns}). Concluding interview.",
            "follow_up_goal": "Final assessment wrap up.",
            "follow_up_type": "summary",
            "probe_count": current_probe_count,
            "current_step": "reflecting_completed"
        }

    evaluations: List[Dict[str, Any]] = state.get("evaluations", [])
    latest_evaluation = evaluations[-1] if evaluations else {}
    
    target_role: str = state.get("target_role", "Software Engineer")
    current_difficulty: str = state.get("current_difficulty", "Mid-Level")
    latest_question: str = latest_evaluation.get("question") or state.get("current_question") or ""
    latest_response: str = (latest_evaluation.get("candidate_response") or state.get("candidate_response") or "").strip()
    latest_score: int = latest_evaluation.get("score", 6)
    latest_feedback: str = latest_evaluation.get("feedback", "")

    # Hard Fatigue Rule: Never probe more than twice on the same topic
    if current_probe_count >= 2:
        logger.info(f"Reflection Agent: Probe limit reached ({current_probe_count}). Advancing to next_topic.")
        return {
            "reflection_decision": "next_topic",
            "reflection_reasoning": "Completed 2 probes on current topic. Moving to next technical domain.",
            "follow_up_goal": "Production monitoring, system observability, and operational metrics.",
            "follow_up_type": "scenario_stress_test",
            "probe_count": 0,
            "current_step": "reflecting_completed"
        }

    llm = get_llm(temperature=0.2)

    if llm is not None:
        try:
            reflection_prompt = REFLECTION_SYSTEM_PROMPT.format(
                target_role=target_role,
                current_difficulty=current_difficulty,
                turn_count=turn_count,
                max_turns=max_turns,
                latest_question=latest_question,
                latest_response=latest_response,
                latest_score=latest_score,
                latest_feedback=latest_feedback
            )
            structured_llm = llm.with_structured_output(ReflectionOutput, method="json_mode")
            reflection_result: ReflectionOutput = structured_llm.invoke(reflection_prompt)

            
            decision = reflection_result.decision
            if decision in ["probe_deeper", "simplify"]:
                new_probe_count = current_probe_count + 1
            else:
                new_probe_count = 0

            follow_up = reflection_result.follow_up_goal or "Model selection and deployment factors."
            follow_up_type = reflection_result.follow_up_type or ("simplification" if decision == "simplify" else "deeper_tradeoffs")
            
            logger.info(f"Reflection Agent Decision: {decision}. Probe count: {new_probe_count}. Goal: {follow_up}")
            return {
                "reflection_decision": decision,
                "reflection_reasoning": reflection_result.reasoning,
                "follow_up_goal": follow_up,
                "follow_up_type": follow_up_type,
                "probe_count": new_probe_count,
                "current_step": "reflecting_completed"
            }
        except Exception as err:
            logger.warning(f"Reflection Agent LLM invocation failed: {err}. Using heuristic decision.")

    # Heuristic Fallback Decision Tree
    has_response = bool(latest_response)
    lower_res = latest_response.lower()
    is_negation = has_response and lower_res in ["no", "nope", "na", "no.", "none"]
    is_idk = has_response and any(p in lower_res for p in ["i don't know", "dont know", "not sure", "idk", "no idea"])
    is_brief_or_vague = has_response and not (is_negation or is_idk) and (len(latest_response.split()) < 4 or any(p in lower_res for p in ["i'd use an llm", "use an llm", "by using llm", "using llms"]))

    if is_negation or is_idk:
        if current_probe_count == 0:
            routing_decision: ReflectionDecisionType = "simplify"
            reasoning = "Candidate responded negatively or stated unfamiliarity. Simplifying question angle."
            follow_up_goal = "Foundational high-level system concepts."
            follow_up_type = "simplification"
            new_probe_count = 1
        else:
            routing_decision = "next_topic"
            reasoning = "Candidate struggled on current topic. Moving to next topic to maintain interview momentum."
            follow_up_goal = "Production monitoring and deployment observability."
            follow_up_type = "scenario_stress_test"
            new_probe_count = 0
    elif is_brief_or_vague:
        if current_probe_count == 0:
            routing_decision = "probe_deeper"
            reasoning = "Candidate mentioned tool/approach briefly. Probing deeper into specific model selection."
            follow_up_goal = "Model selection, framework choices, and latency trade-offs."
            follow_up_type = "deeper_tradeoffs"
            new_probe_count = 1
        else:
            routing_decision = "simplify"
            reasoning = "Candidate answer remained brief. Asking for a concrete real-world example."
            follow_up_goal = "Practical real-world project example."
            follow_up_type = "real_world_example"
            new_probe_count = 2
    elif latest_score >= 8:
        routing_decision = "increase_difficulty"
        reasoning = f"Candidate scored {latest_score}/10 demonstrating high technical depth."
        follow_up_goal = "High-concurrency failure modes and 4x latency spike scenario."
        follow_up_type = "scenario_stress_test"
        new_probe_count = 0
    elif latest_score <= 4:
        if current_probe_count == 0:
            routing_decision = "simplify"
            reasoning = f"Candidate score low ({latest_score}/10). Lowering question complexity."
            follow_up_goal = "Foundational component responsibilities."
            follow_up_type = "simplification"
            new_probe_count = 1
        else:
            routing_decision = "next_topic"
            reasoning = f"Candidate struggled on concept. Transitioning to next key area."
            follow_up_goal = "System scalability and monitoring."
            follow_up_type = "scenario_stress_test"
            new_probe_count = 0
    elif latest_evaluation.get("weak_points") and len(latest_evaluation.get("weak_points", [])) > 0:
        if current_probe_count == 0:
            routing_decision = "probe_deeper"
            reasoning = f"Candidate scored {latest_score}/10 with specific weak points."
            follow_up_goal = latest_evaluation.get("weak_points")[0]
            follow_up_type = "deeper_tradeoffs"
            new_probe_count = 1
        else:
            routing_decision = "simplify"
            reasoning = f"Probing weak point for second time. Asking for real-world example."
            follow_up_goal = "Real-world trade-off decision example."
            follow_up_type = "real_world_example"
            new_probe_count = 2
    else:
        routing_decision = "next_topic"
        reasoning = f"Candidate answered satisfactorily (Score: {latest_score}/10)."
        follow_up_goal = "Production monitoring, metrics, and deployment observability."
        follow_up_type = "scenario_stress_test"
        new_probe_count = 0

    logger.info(f"Reflection Agent Decision: {routing_decision}. Probe count: {new_probe_count}. Goal: {follow_up_goal}")
    return {
        "reflection_decision": routing_decision,
        "reflection_reasoning": reasoning,
        "follow_up_goal": follow_up_goal,
        "follow_up_type": follow_up_type,
        "probe_count": new_probe_count,
        "current_step": "reflecting_completed"
    }
