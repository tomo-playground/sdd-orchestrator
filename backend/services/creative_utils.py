"""Creative Lab shared utilities — DRY extraction from pipeline/shorts modules."""

from __future__ import annotations

import json
import re

from models.creative import CreativeTrace


def parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM output (strip markdown fences)."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
    return json.loads(cleaned)


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

    Comma-separated → stripped → non-empty items.
    """
    if not prompt:
        return []
    return [tag.strip() for tag in prompt.split(",") if tag.strip()]


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
