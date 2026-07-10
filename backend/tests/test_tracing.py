"""Tests for run tracing and LangSmith configuration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent.state import Finding
from app.config import Settings
from app.telemetry import RunTracer, configure_langsmith


def test_run_tracer_writes_run_step_and_result(tmp_path: Path) -> None:
    tracer = RunTracer(
        "How cheap is solar?", trace_dir=str(tmp_path), provider="ollama", model="qwen2.5:7b"
    )
    tracer.record_step({"node": "plan", "phase": "complete", "message": "planned"})
    state = {
        "report": "Solar is cheap [1].",
        "iteration": 2,
        "total_tokens": 123,
        "unsupported_claims": [],
        "findings": [Finding(sub_question="q", title="T", url="https://x.test", snippet="s")],
    }
    summary = tracer.finish(state)

    records = [json.loads(line) for line in tracer.path.read_text(encoding="utf-8").splitlines()]
    types = [r["type"] for r in records]
    assert types == ["run", "step", "result"]

    assert records[0]["question"] == "How cheap is solar?"
    assert records[0]["model"] == "qwen2.5:7b"
    assert records[1]["node"] == "plan"

    result = records[2]
    assert result["report"] == "Solar is cheap [1]."
    assert result["sources"] == [{"index": 1, "title": "T", "url": "https://x.test"}]
    assert summary["sources"] == 1
    assert summary["total_tokens"] == 123


def test_configure_langsmith_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    settings = Settings(_env_file=None, langsmith_tracing=False)  # type: ignore[call-arg]
    assert configure_langsmith(settings) is False
    assert "LANGCHAIN_TRACING_V2" not in __import__("os").environ


def test_configure_langsmith_sets_env_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT"):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        langsmith_tracing=True,
        langsmith_api_key="ls-test-key",
        langsmith_project="proj-x",
    )

    assert configure_langsmith(settings) is True
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "ls-test-key"
    assert os.environ["LANGCHAIN_PROJECT"] == "proj-x"
