import pytest
from graph.interview_graph import build_interview_graph


def test_build_interview_graph():
    graph = build_interview_graph()
    assert graph is not None
