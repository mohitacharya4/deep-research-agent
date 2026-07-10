"""FastAPI application exposing the research agent over an SSE stream.

`GET /research?question=...` streams the agent's progress as Server-Sent Events:

    event: step    -> a StepEvent (node progress, token usage)
    event: report  -> the final report + sources once the run completes
    event: error   -> an error message if the run failed
    event: done    -> terminal marker

A GET endpoint is used deliberately so the browser's native ``EventSource`` can consume it.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Literal, cast

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app import __version__
from app.agent.graph import build_graph
from app.agent.state import Finding, ResearchState
from app.config import get_settings
from app.telemetry import configure_logging

_STREAM_MODES: list[Literal["custom", "values"]] = ["custom", "values"]

configure_logging()
app = FastAPI(title="Deep Research Agent", version=__version__)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness probe with the active LLM configuration."""
    return {
        "status": "ok",
        "version": __version__,
        "provider": settings.llm_provider,
        "model": (
            settings.ollama_model
            if settings.llm_provider == "ollama"
            else settings.anthropic_model
        ),
    }


def _report_payload(state: ResearchState) -> dict[str, Any]:
    """Shape the final state into the report event body."""
    findings: list[Finding] = state.get("findings", [])
    sources = [{"index": i, "title": f.title, "url": f.url} for i, f in enumerate(findings, 1)]
    return {
        "question": state.get("question", ""),
        "report": state.get("report", ""),
        "sources": sources,
        "unsupported_claims": state.get("unsupported_claims", []),
        "total_tokens": state.get("total_tokens", 0),
        "iterations": state.get("iteration", 0),
    }


async def _research_events(
    question: str, max_iterations: int, request: Request
) -> AsyncIterator[dict[str, str]]:
    """Yield SSE events as the research graph runs."""
    graph = build_graph()
    initial: ResearchState = {"question": question, "max_iterations": max_iterations}
    final_state: ResearchState = {}

    try:
        async for mode, payload in graph.astream(initial, stream_mode=_STREAM_MODES):
            if await request.is_disconnected():
                return
            if mode == "custom":
                yield {"event": "step", "data": json.dumps(payload)}
            elif mode == "values":
                final_state = cast(ResearchState, payload)
        yield {"event": "report", "data": json.dumps(_report_payload(final_state))}
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        yield {"event": "error", "data": json.dumps({"message": str(exc)})}
    finally:
        yield {"event": "done", "data": "{}"}


@app.get("/research")
async def research(
    request: Request,
    question: str = Query(..., min_length=3, description="The research question"),
    max_iterations: int | None = Query(default=None, ge=1, le=8),
) -> EventSourceResponse:
    """Stream a research run for ``question`` as Server-Sent Events."""
    budget = max_iterations or settings.max_iterations
    return EventSourceResponse(_research_events(question, budget, request))
