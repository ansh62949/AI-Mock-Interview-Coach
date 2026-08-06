from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from schemas.state import InterviewState

from agents.planner import run_planner_agent
from agents.interviewer import run_interviewer_agent
from agents.evaluator import run_evaluator_agent
from agents.reflection import run_reflection_agent
from agents.difficulty import run_difficulty_controller
from agents.coach import run_coach_agent
from utils.logger import logger


# Node Wrappers
def planner_node(state: InterviewState) -> Dict[str, Any]:
    """Node: Analyzes candidate profile and builds initial strategy."""
    return run_planner_agent(state)


def interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """Node: Generates role-tailored and difficulty-calibrated question."""
    return run_interviewer_agent(state)


def evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """Node: Scores candidate's response and extracts feedback."""
    return run_evaluator_agent(state)


def reflection_node(state: InterviewState) -> Dict[str, Any]:
    """Node: Evaluates performance trajectory to determine next routing action."""
    return run_reflection_agent(state)


def difficulty_controller_node(state: InterviewState) -> Dict[str, Any]:
    """Node: Escalates or de-escalates candidate difficulty level."""
    return run_difficulty_controller(state)


def coach_node(state: InterviewState) -> Dict[str, Any]:
    """Node: Synthesizes turn logs into final coaching report."""
    return run_coach_agent(state)


# Conditional Edge Router
def route_reflection(state: InterviewState) -> Literal["coach", "difficulty_controller", "interviewer"]:
    """
    Conditional Routing Logic based on Reflection Agent decision:
    - 'finish' or max_turns reached -> Transition to Coach Agent node.
    - 'probe_deeper' -> Transition directly to Interviewer Agent for follow-up.
    - 'increase_difficulty', 'decrease_difficulty', 'next_topic' -> Transition to Difficulty Controller node.
    """
    decision = state.get("reflection_decision", "next_topic")
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 5)

    if decision == "finish" or turn_count >= max_turns:
        logger.info(f"Graph Router: Routing to Coach Node (turn={turn_count}/{max_turns}, decision={decision}).")
        return "coach"
    elif decision == "probe_deeper":
        logger.info(f"Graph Router: Routing directly to Interviewer Node for follow-up probe.")
        return "interviewer"
    else:
        logger.info(f"Graph Router: Routing to Difficulty Controller Node (decision={decision}).")
        return "difficulty_controller"


def build_interview_graph():
    """
    Constructs and compiles the multi-agent LangGraph StateGraph pipeline.
    
    Graph Topology:
      [START] -> planner -> interviewer -> [END / Wait for Candidate]
      [Candidate Response] -> evaluator -> reflection -> (conditional route)
                                                          |-- 'finish' --> coach -> [END]
                                                          |-- 'probe_deeper' --> interviewer
                                                          |-- 'next/difficulty' --> difficulty_controller -> interviewer
    """
    workflow = StateGraph(InterviewState)

    # Register Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("difficulty_controller", difficulty_controller_node)
    workflow.add_node("coach", coach_node)

    # Entry & Preparation Edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "interviewer")
    workflow.add_edge("interviewer", END)  # Pauses execution for candidate answer input

    # Evaluation & Reflection Loop
    workflow.add_edge("evaluator", "reflection")

    # Conditional Routing Edges
    workflow.add_conditional_edges(
        "reflection",
        route_reflection,
        {
            "coach": "coach",
            "difficulty_controller": "difficulty_controller",
            "interviewer": "interviewer"
        }
    )

    # Loop Re-entry & Completion Edges
    workflow.add_edge("difficulty_controller", "interviewer")
    workflow.add_edge("coach", END)

    return workflow.compile()
