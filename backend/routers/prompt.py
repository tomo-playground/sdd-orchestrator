"""Prompt manipulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import cap_style_lora_weight, logger
from database import get_db
from schemas import (
    EditPromptRequest,
    EditPromptResponse,
    NegativePreviewRequest,
    NegativePreviewResponse,
    PromptComposeRequest,
    PromptComposeResponse,
    PromptSplitRequest,
    TranslateKoRequest,
    TranslateKoResponse,
)
from services.generation_prompt import _collect_context_tags
from services.prompt import (
    detect_scene_complexity,
    split_prompt_example,
    split_prompt_tokens,
)
from services.prompt.ko_translator import translate_ko_to_prompt
from services.prompt.prompt_editor import edit_prompt_with_instruction
from services.prompt.service import PromptService

service_router = APIRouter(prefix="/prompt", tags=["prompt"])
admin_router = APIRouter(prefix="/prompt", tags=["prompt-admin"])


def _convert_loras(loras: list | None) -> list[dict] | None:
    """Convert PromptComposeLoRA list to style_loras dicts."""
    if not loras:
        return None
    return [
        {
            "name": lora.name,
            "weight": lora.weight,
            "trigger_words": lora.trigger_words or [],
        }
        for lora in loras
    ]


def _compose_negative_preview(
    storyboard_id: int | None,
    character_id: int | None,
    character_b_id: int | None,
    scene_negative: str,
    db: Session,
) -> tuple[str, list[dict]]:
    """Compose negative prompt preview with per-source tracking.

    Reuses the same logic as image_generation_core.compose_scene_with_style:
      1. StyleProfile: default_negative + negative_embeddings
      2. Character(s): custom_negative_prompt + recommended_negative
      3. Scene: user-entered negative_prompt

    Returns: (final_negative, sources_list)
    """
    from models.character import Character
    from services.prompt import split_prompt_tokens
    from services.prompt.prompt import normalize_negative_prompt
    from services.style_context import resolve_style_context

    sources: list[dict] = []
    parts: list[str] = []

    # 1. StyleProfile negative
    ctx = resolve_style_context(storyboard_id, db) if storyboard_id else None
    if ctx:
        style_tokens: list[str] = []
        seen_lower: set[str] = set()
        for token_source in [
            split_prompt_tokens(ctx.default_negative) if ctx.default_negative else [],
            ctx.negative_embeddings or [],
        ]:
            for t in token_source:
                if t.lower() not in seen_lower:
                    seen_lower.add(t.lower())
                    style_tokens.append(t)
        if style_tokens:
            sources.append({"source": "style_profile", "tokens": style_tokens})
            parts.append(", ".join(style_tokens))

    # 2. Character negative (both chars for multi-character scenes)
    for cid in [character_id, character_b_id]:
        if not cid:
            continue
        char = db.query(Character).filter(Character.id == cid).first()
        if not char:
            continue
        char_tokens: list[str] = []
        if char.custom_negative_prompt:
            char_tokens.extend(split_prompt_tokens(char.custom_negative_prompt))
        if char.recommended_negative:
            char_tokens.extend(char.recommended_negative)
        if char_tokens:
            sources.append({"source": f"character:{char.name}", "tokens": char_tokens})
            parts.append(", ".join(char_tokens))

    # 3. Scene-level negative
    if scene_negative and scene_negative.strip():
        scene_tokens = split_prompt_tokens(scene_negative)
        if scene_tokens:
            sources.append({"source": "scene", "tokens": scene_tokens})
            parts.append(", ".join(scene_tokens))

    final = normalize_negative_prompt(", ".join(parts)) if parts else ""
    return final, sources


@service_router.post("/negative-preview", response_model=NegativePreviewResponse)
async def negative_preview(
    request: NegativePreviewRequest,
    db: Session = Depends(get_db),
):
    """Compose negative prompt preview (lightweight, no character_id required).

    Returns composed negative from StyleProfile + Character + Scene sources.
    """
    scene_negative = ""
    if request.scene_id:
        from models.scene import Scene

        scene_row = db.query(Scene).filter(Scene.id == request.scene_id, Scene.deleted_at.is_(None)).first()
        if scene_row:
            scene_negative = scene_row.negative_prompt or ""

    neg_prompt, neg_sources = _compose_negative_preview(
        storyboard_id=request.storyboard_id,
        character_id=request.character_id,
        character_b_id=request.character_b_id,
        scene_negative=scene_negative,
        db=db,
    )

    return {"negative_prompt": neg_prompt, "negative_sources": neg_sources}


@service_router.post("/translate-ko", response_model=TranslateKoResponse)
def translate_ko_endpoint(
    request: TranslateKoRequest,
    db: Session = Depends(get_db),
):
    """Translate Korean scene description to Danbooru-style image prompt."""
    result = translate_ko_to_prompt(
        ko_text=request.ko_text,
        current_prompt=request.current_prompt,
        character_id=request.character_id,
        db=db,
    )
    return result


@service_router.post("/edit-prompt", response_model=EditPromptResponse)
def edit_prompt_endpoint(
    request: EditPromptRequest,
    db: Session = Depends(get_db),
):
    """Edit prompt tags based on a natural language instruction."""
    result = edit_prompt_with_instruction(
        current_prompt=request.current_prompt,
        instruction=request.instruction,
        character_id=request.character_id,
        db=db,
    )
    return result


@admin_router.post("/split")
async def split_prompt_endpoint(request: PromptSplitRequest):
    logger.info("📥 [Prompt Split Req] %s", request.model_dump())
    return split_prompt_example(request)


@service_router.post("/compose", response_model=PromptComposeResponse)
async def compose_prompt(
    request: PromptComposeRequest,
    db: Session = Depends(get_db),
):
    """Compose a prompt using 12-Layer engine.

    When character_id is provided, uses PromptService with full
    character tags, LoRA triggers, and gender enhancement from DB.
    Otherwise uses PromptBuilder.compose() for generic composition.

    Accepts optional base_prompt (quality tags) and context_tags
    (scene context like expression, gaze, pose) which are merged
    into the token list before prompt composition.
    """
    logger.info(
        "📥 [Prompt Compose] character_id=%s, %d tokens, loras=%s",
        request.character_id,
        len(request.tokens),
        [lora.name for lora in (request.loras or [])],
    )

    try:
        # 1. Merge context_tags + scene tokens (character data loaded from DB via character_id)
        all_tokens: list[str] = []
        if request.context_tags:
            all_tokens.extend(_collect_context_tags(request.context_tags))
        all_tokens.extend(request.tokens)

        # 1b. Inject Background location tags (Stage BG → deduped)
        if request.background_id:
            from models.background import Background

            bg = db.query(Background).filter(Background.id == request.background_id).first()
            if bg and bg.tags:
                from services.prompt.prompt import merge_tags_dedup

                all_tokens = merge_tags_dedup(all_tokens, bg.tags)

        # 2. Resolve style LoRAs: request > DB (storyboard → group → style_profile)
        style_loras = _convert_loras(request.loras)
        if not style_loras and request.storyboard_id:
            from services.image_generation_core import resolve_style_loras_from_storyboard

            style_loras = resolve_style_loras_from_storyboard(request.storyboard_id, db)
            logger.info(
                "🎨 [Prompt Compose] Resolved %d style LoRAs from storyboard %d",
                len(style_loras) if style_loras else 0,
                request.storyboard_id,
            )

        # 3. Resolve effective character_b_id (only for scene_mode="multi")
        effective_b_id = None
        if request.character_b_id and request.scene_id:
            from models.scene import Scene

            scene = db.query(Scene).filter(Scene.id == request.scene_id, Scene.deleted_at.is_(None)).first()
            if scene and scene.scene_mode == "multi":
                effective_b_id = request.character_b_id

        # 4. prompt engine composition (character tags, LoRAs, gender loaded from DB)
        builder_ref = None  # Track builder for layer extraction
        if request.character_id and effective_b_id:
            from models.character import Character
            from services.prompt.composition import PromptBuilder
            from services.prompt.multi_character import MultiCharacterComposer

            char_a = db.query(Character).filter(Character.id == request.character_id).first()
            char_b = db.query(Character).filter(Character.id == effective_b_id).first()
            if char_a and char_b:
                builder = PromptBuilder(db)
                composer = MultiCharacterComposer(builder)
                composed_prompt = composer.compose(
                    char_a,
                    char_b,
                    all_tokens,
                    style_loras=style_loras,
                )
                # Multi-char: builder_ref stays None (no single 12-layer decomposition)
            else:
                service = PromptService(db)
                composed_prompt = service.generate_prompt_for_scene(
                    character_id=request.character_id,
                    scene_tags=all_tokens,
                    style_loras=style_loras,
                )
                builder_ref = service.builder
        else:
            service = PromptService(db)
            composed_prompt = service.generate_prompt_for_scene(
                character_id=request.character_id,
                scene_tags=all_tokens,
                style_loras=style_loras,
            )
            builder_ref = service.builder

        # 5. Build response
        composed_tokens = split_prompt_tokens(composed_prompt)
        scene_complexity = detect_scene_complexity(request.tokens)

        lora_weights = None
        if request.loras:
            lora_weights = {lora.name: cap_style_lora_weight(lora.weight, lora.lora_type) for lora in request.loras}
        elif style_loras:
            lora_weights = {
                lr["name"]: cap_style_lora_weight(lr["weight"], lr.get("lora_type", "style")) for lr in style_loras
            }

        # 6. Compose negative preview
        scene_negative = ""
        if request.scene_id:
            from models.scene import Scene

            scene_row = db.query(Scene).filter(Scene.id == request.scene_id, Scene.deleted_at.is_(None)).first()
            if scene_row:
                scene_negative = scene_row.negative_prompt or ""

        neg_prompt, neg_sources = _compose_negative_preview(
            storyboard_id=request.storyboard_id,
            character_id=request.character_id,
            character_b_id=effective_b_id,
            scene_negative=scene_negative,
            db=db,
        )

        logger.info(
            "✅ [Prompt Compose] %d tokens → %d composed, neg_sources=%d",
            len(all_tokens),
            len(composed_tokens),
            len(neg_sources),
        )

        return {
            "prompt": composed_prompt,
            "tokens": composed_tokens,
            "scene_complexity": scene_complexity,
            "lora_weights": lora_weights,
            "meta": {
                "token_count": len(composed_tokens),
                "has_break": "BREAK" in composed_tokens,
                "quality_tags_added": any(t in composed_tokens for t in ["best_quality", "masterpiece"]),
            },
            "negative_prompt": neg_prompt or None,
            "negative_sources": neg_sources or None,
            "layers": builder_ref.get_last_composed_layers() if builder_ref else None,
        }

    except Exception as e:
        from services.error_responses import raise_user_error

        raise_user_error("prompt_compose", e)


class ValidateTagsRequest(BaseModel):
    """Request body for tag validation."""

    tags: list[str]
    check_danbooru: bool = True


class TagWarningItem(BaseModel):
    """Individual tag warning."""

    tag: str
    reason: str
    suggestion: str | None = None


class ValidateTagsResponse(BaseModel):
    """Response for tag validation."""

    valid: list[str]
    risky: list[str]
    unknown: list[str]
    warnings: list[TagWarningItem]
    total_tags: int
    valid_count: int
    risky_count: int
    unknown_count: int


class AutoReplaceRequest(BaseModel):
    """Request body for auto-replacement."""

    tags: list[str]


@service_router.post("/validate-tags", response_model=ValidateTagsResponse)
async def validate_tags(
    request: ValidateTagsRequest,
    db: Session = Depends(get_db),
):
    """Validate prompt tags against DB and Danbooru.

    Checks:
    1. Tag existence in local DB
    2. Known problematic tags via TagAliasCache
    3. Tag post count in Danbooru (if enabled)

    Returns validation results with warnings for risky tags.
    """
    from models.tag import Tag
    from services.keywords.db_cache import TagAliasCache

    logger.info("📥 [Validate Tags] tags=%d, check_danbooru=%s", len(request.tags), request.check_danbooru)

    risky_tags: list[str] = []
    unknown_in_db: list[str] = []
    warnings: list[TagWarningItem] = []

    for tag in request.tags:
        # Check if risky (has alias replacement)
        replacement = TagAliasCache.get_replacement(tag)
        if replacement is not ...:
            risky_tags.append(tag)
            suggestion = replacement if replacement else None
            reason = "removed (no alternative)" if not replacement else "risky tag"
            warnings.append(TagWarningItem(tag=tag, reason=reason, suggestion=suggestion))
            continue

        # Check DB existence
        normalized = tag.strip().replace(" ", "_")
        exists = db.query(Tag).filter(Tag.name == normalized).first()
        if not exists:
            unknown_in_db.append(tag)

    valid_tags = [t for t in request.tags if t not in risky_tags and t not in unknown_in_db]

    logger.info(
        "✅ [Validate Tags] valid=%d, risky=%d, unknown=%d",
        len(valid_tags),
        len(risky_tags),
        len(unknown_in_db),
    )

    return ValidateTagsResponse(
        valid=valid_tags,
        risky=risky_tags,
        unknown=unknown_in_db,
        warnings=warnings,
        total_tags=len(request.tags),
        valid_count=len(valid_tags),
        risky_count=len(risky_tags),
        unknown_count=len(unknown_in_db),
    )


@service_router.post("/auto-replace")
async def replace_tags(request: AutoReplaceRequest):
    """Automatically replace known risky tags with safe alternatives.

    Uses TagAliasCache to replace problematic tags like "medium shot"
    with Danbooru-verified alternatives like "cowboy_shot".
    """
    from services.keywords.db_cache import TagAliasCache

    logger.info("📥 [Auto Replace] tags=%d", len(request.tags))

    replaced: list[str] = []
    replacements: list[dict] = []
    removed: list[str] = []

    for tag in request.tags:
        replacement = TagAliasCache.get_replacement(tag)
        if replacement is ...:
            # Not a risky tag, keep as-is
            replaced.append(tag)
        elif replacement is None:
            # Should be removed (no alternative)
            removed.append(tag)
            replacements.append({"from": tag, "to": None, "action": "removed"})
        else:
            # Replace with alternative
            replaced.append(replacement)
            replacements.append({"from": tag, "to": replacement, "action": "replaced"})

    replaced_count = sum(1 for r in replacements if r["action"] == "replaced")

    return {
        "original": request.tags,
        "replaced": replaced,
        "replacements": replacements,
        "replaced_count": replaced_count,
        "removed_count": len(removed),
        "removed": removed,
    }
