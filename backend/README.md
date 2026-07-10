# Backend — Deep Research Agent

Python 3.12 · FastAPI · LangGraph · Ollama / Anthropic · Tavily. Managed with [`uv`](https://docs.astral.sh/uv/).

## Setup

```bash
cd backend
uv sync                        # install deps into .venv
cp .env.example .env           # then fill in TAVILY_API_KEY
ollama pull qwen2.5:7b-instruct
```

## Run

```bash
uv run research "What are the tradeoffs of RAG vs fine-tuning in 2025?"   # CLI
uv run uvicorn app.main:app --reload                                     # API
```

## Dev

```bash
uv run ruff check .
uv run mypy app
uv run pytest
```
