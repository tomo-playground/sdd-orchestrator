"""Edit Danbooru-style prompt tags via natural language instruction.

Uses Gemini to interpret the user's instruction and modify only the
relevant tags while preserving the rest. Mirrors ko_translator.py caching.
"""

from __future__ import annotations

import hashlib
import json
import time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import CACHE_DIR, CACHE_TTL_SECONDS, GEMINI_TEXT_MODEL, gemini_client, logger
from services.prompt.ko_translator import _build_exclude_section


def edit_prompt_with_instruction(
    current_prompt: str,
    instruction: str,
    character_id: int | None = None,
    db: Session | None = None,
) -> dict:
    """Edit prompt tags based on a natural language instruction.

    Returns: {"edited_prompt": "tag1, tag2, ..."}
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")
    if not current_prompt or not current_prompt.strip():
        raise HTTPException(status_code=400, detail="current_prompt is required")
    if not instruction or not instruction.strip():
        raise HTTPException(status_code=400, detail="instruction is required")

    cache_key = hashlib.sha256(f"prompt_edit|{current_prompt}|{instruction}|{character_id or ''}".encode()).hexdigest()[
        :16
    ]
    cache_file = CACHE_DIR / f"prompt_edit_{cache_key}.json"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            return json.loads(cache_file.read_text(encoding="utf-8"))

    exclude_section = _build_exclude_section(character_id, db)

    system_instruction = (
        "You are a Danbooru tag editor. Given existing comma-separated tags "
        "and an edit instruction, return the modified tag list.\n\n"
        "Rules:\n"
        "1. Input and output are comma-separated Danbooru-style tags\n"
        "2. Only change tags related to the instruction; preserve all others\n"
        "3. Keep the Danbooru underscore format (e.g. cowboy_shot, looking_at_viewer)\n"
        "4. Do NOT change character identity tags (hair, eyes, body, clothing)"
        f"{exclude_section}\n\n"
        f"Current tags: {current_prompt.strip()}\n"
        f"Instruction: {instruction.strip()}\n\n"
        "Output ONLY the modified comma-separated tags, no explanation."
    )

    try:
        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=system_instruction,
        )
        text = (res.text or "").strip().replace("```", "")
        result = {"edited_prompt": text}
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result
    except Exception as exc:
        logger.exception("Prompt edit failed")
        raise HTTPException(status_code=500, detail="Prompt edit failed") from exc
