"""Tests for the web fetch + extraction tool (HTTP mocked with respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from app.tools.web_fetch import web_fetch

_ARTICLE_HTML = """
<html>
  <head><title>Understanding RAG</title></head>
  <body>
    <nav>Home About Contact</nav>
    <article>
      <h1>Understanding Retrieval-Augmented Generation</h1>
      <p>Retrieval-augmented generation combines a language model with an external
      knowledge store so that answers can cite up-to-date sources instead of relying
      only on parameters frozen at training time.</p>
      <p>In practice a retriever finds relevant passages, and the generator conditions
      its output on those passages. This reduces hallucination and makes the system
      easier to keep current, because updating the corpus does not require retraining.</p>
    </article>
    <footer>Copyright 2026</footer>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_web_fetch_extracts_main_content() -> None:
    url = "https://example.com/rag"
    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, text=_ARTICLE_HTML))
        doc = await web_fetch(url)

    assert doc.ok
    assert "retrieval-augmented generation" in doc.text.lower()
    # Boilerplate should be stripped out by trafilatura.
    assert "Copyright 2026" not in doc.text


@pytest.mark.asyncio
async def test_web_fetch_records_http_error_without_raising() -> None:
    url = "https://example.com/missing"
    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(404))
        doc = await web_fetch(url)

    assert not doc.ok
    assert doc.error is not None


@pytest.mark.asyncio
async def test_web_fetch_truncates_to_max_chars() -> None:
    url = "https://example.com/rag"
    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, text=_ARTICLE_HTML))
        doc = await web_fetch(url, max_chars=50)

    assert len(doc.text) <= 50
