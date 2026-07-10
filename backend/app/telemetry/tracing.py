"""Logging configuration and run-level summaries.

Per-step observability is emitted by :mod:`app.telemetry.events`; this module handles
process-wide logging setup and condenses a finished run into a small metrics dict
(tokens, sources, iterations, citation issues) for logs and the eval harness.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings

logger = logging.getLogger("deep_research.tracing")

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a single stderr handler to the ``deep_research`` logger tree (idempotent)."""
    global _CONFIGURED
    logger = logging.getLogger("deep_research")
    logger.setLevel(level)
    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)
        logger.propagate = False
        _CONFIGURED = True


def summarize_run(state: dict[str, Any]) -> dict[str, Any]:
    """Condense a finished run's state into a metrics dict."""
    findings = state.get("findings", [])
    return {
        "iterations": state.get("iteration", 0),
        "sources": len(findings),
        "total_tokens": state.get("total_tokens", 0),
        "citation_issues": len(state.get("unsupported_claims", []) or []),
    }


def configure_langsmith(settings: Settings) -> bool:
    """Enable LangSmith tracing from typed settings, if requested.

    pydantic-settings reads ``.env`` but does not export to ``os.environ``; LangChain
    reads ``os.environ``. This bridges the two so LangSmith config in ``.env`` actually
    takes effect. No-op (returns False) unless tracing is on and an API key is present.
    """
    if not (settings.langsmith_tracing and settings.langsmith_api_key):
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
    logger.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)
    return True


def _slug(text: str, max_len: int = 40) -> str:
    """Filesystem-safe slug from free text."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:max_len].strip("-") or "run"


class RunTracer:
    """Persists a single research run's events to a JSONL file.

    One file per run under ``trace_dir``; each line is a record: a ``run`` header,
    a ``step`` per emitted event, and a final ``result`` with the report and metrics.
    Written incrementally so a crash still leaves a partial, inspectable trace.
    """

    def __init__(
        self, question: str, *, trace_dir: str = "runs", provider: str = "", model: str = ""
    ) -> None:
        self._started = time.time()
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        directory = Path(trace_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{stamp}-{_slug(question)}.jsonl"
        self.run_id = self.path.stem
        self._write(
            {
                "type": "run",
                "run_id": self.run_id,
                "question": question,
                "provider": provider,
                "model": model,
                "started_at": stamp,
            }
        )

    def _write(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def record_step(self, event: dict[str, Any]) -> None:
        """Append one emitted StepEvent to the trace."""
        self._write({"type": "step", **event})

    def finish(self, state: dict[str, Any]) -> dict[str, Any]:
        """Append the final result record and return the run summary."""
        findings = state.get("findings", [])
        summary = summarize_run(state)
        self._write(
            {
                "type": "result",
                # summary first so the explicit keys below win any name clash
                # (summary's "sources" is a count; here we want the full list).
                **summary,
                "report": state.get("report", ""),
                "sources": [
                    {"index": i, "title": f.title, "url": f.url}
                    for i, f in enumerate(findings, start=1)
                ],
                "duration_s": round(time.time() - self._started, 1),
            }
        )
        return summary
