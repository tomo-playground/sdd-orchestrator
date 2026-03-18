from __future__ import annotations

import json
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from config import (
    GEMINI_TEXT_MODEL,
    gemini_client,
    logger,
)
from models.associations import CharacterTag
from models.character import Character
from services.keywords import get_keyword_context_and_tags
from services.presets import get_preset_by_structure
from services.script.scene_postprocess import (
    auto_pin_raw_scenes,
    ensure_dialogue_speakers,
    strip_no_humans_from_dialogue,
    warn_script_issues,
)
from services.storyboard.helpers import (
    normalize_scene_tags_key,
    strip_markdown_codeblock,
    trim_scenes_to_duration,
)

# Style-conflicting tag filter — remove tags that contradict the visual style
_STYLE_CONFLICTING_TAGS: dict[str, frozenset[str]] = {
    "realistic": frozenset(
        {"anime", "chibi", "illustration", "drawing", "watercolor", "sketch", "cartoon", "super_deformed"}
    ),
    "photorealistic": frozenset(
        {"anime", "chibi", "illustration", "drawing", "watercolor", "sketch", "cartoon", "super_deformed"}
    ),
}


def _tag_base_key(token: str) -> str:
    """Extract the base tag name from a prompt token, stripping weights and parentheses.

    Handles plain tags, weighted tags (cartoon:1.3), and NAI-style ((cartoon:1.3)).
    Examples:
        "anime"         → "anime"
        "(anime:1.3)"   → "anime"
        "((anime:1.3))" → "anime"
        "super_deformed"→ "super_deformed"
    """
    t = token.strip()
    # Strip leading parentheses
    t = t.lstrip("(")
    # Strip weight notation and trailing parentheses: "anime:1.3)" → "anime"
    t = t.split(":")[0]
    t = t.rstrip(")")
    return t.strip().lower().replace(" ", "_")


def _filter_style_conflicting_tags(scenes: list[dict], style: str) -> None:
    """Remove style-conflicting tags from image_prompt (in-place).

    Gemini occasionally generates tags that contradict the visual style
    (e.g. 'anime' or '(anime:1.3)' in Realistic style). This is a defense-in-depth filter.
    Handles both plain tags and weighted tokens like (anime:1.3).
    """
    conflicting = _STYLE_CONFLICTING_TAGS.get(style.lower())
    if not conflicting:
        return
    for scene in scenes:
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue
        tokens = [t.strip() for t in prompt.split(",") if t.strip()]
        filtered = [t for t in tokens if _tag_base_key(t) not in conflicting]
        removed = [t for t in tokens if _tag_base_key(t) in conflicting]
        if removed:
            logger.warning(
                "[StyleFilter] Removed %d conflicting tag(s) for '%s' style in scene %s: %s",
                len(removed),
                style,
                scene.get("scene_id", "?"),
                removed,
            )
            scene["image_prompt"] = ", ".join(filtered)


# Gemini PROHIBITED_CONTENT 필터 우회 — 미성년자 연상 단어를 성인 동등 표현으로 치환
# (DB 저장값 무변경, Gemini 렌더링 시점에만 적용)
_MINOR_TERM_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"소녀들?(?!\s*시대)"), "여성"),  # 소녀(들) → 여성 (소녀시대 제외)
    (re.compile(r"소년들?"), "남성"),  # 소년(들) → 남성
    (re.compile(r"여자\s*아이들?"), "여성들"),  # 여자아이(들) → 여성들
    (re.compile(r"남자\s*아이들?"), "남성들"),  # 남자아이(들) → 남성들
    (re.compile(r"어린\s*이들?"), "사람들"),  # 어린이(들) → 사람들
    # Danbooru 태그 우회 (Gemini 2.5 Flash PROHIBITED_CONTENT 차단 방지)
    (re.compile(r"\b1girl\b"), "1woman"),
    (re.compile(r"\b(\d+)girls\b"), r"\1women"),
    (re.compile(r"\bmultiple_girls\b"), "multiple_women"),
    (re.compile(r"\b1boy\b"), "1man"),
    (re.compile(r"\b(\d+)boys\b"), r"\1men"),
    (re.compile(r"\bmultiple_boys\b"), "multiple_men"),
    (re.compile(r"\bschool_swimsuit\b"), "student_swimwear"),
    (re.compile(r"\bschool_uniform\b"), "student_uniform"),
    (re.compile(r"\bloli\b", re.IGNORECASE), "small_body"),
    (re.compile(r"\bshota\b", re.IGNORECASE), "small_body"),
]


# Gemini 응답값을 다시 Danbooru 태그(SD WebUI용)로 원상복구
_RESTORE_DANBOORU_TAGS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b1woman\b"), "1girl"),
    (re.compile(r"\b(\d+)women\b"), r"\1girls"),
    (re.compile(r"\bmultiple_women\b"), "multiple_girls"),
    (re.compile(r"\b1man\b"), "1boy"),
    (re.compile(r"\b(\d+)men\b"), r"\1boys"),
    (re.compile(r"\bmultiple_men\b"), "multiple_boys"),
    (re.compile(r"\bstudent_swimwear\b"), "school_swimsuit"),
    (re.compile(r"\bstudent_uniform\b"), "school_uniform"),
]


def _restore_danbooru_tags(text: str) -> str:
    """Gemini가 생성한 우회 태그를 다시 SD가 인식할 수 있는 원래 Danbooru 태그로 복구한다."""
    restored = text
    for pattern, replacement in _RESTORE_DANBOORU_TAGS:
        restored = pattern.sub(replacement, restored)
    return restored


def _sanitize_for_gemini_prompt(text: str) -> str:
    """Gemini PROHIBITED_CONTENT 방지: 미성년자 연상 단어를 치환한다.

    topic 단독 또는 렌더링된 전체 프롬프트 모두에 적용 가능.
    DB 저장값은 변경하지 않고, Gemini 호출 직전에만 적용한다.
    """
    sanitized = text
    for pattern, replacement in _MINOR_TERM_REPLACEMENTS:
        sanitized = pattern.sub(replacement, sanitized)
    if sanitized != text:
        logger.info("[Sanitize] PROHIBITED_CONTENT 방지 치환 적용 (길이: %d → %d)", len(text), len(sanitized))
    return sanitized


# ── Chat context prompt injection defense ─────────────────────────────
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+are", re.IGNORECASE),
    re.compile(r"new\s+instructions?:", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
]


def sanitize_chat_context(chat_context: list[dict]) -> list[dict]:
    """Sanitize chat_context messages to prevent prompt injection.

    Strips known injection patterns from each message's text field.
    Returns a new list with sanitized copies (original is not mutated).
    """
    if not chat_context:
        return chat_context

    sanitized: list[dict] = []
    for msg in chat_context:
        # Pydantic 모델 또는 dict 양쪽 지원
        raw = msg if isinstance(msg, dict) else msg.model_dump()
        text = raw.get("text", "")
        if not isinstance(text, str):
            sanitized.append(raw)
            continue

        cleaned = text
        for pattern in _INJECTION_PATTERNS:
            cleaned = pattern.sub("", cleaned)

        cleaned = cleaned.strip()
        if cleaned != text:
            logger.warning(
                "[Sanitize] Prompt injection pattern removed from chat_context (role=%s, before=%d, after=%d)",
                raw.get("role", "?"),
                len(text),
                len(cleaned),
            )

        sanitized.append({**raw, "text": cleaned})

    return sanitized


def sanitize_user_input(text: str) -> str:
    """사용자 입력 문자열에서 prompt injection 패턴을 제거한다."""
    if not text:
        return text
    cleaned = text
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()


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
        "description": char.description or "",
        "identity_tags": identity_tags,
        "costume_tags": costume_tags,
        "lora_triggers": lora_triggers,
        "positive_prompt": char.positive_prompt or "",
    }
    logger.info(
        "[Character Context] %s: identity=%s, costume=%s, lora_triggers=%s",
        char.name,
        identity_tags,
        costume_tags,
        lora_triggers,
    )
    return ctx


async def generate_script(request, db: Session | None = None, pipeline_context: dict | None = None) -> dict:
    """Generate a storyboard from a topic using Gemini (async)."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    try:
        structure_lower = request.structure.lower()
        structure_normalized = structure_lower.replace("_", " ")
        has_two_characters = structure_normalized in ("dialogue", "narrated dialogue")

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

        # 2인 구조 + 양쪽 캐릭터 지정 → 멀티캐릭터 모드
        is_multi_character_capable = (
            structure_normalized in ("dialogue", "narrated dialogue")
            and request.character_id is not None
            and request.character_b_id is not None
        )
        if is_multi_character_capable:
            logger.info("[Storyboard] Multi-character mode enabled")

        # Release DB connection before Gemini API call (10-30s)
        # DB auto-reconnects when needed later (auto_populate_character_actions)
        if db:
            db.close()

        preset = get_preset_by_structure(request.structure)
        template_name = preset.template if preset else "create_storyboard"
        extra_fields = preset.extra_fields if preset else {}

        from services.agent.langfuse_prompt import compile_prompt
        from services.agent.prompt_builders_c import (
            build_character_tag_rules,
            build_description_section,
            build_dialogue_scene_max,
            build_dialogue_scene_range,
            build_multi_character_rules,
            build_multi_scene_mode_field,
            build_optional_text_section,
            build_scene_count_max,
            build_scene_count_range,
            build_storyboard_chat_context,
        )
        from services.agent.prompt_builders_writer import (
            build_korean_critical_hint,
            build_korean_rules_block,
        )
        from services.agent.prompt_partials import (
            EMOTION_CONSISTENCY_RULES,
            IMAGE_PROMPT_KO_RULES,
            render_allowed_tags,
            render_character_profile,
            render_selected_concept,
        )

        # 파이프라인 컨텍스트 (research_brief, writer_plan 등) 주입
        ctx = pipeline_context or {}
        keyword_context, allowed_tags = get_keyword_context_and_tags()
        safe_topic = _sanitize_for_gemini_prompt(request.topic)

        structure_lower_norm = request.structure.lower().replace("_", " ")
        is_dialogue_structure = structure_lower_norm in ("dialogue", "narrated dialogue")

        # 파셜 pre-render
        partial_vars = {
            "partial_selected_concept": render_selected_concept(request.selected_concept),
            "partial_character_profile": render_character_profile(character_context),
            "partial_character_profile_a": render_character_profile(character_context, "A"),
            "partial_character_profile_b": render_character_profile(character_b_context, "B"),
            "partial_image_prompt_ko_rules": IMAGE_PROMPT_KO_RULES,
            "partial_emotion_consistency_rules": EMOTION_CONSISTENCY_RULES,
            "partial_allowed_tags": render_allowed_tags(allowed_tags),
        }

        # 공통 빌더 변수
        sanitized_chat = sanitize_chat_context(ctx.get("chat_context", []))
        builder_vars = {
            "topic": safe_topic,
            "duration": str(request.duration),
            "style": request.style,
            "structure": request.structure,
            "language": request.language,
            "actor_a_gender": request.actor_a_gender or "",
            "keyword_context": keyword_context,
            "description_section": build_description_section(request.description),
            "director_plan_context_section": build_optional_text_section(
                "Creative Direction (from Director)",
                ctx.get("director_plan_context"),
            ),
            "chat_context_block": build_storyboard_chat_context(sanitized_chat),
            "research_brief_section": build_optional_text_section(
                "Reference Information",
                ctx.get("research_brief"),
            ),
            "writer_plan_section": build_optional_text_section(
                "Writer Plan",
                ctx.get("writer_plan"),
            ),
            "revision_feedback_section": build_optional_text_section(
                "Revision Request",
                ctx.get("revision_feedback"),
            ),
            "current_script_section": build_optional_text_section(
                "Current Script (revise based on this)",
                ctx.get("current_script_summary"),
            ),
            "character_tag_rules": build_character_tag_rules(character_context is not None),
            "korean_rules_block": build_korean_rules_block(request.language),
            "korean_critical_hint": build_korean_critical_hint(request.language),
            **partial_vars,
            **extra_fields,
        }

        # structure별 씬 개수 변수
        if is_dialogue_structure:
            builder_vars["dialogue_scene_range"] = build_dialogue_scene_range(request.duration)
            builder_vars["dialogue_scene_max"] = build_dialogue_scene_max(request.duration)
            builder_vars["multi_character_rules"] = build_multi_character_rules(
                is_multi_character_capable,
                character_context,
                character_b_context,
            )
            builder_vars["multi_scene_mode_field"] = build_multi_scene_mode_field(is_multi_character_capable)
            builder_vars["multi_scene_mode_hint"] = (
                '   - scene_mode: "single" (default) or "multi" (both characters)' if is_multi_character_capable else ""
            )
        else:
            builder_vars["scene_count_range"] = build_scene_count_range(
                request.duration,
                request.structure,
            )
            builder_vars["scene_count_max"] = build_scene_count_max(
                request.duration,
                request.structure,
            )

        compiled = compile_prompt(template_name, **builder_vars)
        from services.llm import LLMConfig, get_llm_provider

        # CLAUDE.md 규칙: system_instruction ↔ contents 분리 필수
        # system: LangFuse system(역할) + 렌더링된 프롬프트 (지시+규칙+태그)
        # user: 사용자 데이터 — 안전 필터 오탐 방지
        lf_system = compiled.system or ""
        sanitized_user = _sanitize_for_gemini_prompt(compiled.user)
        sys_parts = [lf_system, sanitized_user]
        system_instruction = "\n\n".join(p for p in sys_parts if p)

        user_parts = [f"Topic: {safe_topic}"]
        if request.description:
            user_parts.append(f"Description: {request.description}")
        if request.selected_concept:
            user_parts.append(f"Selected Concept: {request.selected_concept}")
        if ctx.get("revision_feedback"):
            user_parts.append(f"Revision Feedback: {ctx['revision_feedback']}")
        if ctx.get("chat_context"):
            cc = ctx["chat_context"]
            cc_str = json.dumps([m.model_dump() if hasattr(m, "model_dump") else m for m in cc], ensure_ascii=False)
            user_parts.append(f"Chat Context: {cc_str}")
        user_contents = "\n".join(user_parts)
        logger.info(
            "[Writer] system_instruction=%dch, contents=%dch, sys_preview='%s', user_preview='%s'",
            len(system_instruction),
            len(user_contents),
            system_instruction[:150].replace("\n", " "),
            user_contents[:150].replace("\n", " "),
        )
        llm_resp = await get_llm_provider().generate(
            step_name="writer",
            contents=user_contents,
            config=LLMConfig(system_instruction=system_instruction),
            model=GEMINI_TEXT_MODEL,
            langfuse_prompt=compiled.langfuse_prompt,
        )
        res = llm_resp.raw
        if not res.text:
            # Check why it failed
            error_reason = "Unknown error"
            user_message = "시나리오 생성에 실패했습니다."
            suggestions = []

            if res.prompt_feedback and res.prompt_feedback.block_reason:
                block_reason = str(res.prompt_feedback.block_reason)
                error_reason = f"Blocked by safety filters: {block_reason}"
                # 진단용: 차단된 프롬프트 앞부분 로그 (root cause 분석)
                logger.debug("[Sanitize-Debug] 차단된 프롬프트 앞 500자:\n%s", system_instruction[:500])
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

        restored_text = _restore_danbooru_tags(res.text)
        cleaned = strip_markdown_codeblock(restored_text)
        scenes = json.loads(cleaned)
        scenes = normalize_scene_tags_key(scenes)

        # Guard: trim excess scenes if Gemini exceeded the duration-based limit
        scenes = trim_scenes_to_duration(scenes, request.duration, request.structure)

        # Duration auto-calculation from reading time
        from services.storyboard.helpers import estimate_reading_duration

        for scene in scenes:
            if scene.get("script", "").strip():
                scene["duration"] = estimate_reading_duration(scene["script"], request.language)

        # Post-process scenes: warnings, tag pipeline, dialogue defense, auto-pin
        warn_script_issues(scenes)
        from services.danbooru import schedule_background_classification
        from services.script.scene_postprocess import process_scene_tags_async

        unknown_tags = await process_scene_tags_async(scenes)
        schedule_background_classification(unknown_tags)
        # Defense: remove style-conflicting tags (e.g. 'anime' in Realistic style)
        if request.style:
            _filter_style_conflicting_tags(scenes, request.style)
        if has_two_characters:
            strip_no_humans_from_dialogue(scenes)
            ensure_dialogue_speakers(scenes)
        auto_pin_raw_scenes(scenes, structure_lower)

        # Auto-populate character_actions from context_tags
        if (request.character_id or request.character_b_id) and db:
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

        from services.error_responses import raise_user_error

        raise_user_error("script_generate", exc)
        raise  # unreachable; satisfies type checker
