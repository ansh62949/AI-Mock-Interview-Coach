import json
import time
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from schemas.state import InterviewState
from prompts.interviewer import INTERVIEWER_SYSTEM_PROMPT
from tools.interview_tools import (
    INTERVIEWER_TOOLS,
    set_current_interview_state,
    search_interview_questions,
    get_candidate_profile,
    get_job_requirements,
    get_candidate_weaknesses,
    get_interview_history
)
from services.rag_service import rag_service
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
    ReAct-Style Interviewer Agent:
    Dynamically decides whether to execute tools (ChromaDB Vector Questions, Candidate Profile, Job Requirements,
    Candidate Weaknesses, History), receives tool outputs, reasons over results, and formulates interview questions.
    """
    # Set active thread state for tool execution
    set_current_interview_state(state)

    target_role: str = state.get("target_role", "Software Engineer")
    resume_summary: str = state.get("resume_summary", "")
    current_difficulty: str = state.get("current_difficulty", "Mid-Level")
    
    interview_strategy: Dict[str, Any] = state.get("interview_strategy") or {}
    key_topics: List[str] = interview_strategy.get("key_topics", ["Software Engineering"])
    focus_summary: str = interview_strategy.get("focus_summary", "")

    conversation_history: List[Dict[str, str]] = state.get("conversation_history", [])
    history_formatted: str = format_transcript_history(conversation_history)
    candidate_response: str = (state.get("candidate_response") or "").strip()
    
    reflection_decision: str = state.get("reflection_decision", "next_topic")
    follow_up_goal: str = state.get("follow_up_goal") or "Technical depth and trade-off evaluation."
    follow_up_type: str = state.get("follow_up_type") or "deeper_tradeoffs"

    executed_tool_records: List[Dict[str, Any]] = []

    llm = get_llm(temperature=0.6)

    if llm is not None:
        try:
            # Bind tools to Chat model
            llm_with_tools = llm.bind_tools(INTERVIEWER_TOOLS)
            tool_map = {t.name: t for t in INTERVIEWER_TOOLS}

            system_content = INTERVIEWER_SYSTEM_PROMPT.format(
                target_role=target_role,
                current_difficulty=current_difficulty,
                resume_summary=resume_summary or 'General engineering background.',
                focus_summary=focus_summary or f'Technical evaluation for {target_role}.',
                reflection_decision=reflection_decision,
                follow_up_goal=follow_up_goal,
                follow_up_type=follow_up_type,
                latest_candidate_response=candidate_response or 'No candidate response yet (Turn 1 initial question).',
                history_formatted=history_formatted
            )

            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=f"Formulate the next technical interview question for the candidate targeting {target_role} at {current_difficulty} level. Decide if you need any tools first.")
            ]

            # ReAct Loop: LLM -> decide tool -> tool execution -> tool message -> LLM -> question
            max_tool_iterations = 3
            question_text = ""

            for step in range(max_tool_iterations):
                ai_msg = llm_with_tools.invoke(messages)
                messages.append(ai_msg)

                if hasattr(ai_msg, 'tool_calls') and ai_msg.tool_calls:
                    logger.info(f"ReAct Loop (Step {step+1}): LLM emitted tool calls: {[tc.get('name') for tc in ai_msg.tool_calls]}")
                    for tc in ai_msg.tool_calls:
                        t_name = tc.get("name")
                        t_args = tc.get("args", {})
                        t_fn = tool_map.get(t_name)
                        
                        if t_fn:
                            try:
                                t_res = t_fn.invoke(t_args)
                                t_str = str(t_res)
                            except Exception as tex:
                                t_res = f"Tool Error: {tex}"
                                t_str = str(t_res)

                            # Format safe human-friendly activity summary for Agent Trace UI
                            safe_summaries = {
                                "search_interview_questions": f"Retrieved relevant questions from ChromaDB vector store.",
                                "search_technical_knowledge": "Retrieved technical reference knowledge.",
                                "get_candidate_profile": "Reviewed candidate resume context & skills.",
                                "get_job_requirements": "Checked job description requirements.",
                                "get_candidate_weaknesses": "Targeting identified knowledge gaps & weaknesses.",
                                "get_interview_history": "Checked transcript history to prevent repetition."
                            }
                            summary_text = safe_summaries.get(t_name, t_str[:120] + ("..." if len(t_str) > 120 else ""))

                            executed_tool_records.append({
                                "tool": t_name,
                                "arguments": t_args,
                                "result_summary": summary_text,
                                "timestamp": time.strftime("%H:%M:%S")
                            })

                            messages.append(ToolMessage(
                                content=t_str,
                                tool_call_id=tc.get("id", f"call_{step}_{t_name}")
                            ))

                else:
                    question_text = ai_msg.content.strip() if hasattr(ai_msg, 'content') and ai_msg.content else ""
                    break

            # If ReAct loop resulted in question text
            if question_text:
                logger.info(f"Interviewer Agent generated question via ReAct loop with {len(executed_tool_records)} tool calls executed.")
                return {
                    "current_question": question_text,
                    "tool_calls": executed_tool_records,
                    "current_topic": key_topics[0] if key_topics else target_role,
                    "turn_count": state.get("turn_count", 0) + 1,
                    "current_step": "question_generated"
                }

        except Exception as err:
            logger.warning(f"Interviewer Agent ReAct LLM invocation failed: {err}. Executing tool-grounded fallback.")

    # FALLBACK ENGINE GROUNDED IN DIRECT TOOL RETRIEVAL
    fallback_query = follow_up_goal if follow_up_goal else f"{target_role} {key_topics[0] if key_topics else 'Architecture'}"
    fallback_q = search_interview_questions.invoke({
        "query": fallback_query,
        "difficulty": current_difficulty,
        "role": target_role,
        "top_k": 3
    })
    
    if follow_up_type == "teach_then_probe":
        retrieved_question = f"No problem. Let's break it down into a simpler scenario: Imagine traffic suddenly increases 100x. What auto-scaling behavior would you expect for your backend service?"
    elif follow_up_type == "target_misconception":
        retrieved_question = f"Let's clarify that concept. How does auto-scaling work in production environments when traffic spikes unexpectedly?"
    else:
        retrieved_question = "Can you walk me through an end-to-end technical system you built, highlighting key architectural decisions and performance trade-offs?"
        if isinstance(fallback_q, list) and len(fallback_q) > 0 and "question" in fallback_q[0]:
            retrieved_question = fallback_q[0]["question"]

    executed_tool_records.append({
        "tool": "search_interview_questions",
        "arguments": {"query": fallback_query, "difficulty": current_difficulty},
        "result_summary": "Retrieved relevant questions from ChromaDB vector store.",
        "timestamp": time.strftime("%H:%M:%S")
    })


    return {
        "current_question": retrieved_question,
        "tool_calls": executed_tool_records,
        "current_topic": key_topics[0] if key_topics else target_role,
        "turn_count": state.get("turn_count", 0) + 1,
        "current_step": "question_generated"
    }
