"""Logging configuration and run-level summaries.

Per-step observability is emitted by :mod:`app.telemetry.events`; this module handles
process-wide logging setup and condenses a finished run into a small metrics dict
(tokens, sources, iterations, citation issues) for logs and the eval harness.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

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
