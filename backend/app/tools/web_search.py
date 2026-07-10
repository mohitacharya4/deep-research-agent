"""Web search tool backed by the Tavily API.

We call Tavily's REST endpoint directly with ``httpx`` rather than through a wrapper so
the HTTP boundary is explicit and trivially mockable in tests (see ``tests/test_web_search.py``).
"""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.tools.schemas import SearchResult

TAVILY_ENDPOINT = "https://api.tavily.com/search"
_TIMEOUT = httpx.Timeout(20.0)


async def web_search(query: str, max_results: int | None = None) -> list[SearchResult]:
    """Search the web for ``query`` and return the top results.

    Args:
        query: The search query.
        max_results: How many results to return (defaults to the configured value).

    Returns:
        A list of :class:`SearchResult`, best-scoring first.

    Raises:
        RuntimeError: If ``TAVILY_API_KEY`` is not configured.
    """
    settings = get_settings()
    if not settings.tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Add it to backend/.env "
            "(get a free key at https://app.tavily.com)."
        )

    limit = max_results or settings.search_results_per_query
    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": limit,
        "search_depth": "advanced",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(TAVILY_ENDPOINT, json=payload)
        response.raise_for_status()
        data = response.json()

    return _parse_results(data)


def _parse_results(data: dict[str, object]) -> list[SearchResult]:
    """Convert a raw Tavily response body into typed results."""
    raw_results = data.get("results")
    if not isinstance(raw_results, list):
        return []

    results: list[SearchResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        results.append(
            SearchResult(
                title=str(item.get("title") or "Untitled"),
                url=str(item.get("url") or ""),
                snippet=str(item.get("content") or ""),
                score=float(item.get("score") or 0.0),
            )
        )
    return [r for r in results if r.url]
