"""The research nodes.

Each function is a node in the LangGraph state machine. Nodes are deterministic
orchestrators: they call tools and the LLM, emit a :class:`StepEvent`, and return a
partial state update. Keeping orchestration in code (rather than letting a small local
model free-run tool calls) makes the loop reliable and easy to reason about.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent import prompts
from app.agent.state import Candidate, Finding, ResearchState
from app.config import get_settings
from app.llm import get_llm
from app.telemetry import StepEvent, emit
from app.tools import get_tool
from app.tools.schemas import FetchedDocument, SearchResult

# --------------------------------------------------------------------------- helpers


def _tokens(message: Any) -> int:
    """Extract total token usage from an LLM response, if the provider reports it."""
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        return int(usage.get("total_tokens") or 0)
    return 0


async def _llm_call(llm: BaseChatModel, system: str, user: str) -> tuple[str, int]:
    """Invoke the chat model with a system+user turn; return (text, tokens)."""
    message = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
    text = message.content if isinstance(message.content, str) else str(message.content)
    return text.strip(), _tokens(message)


def _parse_json(text: str) -> Any:
    """Leniently parse a JSON value from an LLM response (tolerates fences/prose)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
    return None


# --------------------------------------------------------------------------- nodes


async def plan_node(state: ResearchState) -> ResearchState:
    """Decompose the question into a handful of focused search queries."""
    question = state["question"]
    emit(StepEvent(node="plan", phase="start", message="Planning search strategy"))

    llm = get_llm()
    text, tokens = await _llm_call(
        llm,
        prompts.PLANNER_SYSTEM,
        prompts.PLANNER_USER.format(question=question),
    )
    parsed = _parse_json(text)
    queries = [str(q).strip() for q in parsed if str(q).strip()] if isinstance(parsed, list) else []
    if not queries:
        # Fall back to the raw question so the run can still proceed.
        queries = [question]

    emit(
        StepEvent(
            node="plan",
            phase="complete",
            message=f"Planned {len(queries)} queries",
            data={"queries": queries},
            tokens=tokens,
        )
    )
    return {
        "plan": queries,
        "pending_queries": queries,
        "iteration": 1,
        "seen_urls": [],
        "findings": [],
        "total_tokens": tokens,
    }


async def search_node(state: ResearchState) -> ResearchState:
    """Run each pending query through the web-search tool and de-duplicate hits."""
    settings = get_settings()
    queries = state.get("pending_queries") or state.get("plan") or [state["question"]]
    emit(
        StepEvent(
            node="search",
            phase="start",
            message=f"Searching the web ({len(queries)} queries)",
            data={"queries": queries},
        )
    )

    search_tool = get_tool("web_search")
    batches: list[list[SearchResult]] = await asyncio.gather(
        *(
            search_tool.ainvoke(
                {"query": q, "max_results": settings.search_results_per_query}
            )
            for q in queries
        )
    )

    seen = set(state.get("seen_urls", []))
    candidates: list[Candidate] = []
    for query, results in zip(queries, batches, strict=True):
        for result in results:
            if result.url in seen:
                continue
            seen.add(result.url)
            candidates.append(Candidate(sub_question=query, result=result))

    emit(
        StepEvent(
            node="search",
            phase="complete",
            message=f"Found {len(candidates)} new sources",
            data={"count": len(candidates)},
        )
    )
    return {"candidates": candidates, "seen_urls": sorted(seen)}


async def fetch_node(state: ResearchState) -> ResearchState:
    """Read the highest-scoring new candidates and record them as findings."""
    settings = get_settings()
    candidates = state.get("candidates", [])
    top = sorted(candidates, key=lambda c: c.result.score, reverse=True)[: settings.fetch_top_n]
    emit(
        StepEvent(
            node="fetch",
            phase="start",
            message=f"Reading {len(top)} sources",
            data={"urls": [c.result.url for c in top]},
        )
    )

    fetch_tool = get_tool("web_fetch")
    docs: list[FetchedDocument] = await asyncio.gather(
        *(fetch_tool.ainvoke({"url": c.result.url}) for c in top)
    )

    findings = list(state.get("findings", []))
    for candidate, doc in zip(top, docs, strict=True):
        # If extraction failed, fall back to the search snippet so the source still counts.
        content = doc.text if doc.ok else candidate.result.snippet
        findings.append(
            Finding(
                sub_question=candidate.sub_question,
                title=doc.title or candidate.result.title,
                url=candidate.result.url,
                snippet=candidate.result.snippet,
                content=content,
            )
        )

    emit(
        StepEvent(
            node="fetch",
            phase="complete",
            message=f"Extracted content from {len(top)} sources",
            data={"total_findings": len(findings)},
        )
    )
    return {"findings": findings}


async def reflect_node(state: ResearchState) -> ResearchState:
    """Decide whether the evidence is sufficient, or emit follow-up queries (the loop)."""
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", get_settings().max_iterations)
    findings = state.get("findings", [])

    # Hard stop: never exceed the iteration budget regardless of the model's opinion.
    if iteration >= max_iterations:
        emit(
            StepEvent(
                node="reflect",
                phase="complete",
                message="Reached iteration budget; proceeding to synthesis",
                data={"enough": True, "iteration": iteration},
            )
        )
        return {"enough": True, "gaps": "iteration budget reached"}

    emit(StepEvent(node="reflect", phase="start", message="Assessing coverage and gaps"))

    evidence = "\n".join(
        f"- ({f.sub_question}) {f.title}: {f.snippet[:200]}" for f in findings
    ) or "(no evidence yet)"
    asked = state.get("plan", [])

    llm = get_llm()
    text, tokens = await _llm_call(
        llm,
        prompts.REFLECT_SYSTEM,
        prompts.REFLECT_USER.format(
            question=state["question"],
            asked="\n".join(f"- {q}" for q in asked),
            n_findings=len(findings),
            evidence=evidence,
        ),
    )
    parsed = _parse_json(text)
    parsed = parsed if isinstance(parsed, dict) else {}
    enough = bool(parsed.get("enough", True))
    gaps = str(parsed.get("gaps", "")).strip()
    raw_new = parsed.get("new_queries", [])
    new_queries = [
        str(q).strip()
        for q in (raw_new if isinstance(raw_new, list) else [])
        if str(q).strip() and str(q).strip() not in asked
    ]

    # If the model wants more but offered no usable new query, treat as done.
    if not enough and not new_queries:
        enough = True

    total_tokens = state.get("total_tokens", 0) + tokens
    if enough:
        emit(
            StepEvent(
                node="reflect",
                phase="complete",
                message="Coverage sufficient; proceeding to synthesis",
                data={"enough": True, "gaps": gaps},
                tokens=tokens,
            )
        )
        return {"enough": True, "gaps": gaps, "total_tokens": total_tokens}

    emit(
        StepEvent(
            node="reflect",
            phase="complete",
            message=f"Gaps remain; running {len(new_queries)} follow-up queries",
            data={"enough": False, "gaps": gaps, "new_queries": new_queries},
            tokens=tokens,
        )
    )
    return {
        "enough": False,
        "gaps": gaps,
        "plan": asked + new_queries,
        "pending_queries": new_queries,
        "iteration": iteration + 1,
        "total_tokens": total_tokens,
    }


async def synthesize_node(state: ResearchState) -> ResearchState:
    """Write the final cited report from the gathered findings."""
    findings = state.get("findings", [])
    emit(
        StepEvent(
            node="synthesize",
            phase="start",
            message=f"Writing report from {len(findings)} sources",
        )
    )

    sources_block = "\n\n".join(
        f"[{i}] {f.title} — {f.url}\n{f.content[:1500]}"
        for i, f in enumerate(findings, start=1)
    ) or "(no sources gathered)"

    llm = get_llm()
    body, tokens = await _llm_call(
        llm,
        prompts.SYNTHESIZE_SYSTEM,
        prompts.SYNTHESIZE_USER.format(question=state["question"], sources=sources_block),
    )

    report = body + "\n\n" + _render_sources(findings)
    total_tokens = state.get("total_tokens", 0) + tokens
    emit(
        StepEvent(
            node="synthesize",
            phase="complete",
            message="Draft report ready",
            tokens=tokens,
        )
    )
    return {"report": report, "total_tokens": total_tokens}


async def critic_node(state: ResearchState) -> ResearchState:
    """Verify every citation in the report points at a real source."""
    report = state.get("report", "")
    findings = state.get("findings", [])
    n_sources = len(findings)

    cited = {int(n) for n in re.findall(r"\[(\d+)\]", report)}
    out_of_range = sorted(n for n in cited if n < 1 or n > n_sources)

    problems: list[str] = []
    if not cited and n_sources:
        problems.append("Report contains no citations.")
    for n in out_of_range:
        problems.append(f"Citation [{n}] does not match any source (have 1..{n_sources}).")

    emit(
        StepEvent(
            node="critic",
            phase="complete",
            message=(
                "Citations verified"
                if not problems
                else f"Found {len(problems)} citation issue(s)"
            ),
            data={"cited": sorted(cited), "problems": problems},
        )
    )
    return {"unsupported_claims": problems}


def _render_sources(findings: list[Finding]) -> str:
    """Render a deterministic, numbered Sources section matching citation indices."""
    if not findings:
        return "## Sources\n\n_No sources were gathered._"
    lines = ["## Sources", ""]
    for i, f in enumerate(findings, start=1):
        title = f.title or f.url
        lines.append(f"{i}. [{title}]({f.url})")
    return "\n".join(lines)
