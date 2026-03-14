"""Prompt preparation for generation pipeline.

Extracted from generation.py for module size compliance.
Contains prompt routing, narrator defense, and IP-Adapter reverse lookup.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from config import DEFAULT_SCENE_NEGATIVE_PROMPT, FACEID_SUPPRESS_TAGS, FACEID_SUPPRESS_WEIGHT, logger
from schemas import PromptRewriteRequest, SceneGenerateRequest
from services.generation_style import apply_style_profile_to_prompt
from services.image_generation_core import compose_scene_with_style
from services.keywords.db_cache import TagAliasCache
from services.prompt import normalize_prompt_tokens, split_prompt_tokens
from services.prompt.prompt import rewrite_prompt

if TYPE_CHECKING:
    from services.generation_context import GenerationContext

_PERSON_INDICATORS = frozenset({"1girl", "1boy", "2girls", "2boys", "3girls", "3boys", "solo", "couple", "group"})

# Tags that indicate the scene should use a plain/abstract background → skip env reference injection
_SKIP_ENV_REF_TAGS = frozenset(
    {
        "simple_background",
        "white_background",
        "transparent_background",
        "abstract_background",
        "black_background",
        "grey_background",
        "monochrome_background",
    }
)


def _collect_context_tags(context_tags: dict) -> list[str]:
    """Flatten context_tags dict into a tag list."""
    tags: list[str] = []
    for key in ("expression", "pose", "action", "environment", "mood"):
        val = context_tags.get(key)
        if isinstance(val, list):
            tags.extend(val)
    for key in ("gaze", "camera"):
        val = context_tags.get(key)
        if isinstance(val, str) and val:
            tags.append(val)
    return tags


def _merge_context_tags(request: SceneGenerateRequest) -> None:
    """Merge request.context_tags into request.prompt (prepend)."""
    if not request.context_tags:
        return
    extra = _collect_context_tags(request.context_tags)
    if extra:
        request.prompt = f"{', '.join(extra)}, {request.prompt}"
        logger.info("📎 [ContextTags] Merged %d tags into prompt: %s", len(extra), extra)


# ── Style LoRA resolution ───────────────────────────────────────────


def _resolve_style_loras(storyboard_id: int | None, db) -> list[dict]:
    """Resolve style LoRAs from DB config cascade for prompt engine.

    Delegates to image_generation_core.resolve_style_loras_from_storyboard (SSOT).
    """
    if not storyboard_id:
        return []
    try:
        from services.image_generation_core import resolve_style_loras_from_storyboard

        return resolve_style_loras_from_storyboard(storyboard_id, db)
    except Exception as e:
        logger.error("❌ [_resolve_style_loras] Error: %s", e)
        return []


def _resolve_effective_character_b_id(
    request: SceneGenerateRequest, db
) -> tuple[int | None, list[str]]:
    """Resolve character_b_id only when scene_mode='multi'.

    Returns (effective_b_id, warnings).
    """
    if not request.scene_id:
        return None, []
    from models.scene import Scene

    scene = db.query(Scene).filter(Scene.id == request.scene_id, Scene.deleted_at.is_(None)).first()
    if not scene or scene.scene_mode != "multi":
        return None, []

    if not request.character_b_id:
        logger.warning(
            "⚠️ [Multi-Char] scene_mode=multi but character_b_id missing "
            "(scene_id=%d) — falling back to single-character generation",
            request.scene_id,
        )
        return None, ["multi 씬이지만 캐릭터 B 정보가 없어 single로 생성됩니다."]

    # 동일 ID 방어
    if request.character_b_id == request.character_id:
        logger.warning("👥 [Multi-Char] character_b_id == character_id (%d), ignoring", request.character_id)
        return None, []

    logger.debug("👥 [Multi-Char] scene_mode=multi, using character_b_id=%d", request.character_b_id)
    return request.character_b_id, []


# ── Narrator defense ────────────────────────────────────────────────


def _inject_narrator_defense(request: SceneGenerateRequest) -> None:
    """Auto-inject no_humans for background scenes without person indicators."""
    if request.character_id or request.prompt_pre_composed:
        return
    prompt_norm = request.prompt.lower().replace(" ", "_")
    has_person = any(ind in prompt_norm for ind in _PERSON_INDICATORS)
    if not has_person and "no_humans" not in prompt_norm:
        request.prompt = f"no_humans, {request.prompt}"
        logger.debug("🚫 [Narrator] Auto-injected no_humans for background scene")


def _append_narrator_negative(request: SceneGenerateRequest) -> None:
    """Append person-exclusion tags to negative prompt for narrator scenes."""
    if "no_humans" not in request.prompt:
        return
    from config import NARRATOR_NEGATIVE_PROMPT_EXTRA

    request.negative_prompt = f"{request.negative_prompt}, {NARRATOR_NEGATIVE_PROMPT_EXTRA}"
    logger.debug("🚫 [Narrator Negative] Appended person-exclusion tags to negative prompt")


# ── Prompt handlers ─────────────────────────────────────────────────


def _handle_pre_composed(request: SceneGenerateRequest, db) -> tuple[str, list[str]]:
    """Handle prompt_pre_composed=True: style profile + safety-net LoRA injection.

    DEPRECATED: Frontend should send raw prompt + context_tags instead.
    Backend handles prompt composition directly via _handle_character_scene().
    """
    logger.warning("⚠️ [DEPRECATED] prompt_pre_composed=True received. Use raw prompt + context_tags instead.")
    has_lora_tags = "<lora:" in request.prompt
    request.prompt, request.negative_prompt = apply_style_profile_to_prompt(
        request.prompt,
        request.negative_prompt or "",
        request.storyboard_id,
        db,
        skip_loras=has_lora_tags,
    )
    # Safety net: if still no LoRA tags, resolve from DB and append
    if "<lora:" not in request.prompt and request.storyboard_id:
        _inject_missing_style_loras(request, db)
    logger.debug("🎨 [V3 Engine] Using pre-composed prompt (prompt_pre_composed=True)")
    return request.prompt, []


def _inject_missing_style_loras(request: SceneGenerateRequest, db) -> None:
    """Inject style LoRAs from DB when pre-composed prompt lacks them."""
    style_loras = _resolve_style_loras(request.storyboard_id, db)
    if not style_loras:
        return
    lora_parts = []
    for lr in style_loras:
        lora_parts.append(f"<lora:{lr['name']}:{lr['weight']}>")
        for tw in lr.get("trigger_words", []):
            if tw.lower() not in request.prompt.lower():
                lora_parts.append(tw)
    request.prompt = f"{request.prompt}, {', '.join(lora_parts)}"
    logger.info(
        "🔧 [V3 Engine] Injected missing style LoRAs into pre-composed prompt: %s",
        [lr["name"] for lr in style_loras],
    )


def _resolve_background(request: SceneGenerateRequest, db) -> tuple[list[str] | None, int | None, float | None]:
    """Resolve background tags and ControlNet reference from background_id."""
    if not request.background_id:
        return None, None, None
    from models.background import Background

    bg = db.query(Background).filter(Background.id == request.background_id).first()
    if not bg:
        logger.warning("⚠️ [Background] background_id=%d not found", request.background_id)
        return None, None, None

    logger.info(
        "🏠 [Background] Loaded '%s': tags=%s, image_asset_id=%s, weight=%.2f",
        bg.name,
        bg.tags,
        bg.image_asset_id,
        bg.weight,
    )
    return bg.tags or None, bg.image_asset_id, bg.weight


def _handle_character_scene(
    request: SceneGenerateRequest, db, effective_b_id: int | None, *, style_loras: list[dict] | None = None
) -> tuple[str, list[str]]:
    """Handle raw prompt + character: prompt composition with style LoRAs."""
    _merge_context_tags(request)
    if style_loras is None:
        style_loras = _resolve_style_loras(request.storyboard_id, db)
    logger.debug("🎨 [V3 Engine] Path B: style_loras=%s (from DB)", [lr.get("name") for lr in style_loras])
    bg_tags, bg_image_asset_id, bg_weight = _resolve_background(request, db)
    cleaned_prompt, request.negative_prompt, compose_warnings = compose_scene_with_style(
        raw_prompt=request.prompt,
        negative_prompt=request.negative_prompt or "",
        character_id=request.character_id,
        storyboard_id=request.storyboard_id,
        style_loras=style_loras,
        db=db,
        scene_id=request.scene_id,
        character_b_id=effective_b_id,
        background_tags=bg_tags,
    )

    # Check if scene requires a simple/abstract background (token-exact match)
    prompt_tokens = {t.strip().lower().replace(" ", "_") for t in cleaned_prompt.split(",") if t.strip()}
    should_skip_env_ref = bool(_SKIP_ENV_REF_TAGS & prompt_tokens)

    # Auto-set environment reference from background image
    if bg_image_asset_id and not request.environment_reference_id:
        if should_skip_env_ref:
            logger.info("🚫 [Background] Skipped environment reference injection due to abstract/simple background tag")
        else:
            request.environment_reference_id = bg_image_asset_id
            request.environment_reference_weight = bg_weight or 0.15
            logger.info(
                "🏠 [Background] Auto-set environment_reference_id=%d (weight=%.2f)",
                bg_image_asset_id,
                bg_weight or 0.15,
            )

    logger.debug("🎨 [V3 Engine] Composed prompt for character %d", request.character_id)
    return cleaned_prompt, compose_warnings


def _handle_background_scene(
    request: SceneGenerateRequest, db, *, style_loras: list[dict] | None = None
) -> tuple[str, list[str]]:
    """Handle narrator (no_humans) scene: background composition."""
    _merge_context_tags(request)
    if style_loras is None:
        style_loras = _resolve_style_loras(request.storyboard_id, db)
    bg_tags, _, _ = _resolve_background(request, db)
    cleaned_prompt, request.negative_prompt, compose_warnings = compose_scene_with_style(
        raw_prompt=request.prompt,
        negative_prompt=request.negative_prompt or "",
        character_id=None,
        storyboard_id=request.storyboard_id,
        style_loras=style_loras,
        db=db,
        scene_id=request.scene_id,
        background_tags=bg_tags,
    )
    logger.debug("🎨 [V3 Engine] Background scene composition for Narrator")
    return cleaned_prompt, compose_warnings


def _handle_fallback(request: SceneGenerateRequest, db) -> tuple[str, list[str]]:
    """Handle no character, no no_humans: full style profile, no V3."""
    request.prompt, request.negative_prompt = apply_style_profile_to_prompt(
        request.prompt, request.negative_prompt or "", request.storyboard_id, db
    )
    return request.prompt, []


def _dispatch_prompt_route(request, db, character_obj, effective_b_id, *, style_loras=None) -> tuple[str, list[str]]:
    """Route to appropriate prompt handler based on request state.

    Note: prompt_pre_composed path is DEPRECATED.
    """
    if request.prompt_pre_composed:
        return _handle_pre_composed(request, db)
    elif request.character_id and character_obj:
        return _handle_character_scene(request, db, effective_b_id, style_loras=style_loras)
    elif "no_humans" in request.prompt.lower().replace(" ", "_"):
        return _handle_background_scene(request, db, style_loras=style_loras)
    else:
        return _handle_fallback(request, db)


# ── IP-Adapter reverse lookup ───────────────────────────────────────


def _handle_ip_adapter_reverse_lookup(request: SceneGenerateRequest, db, ctx: GenerationContext) -> None:
    """Reverse lookup: IP-Adapter reference name → character_id + prompt recomposition.

    Forward IP-Adapter auto-enable is handled by CharacterConsistencyResolver.
    Reads/writes ctx.prompt, ctx.character, ctx.warnings.
    """
    if ctx.character:
        return

    from models import Character

    if request.use_ip_adapter and request.ip_adapter_reference:
        char = (
            db.query(Character)
            .filter(Character.name == request.ip_adapter_reference, Character.deleted_at.is_(None))
            .first()
        )
        if char:
            request.character_id = char.id
            logger.info(
                "📊 [Activity Log] Auto-set character_id=%d from IP-Adapter reference '%s'",
                char.id,
                request.ip_adapter_reference,
            )
            style_loras = _resolve_style_loras(request.storyboard_id, db)
            ctx.prompt, request.negative_prompt, compose_warnings = compose_scene_with_style(
                raw_prompt=request.prompt,
                negative_prompt=request.negative_prompt or "",
                character_id=char.id,
                storyboard_id=request.storyboard_id,
                style_loras=style_loras,
                db=db,
                scene_id=request.scene_id,
                character_b_id=ctx.character_b_id,
            )
            ctx.warnings.extend(compose_warnings)
            ctx.character = char
            logger.info("🎨 [V3 Engine] Composed prompt for auto-populated character %d", char.id)
            return

    if not request.character_id and "no_humans" not in request.prompt.lower().replace(" ", "_"):
        ctx.prompt = normalize_prompt_tokens(request.prompt)


# ── Post-processing: Safe Tags + Auto Rewrite ─────────────────────


def _apply_safe_tag_replacement(prompt: str, db) -> str:
    """Replace risky tags using TagAliasCache. LoRA tags are preserved.

    Idempotent: already-replaced tags pass through unchanged.
    """

    TagAliasCache.initialize(db)
    tokens = split_prompt_tokens(prompt)
    result: list[str] = []
    for token in tokens:
        if token.startswith("<lora:") or token.startswith("BREAK"):
            result.append(token)
            continue
        replacement = TagAliasCache.get_replacement(token.strip())
        if replacement is ...:
            result.append(token)
        elif replacement is None:
            logger.info("[SafeTags] Dropped risky tag: %s", token)
            continue
        else:
            if replacement != token.strip():
                logger.info("[SafeTags] Replaced: %s → %s", token.strip(), replacement)
            result.append(replacement)
    return ", ".join(result)


def _apply_auto_rewrite(prompt: str) -> str:
    """Rewrite prompt via Gemini, preserving LoRA/identity tokens.

    Falls back to original prompt on any error (silent fallback).
    """

    tokens = split_prompt_tokens(prompt)
    lora_tokens = [t for t in tokens if t.startswith("<lora:")]
    scene_tokens = [t for t in tokens if not t.startswith("<lora:")]

    base_prompt = ", ".join(lora_tokens) if lora_tokens else ""
    scene_prompt = ", ".join(scene_tokens)

    try:
        rewrite_req = PromptRewriteRequest(
            base_prompt=base_prompt or scene_prompt,
            scene_prompt=scene_prompt,
            mode="compose",
        )
        result = rewrite_prompt(rewrite_req)
        rewritten = result.get("prompt", "")
        if rewritten:
            # Defense: re-inject LoRA tokens if Gemini dropped them
            if lora_tokens:
                for lt in lora_tokens:
                    if lt not in rewritten:
                        rewritten = f"{rewritten}, {lt}"
            logger.info("[AutoRewrite] Prompt rewritten by Gemini (%d→%d chars)", len(prompt), len(rewritten))
            return rewritten
    except Exception as e:
        logger.warning("[AutoRewrite] Gemini rewrite failed, using original: %s", e)
    return prompt


# ── Main orchestrator ───────────────────────────────────────────────


def prepare_prompt(request: SceneGenerateRequest, db, ctx: GenerationContext) -> None:
    """Orchestrator: prepare the final prompt via style profile + prompt composition.

    Routes to specialized handlers based on request state.
    Writes results to ctx (prompt, negative_prompt, character, consistency, warnings).
    """

    from sqlalchemy.orm import joinedload

    from models import Character
    from models.group import Group

    character_obj = (
        db.query(Character)
        .options(joinedload(Character.group).joinedload(Group.style_profile))
        .filter(Character.id == request.character_id)
        .first()
    )
    effective_b_id, b_warnings = _resolve_effective_character_b_id(request, db)
    ctx.warnings.extend(b_warnings)

    # Resolve character consistency strategy
    style_profile_loras = _resolve_style_loras(request.storyboard_id, db) if request.storyboard_id else []
    strategy = _resolve_consistency(request, db, character_obj, style_profile_loras)

    # Resolve StyleContext for generation parameter overrides
    from services.style_context import resolve_style_context

    style_ctx = resolve_style_context(request.storyboard_id, db) if request.storyboard_id else None

    # Store in context
    ctx.consistency = strategy
    ctx.style_loras = style_profile_loras
    ctx.character = character_obj
    ctx.character_b_id = effective_b_id
    ctx.style_context = style_ctx

    # Apply strategy to request for backward compat
    _apply_strategy_to_request(strategy, request)

    logger.debug(
        "🔀 [Prompt Route] pre_composed=%s, character_id=%s, character_found=%s, quality=%s",
        request.prompt_pre_composed,
        request.character_id,
        character_obj is not None,
        strategy.quality_score,
    )

    _inject_narrator_defense(request)

    # Defense: strip no_humans when character_id is set (Gemini generation error)
    if request.character_id and "no_humans" in request.prompt.lower().replace(" ", "_"):
        original = request.prompt
        request.prompt = ", ".join(
            t.strip() for t in request.prompt.split(",") if t.strip().lower().replace(" ", "_").strip() != "no_humans"
        )
        logger.warning(
            "⚠️ [Prompt Defense] Stripped no_humans from character scene (character_id=%d): '%s' → '%s'",
            request.character_id,
            original[:80],
            request.prompt[:80],
        )

    cleaned_prompt, compose_warnings = _dispatch_prompt_route(
        request,
        db,
        character_obj,
        effective_b_id,
        style_loras=style_profile_loras or None,
    )

    # Store composed prompt, then run reverse lookup (may overwrite ctx.prompt/character)
    ctx.prompt = cleaned_prompt
    _handle_ip_adapter_reverse_lookup(request, db, ctx)

    # Post-processing: Safe Tags → Auto Rewrite (before FaceID suppression)
    if request.auto_replace_risky_tags:
        ctx.prompt = _apply_safe_tag_replacement(ctx.prompt, db)
    if request.auto_rewrite_prompt:
        ctx.prompt = _apply_auto_rewrite(ctx.prompt)

    # Phase 3-B: Suppress face tags when FaceID is active
    ctx.prompt = suppress_face_tags_for_faceid(ctx.prompt, strategy.ip_adapter_model)

    _append_narrator_negative(request)

    ctx.negative_prompt = request.negative_prompt or DEFAULT_SCENE_NEGATIVE_PROMPT

    # Merge character-specific negative prompts (scene_negative + common_negative)
    _chars_for_neg = [character_obj]
    if effective_b_id:
        from models import Character as _CharModel

        _char_b = db.query(_CharModel).filter(
            _CharModel.id == effective_b_id,
            _CharModel.deleted_at.is_(None),
        ).first()
        _chars_for_neg.append(_char_b)
    for _ch in _chars_for_neg:
        if not _ch:
            continue
        if _ch.negative_prompt:
            ctx.negative_prompt = f"{ctx.negative_prompt}, {_ch.negative_prompt}"

    ctx.warnings.extend(compose_warnings)
    ctx.warnings.extend(strategy.warnings)

    _debug_verify_loras(ctx)


def _resolve_consistency(request, db, character_obj, style_profile_loras):
    """Resolve character consistency strategy via CharacterConsistencyResolver."""
    from services.character_consistency import CharacterConsistencyResolver, ConsistencyRequest

    resolver = CharacterConsistencyResolver(db)
    return resolver.resolve(
        character_obj,
        style_profile_loras=style_profile_loras or None,
        req=ConsistencyRequest(
            use_ip_adapter=request.use_ip_adapter,
            ip_adapter_reference=request.ip_adapter_reference,
            ip_adapter_weight=request.ip_adapter_weight,
            use_reference_only=request.use_reference_only,
            reference_only_weight=request.reference_only_weight,
        ),
    )


def _apply_strategy_to_request(strategy, request) -> None:
    """Apply resolved strategy back to request for backward compat."""
    if strategy.ip_adapter_enabled:
        request.use_ip_adapter = True
        request.ip_adapter_reference = strategy.ip_adapter_reference
        request.ip_adapter_weight = strategy.ip_adapter_weight
    if strategy.reference_only_enabled != request.use_reference_only:
        request.use_reference_only = strategy.reference_only_enabled


def _debug_verify_loras(ctx: GenerationContext) -> None:
    """Debug: verify LoRA tags in final prompt.

    Background/narrator scenes (no character) legitimately lack LoRA tags,
    so we log at DEBUG instead of WARNING for those cases.
    """
    lora_tags_found = re.findall(r"<lora:[^>]+>", ctx.prompt)
    if lora_tags_found:
        logger.debug("✅ [LoRA Check] %d LoRA tags in prompt: %s", len(lora_tags_found), lora_tags_found)
    elif not ctx.character:
        logger.debug("ℹ️ [LoRA Check] No <lora:> tags — background/narrator scene (expected)")
    else:
        logger.warning("⚠️ [LoRA Check] No <lora:> tags found in cleaned prompt!")


def suppress_face_tags_for_faceid(prompt: str, ip_adapter_model: str | None) -> str:
    """Suppress face feature tags when FaceID mode is active.

    FaceID uses InsightFace embeddings for identity, so explicit face tags
    (hair color, eye color) can conflict. This weakens them to low weight.

    Args:
        prompt: Current generation prompt
        ip_adapter_model: IP-Adapter model type (only "faceid" triggers suppression)

    Returns:
        Modified prompt with face tags suppressed, or original if not faceid
    """
    if ip_adapter_model != "faceid":
        return prompt

    tokens = [t.strip() for t in prompt.split(",")]
    modified = []
    suppressed = []

    for token in tokens:
        if not token:
            continue
        # Skip LoRA tags and already weighted tokens
        if token.startswith("<lora:") or token.startswith("("):
            modified.append(token)
            continue
        # Check if bare tag matches suppress list
        bare = token.strip().replace(" ", "_").lower()
        # Handle weight notation: "tag:1.2" → "tag"
        bare_no_weight = bare.split(":")[0].strip("()")
        if bare_no_weight in FACEID_SUPPRESS_TAGS:
            modified.append(f"({bare_no_weight}:{FACEID_SUPPRESS_WEIGHT})")
            suppressed.append(bare_no_weight)
        else:
            modified.append(token)

    if suppressed:
        logger.info(
            "🧬 [FaceID] Suppressed %d face tags: %s → weight=%.1f",
            len(suppressed),
            suppressed,
            FACEID_SUPPRESS_WEIGHT,
        )

    return ", ".join(modified)
