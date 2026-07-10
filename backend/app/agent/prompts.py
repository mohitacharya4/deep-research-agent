"""Prompt templates for the research nodes.

Kept in one module so prompts are versioned and reviewable in isolation. Each prompt
asks for a small, strict JSON shape; nodes parse it leniently (see ``nodes._parse_json``)
so that even smaller local models stay usable.
"""

from __future__ import annotations

PLANNER_SYSTEM = """You are a meticulous research planner.
Break the user's question into 3 to 5 focused, self-contained search queries that
together cover the question. Prefer specific, keyword-rich queries over broad ones.

Respond with ONLY a JSON array of strings, e.g.:
["first query", "second query", "third query"]"""

PLANNER_USER = """Research question:
{question}"""


REFLECT_SYSTEM = """You are a critical research supervisor deciding whether the evidence
gathered so far is sufficient to answer the question well.

Consider coverage, recency, and whether important sub-topics are missing.
If gaps remain, propose 1 to 3 NEW search queries targeting only what is still missing
(do not repeat queries already asked).

Respond with ONLY a JSON object of this exact shape:
{{"enough": true|false, "gaps": "one sentence on what is missing (or 'none')",
  "new_queries": ["...", "..."]}}"""

REFLECT_USER = """Question:
{question}

Queries already asked:
{asked}

Evidence gathered so far ({n_findings} sources):
{evidence}"""


SYNTHESIZE_SYSTEM = """You are an expert research writer. Write a clear, well-structured
answer to the question using ONLY the numbered sources provided.

Rules:
- Cite every non-obvious claim with a bracketed source number like [1] or [2][3].
- Only cite numbers that exist in the sources list.
- Use Markdown with short sections and, where useful, bullet points.
- Be objective; note disagreements between sources.
- Do NOT invent a sources list — it is appended automatically."""

SYNTHESIZE_USER = """Question:
{question}

Numbered sources:
{sources}

Write the report now."""
