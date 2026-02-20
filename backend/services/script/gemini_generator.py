from __future__ import annotations

import asyncio
import json

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from config import (
    GEMINI_TEXT_MODEL,
    gemini_client,
    logger,
    template_env,
)
from models.associations import CharacterTag
from models.character import Character
from services.keywords import format_keyword_context
from services.presets import get_preset_by_structure
from services.script.scene_postprocess import (
    auto_pin_raw_scenes,
    process_scene_tags,
    strip_no_humans_from_dialogue,
    warn_script_issues,
)
from services.storyboard.helpers import (
    normalize_scene_tags_key,
    strip_markdown_codeblock,
    trim_scenes_to_duration,
)


async def _call_gemini_with_retry(
    contents: str,
    config,
    trace_name: str = "gemini",
) -> object:
    """Call Gemini API with async + exponential backoff retry (max 2 retries)."""
    from services.agent.observability import trace_llm_call

    delays = [1, 3]
    last_exc = None
    for attempt in range(3):
        try:
            async with trace_llm_call(name=trace_name, input_text=contents[:2000]) as llm:
                res = await gemini_client.aio.models.generate_content(
                    model=GEMINI_TEXT_MODEL,
                    contents=contents,
                    config=config,
                )
                llm.record(res)
            return res
        except Exception as exc:
            last_exc = exc
            error_msg = str(exc)
            is_retryable = "429" in error_msg or "5" in error_msg[:1] and len(error_msg) >= 3
            if attempt < 2 and is_retryable:
                delay = delays[attempt]
                logger.warning("Gemini API retry %d/%d after %ds: %s", attempt + 1, 2, delay, error_msg[:100])
                await asyncio.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]


def _load_character_context(character_id: int, db: Session) -> dict | None:
    """Load character data and classify tags for Gemini template injection."""
    char = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == character_id)
        .first()
    )
    if not char:
        logger.warning("Character %d not found, skipping character context", character_id)
        return None

    identity_tags: list[str] = []
    costume_tags: list[str] = []
    for ct in char.tags:
        tag = ct.tag
        if not tag:
            continue
        layer = tag.default_layer
        if layer is not None and layer <= 3:
            identity_tags.append(tag.name)
        elif layer is not None and 4 <= layer <= 6:
            costume_tags.append(tag.name)

    lora_triggers: list[str] = []
    if char.loras:
        from models.lora import LoRA

        for lora_entry in char.loras:
            lora_id = lora_entry.get("lora_id")
            if not lora_id:
                continue
            lora = db.query(LoRA).filter(LoRA.id == lora_id).first()
            if lora and lora.trigger_words:
                lora_triggers.extend(lora.trigger_words)

    ctx = {
        "name": char.name,
        "gender": char.gender or "female",
        "identity_tags": identity_tags,
        "costume_tags": costume_tags,
        "lora_triggers": lora_triggers,
        "custom_base_prompt": char.custom_base_prompt or "",
    }
    logger.info(
        "[Character Context] %s: identity=%s, costume=%s, lora_triggers=%s",
        char.name,
        identity_tags,
        costume_tags,
        lora_triggers,
    )
    return ctx


def _check_multi_character_capable(
    character_id: int | None,
    character_b_id: int | None,
    db: Session,
) -> bool:
    """Check if any LoRA across both characters supports multi-character rendering.

    Queries each character's loras JSONB, looks up LoRA rows, and returns True
    if at least one has is_multi_character_capable=True.
    """
    from models.lora import LoRA

    char_ids = [cid for cid in (character_id, character_b_id) if cid]
    if not char_ids:
        return False

    chars = db.query(Character).filter(Character.id.in_(char_ids)).all()
    lora_ids: set[int] = set()
    for char in chars:
        for entry in char.loras or []:
            lid = entry.get("lora_id")
            if lid:
                lora_ids.add(lid)

    if not lora_ids:
        return False

    count = db.query(LoRA.id).filter(LoRA.id.in_(lora_ids), LoRA.is_multi_character_capable.is_(True)).count()
    return count > 0


async def generate_script(request, db: Session | None = None, pipeline_context: dict | None = None) -> dict:
    """Generate a storyboard from a topic using Gemini (async)."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        structure_lower = request.structure.lower()
        has_two_characters = structure_lower in ("dialogue", "narrated dialogue")

        # Dialogue validation (structures with two characters)
        if has_two_characters:
            if not request.character_id:
                raise HTTPException(status_code=400, detail="Dialogue requires character_id (Speaker A)")
            if not request.character_b_id:
                raise HTTPException(status_code=400, detail="Dialogue requires character_b_id (Speaker B)")
            if request.character_id == request.character_b_id:
                raise HTTPException(status_code=400, detail="Speaker A and B must be different characters")

        # Load character context if character_id provided
        character_context = None
        if request.character_id and db:
            character_context = _load_character_context(request.character_id, db)

        # Load character B context for two-character structures
        character_b_context = None
        if has_two_characters and request.character_b_id and db:
            character_b_context = _load_character_context(request.character_b_id, db)

        # Detect multi-character capable LoRA for template injection
        is_multi_character_capable = False
        if has_two_characters and db:
            is_multi_character_capable = _check_multi_character_capable(
                request.character_id, request.character_b_id, db
            )
            if is_multi_character_capable:
                logger.info("[Storyboard] Multi-character capable LoRA detected")

        # Load channel DNA from GroupConfig if group_id provided
        channel_dna = None
        if request.group_id and db:
            from models.group_config import GroupConfig

            gc = db.query(GroupConfig).filter(GroupConfig.group_id == request.group_id).first()
            if gc and gc.channel_dna:
                channel_dna = gc.channel_dna

        # Release DB connection before Gemini API call (10-30s)
        # DB auto-reconnects when needed later (auto_populate_character_actions)
        if db:
            db.close()

        preset = get_preset_by_structure(request.structure)
        template_name = preset.template if preset else "create_storyboard.j2"
        extra_fields = preset.extra_fields if preset else {}

        template = template_env.get_template(template_name)

        fallback_instruction = (
            "SYSTEM: You are a professional storyboarder and scriptwriter. "
            "Write clear, engaging scripts in the requested language. "
            "STRICT: Each script must be max 30 chars (Korean) / 60 chars (English) to fit 2 lines on screen. "
            "If a sentence is too long, split it into two scenes. "
            "No emojis. Use ONLY the allowed keywords list for image_prompt tags. "
            "Do not invent new tags. Return raw JSON only."
        )
        system_instruction = fallback_instruction

        # 파이프라인 컨텍스트 (research_brief, writer_plan 등) 주입
        ctx = pipeline_context or {}
        rendered = template.render(
            topic=request.topic,
            description=request.description or "",
            duration=request.duration,
            style=request.style,
            structure=request.structure,
            language=request.language,
            actor_a_gender=request.actor_a_gender,
            keyword_context=format_keyword_context(),
            character_context=character_context,
            character_b_context=character_b_context,
            is_multi_character_capable=is_multi_character_capable,
            channel_dna=channel_dna,
            selected_concept=request.selected_concept,
            research_brief=ctx.get("research_brief", ""),
            writer_plan=ctx.get("writer_plan", ""),
            revision_feedback=ctx.get("revision_feedback", ""),
            current_script_summary=ctx.get("current_script_summary", ""),
            **extra_fields,
        )
        from google.genai import types

        config = types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                    threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        )
        res = await _call_gemini_with_retry(
            contents=f"{system_instruction}\n\n{rendered}",
            config=config,
            trace_name="writer",
        )
        if not res.text:
            # Check why it failed
            error_reason = "Unknown error"
            user_message = "시나리오 생성에 실패했습니다."
            suggestions = []

            if res.prompt_feedback and res.prompt_feedback.block_reason:
                block_reason = str(res.prompt_feedback.block_reason)
                error_reason = f"Blocked by safety filters: {block_reason}"
                user_message = "🛡️ Gemini 안전 필터가 콘텐츠를 차단했습니다"
                suggestions = [
                    "다른 주제로 시도해보세요 (예: 일상, 취미, 지식 공유)",
                    "폭력적, 성적, 혐오적 표현이 포함되지 않았는지 확인하세요",
                    "민감한 주제 (정치, 종교, 건강 정보)는 피해주세요",
                    "캐릭터나 스타일을 변경해보세요",
                ]
            elif res.candidates and res.candidates[0].finish_reason:
                finish_reason = str(res.candidates[0].finish_reason)
                error_reason = f"Finished with reason: {finish_reason}"
                if "SAFETY" in finish_reason.upper():
                    user_message = "🛡️ 생성된 콘텐츠가 안전 정책에 위배됩니다"
                    suggestions = [
                        "더 긍정적이고 안전한 주제로 변경해보세요",
                        "캐릭터 설정이나 스타일을 조정해보세요",
                    ]
                elif "MAX_TOKENS" in finish_reason.upper():
                    user_message = "⚠️ 생성 길이가 제한을 초과했습니다"
                    suggestions = ["영상 길이를 줄여보세요 (15-30초 권장)"]
                else:
                    user_message = f"⚠️ 생성이 중단되었습니다 ({finish_reason})"
                    suggestions = ["다시 시도하거나, 설정을 변경해보세요"]

            suggestion_text = " / ".join(suggestions[:2]) if suggestions else ""
            logger.error(
                "[Gemini Error] %s | Reason: %s | Suggestions: %s",
                user_message,
                error_reason,
                " | ".join(suggestions),
            )
            raise ValueError(f"{user_message} ({suggestion_text})" if suggestion_text else user_message)

        cleaned = strip_markdown_codeblock(res.text)
        scenes = json.loads(cleaned)
        scenes = normalize_scene_tags_key(scenes)

        # Guard: trim excess scenes if Gemini exceeded the duration-based limit
        scenes = trim_scenes_to_duration(scenes, request.duration)

        # Post-process scenes: warnings, tag pipeline, dialogue defense, auto-pin
        warn_script_issues(scenes)
        process_scene_tags(scenes)
        if has_two_characters:
            strip_no_humans_from_dialogue(scenes)
        auto_pin_raw_scenes(scenes, structure_lower)

        # Auto-populate character_actions from context_tags (Dialogue/Narrated Dialogue)
        if has_two_characters and (request.character_id or request.character_b_id) and db:
            from services.characters import auto_populate_character_actions

            scenes = auto_populate_character_actions(scenes, request.character_id, request.character_b_id, db)

        logger.info(f"[Storyboard] Returning {len(scenes)} scenes with negative prompts")
        for i, s in enumerate(scenes):
            logger.info(f"  Scene {i + 1} negative: {s.get('negative_prompt', 'NONE')[:80]}")
        result = {"scenes": scenes}
        if request.character_id:
            result["character_id"] = request.character_id
        if request.character_b_id:
            result["character_b_id"] = request.character_b_id
        return result
    except Exception as exc:
        # Check if it's a Gemini API quota error
        error_msg = str(exc)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.error("Gemini API quota exhausted")
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exhausted. Please try again later or check your API limits at https://aistudio.google.com/app/apikey",
            ) from exc

        logger.exception("Storyboard generation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
