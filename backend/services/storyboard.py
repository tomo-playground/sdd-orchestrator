from __future__ import annotations

import json
import re

from fastapi import HTTPException

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, GEMINI_TEXT_MODEL, gemini_client, template_env
from schemas import StoryboardRequest
from services.keywords import format_keyword_context
from services.presets import get_preset_by_structure


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
    """Rename 'scene_tags' to 'context_tags' if present in Gemini output.

    The Jinja2 template historically asked Gemini for 'scene_tags', but the
    backend and DB model expect 'context_tags'.  This normalizer bridges the
    gap so both field names work seamlessly.
    """
    for scene in scenes:
        if "scene_tags" in scene and "context_tags" not in scene:
            scene["context_tags"] = scene.pop("scene_tags")
    return scenes


def create_storyboard(request: StoryboardRequest) -> dict:
    """Generate a storyboard from a topic using Gemini."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        preset = get_preset_by_structure(request.structure)
        template_name = preset.template if preset else "create_storyboard.j2"
        extra_fields = preset.extra_fields if preset else {}

        template = template_env.get_template(template_name)
        system_instruction = (
            "SYSTEM: You are a professional storyboarder and scriptwriter. "
            "Write clear, engaging scripts in the requested language (max 80 chars, max 2 lines). "
            "No emojis. Use ONLY the allowed keywords list for image_prompt tags. "
            "Do not invent new tags. Return raw JSON only."
        )
        rendered = template.render(
            topic=request.topic,
            duration=request.duration,
            style=request.style,
            structure=request.structure,
            language=request.language,
            actor_a_gender=request.actor_a_gender,
            keyword_context=format_keyword_context(),
            **extra_fields,
        )
        from google.genai import types

        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=f"{system_instruction}\n\n{rendered}",
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_NONE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_NONE",
                    ),
                ]
            ),
        )
        if not res.text:
            # Check why it failed
            error_reason = "Unknown error"
            if res.prompt_feedback and res.prompt_feedback.block_reason:
                error_reason = f"Blocked by safety filters: {res.prompt_feedback.block_reason}"
            elif res.candidates and res.candidates[0].finish_reason:
                error_reason = f"Finished with reason: {res.candidates[0].finish_reason}"

            raise ValueError(f"Gemini returned empty response. Reason: {error_reason}")

        cleaned = strip_markdown_codeblock(res.text)
        scenes = json.loads(cleaned)
        scenes = normalize_scene_tags_key(scenes)
        for scene in scenes:
            from config import ENABLE_DANBOORU_VALIDATION, logger
            from services.keywords import filter_prompt_tokens
            from services.prompt import (
                normalize_and_fix_tags,
                normalize_prompt_tokens,
                validate_tags_with_danbooru,
            )

            raw_prompt = scene.get("image_prompt", "")
            if not raw_prompt:
                continue

            scene_id = scene.get("scene_id", "?")
            logger.info(f"[Scene {scene_id}] Tag Pipeline Start")
            logger.info(f"  1️⃣  Raw Gemini: {raw_prompt}")

            # Phase 1: Normalize spaces and fix compound adjectives
            # - "thumbs up" → "thumbs_up"
            # - "short green hair" → "short_hair, green_hair"
            normalized = normalize_and_fix_tags(raw_prompt)
            logger.info(f"  2️⃣  Normalized:  {normalized}")

            # Phase 2 (optional): Danbooru validation for unknown tags
            # - Only validates tags not in DB (smart caching)
            # - Adds 2-5s first time, 0s after caching
            if ENABLE_DANBOORU_VALIDATION:
                tags = [t.strip() for t in normalized.split(",") if t.strip()]
                validated_tags = validate_tags_with_danbooru(tags)
                normalized = ", ".join(validated_tags)
                logger.info(f"  3️⃣  Validated:   {normalized}")

            # Phase 3: Filter against DB allowed tags
            filtered = filter_prompt_tokens(normalized)
            if not filtered:
                logger.warning("No allowed keywords in scene prompt; using normalized original.")
                filtered = normalize_prompt_tokens(normalized)

            logger.info(f"  4️⃣  Filtered:    {filtered}")
            logger.info(f"  ✅ Final Prompt: {filtered}")

            scene["image_prompt"] = filtered

            # Apply default negative prompt if not present
            if not scene.get("negative_prompt"):
                logger.info(f"  🔧 Adding default negative prompt to scene {scene_id}")
                scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT
            else:
                logger.info(f"  ℹ️  Scene {scene_id} already has negative_prompt: {scene['negative_prompt'][:50]}...")

        # Auto-pin background based on context_tags.environment
        logger.info("[Storyboard] Auto-pin: Analyzing environment tags for background consistency")
        previous_env_tags = None

        for i, scene in enumerate(scenes):
            context_tags = scene.get("context_tags", {})
            current_env_tags = set(context_tags.get("environment", [])) if context_tags else set()

            # Scene 0: no reference (first scene)
            if i == 0:
                previous_env_tags = current_env_tags
                logger.info(f"  Scene {i}: First scene, env={list(current_env_tags)}")
                continue

            # Same environment as previous scene → auto-pin
            if current_env_tags and previous_env_tags and (current_env_tags & previous_env_tags):
                # Note: We can't set environment_reference_id here because images don't exist yet
                # Instead, mark with a flag for frontend to auto-apply after first image generation
                scene["_auto_pin_previous"] = True
                logger.info(f"  Scene {i}: Same location {list(current_env_tags)} → mark for auto-pin")
            else:
                # Location changed → no pin
                scene["_auto_pin_previous"] = False
                logger.info(f"  Scene {i}: Location changed {list(previous_env_tags)} → {list(current_env_tags)}, no pin")

            previous_env_tags = current_env_tags

        logger.info(f"[Storyboard] Returning {len(scenes)} scenes with negative prompts")
        for i, s in enumerate(scenes):
            logger.info(f"  Scene {i+1} negative: {s.get('negative_prompt', 'NONE')[:80]}")
        return {"scenes": scenes}
    except Exception as exc:
        from config import logger

        # Check if it's a Gemini API quota error
        error_msg = str(exc)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.error("Gemini API quota exhausted")
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exhausted. Please try again later or check your API limits at https://aistudio.google.com/app/apikey"
            ) from exc

        logger.exception("Storyboard generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
