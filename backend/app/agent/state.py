"""The shared state that flows through the research graph.

Nodes read the current state and return a partial update (a dict of the keys they
change). We deliberately keep the reducers simple — nodes replace the collections
they own rather than relying on concurrent merges — so the data flow stays easy to
follow when explaining the agent loop.
"""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel

from app.tools.schemas import SearchResult


class Candidate(BaseModel):
    """A search hit tagged with the sub-question that surfaced it."""

    sub_question: str
    result: SearchResult


class Finding(BaseModel):
    """A read source: the evidence the report is built and cited from."""

    sub_question: str
    title: str
    url: str
    snippet: str
    content: str = ""


class ResearchState(TypedDict, total=False):
    """Graph state for one research run."""

    # Inputs / config
    question: str
    max_iterations: int

    # Planner output and the queries still to run this iteration
    plan: list[str]
    pending_queries: list[str]

    # Working memory
    candidates: list[Candidate]
    findings: list[Finding]
    seen_urls: list[str]

    # Loop control + reflection
    iteration: int
    enough: bool
    gaps: str

    # Outputs
    report: str
    unsupported_claims: list[str]
    total_tokens: int
