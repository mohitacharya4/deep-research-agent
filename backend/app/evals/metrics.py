"""Pure, deterministic scoring functions for a research report.

These need no LLM and no network, so they are cheap to run in CI and easy to unit test.
The LLM-judge (subjective quality) lives in ``evals/run_evals.py`` and composes these.
"""

from __future__ import annotations

import re
from typing import Any

_CITATION_RE = re.compile(r"\[(\d+)\]")


def citation_stats(report: str, n_sources: int) -> dict[str, Any]:
    """Measure how well the report cites its available sources.

    Returns the set of cited indices, any that point outside ``1..n_sources``
    (hallucinated citations), and ``source_coverage`` — the fraction of available
    sources the report actually cites.
    """
    cited = sorted({int(n) for n in _CITATION_RE.findall(report)})
    valid = [n for n in cited if 1 <= n <= n_sources]
    invalid = [n for n in cited if n < 1 or n > n_sources]
    coverage = len(valid) / n_sources if n_sources else 0.0
    return {
        "n_sources": n_sources,
        "cited": cited,
        "invalid": invalid,
        "has_citations": bool(cited),
        "source_coverage": round(coverage, 3),
    }


def keyword_recall(report: str, must_include: list[str]) -> dict[str, Any]:
    """Fraction of expected keywords/phrases present in the report (case-insensitive)."""
    if not must_include:
        return {"recall": 1.0, "missing": []}
    lowered = report.lower()
    missing = [kw for kw in must_include if kw.lower() not in lowered]
    recall = 1.0 - len(missing) / len(must_include)
    return {"recall": round(recall, 3), "missing": missing}
