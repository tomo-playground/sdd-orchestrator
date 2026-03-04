"""Post-processing steps for Gemini-generated scenes.

Extracted from gemini_generator.py for file size compliance (< 400 lines).
"""

from __future__ import annotations

import re

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, ENABLE_DANBOORU_VALIDATION, logger

MAX_SCRIPT_CHARS = 35
MAX_NARRATOR_SCRIPT_CHARS = 20

_NARRATOR_PERSON_PATTERN = re.compile(r"(그|그녀|그들|두\s*사람|세\s*사람|그가|그녀가|그는|그녀는|서로를|서로)")


def annotate_speakable(scenes: list[dict]) -> None:
    """Mark each scene with speakable flag based on script content (in-place).

    This is the SSOT for TTS eligibility. Downstream nodes (TTS Designer,
    Director, Rendering) use this flag to skip non-speech scenes.
    """
    from services.video.utils import has_speakable_content

    for scene in scenes:
        script = scene.get("script", "")
        scene["speakable"] = has_speakable_content(script)
        if not scene["speakable"]:
            logger.warning(
                "[Scene %s] Non-speakable script: '%s' — TTS will be skipped",
                scene.get("scene_id", scene.get("order", "?")),
                script[:30],
            )


def warn_script_issues(scenes: list[dict]) -> None:
    """Warn if scripts exceed 2-line rendering limit or narrator scripts describe characters."""
    for s in scenes:
        script = s.get("script", "")
        scene_id = s.get("scene_id", "?")

        if len(script) > MAX_SCRIPT_CHARS:
            logger.warning(
                "[Scene %s] Script too long for 2 lines: %d chars (max %d): '%s...'",
                scene_id,
                len(script),
                MAX_SCRIPT_CHARS,
                script[:40],
            )

        if s.get("speaker") != "Narrator":
            continue
        if _NARRATOR_PERSON_PATTERN.search(script):
            logger.warning(
                "[Scene %s] Narrator script contains character reference: '%s' "
                "— should describe environment/mood, not character actions",
                scene_id,
                script,
            )
        if len(script) > MAX_NARRATOR_SCRIPT_CHARS:
            logger.warning(
                "[Scene %s] Narrator script too long: %d chars (max %d): '%s...'",
                scene_id,
                len(script),
                MAX_NARRATOR_SCRIPT_CHARS,
                script[:30],
            )


def process_scene_tags(scenes: list[dict]) -> None:
    """Normalize, validate, and filter image_prompt tags for each scene (in-place)."""
    from services.keywords import filter_prompt_tokens
    from services.prompt import (
        normalize_and_fix_tags,
        normalize_prompt_tokens,
        validate_tags_with_danbooru,
    )

    for scene in scenes:
        raw_prompt = scene.get("image_prompt", "")
        if not raw_prompt:
            continue

        scene_id = scene.get("scene_id", "?")
        logger.info("[Scene %s] Tag Pipeline Start", scene_id)
        logger.info("  1\ufe0f\u20e3  Raw Gemini: %s", raw_prompt)

        normalized = normalize_and_fix_tags(raw_prompt)
        logger.info("  2\ufe0f\u20e3  Normalized:  %s", normalized)

        if ENABLE_DANBOORU_VALIDATION:
            tags = [t.strip() for t in normalized.split(",") if t.strip()]
            validated_tags = validate_tags_with_danbooru(tags)
            normalized = ", ".join(validated_tags)
            logger.info("  3\ufe0f\u20e3  Validated:   %s", normalized)

        filtered = filter_prompt_tokens(normalized)
        if not filtered:
            logger.warning("No allowed keywords in scene prompt; using normalized original.")
            filtered = normalize_prompt_tokens(normalized)

        logger.info("  4\ufe0f\u20e3  Filtered:    %s", filtered)
        logger.info("  \u2705 Final Prompt: %s", filtered)

        scene["image_prompt"] = filtered

        if not scene.get("negative_prompt"):
            logger.info("  \U0001f527 Adding default negative prompt to scene %s", scene_id)
            scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT
        else:
            logger.info(
                "  \u2139\ufe0f  Scene %s already has negative_prompt: %s...",
                scene_id,
                scene["negative_prompt"][:50],
            )


async def process_scene_tags_async(scenes: list[dict]) -> list[str]:
    """Async version of process_scene_tags. DB cache only, returns unknown tags.

    Uses validate_tags_with_danbooru_async (DB-only) instead of
    validate_tags_with_danbooru (Danbooru API). Unknown tags are returned
    for background classification via schedule_background_classification().
    """
    from services.keywords import filter_prompt_tokens
    from services.prompt import normalize_and_fix_tags, normalize_prompt_tokens
    from services.prompt.prompt import validate_tags_with_danbooru_async

    all_unknown: list[str] = []

    for scene in scenes:
        raw_prompt = scene.get("image_prompt", "")
        if not raw_prompt:
            continue

        scene_id = scene.get("scene_id", "?")
        logger.info("[Scene %s] Tag Pipeline Start (async)", scene_id)

        normalized = normalize_and_fix_tags(raw_prompt)

        if ENABLE_DANBOORU_VALIDATION:
            tags = [t.strip() for t in normalized.split(",") if t.strip()]
            validated_tags, unknown_tags = await validate_tags_with_danbooru_async(tags)
            normalized = ", ".join(validated_tags)
            all_unknown.extend(unknown_tags)

        filtered = filter_prompt_tokens(normalized)
        if not filtered:
            filtered = normalize_prompt_tokens(normalized)

        scene["image_prompt"] = filtered

        if not scene.get("negative_prompt"):
            scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT

    return all_unknown


def strip_no_humans_from_dialogue(scenes: list[dict]) -> None:
    """Strip no_humans tag from speaker scenes in dialogue structures (in-place)."""
    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker in ("A", "B"):
            prompt = scene.get("image_prompt", "")
            if "no_humans" in prompt.lower().replace(" ", "_"):
                tags = [t.strip() for t in prompt.split(",")]
                tags = [t for t in tags if t.lower().replace(" ", "_").strip() != "no_humans"]
                scene["image_prompt"] = ", ".join(tags)
                logger.warning(
                    "[Scene %s] Stripped no_humans from Speaker %s (Dialogue requires character)",
                    scene.get("scene_id", "?"),
                    speaker,
                )


def ensure_dialogue_speakers(scenes: list[dict]) -> None:
    """Quick 모드 방어선: Dialogue 씬에 A와 B 모두 존재하는지 확인하고 자동 수정 (in-place).

    A,B 모두 존재하면 빠른 탈출. 아니면 non-Narrator 씬을 교대 배정.
    """
    speakers = {s.get("speaker") for s in scenes}
    if "A" in speakers and "B" in speakers:
        return  # 양쪽 모두 존재 — OK

    non_narrator = [s for s in scenes if s.get("speaker") != "Narrator"]
    if not non_narrator:
        logger.warning("[PostProcess] ensure_dialogue_speakers: non-Narrator 씬 없음, 수정 불가")
        return

    for i, scene in enumerate(non_narrator):
        scene["speaker"] = "A" if i % 2 == 0 else "B"

    logger.warning(
        "[PostProcess] Dialogue speaker 자동 교대 배정: %d개 non-Narrator 씬 (원래 speakers=%s)",
        len(non_narrator),
        speakers,
    )


def auto_pin_raw_scenes(scenes: list[dict], structure_lower: str) -> None:
    """Set _auto_pin_previous flags on raw Gemini scene dicts (in-place)."""
    is_dialogue_structure = structure_lower in ("dialogue", "narrated dialogue")

    if is_dialogue_structure:
        logger.info("[Storyboard] Auto-pin: %s structure - all scenes share background", structure_lower)
        for i, scene in enumerate(scenes):
            scene["_auto_pin_previous"] = i > 0
            if i == 0:
                logger.info("  Scene %d: First scene (no auto-pin)", i)
            else:
                logger.info("  Scene %d: Auto-pin to previous (shared background)", i)
    else:
        logger.info("[Storyboard] Auto-pin: Analyzing environment tags for background consistency")
        previous_env_tags: set[str] | None = None

        for i, scene in enumerate(scenes):
            context_tags = scene.get("context_tags", {})
            current_env_tags = set(context_tags.get("environment", [])) if context_tags else set()

            if i == 0:
                previous_env_tags = current_env_tags
                scene["_auto_pin_previous"] = False
                logger.info("  Scene %d: First scene, env=%s", i, list(current_env_tags))
            elif current_env_tags and previous_env_tags and (current_env_tags & previous_env_tags):
                scene["_auto_pin_previous"] = True
                logger.info("  Scene %d: Same location %s → mark for auto-pin", i, list(current_env_tags))
            else:
                scene["_auto_pin_previous"] = False
                logger.info(
                    "  Scene %d: Location changed %s → %s, no pin",
                    i,
                    list(previous_env_tags or set()),
                    list(current_env_tags),
                )
            previous_env_tags = current_env_tags
