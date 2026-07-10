"""Tests for the deterministic eval metrics."""

from __future__ import annotations

from app.evals.metrics import citation_stats, keyword_recall


def test_citation_stats_counts_valid_and_invalid() -> None:
    report = "Claim one [1]. Claim two [2]. Bogus [9]."
    stats = citation_stats(report, n_sources=3)

    assert stats["cited"] == [1, 2, 9]
    assert stats["invalid"] == [9]
    assert stats["has_citations"] is True
    # 2 of 3 available sources are validly cited.
    assert stats["source_coverage"] == round(2 / 3, 3)


def test_citation_stats_handles_no_sources() -> None:
    stats = citation_stats("No citations here.", n_sources=0)
    assert stats["has_citations"] is False
    assert stats["source_coverage"] == 0.0


def test_keyword_recall_full_and_partial() -> None:
    report = "Retrieval augmented generation lowers cost."
    assert keyword_recall(report, ["retrieval", "cost"])["recall"] == 1.0

    partial = keyword_recall(report, ["retrieval", "fine-tuning"])
    assert partial["recall"] == 0.5
    assert partial["missing"] == ["fine-tuning"]


def test_keyword_recall_empty_expectations() -> None:
    assert keyword_recall("anything", [])["recall"] == 1.0
