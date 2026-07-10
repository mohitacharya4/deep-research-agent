"""Evaluate the research agent against ``dataset.jsonl``.

For every question it runs the full agent, then scores the report on:

* citation validity + source coverage (deterministic, see app.evals.metrics),
* keyword recall against expected terms, and
* an LLM-judge quality score (1-5) with a rubric.

Usage:
    uv run python evals/run_evals.py               # full dataset
    uv run python evals/run_evals.py --limit 2     # quick smoke run
    uv run python evals/run_evals.py --no-judge    # skip the LLM judge
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from statistics import mean
from typing import Any

from app.agent.graph import run_research
from app.agent.nodes import _llm_call, _parse_json
from app.config import get_settings
from app.evals.metrics import citation_stats, keyword_recall
from app.llm import get_llm
from app.telemetry import configure_logging

DATASET = Path(__file__).parent / "dataset.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"

JUDGE_SYSTEM = """You are a strict evaluator of research answers. Score the report from 1 to 5:
5 = accurate, well-structured, directly answers the question, claims are cited.
3 = partially answers; some gaps or weak citations.
1 = off-topic, unsupported, or empty.

Respond with ONLY JSON: {"score": <1-5>, "rationale": "<one sentence>"}"""

JUDGE_USER = """Question:
{question}

Report:
{report}"""


async def judge_report(question: str, report: str) -> tuple[int, str]:
    """Ask the (judge) model to rate a report 1-5."""
    settings = get_settings()
    llm = get_llm(
        provider=settings.judge_provider or settings.llm_provider,
        model=settings.judge_model,
    )
    text, _ = await _llm_call(
        llm, JUDGE_SYSTEM, JUDGE_USER.format(question=question, report=report[:6000])
    )
    parsed = _parse_json(text)
    if not isinstance(parsed, dict):
        return 0, "unparseable judge response"
    try:
        score = max(0, min(5, int(parsed.get("score", 0))))
    except (TypeError, ValueError):
        score = 0
    return score, str(parsed.get("rationale", "")).strip()


async def evaluate_one(item: dict[str, Any], use_judge: bool) -> dict[str, Any]:
    """Run and score a single dataset item."""
    question = item["question"]
    must_include = item.get("must_include", [])

    started = time.time()
    state = await run_research(question)
    report = state.get("report", "")
    n_sources = len(state.get("findings", []))

    cites = citation_stats(report, n_sources)
    recall = keyword_recall(report, must_include)
    score, rationale = await judge_report(question, report) if use_judge else (None, "")

    return {
        "question": question,
        "sources": n_sources,
        "iterations": state.get("iteration", 0),
        "tokens": state.get("total_tokens", 0),
        "source_coverage": cites["source_coverage"],
        "invalid_citations": cites["invalid"],
        "keyword_recall": recall["recall"],
        "missing_keywords": recall["missing"],
        "judge_score": score,
        "judge_rationale": rationale,
        "seconds": round(time.time() - started, 1),
    }


def _print_table(results: list[dict[str, Any]]) -> None:
    print("\n" + "=" * 88)
    print(f"{'#':>2}  {'cov':>5}  {'recall':>6}  {'judge':>5}  {'src':>3}  {'sec':>5}  question")
    print("-" * 88)
    for i, r in enumerate(results, 1):
        if "error" in r:
            print(f"{i:>2}  {'ERR':>5}  {'':>6}  {'':>5}  {'':>3}  {'':>5}  {r['question'][:48]}")
            continue
        judge = "-" if r["judge_score"] is None else f"{r['judge_score']}/5"
        print(
            f"{i:>2}  {r['source_coverage']:>5}  {r['keyword_recall']:>6}  {judge:>5}  "
            f"{r['sources']:>3}  {r['seconds']:>5}  {r['question'][:48]}"
        )
    print("=" * 88)


def _print_aggregates(results: list[dict[str, Any]]) -> None:
    ok = [r for r in results if "error" not in r]
    if not ok:
        print("No successful runs to aggregate.")
        return
    print("\nAggregates over", len(ok), "runs:")
    print(f"  mean source_coverage : {mean(r['source_coverage'] for r in ok):.3f}")
    print(f"  mean keyword_recall  : {mean(r['keyword_recall'] for r in ok):.3f}")
    judged = [r["judge_score"] for r in ok if r["judge_score"] is not None]
    if judged:
        print(f"  mean judge_score     : {mean(judged):.2f} / 5")
    invalid = sum(len(r["invalid_citations"]) for r in ok)
    print(f"  total invalid citations: {invalid}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the research agent")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N items")
    parser.add_argument("--no-judge", action="store_true", help="Skip the LLM judge")
    args = parser.parse_args()

    configure_logging(logging.WARNING)
    items = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    if args.limit:
        items = items[: args.limit]

    results: list[dict[str, Any]] = []
    for i, item in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {item['question'][:60]}…")
        try:
            results.append(await evaluate_one(item, use_judge=not args.no_judge))
        except Exception as exc:  # noqa: BLE001 - record and continue the sweep
            results.append({"question": item["question"], "error": str(exc)})
            print(f"    ! failed: {exc}")

    _print_table(results)
    _print_aggregates(results)

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"eval-{int(time.time())}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved detailed results to {out}")


if __name__ == "__main__":
    asyncio.run(main())
