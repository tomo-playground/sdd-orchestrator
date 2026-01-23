"""General utility functions for Shorts Producer Backend."""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap
from typing import Any


def parse_json_payload(text: str) -> dict[str, Any]:
    """Parse JSON from text, handling markdown code blocks."""
    cleaned = text.strip().replace("```json", "").replace("```", "")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive fields from a payload for logging."""
    redacted = {}
    for key, value in payload.items():
        if key in {"image_url", "image", "image_b64"} and isinstance(value, str):
            redacted[key] = "<redacted>"
        elif isinstance(value, list):
            redacted[key] = [
                scrub_payload(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, dict):
            redacted[key] = scrub_payload(value)
        else:
            redacted[key] = value
    return redacted


def wrap_text(text: str, width: int, max_lines: int = 2) -> str:
    """Wrap text for subtitle display with intelligent line breaking."""
    if not text:
        return ""
    # "..."을 임시 플레이스홀더로 치환 (split 방지)
    placeholder = "\x00ELLIPSIS\x00"
    text = text.replace("...", placeholder)

    forced_split = None
    for mark in ("…", ".", "!", "?"):
        if mark in text:
            forced_split = mark
            break
    if forced_split:
        head, tail = text.split(forced_split, 1)
        head = head.strip()
        tail = tail.strip()
        if forced_split != "…":
            head = f"{head}{forced_split}"
        lines = [head, tail] if tail else [head]
    else:
        lines = textwrap.wrap(text, width=width)
    if max_lines > 0 and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            max_tail = max(0, width - 3)
            lines[-1] = lines[-1][:max_tail].rstrip() + "..."

    # 플레이스홀더를 "..."로 복원
    result = "\n".join(lines)
    return result.replace(placeholder, "...")


def get_audio_duration(path: pathlib.Path) -> float:
    """Get the duration of an audio file in seconds using ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def to_edge_tts_rate(multiplier: float) -> str:
    """Convert a speed multiplier to EdgeTTS rate format (e.g., +10%, -20%)."""
    safe_multiplier = max(0.1, min(multiplier, 2.0))
    percent = int(round((safe_multiplier - 1.0) * 100))
    return f"+{percent}%" if percent >= 0 else f"{percent}%"
