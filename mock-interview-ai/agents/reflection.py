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

    # Classification State Guided Routing
    answer_status = latest_evaluation.get("answer_status", "partial")
    followup_strategy = latest_evaluation.get("followup_strategy", "probe_missing_concept")
    misconceptions = latest_evaluation.get("misconceptions", [])
    knowledge_gaps = latest_evaluation.get("knowledge_gaps", [])

    if answer_status == "unknown" or followup_strategy == "teach_then_probe":
        if current_probe_count == 0:
            routing_decision: ReflectionDecisionType = "simplify"
            reasoning = "Candidate explicitly stated unfamiliarity (unknown state). Breaking down concept into simpler scenario."
            follow_up_goal = "Break down concept into simpler conceptual building blocks before probing trade-offs."
            follow_up_type = "teach_then_probe"
            new_probe_count = 1
        else:
            routing_decision = "next_topic"
            reasoning = "Candidate unfamiliar on current topic after probe. Transitioning to next technical domain."
            follow_up_goal = "Production monitoring, system observability, and deployment metrics."
            follow_up_type = "scenario_stress_test"
            new_probe_count = 0
    elif answer_status == "incorrect" or followup_strategy == "target_misconception":
        if current_probe_count == 0:
            routing_decision = "probe_deeper"
            misc_text = misconceptions[0] if misconceptions else "technical misconception"
            reasoning = f"Candidate expressed explicit misconception: {misc_text}. Addressing misconception."
            follow_up_goal = f"Politely address misconception ({misc_text}) and ask targeted question."
            follow_up_type = "target_misconception"
            new_probe_count = 1
        else:
            routing_decision = "simplify"
            reasoning = "Targeted misconception probe complete. Asking for concrete foundational example."
            follow_up_goal = "Concrete foundational example."
            follow_up_type = "real_world_example"
            new_probe_count = 2
    elif answer_status == "off_topic" or followup_strategy == "redirect":
        routing_decision = "next_topic"
        reasoning = "Candidate response was off-topic. Redirecting back to target role requirements."
        follow_up_goal = "Core role technical requirements."
        follow_up_type = "redirect"
        new_probe_count = 0
    elif answer_status == "correct" or followup_strategy == "increase_depth" or latest_score >= 8:
        routing_decision = "increase_difficulty"
        reasoning = f"Candidate answered correctly (Score: {latest_score}/10). Advancing technical depth and scale."
        follow_up_goal = "High-concurrency failure modes, 10,000 req/sec scale, and operational cost trade-offs."
        follow_up_type = "increase_depth"
        new_probe_count = 0
    elif current_probe_count == 0:
        routing_decision = "probe_deeper"
        gap_text = knowledge_gaps[0] if knowledge_gaps else "missing trade-off detail"
        reasoning = f"Candidate response partially correct with gap ({gap_text}). Probing missing concept."
        follow_up_goal = f"Probe missing technical concept: {gap_text}"
        follow_up_type = "probe_missing_concept"
        new_probe_count = 1
    else:
        routing_decision = "next_topic"
        reasoning = f"Completed probing on topic. Transitioning to next key area."
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
