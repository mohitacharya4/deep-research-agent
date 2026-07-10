"""Tests for settings loading and env coercion."""

from __future__ import annotations

import pytest

from app.config import Settings


def test_blank_optional_env_values_become_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mirrors .env.example shipping empty JUDGE_PROVIDER= / JUDGE_MODEL= lines.
    monkeypatch.setenv("JUDGE_PROVIDER", "")
    monkeypatch.setenv("JUDGE_MODEL", "  ")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.judge_provider is None
    assert settings.judge_model is None
    assert settings.anthropic_api_key is None


def test_populated_optional_values_are_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_PROVIDER", "anthropic")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-abc123")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.judge_provider == "anthropic"
    assert settings.tavily_api_key == "tvly-abc123"


def test_cors_origin_list_splits_and_trims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test ,")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]
