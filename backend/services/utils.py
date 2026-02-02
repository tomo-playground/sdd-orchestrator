"""General utility functions for Shorts Producer Backend."""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont


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


def wrap_text_by_font(
    text: str,
    font: FreeTypeFont,
    max_width_px: int,
    max_lines: int = 2,
    balance_lines: bool = True,
) -> list[str]:
    """Wrap text based on actual rendered pixel width with balanced line lengths.

    Args:
        text: Text to wrap.
        font: PIL FreeTypeFont instance for measuring text width.
        max_width_px: Maximum line width in pixels.
        max_lines: Maximum number of lines (0 for unlimited).
        balance_lines: If True, try to make line lengths similar.

    Returns:
        List of wrapped lines.
    """
    if not text:
        return []

    # "..."을 임시 플레이스홀더로 치환 (split 방지)
    placeholder = "\x00ELLIPSIS\x00"
    text = text.replace("...", placeholder)

    def measure_width(s: str) -> int:
        """Measure text width in pixels."""
        bbox = font.getbbox(s)
        return bbox[2] - bbox[0] if bbox else 0

    def restore_ellipsis(s: str) -> str:
        """Restore placeholder to ellipsis."""
        return s.replace(placeholder, "...")

    def find_balanced_split(words: list[str], target_lines: int) -> list[str]:
        """Find the best split points to balance line lengths."""
        if target_lines <= 1 or len(words) <= 1:
            return [" ".join(words)]

        # For 2 lines, find the split point that minimizes length difference
        if target_lines == 2:
            best_split = len(words) // 2
            best_diff = float("inf")

            for i in range(1, len(words)):
                line1 = " ".join(words[:i])
                line2 = " ".join(words[i:])
                w1, w2 = measure_width(line1), measure_width(line2)

                # Both lines must fit
                if w1 > max_width_px or w2 > max_width_px:
                    continue

                diff = abs(w1 - w2)
                if diff < best_diff:
                    best_diff = diff
                    best_split = i

            line1 = " ".join(words[:best_split])
            line2 = " ".join(words[best_split:])
            return [line1, line2] if line2 else [line1]

        # For 3+ lines, use greedy approach with balancing
        total_width = measure_width(" ".join(words))
        target_width = total_width // target_lines

        lines = []
        current_words: list[str] = []

        for word in words:
            test_line = " ".join(current_words + [word])
            if measure_width(test_line) <= max(target_width, max_width_px * 0.7):
                current_words.append(word)
            else:
                if current_words:
                    lines.append(" ".join(current_words))
                current_words = [word]

            if len(lines) >= target_lines - 1:
                # Put remaining words in last line
                current_words.extend(words[words.index(word) + 1 :])
                break

        if current_words:
            lines.append(" ".join(current_words))

        return lines[:target_lines]

    # 1. 문장부호 기준 강제 분리
    forced_split = None
    # Removed '.' to prevent splitting decimals (e.g. 0.25)
    for mark in ("…", "!", "?"):
        if mark in text:
            forced_split = mark
            break

    if forced_split:
        head, tail = text.split(forced_split, 1)
        head = head.strip()
        tail = tail.strip()
        if forced_split != "…":
            head = f"{head}{forced_split}"
        initial_lines = [head, tail] if tail else [head]
    else:
        initial_lines = [text]

    # 2. 각 줄을 픽셀 너비 기준으로 처리
    result_lines: list[str] = []

    for line in initial_lines:
        if max_lines > 0 and len(result_lines) >= max_lines:
            break

        line = line.strip()
        if not line:
            continue

        # 이미 최대 너비 이하면 그대로 추가
        if measure_width(line) <= max_width_px:
            result_lines.append(line)
            continue

        words = line.split()
        remaining_lines = max_lines - len(result_lines) if max_lines > 0 else 2

        # 균형 맞추기 시도
        if balance_lines and remaining_lines >= 2:
            balanced = find_balanced_split(words, remaining_lines)
            # 모든 줄이 max_width_px 이하인지 확인
            if all(measure_width(line) <= max_width_px for line in balanced):
                result_lines.extend(balanced)
                continue

        # 균형 맞추기 실패 시 기존 greedy 방식
        current_line = ""
        for word in words:
            if max_lines > 0 and len(result_lines) >= max_lines:
                break

            test_line = f"{current_line} {word}".strip() if current_line else word

            if measure_width(test_line) <= max_width_px:
                current_line = test_line
            else:
                if current_line:
                    result_lines.append(current_line)
                current_line = word

                # 단일 단어가 너비 초과하면 강제로 자름
                if measure_width(word) > max_width_px:
                    trimmed = ""
                    for char in word:
                        if measure_width(trimmed + char) <= max_width_px:
                            trimmed += char
                        else:
                            break
                    current_line = trimmed if trimmed else word[:1]

        if current_line and (max_lines == 0 or len(result_lines) < max_lines):
            result_lines.append(current_line)

    # max_lines 제한
    if max_lines > 0 and len(result_lines) > max_lines:
        result_lines = result_lines[:max_lines]

    return [restore_ellipsis(line) for line in result_lines]


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


