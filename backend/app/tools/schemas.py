"""Pydantic models shared across tools and the agent graph."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single web search hit returned by the search tool."""

    title: str
    url: str
    snippet: str = Field(description="Short content preview provided by the search API")
    score: float = Field(default=0.0, description="Relevance score from the search API (0..1)")


class FetchedDocument(BaseModel):
    """The extracted main content of a web page (or an error explaining why not)."""

    url: str
    title: str = ""
    text: str = Field(default="", description="Cleaned main-body text, truncated")
    error: str | None = Field(default=None, description="Populated when extraction failed")

    @property
    def ok(self) -> bool:
        """True when the page was fetched and yielded usable text."""
        return self.error is None and bool(self.text)
