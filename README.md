# Deep Research Agent

An agentic research assistant that runs a **local LLM** (via [Ollama](https://ollama.com)) or a
cloud model, plans a research strategy, searches the web, reads and de-duplicates sources, reflects
on gaps in a loop, and produces a **cited** markdown report — streamed live to a React UI.

> Think "local, hackable Perplexity" — built to showcase agent-loop engineering, not just an LLM call.

## Why this project

Most LLM demos are a single prompt behind a text box. This one is deliberately built to show the
*engineering around* an agent:

- **Explicit agent loop** — a [LangGraph](https://langchain-ai.github.io/langgraph/) state machine
  (`plan → search → fetch → reflect ↺ → synthesize → critic`) you can read and reason about, with a
  hard iteration guard so it can't run away.
- **Provider-agnostic LLM layer** — defaults to a local Ollama model; swap to a cloud model
  (Anthropic) with a single env var.
- **Pluggable tool registry** — web search (Tavily) and content extraction are ordinary tools with
  JSON schemas, easy to extend.
- **Observability** — every node emits a structured event with token accounting, streamed over SSE.
- **Evaluations** — an eval harness scores report quality (LLM judge) and citation coverage, because
  evaluating agents is the hard part.

## Status

🚧 Under active construction — see the commit history for the build story.

## Quickstart

_Coming soon (backend + frontend wiring in progress)._

## License

MIT — see [LICENSE](./LICENSE).
