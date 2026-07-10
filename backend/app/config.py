"""Typed application configuration loaded from environment / .env.

All runtime knobs live here so the rest of the app depends on a single, validated
`Settings` object rather than reading ``os.environ`` ad hoc.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["ollama", "anthropic"]


class Settings(BaseSettings):
    """Validated settings sourced from environment variables and a local ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- LLM provider ----
    llm_provider: LLMProvider = "ollama"
    llm_temperature: float = 0.0

    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_base_url: str = "http://localhost:11434"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # Optional dedicated judge model for evals; falls back to the main LLM when unset.
    judge_provider: LLMProvider | None = None
    judge_model: str | None = None

    # ---- Tools ----
    tavily_api_key: str | None = None

    # ---- Agent behaviour ----
    max_iterations: int = Field(default=3, ge=1, le=8)
    search_results_per_query: int = Field(default=5, ge=1, le=20)
    fetch_top_n: int = Field(default=3, ge=0, le=10)

    # ---- Server ----
    cors_origins: str = "http://localhost:5173"

    @field_validator(
        "anthropic_api_key",
        "judge_provider",
        "judge_model",
        "tavily_api_key",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        """Treat empty/whitespace env values (e.g. ``JUDGE_PROVIDER=``) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list (comma-separated in the env var)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached, process-wide `Settings` instance."""
    return Settings()
