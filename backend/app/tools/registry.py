"""A small tool registry.

Each capability (web search, page fetch) is registered once as a LangChain
``StructuredTool`` with a JSON schema. That makes tools:

* callable directly from graph nodes (``await get_tool("web_search").ainvoke(...)``), and
* bindable to a chat model (``llm.bind_tools(all_tools())``) for LLM-driven tool calling.

Keeping them in one registry means adding a new tool is a single ``register()`` call.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from app.tools.web_fetch import web_fetch
from app.tools.web_search import web_search

_REGISTRY: dict[str, StructuredTool] = {}


def register(tool: StructuredTool) -> StructuredTool:
    """Add a tool to the registry (idempotent by name)."""
    _REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> StructuredTool:
    """Look up a registered tool by name."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"No tool named {name!r}. Registered: {sorted(_REGISTRY)}") from exc


def all_tools() -> list[StructuredTool]:
    """Return every registered tool (order-stable)."""
    return list(_REGISTRY.values())


register(
    StructuredTool.from_function(
        coroutine=web_search,
        name="web_search",
        description=(
            "Search the web for a query and return a ranked list of results "
            "(title, url, snippet). Use for discovering sources."
        ),
    )
)

register(
    StructuredTool.from_function(
        coroutine=web_fetch,
        name="web_fetch",
        description=(
            "Fetch a single URL and return its cleaned main-body text. "
            "Use to read a source discovered via web_search."
        ),
    )
)
