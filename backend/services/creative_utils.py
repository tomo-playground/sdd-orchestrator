"""Creative Lab shared utilities — DRY extraction from pipeline/shorts modules."""

from __future__ import annotations

import json
import re

from config import logger
from models.creative import CreativeAgentPreset, CreativeTrace
from services.prompt.prompt import split_prompt_tokens


def parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM output (strip markdown fences, fix invalid escapes)."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        cleaned_fixed = _fix_json_escapes(cleaned)
        return json.loads(cleaned_fixed)


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


def parse_image_prompt_to_tags(prompt: str) -> list[str]:
    """Split image_prompt string into a Danbooru tag list.

    Delegates to split_prompt_tokens() (SSOT).
    """
    if not prompt:
        return []
    return split_prompt_tokens(prompt)


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


def record_handoff(db, session_id: int, target: str, content: str) -> CreativeTrace:
    """Record a handoff trace from director to target agent."""
    seq = get_next_sequence(db, session_id)
    return record_trace_sync(
        db,
        session_id=session_id,
        round_number=0,
        sequence=seq,
        trace_type="handoff",
        agent_role="creative_director",
        target_agent=target,
        input_prompt=content,
        output_content=content,
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        step_name=target,
    )


def record_feedback(
    db,
    session_id: int,
    target: str,
    issues: list[str],
    parent_trace_id: int | None = None,
) -> CreativeTrace:
    """Record a feedback trace from director to target agent."""
    feedback_text = "\n".join(f"- {issue}" for issue in issues)
    seq = get_next_sequence(db, session_id)
    return record_trace_sync(
        db,
        session_id=session_id,
        round_number=0,
        sequence=seq,
        trace_type="feedback",
        agent_role="creative_director",
        target_agent=target,
        input_prompt=f"Quality issues for {target}",
        output_content=feedback_text,
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        step_name=target,
        feedback=feedback_text,
        parent_trace_id=parent_trace_id,
    )


def record_quality_report(db, session_id: int, qc_result: dict, step_name: str) -> None:
    """Record a quality_report trace."""
    seq = get_next_sequence(db, session_id)
    record_trace_sync(
        db,
        session_id=session_id,
        round_number=0,
        sequence=seq,
        trace_type="quality_report",
        agent_role="creative_director",
        input_prompt=f"QC check for {step_name}",
        output_content=json.dumps(qc_result, ensure_ascii=False),
        model_id="system",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        latency_ms=0,
        temperature=0.0,
        phase="production",
        step_name=step_name,
    )


def calculate_total_tokens(db, session_id: int) -> dict:
    """Sum token usage across all traces in a session."""
    traces = db.query(CreativeTrace).filter(CreativeTrace.session_id == session_id).all()
    total_prompt = sum((t.token_usage or {}).get("prompt_tokens", 0) for t in traces)
    total_completion = sum((t.token_usage or {}).get("completion_tokens", 0) for t in traces)
    return {
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
    }
