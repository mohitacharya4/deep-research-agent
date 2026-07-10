"""End-to-end test of the research graph with the LLM and tools faked out.

This exercises the real state machine — including the reflect→search loop and the
iteration budget — without touching Ollama or the network.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.agent.graph import run_research
from app.tools.schemas import FetchedDocument, SearchResult


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.usage_metadata = {"total_tokens": 7}


class _FakeLLM:
    """Returns canned responses keyed off the system prompt; loops once then stops."""

    def __init__(self) -> None:
        self._reflect_calls = 0

    async def ainvoke(self, messages: list[Any]) -> _FakeMessage:
        system = str(messages[0].content)
        if "research planner" in system:
            return _FakeMessage('["initial query one", "initial query two"]')
        if "research supervisor" in system:
            self._reflect_calls += 1
            # First reflection asks for a follow-up (drives the loop); later ones stop.
            if self._reflect_calls == 1:
                return _FakeMessage(
                    '{"enough": false, "gaps": "missing recent data", '
                    '"new_queries": ["a follow up query"]}'
                )
            return _FakeMessage('{"enough": true, "gaps": "none", "new_queries": []}')
        if "research writer" in system:
            return _FakeMessage("Solar costs fell sharply [1]. Wind is competitive [2].")
        return _FakeMessage("{}")


class _FakeTool:
    def __init__(self, fn: Any) -> None:
        self._fn = fn

    async def ainvoke(self, args: dict[str, Any]) -> Any:
        return await self._fn(args)


async def _fake_search(args: dict[str, Any]) -> list[SearchResult]:
    query = args["query"]
    return [
        SearchResult(
            title=f"Result for {query} #{i}",
            url=f"https://example.com/{abs(hash(query)) % 1000}/{i}",
            snippet=f"snippet about {query} number {i}",
            score=1.0 - i * 0.1,
        )
        for i in range(3)
    ]


async def _fake_fetch(args: dict[str, Any]) -> FetchedDocument:
    return FetchedDocument(
        url=args["url"],
        title="Fetched page",
        text="Detailed extracted content used for synthesis.",
    )


@pytest.fixture
def _patch_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr("app.agent.nodes.get_llm", lambda **_: _FakeLLM())

    tools = {"web_search": _FakeTool(_fake_search), "web_fetch": _FakeTool(_fake_fetch)}
    monkeypatch.setattr("app.agent.nodes.get_tool", lambda name: tools[name])


@pytest.mark.usefixtures("_patch_agent")
async def test_full_research_run_loops_then_reports() -> None:
    state = await run_research("How cheap is renewable energy in 2025?", max_iterations=3)

    # The loop ran at least twice (initial plan + one reflect-driven follow-up).
    assert state["iteration"] >= 2
    assert state["enough"] is True

    # A cited report with a Sources section was produced.
    report = state["report"]
    assert "[1]" in report
    assert "## Sources" in report

    # Citations were verified and all point at real sources.
    assert state["unsupported_claims"] == []
    assert state["total_tokens"] > 0
    assert len(state["findings"]) >= 2


@pytest.mark.usefixtures("_patch_agent")
async def test_iteration_budget_is_respected() -> None:
    state = await run_research("A question", max_iterations=1)
    # With a budget of 1, reflect must hard-stop without looping.
    assert state["iteration"] == 1
    assert state["enough"] is True
