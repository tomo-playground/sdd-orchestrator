from __future__ import annotations

import math
import re

from config import logger


def strip_markdown_codeblock(text: str) -> str:
    """Strip markdown code block fences from Gemini response text.

    Handles variations: ```json, ```JSON, ``` with/without language tag,
    leading/trailing whitespace, and text outside the code block.
    """
    # Match ```<optional lang>\n<content>\n``` (case-insensitive, dotall)
    pattern = r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # No code block found -- return stripped original text
    return text.strip()


def normalize_scene_tags_key(scenes: list[dict]) -> list[dict]:
    """Rename 'scene_tags' to 'context_tags' if present in Gemini output."""
    for scene in scenes:
        if "scene_tags" in scene and "context_tags" not in scene:
            scene["context_tags"] = scene.pop("scene_tags")
    return scenes


def calculate_min_scenes(duration: int) -> int:
    """Calculate the minimum expected scene count for a given duration.

    Formula: ceil(duration / max_scene_duration) — uses SCENE_DURATION_RANGE[1] (3.5s).
    This is intentionally lower than the Gemini template's recommended minimum
    (duration/3) to allow a tolerance buffer for Review validation.
    Returns at least 1.
    """
    from config import SCENE_DURATION_RANGE

    return max(1, math.ceil(duration / SCENE_DURATION_RANGE[1]))


def calculate_max_scenes(duration: int) -> int:
    """Calculate the maximum allowed scene count for a given duration.

    Formula: ceil(duration / 2) — assumes minimum 2 seconds per scene.
    Returns at least 1.
    """
    return max(1, math.ceil(duration / 2))


def trim_scenes_to_duration(scenes: list[dict], duration: int) -> list[dict]:
    """Trim Gemini-generated scenes if count exceeds max for the given duration.

    Returns the original list if within bounds, or a trimmed copy.
    """
    max_scenes = calculate_max_scenes(duration)
    if len(scenes) <= max_scenes:
        return scenes
    logger.warning(
        "[Storyboard] Gemini returned %d scenes for %ds (max %d). Trimming.",
        len(scenes),
        duration,
        max_scenes,
    )
    return scenes[:max_scenes]


def estimate_reading_duration(text: str, language: str) -> float:
    """Script 텍스트로부터 읽기 시간을 추정한다. config.py READING_SPEED 사용."""
    from config import READING_DURATION_PADDING, READING_SPEED, SCENE_DURATION_MAX

    cfg = READING_SPEED.get(language, READING_SPEED["Korean"])
    stripped = text.strip()
    if not stripped:
        return 2.0

    if cfg.get("unit") == "words":
        count = len(stripped.split())
        rate = cfg["wps"]
    else:
        count = len(stripped.replace(" ", ""))
        rate = cfg["cps"]

    raw = count / rate + READING_DURATION_PADDING
    return max(2.0, min(SCENE_DURATION_MAX, round(raw, 1)))


def truncate_title(title: str, max_length: int = 190) -> str:
    """Truncate title if it exceeds constraints."""
    if not title:
        return "Untitled"
    if len(title) > max_length:
        return title[:max_length] + "..."
    return title


def calculate_auto_pin_flags(scenes: list, structure: str | None = None) -> dict[int, bool]:
    """Calculate _auto_pin_previous flags for scenes based on environment tags.

    A scene should auto-pin to the previous scene if they share at least one
    environment tag (same location).

    For Dialogue and Narrated Dialogue structures, all scenes after the first
    auto-pin because all speakers share the same environment by spec.

    Args:
        scenes: List of Scene ORM objects, sorted by order
        structure: Storyboard structure type (Monologue, Dialogue, Narrated Dialogue)

    Returns:
        Dict mapping scene.id -> bool (True if should auto-pin)
    """
    result: dict[int, bool] = {}

    # For Dialogue/Narrated Dialogue: all scenes share the same background
    is_dialogue = structure and structure.lower() in ("dialogue", "narrated dialogue")

    if is_dialogue:
        for i, scene in enumerate(scenes):
            # First scene has no previous to pin to; all others auto-pin
            result[scene.id] = i > 0
        return result

    # For Monologue: use environment tag overlap logic
    previous_env_tags: set[str] | None = None

    for i, scene in enumerate(scenes):
        context_tags = scene.context_tags or {}
        current_env_tags = set(context_tags.get("environment", []))

        if i == 0:
            # First scene has no previous to pin to
            result[scene.id] = False
        elif current_env_tags and previous_env_tags and (current_env_tags & previous_env_tags):
            # Same location as previous scene
            result[scene.id] = True
        else:
            # Location changed
            result[scene.id] = False

        previous_env_tags = current_env_tags

    return result


def _sanitize_candidates_for_db(candidates: list) -> list[dict]:
    """Strip image_url from candidates before JSONB storage."""
    result = []
    for c in candidates:
        d = c.model_dump(exclude={"image_url"}) if hasattr(c, "model_dump") else dict(c)
        d.pop("image_url", None)
        result.append(d)
    return result
