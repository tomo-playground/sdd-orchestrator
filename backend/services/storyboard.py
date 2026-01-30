from __future__ import annotations

import json

from fastapi import HTTPException

from config import GEMINI_TEXT_MODEL, gemini_client, template_env, DEFAULT_SCENE_NEGATIVE_PROMPT
from schemas import StoryboardRequest
from services.keywords import format_keyword_context
from services.presets import get_preset_by_structure


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

        scenes = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
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
