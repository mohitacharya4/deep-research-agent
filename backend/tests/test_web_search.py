"""Tests for the Tavily-backed web search tool (HTTP mocked with respx)."""

from __future__ import annotations

import importlib

import httpx
import pytest
import respx

from app.config import Settings, get_settings
from app.tools.web_search import TAVILY_ENDPOINT, web_search


@pytest.mark.asyncio
async def test_web_search_parses_and_filters_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()

    body = {
        "results": [
            {"title": "A", "url": "https://a.example", "content": "snippet a", "score": 0.9},
            {"title": "B", "url": "https://b.example", "content": "snippet b", "score": 0.5},
            {"title": "Dropped", "url": "", "content": "no url", "score": 0.1},
        ]
    }

    with respx.mock:
        route = respx.post(TAVILY_ENDPOINT).mock(return_value=httpx.Response(200, json=body))
        results = await web_search("some query", max_results=3)

    assert route.called
    # The result with an empty URL is filtered out.
    assert [r.url for r in results] == ["https://a.example", "https://b.example"]
    assert results[0].title == "A"
    assert results[0].snippet == "snippet a"
    assert results[0].score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_web_search_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force keyless settings that ignore any local .env, so the test is hermetic.
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    keyless = Settings(_env_file=None, tavily_api_key=None)  # type: ignore[call-arg]

    # Resolve the module explicitly: the app.tools package re-exports a web_search
    # function that shadows the submodule for attribute lookups.
    web_search_module = importlib.import_module("app.tools.web_search")
    monkeypatch.setattr(web_search_module, "get_settings", lambda: keyless)

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        await web_search("q")
