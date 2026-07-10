"""Command-line entry point: run a research query and stream progress to the terminal.

    uv run research "What are the tradeoffs of RAG vs fine-tuning in 2025?"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any, Literal, cast

from app.agent.graph import build_graph
from app.agent.state import ResearchState
from app.config import get_settings

_PHASE_ICON = {"start": "▶", "progress": "·", "complete": "✓"}
_STREAM_MODES: list[Literal["custom", "values"]] = ["custom", "values"]


def _force_utf8_output() -> None:
    """Emit UTF-8 regardless of the console code page (Windows defaults to cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


async def _run(question: str, max_iterations: int | None) -> dict[str, Any]:
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
            icon = _PHASE_ICON.get(str(event.get("phase")), "·")
            node = str(event.get("node", "")).ljust(10)
            tokens = event.get("tokens")
            suffix = f"  ({tokens} tok)" if tokens else ""
            print(f"  {icon} {node} {event.get('message', '')}{suffix}")
        elif mode == "values":
            final_state = cast(dict[str, Any], payload)
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
    args = parser.parse_args()
    question = " ".join(args.question)

    print(f"\n🔎 Researching: {question}\n")
    state = asyncio.run(_run(question, args.max_iterations))

    print("\n" + "=" * 70)
    print(state.get("report", "(no report produced)"))
    print("=" * 70)

    problems = state.get("unsupported_claims") or []
    if problems:
        print("\n⚠ Citation issues:")
        for p in problems:
            print(f"  - {p}")
    n_sources = len(state.get("findings", []))
    print(f"\nTotal tokens: {state.get('total_tokens', 0)} | Sources: {n_sources}\n")


if __name__ == "__main__":
    main()
