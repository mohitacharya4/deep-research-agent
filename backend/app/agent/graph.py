"""The research state machine.

    plan → search → fetch → reflect ─(gaps? & budget left)→ search
                                  └─(enough)──────────────→ synthesize → critic → END

The single conditional edge out of ``reflect`` is the agent loop: it either routes
back to ``search`` with fresh follow-up queries or moves on to write the report.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent import nodes
from app.agent.state import ResearchState
from app.config import get_settings

# The research graph, fully parametrised by our state type.
ResearchGraph = CompiledStateGraph[ResearchState, Any, ResearchState, ResearchState]


def _route_after_reflect(state: ResearchState) -> Literal["search", "synthesize"]:
    """Loop back to search while gaps remain, otherwise synthesize the report."""
    return "synthesize" if state.get("enough", True) else "search"


def build_graph() -> ResearchGraph:
    """Build and compile the research graph."""
    graph: StateGraph[ResearchState, Any, ResearchState, ResearchState] = StateGraph(
        ResearchState
    )

    graph.add_node("plan", nodes.plan_node)
    graph.add_node("search", nodes.search_node)
    graph.add_node("fetch", nodes.fetch_node)
    graph.add_node("reflect", nodes.reflect_node)
    graph.add_node("synthesize", nodes.synthesize_node)
    graph.add_node("critic", nodes.critic_node)

    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "fetch")
    graph.add_edge("fetch", "reflect")
    graph.add_conditional_edges(
        "reflect",
        _route_after_reflect,
        {"search": "search", "synthesize": "synthesize"},
    )
    graph.add_edge("synthesize", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


async def run_research(question: str, max_iterations: int | None = None) -> ResearchState:
    """Run the full research graph to completion and return the final state."""
    settings = get_settings()
    initial: ResearchState = {
        "question": question,
        "max_iterations": max_iterations or settings.max_iterations,
    }
    graph = build_graph()
    result = await graph.ainvoke(initial)
    return cast(ResearchState, result)
