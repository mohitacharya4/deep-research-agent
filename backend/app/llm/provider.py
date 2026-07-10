"""Provider-agnostic chat-model factory.

The whole application talks to ``get_llm()`` and never imports a concrete provider.
Switching from a local Ollama model to a cloud model is a one-env-var change
(``LLM_PROVIDER``) — the returned object is always a LangChain ``BaseChatModel``, so
``.invoke()``, ``.bind_tools()`` and structured output behave identically downstream.
"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import LLMProvider, Settings, get_settings


def get_llm(
    *,
    provider: LLMProvider | None = None,
    model: str | None = None,
    temperature: float | None = None,
    settings: Settings | None = None,
) -> BaseChatModel:
    """Build a chat model for the configured (or explicitly requested) provider.

    Args:
        provider: Override the configured provider (used by the eval judge).
        model: Override the model name for the chosen provider.
        temperature: Override sampling temperature.
        settings: Injected settings (defaults to the cached process settings).

    Returns:
        A ready-to-use LangChain chat model.
    """
    settings = settings or get_settings()
    provider = provider or settings.llm_provider
    temperature = settings.llm_temperature if temperature is None else temperature

    if provider == "ollama":
        return _build_ollama(settings, model, temperature)
    if provider == "anthropic":
        return _build_anthropic(settings, model, temperature)

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def _build_ollama(settings: Settings, model: str | None, temperature: float) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model or settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )


def _build_anthropic(settings: Settings, model: str | None, temperature: float) -> BaseChatModel:
    if not settings.anthropic_api_key:
        raise ValueError(
            "LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY. "
            "Set it in .env or switch LLM_PROVIDER back to 'ollama'."
        )
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "The 'anthropic' extra is not installed. Run: uv sync --extra anthropic"
        ) from exc

    chat = ChatAnthropic(
        model_name=model or settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=temperature,
        timeout=60,
        stop=None,
    )
    return cast(BaseChatModel, chat)
