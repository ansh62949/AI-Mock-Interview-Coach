from typing import Dict, Any, List
from schemas.state import InterviewState
from prompts.interviewer import INTERVIEWER_SYSTEM_PROMPT
from utils.llm import get_llm
from utils.logger import logger


def format_transcript_history(history: List[Dict[str, str]]) -> str:
    """Formats conversation history array into clean transcript block for prompt input."""
    if not history:
        return "No previous exchanges."
    
    transcript_lines: List[str] = []
    for message in history:
        speaker_role = "Interviewer" if message.get("role") == "interviewer" else "Candidate"
        transcript_lines.append(f"{speaker_role}: {message.get('content', '')}")
    return "\n".join(transcript_lines)


def run_interviewer_agent(state: InterviewState) -> Dict[str, Any]:
    """
    Interviewer Agent: Formulates natural conversational technical interview questions.
    Passes full context (role, resume, transcript, latest answer, reflection goal, probing style).
    """
    target_role: str = state.get("target_role", "Software Engineer")
    resume_summary: str = state.get("resume_summary", "")
    focus_area: str = state.get("focus_area", "Mixed")
    current_difficulty: str = state.get("current_difficulty", "Mid-Level")
    
    interview_strategy: Dict[str, Any] = state.get("interview_strategy") or {}
    key_topics: List[str] = interview_strategy.get("key_topics", ["System Architecture", "LLM Design"])
    focus_summary: str = interview_strategy.get("focus_summary", "")

    conversation_history: List[Dict[str, str]] = state.get("conversation_history", [])
    history_formatted: str = format_transcript_history(conversation_history)
    
    candidate_response: str = (state.get("candidate_response") or "").strip()
    
    evaluations: List[Dict[str, Any]] = state.get("evaluations", [])
    latest_evaluation = evaluations[-1] if evaluations else {}
    latest_feedback: str = latest_evaluation.get("feedback", "Initial interview step.")
    
    reflection_decision: str = state.get("reflection_decision", "next_topic")
    follow_up_goal: str = state.get("follow_up_goal") or "Model selection and deployment architecture."
    follow_up_type: str = state.get("follow_up_type") or "deeper_tradeoffs"

    llm = get_llm(temperature=0.7)

    if llm is not None:
        try:
            interviewer_prompt = INTERVIEWER_SYSTEM_PROMPT.format(
                target_role=target_role,
                current_difficulty=current_difficulty,
                resume_summary=resume_summary or "General engineering candidate background.",
                focus_summary=focus_summary or f"Technical interview for {target_role}.",
                key_topics=", ".join(key_topics),
                follow_up_goal=follow_up_goal,
                follow_up_type=follow_up_type,
                reflection_decision=reflection_decision,
                latest_candidate_response=candidate_response or "No candidate response yet (Turn 1 initial question).",
                history_formatted=history_formatted
            )
            response = llm.invoke(interviewer_prompt)
            question_text = response.content.strip()
            if question_text:
                logger.info(f"Interviewer Agent generated natural conversational question for turn {state.get('turn_count', 0) + 1}.")
                return _build_interviewer_output(state, question_text)
        except Exception as err:
            logger.warning(f"Interviewer Agent LLM invocation failed: {err}. Using natural fallback question.")

    # Contextual Fallback Question Generation (Free of Raw Evaluator Text)
    current_turn = state.get("turn_count", 0) + 1
    lower_ans = candidate_response.lower()
    lower_resume = resume_summary.lower()
    is_negation = lower_ans in ["no", "nope", "na", "no.", "none"]
    is_idk = any(p in lower_ans for p in ["don't know", "dont know", "not sure", "idk", "no idea"])

    if is_negation or is_idk:
        if reflection_decision == "next_topic":
            question_text = "That's okay. Let's move to another area: How would you evaluate and monitor the performance and latency of an AI application after deploying it to production?"
        else:
            question_text = "No problem. Let me reframe that: Imagine you're building a simple AI service. At what point would you decide that splitting it into multiple microservices is better than keeping everything in one application?"
    elif "pr ai" in lower_ans or "pull request" in lower_ans or "6 agents" in lower_ans or "agent" in lower_ans:
        question_text = "You mentioned building a PR AI with multiple agents. How did you coordinate state and communication between those agents, and why did you choose that architecture?"
    elif "kafka" in lower_ans or "event stream" in lower_ans:
        if follow_up_type == "real_world_example":
            question_text = "That makes sense. Can you share an example from your experience where introducing Kafka added unexpected operational overhead, and how you handled it?"
        else:
            question_text = "You mentioned using Kafka for event streaming. What key factors led you to choose Kafka over RabbitMQ or Redis Pub/Sub for your data pipeline?"
    elif "fastapi" in lower_ans or "python" in lower_ans:
        question_text = "You mentioned using FastAPI. How did you structure your API endpoints and handle concurrent async requests without blocking the event loop?"
    elif "rag" in lower_ans or "vector" in lower_ans or "pgvector" in lower_ans or "langgraph" in lower_ans:
        if follow_up_type == "real_world_example":
            question_text = "That's a reasonable approach to RAG. Can you describe a real project where you had to choose between a simple vector search and a more complex graph pipeline? What influenced your decision?"
        else:
            question_text = "You mentioned building a RAG system with LangGraph and pgvector. How do you manage embedding index updates and maintain retrieval quality over time?"
    elif "llm" in lower_ans or "model" in lower_ans:
        if follow_up_type == "real_world_example":
            question_text = "Can you describe a situation from your experience where introducing an external LLM service was actually worth the added latency and cost?"
        else:
            question_text = "That's a good starting point. Which specific LLM model family would you choose for this workload, and what factors would influence that decision?"
    elif candidate_response:
        question_text = f"That makes sense. You mentioned {candidate_response[:40]}... How do you decide when introducing another technology is worth the added complexity?"
    else:
        # Resume-aware Initial Turn 1 Question
        if "pr ai" in lower_resume or "agent" in lower_resume or "pull request" in lower_resume:
            question_text = f"I see from your background that you built an AI system with multiple agents. Walk me through how you designed that architecture and how the agents interacted."
        elif "rag" in lower_resume or "vector" in lower_resume:
            question_text = f"I notice you have experience with RAG and vector search. Suppose you are building a production AI document assistant. How would you design the system architecture from request to response?"
        else:
            question_text = f"Let's start with something practical. Suppose you are building a production AI application for a {target_role} team. How would you design the overall system architecture from request to response?"

    logger.info(f"Interviewer Agent completed using natural contextual fallback question for turn {current_turn}.")
    return _build_interviewer_output(state, question_text)


def _build_interviewer_output(state: InterviewState, question_text: str) -> Dict[str, Any]:
    """Constructs state updates for new interviewer question."""
    next_turn_count = state.get("turn_count", 0) + 1
    new_message = {"role": "interviewer", "content": question_text}
    
    return {
        "current_question": question_text,
        "turn_count": next_turn_count,
        "conversation_history": [new_message],
        "current_step": "awaiting_candidate_response"
    }
