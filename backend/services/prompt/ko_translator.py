"""Korean scene description -> Danbooru-style image prompt translator.

Uses Gemini to convert Korean scene descriptions into comma-separated
Danbooru tags suitable for Stable Diffusion image generation.
Follows the same caching pattern as rewrite_prompt() in prompt.py.
"""

from __future__ import annotations

import hashlib
import json
import time

from fastapi import HTTPException
from google.genai import types
from sqlalchemy.orm import Session

from config import CACHE_DIR, CACHE_TTL_SECONDS, GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client, logger


def _build_exclude_section(character_id: int | None, db: Session | None) -> str:
    """Build exclude instruction from character identity tags."""
    if not character_id or not db:
        return ""
    try:
        from models.associations import CharacterTag
        from models.tag import Tag

        rows = (
            db.query(Tag.name)
            .join(CharacterTag, CharacterTag.tag_id == Tag.id)
            .filter(CharacterTag.character_id == character_id)
            .all()
        )
        if rows:
            tag_names = ", ".join(r[0] for r in rows)
            return f"\nExclude these character identity tags (already injected): {tag_names}"
    except Exception as exc:
        logger.warning("Failed to load character tags for exclude list: %s", exc)
    return ""


def translate_ko_to_prompt(
    ko_text: str,
    current_prompt: str | None = None,
    character_id: int | None = None,
    db: Session | None = None,
) -> dict:
    """Translate Korean scene description to Danbooru-style prompt tags.

    Returns: {"translated_prompt": "tag1, tag2, ...", "source_ko": "..."}
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")
    if not ko_text or not ko_text.strip():
        raise HTTPException(status_code=400, detail="ko_text is required")

    # SHA256 cache
    cache_key = hashlib.sha256(
        f"ko_translate|{ko_text}|{current_prompt or ''}|{character_id or ''}".encode()
    ).hexdigest()[:16]
    cache_file = CACHE_DIR / f"ko_translate_{cache_key}.json"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            return cached

    exclude_section = _build_exclude_section(character_id, db)

    system_prompt = (
        "You are a Danbooru tag expert. Convert the Korean scene description "
        "into comma-separated Danbooru-style tags for Stable Diffusion.\n\n"
        "Rules:\n"
        "1. Output ONLY comma-separated English tags in Danbooru underscore format\n"
        "2. Do NOT include character identity tags (hair, eyes, body, clothing)\n"
        "3. Focus on: action, emotion, pose, camera angle, environment, lighting\n"
        "4. Use standard Danbooru tags: cowboy_shot, looking_at_viewer, smile, etc.\n"
        "5. If camera/composition is implied, add appropriate tags"
        f"{exclude_section}\n\n"
        "Output ONLY the tags, no explanation."
    )

    user_content = f"Korean: {ko_text}"
    if current_prompt:
        user_content += f"\nCurrent EN prompt (for reference): {current_prompt}"

    try:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )
        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=user_content,
            config=config,
        )
        text = (res.text or "").strip().replace("```", "")
        result = {"translated_prompt": text, "source_ko": ko_text}
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result
    except Exception as exc:
        logger.exception("KO -> EN translation failed")
        raise HTTPException(status_code=500, detail="Translation failed") from exc
