"""Creative utilities — shared helpers for LangGraph agent nodes."""

from __future__ import annotations

import json
import re

from config import logger
from models.creative import CreativeAgentPreset, CreativeTrace


def _strip_preamble(text: str) -> str | None:
    """Strip preamble text before first '{' (Gemini sometimes adds 'Okay, ...' before JSON)."""
    brace_idx = text.find("{")
    return text[brace_idx:] if brace_idx >= 0 else None


def parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM output (strip markdown fences, preamble, fix escapes)."""
    if not raw:
        raise ValueError("Empty LLM response received")

    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())

    # Try each strategy: raw → stripped → escape-fixed(stripped) → escape-fixed(raw)
    candidates = [cleaned]
    stripped = _strip_preamble(cleaned)
    if stripped and stripped != cleaned:
        candidates.append(stripped)

    for text in candidates:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                return json.loads(_fix_json_escapes(text))
            except json.JSONDecodeError:
                continue

    # Final fallback — will raise if all strategies fail
    return json.loads(_fix_json_escapes(cleaned))


_VALID_JSON_ESCAPES = frozenset('"\\\\/bfnrt')
_HEX_CHARS = frozenset("0123456789abcdefABCDEF")


def _fix_json_escapes(text: str) -> str:
    """Fix invalid JSON backslash escapes from LLM output character-by-character."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        # Backslash found — check next char
        if i + 1 >= n:
            out.append("\\\\")
            i += 1
            continue
        nxt = text[i + 1]
        if nxt in _VALID_JSON_ESCAPES:
            out.append(text[i : i + 2])
            i += 2
        elif nxt == "u":
            # Valid unicode: \uXXXX (4 hex digits)
            if i + 5 < n and all(c in _HEX_CHARS for c in text[i + 2 : i + 6]):
                out.append(text[i : i + 6])
                i += 6
            else:
                out.append("\\\\")
                i += 1
        else:
            out.append("\\\\")
            i += 1
    return "".join(out)


def load_preset(db, agent_role: str) -> CreativeAgentPreset | None:
    """Load an agent preset by role key. Returns None if not found."""
    preset = (
        db.query(CreativeAgentPreset)
        .filter(
            CreativeAgentPreset.agent_role == agent_role,
            CreativeAgentPreset.deleted_at.is_(None),
        )
        .first()
    )
    if not preset:
        logger.warning("[Preset] No preset found for agent_role=%s, using fallback", agent_role)
    return preset


def get_next_sequence(db, session_id: int) -> int:
    """Get next sequence number for traces in a session."""
    last = (
        db.query(CreativeTrace.sequence)
        .filter(CreativeTrace.session_id == session_id)
        .order_by(CreativeTrace.sequence.desc())
        .first()
    )
    return (last[0] + 1) if last else 0


def record_trace_sync(db, **kwargs) -> CreativeTrace:
    """Create and flush a CreativeTrace synchronously (for background tasks)."""
    trace = CreativeTrace(**kwargs)
    db.add(trace)
    db.flush()
    return trace


def resolve_characters_from_context(ctx: dict) -> dict[str, dict]:
    """Extract per-speaker character info from context.

    Returns: {"A": {"id": 1, "name": "하루", "tags": [...]}, ...}
    Supports legacy single character_name as well.
    """
    characters = ctx.get("characters")
    if characters:
        return characters

    # Legacy fallback: single character_name → speaker "A"
    name = ctx.get("character_name")
    if name:
        return {"A": {"id": ctx.get("character_id"), "name": name, "tags": []}}

    return {}
