"""Agent tools: web search and page fetch, exposed via a small registry."""

from app.tools.registry import all_tools, get_tool, register
from app.tools.schemas import FetchedDocument, SearchResult
from app.tools.web_fetch import web_fetch
from app.tools.web_search import web_search

__all__ = [
    "all_tools",
    "get_tool",
    "register",
    "web_search",
    "web_fetch",
    "SearchResult",
    "FetchedDocument",
]
