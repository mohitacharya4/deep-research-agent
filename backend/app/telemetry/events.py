"""Structured step events emitted by agent nodes.

Every node reports its progress as a :class:`StepEvent`. Inside a running graph the
event is pushed to LangGraph's custom stream writer (so the API can forward it over
SSE) *and* logged. Outside a graph run the writer is absent and we just log, which
keeps nodes unit-testable without a live stream.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger("deep_research.telemetry")

Phase = Literal["start", "progress", "complete"]


class StepEvent(BaseModel):
    """A single observable moment in a research run."""

    node: str = Field(description="Name of the emitting node, e.g. 'search'")
    phase: Phase = "progress"
    message: str = Field(description="Human-readable status line")
    data: dict[str, Any] = Field(default_factory=dict)
    tokens: int | None = Field(default=None, description="LLM tokens used by this step, if any")
    ts: float = Field(default_factory=time.time)


def emit(event: StepEvent) -> None:
    """Send an event to the active stream (if any) and the logger.

    Safe to call from anywhere: when no LangGraph stream is active,
    :func:`get_stream_writer` raises and we fall back to logging only.
    """
    logger.info("[%s/%s] %s", event.node, event.phase, event.message)
    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
    except Exception:  # noqa: BLE001 - no active stream; logging is enough
        return
    if writer is not None:
        writer(event.model_dump())
