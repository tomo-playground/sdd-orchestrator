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


# normalize_structure() 적용 후 결과("Narrated Dialogue")와 미적용 원본("Narrated_Dialogue") 모두 포함.
# 일부 호출자가 normalize 없이 raw structure를 전달할 수 있으므로 방어적으로 두 형태를 지원한다.
_DIALOGUE_STRUCTURES: frozenset[str] = frozenset({"Dialogue", "Narrated Dialogue", "Narrated_Dialogue"})


def normalize_structure(structure: str | None) -> str:
    """structure 문자열을 Title Case 표준형으로 정규화한다.

    "monologue" → "Monologue", "narrated_dialogue" → "Narrated Dialogue"
    """
    if not structure:
        return "Monologue"
    s = structure.strip().replace("_", " ")
    return " ".join(word.capitalize() for word in s.split())


def calculate_min_scenes(duration: int, structure: str | None = None) -> int:
    """Calculate the minimum expected scene count for a given duration.

    Dialogue structures use ~6s/exchange — formula: ceil(duration / 6).
    Other structures: ceil(duration / SCENE_DURATION_RANGE[1]) (3.5s).
    Returns at least 3 for Dialogue, 1 for others.
    """
    if structure in _DIALOGUE_STRUCTURES:
        return max(3, math.ceil(duration / 6.0))
    from config import SCENE_DURATION_RANGE

    return max(1, math.ceil(duration / SCENE_DURATION_RANGE[1]))


def calculate_max_scenes(duration: int, structure: str | None = None) -> int:
    """Calculate the maximum allowed scene count for a given duration.

    Dialogue structures use ~4s minimum/exchange — formula: ceil(duration / 4).
    Other structures: ceil(duration / 2).
    Returns at least 3 for Dialogue, 1 for others.
    """
    if structure in _DIALOGUE_STRUCTURES:
        return max(3, math.ceil(duration / 4.0))
    return max(1, math.ceil(duration / 2))


def trim_scenes_to_duration(scenes: list[dict], duration: int, structure: str | None = None) -> list[dict]:
    """Trim Gemini-generated scenes if count exceeds max for the given duration.

    Returns the original list if within bounds, or a trimmed copy.
    """
    max_scenes = calculate_max_scenes(duration, structure)
    if len(scenes) <= max_scenes:
        return scenes
    logger.warning(
        "[Storyboard] Gemini returned %d scenes for %ds (max %d, structure=%s). Trimming.",
        len(scenes),
        duration,
        max_scenes,
        structure,
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
    is_dialogue = structure and structure.lower().replace("_", " ") in ("dialogue", "narrated dialogue")

    if is_dialogue:
        for i, scene in enumerate(scenes):
            # Stage background overrides auto-pin
            if getattr(scene, "background_id", None):
                result[scene.id] = False
            else:
                result[scene.id] = i > 0
        return result

    # For Monologue: use environment tag overlap logic
    previous_env_tags: set[str] | None = None

    for i, scene in enumerate(scenes):
        # Stage background overrides auto-pin (dedicated environment reference)
        if getattr(scene, "background_id", None):
            result[scene.id] = False
            context_tags = scene.context_tags or {}
            previous_env_tags = set(context_tags.get("environment", []))
            continue

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


def resolve_scene_id_by_client_id(db, scene_id: int, client_id: str | None, storyboard_id: int | None) -> int | None:
    """Resolve current scene DB ID, falling back to client_id when scene_id is stale.

    Returns the resolved scene_id, or None if both lookups fail.
    """
    from models.scene import Scene

    exists = db.query(Scene.id).filter(Scene.id == scene_id, Scene.deleted_at.is_(None)).first()
    if exists:
        return scene_id

    if client_id and storyboard_id:
        fallback = (
            db.query(Scene.id)
            .filter(
                Scene.client_id == client_id,
                Scene.storyboard_id == storyboard_id,
                Scene.deleted_at.is_(None),
            )
            .first()
        )
        if fallback:
            logger.info(
                "[SceneResolver] scene_id %d stale, resolved via client_id %s → %d",
                scene_id,
                client_id,
                fallback[0],
            )
            return fallback[0]

    logger.warning("[SceneResolver] scene_id %d not found, client_id=%s", scene_id, client_id)
    return None


def resolve_project_group_ids(db, storyboard_id: int) -> tuple[int, int] | None:
    """Resolve (project_id, group_id) from storyboard_id.

    Storyboard has group_id; project_id is derived via Group.
    """
    from models.group import Group
    from models.storyboard import Storyboard

    row = (
        db.query(Group.project_id, Storyboard.group_id)
        .join(Group, Group.id == Storyboard.group_id)
        .filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None))
        .first()
    )
    if row:
        return (row.project_id, row.group_id)
    return None


def _sanitize_candidates_for_db(candidates: list) -> list[dict]:
    """Strip image_url from candidates before JSONB storage."""
    result = []
    for c in candidates:
        d = c.model_dump(exclude={"image_url"}) if hasattr(c, "model_dump") else dict(c)
        d.pop("image_url", None)
        result.append(d)
    return result
