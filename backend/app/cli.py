"""Command-line entry point: run a research query and stream progress to the terminal.

    uv run research "What are the tradeoffs of RAG vs fine-tuning in 2025?"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any, Literal, cast

from app.agent.graph import build_graph
from app.agent.state import ResearchState
from app.config import get_settings
from app.telemetry import RunTracer, configure_langsmith, configure_logging

_PHASE_ICON = {"start": "▶", "progress": "·", "complete": "✓"}
_STREAM_MODES: list[Literal["custom", "values"]] = ["custom", "values"]


def _force_utf8_output() -> None:
    """Emit UTF-8 regardless of the console code page (Windows defaults to cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


async def _run(
    question: str, max_iterations: int | None, tracer: RunTracer | None
) -> dict[str, Any]:
    settings = get_settings()
    graph = build_graph()
    initial: ResearchState = {
        "question": question,
        "max_iterations": max_iterations or settings.max_iterations,
    }

    final_state: dict[str, Any] = {}
    async for mode, payload in graph.astream(initial, stream_mode=_STREAM_MODES):
        if mode == "custom":
            event = cast(dict[str, Any], payload)
            if tracer is not None:
                tracer.record_step(event)
            icon = _PHASE_ICON.get(str(event.get("phase")), "·")
            node = str(event.get("node", "")).ljust(10)
            tokens = event.get("tokens")
            suffix = f"  ({tokens} tok)" if tokens else ""
            print(f"  {icon} {node} {event.get('message', '')}{suffix}")
        elif mode == "values":
            final_state = cast(dict[str, Any], payload)

    if tracer is not None:
        tracer.finish(final_state)
    return final_state


def main() -> None:
    """Parse arguments and run the research agent."""
    _force_utf8_output()
    parser = argparse.ArgumentParser(description="Deep Research Agent (CLI)")
    parser.add_argument("question", nargs="+", help="The research question")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Override the reflection loop budget",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show INFO-level telemetry logs"
    )
    args = parser.parse_args()
    question = " ".join(args.question)

    settings = get_settings()
    configure_logging(logging.INFO if args.verbose else logging.WARNING)
    if configure_langsmith(settings):
        print(f"LangSmith tracing: on (project={settings.langsmith_project})")

    model = (
        settings.ollama_model
        if settings.llm_provider == "ollama"
        else settings.anthropic_model
    )
    tracer = (
        RunTracer(
            question,
            trace_dir=settings.trace_dir,
            provider=settings.llm_provider,
            model=model,
        )
        if settings.persist_traces
        else None
    )

    print(f"\n🔎 Researching: {question}\n")
    state = asyncio.run(_run(question, args.max_iterations, tracer))

    print("\n" + "=" * 70)
    print(state.get("report", "(no report produced)"))
    print("=" * 70)

    problems = state.get("unsupported_claims") or []
    if problems:
        print("\n⚠ Citation issues:")
        for p in problems:
            print(f"  - {p}")
    n_sources = len(state.get("findings", []))
    print(f"\nTotal tokens: {state.get('total_tokens', 0)} | Sources: {n_sources}")
    if tracer is not None:
        print(f"Trace saved to: {tracer.path}")
    print()


if __name__ == "__main__":
    main()
