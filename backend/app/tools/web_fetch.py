"""Web page fetch + main-content extraction tool.

Downloads a URL with ``httpx`` and extracts the readable article text with
``trafilatura`` (stripping nav, ads, boilerplate). Failures are captured on the
returned document rather than raised, so one bad URL never aborts a research run.
"""

from __future__ import annotations

import asyncio

import httpx
import trafilatura

from app.tools.schemas import FetchedDocument

_TIMEOUT = httpx.Timeout(20.0)
_MAX_CHARS = 12_000
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DeepResearchAgent/0.1; +https://github.com/)"
    )
}


async def web_fetch(url: str, max_chars: int = _MAX_CHARS) -> FetchedDocument:
    """Fetch ``url`` and return its cleaned main-body text.

    Never raises for network/parse problems — the failure is recorded on
    :attr:`FetchedDocument.error` so callers can skip and continue.
    """
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except httpx.HTTPError as exc:
        return FetchedDocument(url=url, error=f"fetch failed: {exc}")

    # trafilatura is CPU-bound and synchronous; keep the event loop responsive.
    extracted = await asyncio.to_thread(_extract, html)
    if extracted is None:
        return FetchedDocument(url=url, error="no extractable content")

    title, text = extracted
    return FetchedDocument(url=url, title=title, text=text[:max_chars])


def _extract(html: str) -> tuple[str, str] | None:
    """Run trafilatura extraction; return (title, text) or None."""
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    if not text:
        return None

    title = ""
    metadata = trafilatura.extract_metadata(html)
    if metadata is not None and metadata.title:
        title = metadata.title
    return title, text
