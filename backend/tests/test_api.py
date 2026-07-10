"""Tests for the FastAPI SSE endpoints (agent faked out)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tools.schemas import FetchedDocument, SearchResult


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.usage_metadata = {"total_tokens": 4}


class _FakeLLM:
    async def ainvoke(self, messages: list[Any]) -> _FakeMessage:
        system = str(messages[0].content)
        if "research planner" in system:
            return _FakeMessage('["only query"]')
        if "research supervisor" in system:
            return _FakeMessage('{"enough": true, "gaps": "none", "new_queries": []}')
        if "research writer" in system:
            return _FakeMessage("The answer is well supported [1].")
        return _FakeMessage("{}")


class _FakeTool:
    def __init__(self, fn: Any) -> None:
        self._fn = fn

    async def ainvoke(self, args: dict[str, Any]) -> Any:
        return await self._fn(args)


async def _fake_search(args: dict[str, Any]) -> list[SearchResult]:
    return [SearchResult(title="A source", url="https://example.com/a", snippet="s", score=0.9)]


async def _fake_fetch(args: dict[str, Any]) -> FetchedDocument:
    return FetchedDocument(url=args["url"], title="A source", text="extracted body text")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setenv("PERSIST_TRACES", "false")  # don't write trace files during tests
    monkeypatch.setattr("app.agent.nodes.get_llm", lambda **_: _FakeLLM())
    tools = {"web_search": _FakeTool(_fake_search), "web_fetch": _FakeTool(_fake_fetch)}
    monkeypatch.setattr("app.agent.nodes.get_tool", lambda name: tools[name])
    return TestClient(app)


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_research_stream_emits_steps_and_report(client: TestClient) -> None:
    resp = client.get("/research", params={"question": "Is the sky blue?", "max_iterations": 1})
    assert resp.status_code == 200
    body = resp.text

    # The stream contains step events, a final report event, and a terminal marker.
    assert "event: step" in body
    assert "event: report" in body
    assert "event: done" in body
    # The report event carries the synthesized answer and a source.
    assert "well supported" in body
    assert "https://example.com/a" in body
