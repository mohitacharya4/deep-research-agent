"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Ensure each test sees fresh settings (the process cache is cleared around it)."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
