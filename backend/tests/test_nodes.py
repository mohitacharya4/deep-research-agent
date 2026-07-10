"""Tests for node helper functions."""

from __future__ import annotations

from app.agent.nodes import _parse_json, _strip_trailing_source_list


def test_strip_trailing_source_list_removes_model_reference_block() -> None:
    body = (
        "Solar costs fell sharply [1]. Wind is competitive [2].\n\n"
        "[1] Some Article — https://example.com/a\n"
        "[2] Another — https://example.com/b\n"
    )
    cleaned = _strip_trailing_source_list(body)
    assert cleaned == "Solar costs fell sharply [1]. Wind is competitive [2]."


def test_strip_trailing_source_list_keeps_inline_citations() -> None:
    body = "A claim [1] and another [2] with no trailing reference list."
    assert _strip_trailing_source_list(body) == body


def test_parse_json_handles_code_fences() -> None:
    assert _parse_json('```json\n["a", "b"]\n```') == ["a", "b"]


def test_parse_json_extracts_object_from_prose() -> None:
    text = 'Sure! Here is the result: {"enough": true, "gaps": "none"} — hope that helps.'
    assert _parse_json(text) == {"enough": True, "gaps": "none"}


def test_parse_json_returns_none_on_garbage() -> None:
    assert _parse_json("not json at all") is None
