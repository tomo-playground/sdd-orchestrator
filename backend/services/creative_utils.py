"""Creative Lab shared utilities — DRY extraction from pipeline/shorts modules."""

from __future__ import annotations

import json
import re

from models.creative import CreativeTrace


def parse_json_response(raw: str) -> dict:
    """Extract JSON from LLM output (strip markdown fences)."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned.strip())
    # Attempt to fix common LLM JSON errors
    # 1. Fix unescaped backslashes (e.g. "path\to\file" -> "path\\to\\file"), but ignore valid escapes like \n, \t, \", \\
    # This is complex to do perfectly with regex, but we can try to catch obvious ones or just rely on a try-except block with fallback
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: simple escape of backslashes that look like they aren't part of a valid escape sequence
        # This is a heuristic and might not cover all cases
        # For now, let's try to just log the error and re-raise, or try to escape single backslashes if strictly needed.
        # Given the error is "Invalid \escape", it means there's a backslash followed by an invalid character.
        # We can try to double-escape backslashes that are NOT followed by specific chars.
        # Valid escapes in JSON: ", \, /, b, f, n, r, t, uXXXX
        # We want to turn invalid `\x` into `\\x`
        
        # 1. Regex to find backslashes that are NOT followed by valid escape chars
        # valid: ["\\/bfnrtu]
        # So we look for \ followed by anything ELSE
        cleaned_fixed = re.sub(r'\\(?![\\/bfnrtu"])', r"\\\\", cleaned)
        
        # 2. Fix invalid unicode escapes (e.g. \uXXXX where XXXX is not 4 hex digits)
        # The previous attempt didn't work because `\u` is already being processed by step 1 if we are not careful?
        # Step 1 excludes `u` from `[^\\/bfnrtu]`. So `\u` is preserved.
        # Now we want `\u` to be `\\u` IF it's not followed by 4 hex digits.
        # Regex: `\\u(?![0-9a-fA-F]{4})` matches `\u` not followed by 4 hex digits.
        # However, due to python string escaping, we need to be very careful with backslashes in regex.
        # In literal r'\\u', we match a literal backslash and u.
        cleaned_fixed = re.sub(r'\\u(?![0-9a-fA-F]{4})', r"\\\\u", cleaned_fixed)
        
        try:
             return json.loads(cleaned_fixed)
        except json.JSONDecodeError:
            # If still failing, raise the original error (or the new one)
            raise


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
