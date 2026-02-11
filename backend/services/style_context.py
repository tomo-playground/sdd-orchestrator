"""StyleContext Value Object — DB 조회와 프롬프트 조립 관심사 분리.

Storyboard/Group → Config cascade → StyleProfile + LoRA/Embedding resolve를
한곳에서 처리하여 generation.py, image_generation_core.py의 중복 제거.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, joinedload

from config import logger


@dataclass(frozen=True)
class StyleContext:
    profile_id: int
    profile_name: str
    loras: list[dict] = field(default_factory=list)
    positive_embeddings: list[str] = field(default_factory=list)
    negative_embeddings: list[str] = field(default_factory=list)
    default_positive: str = ""
    default_negative: str = ""


def _resolve_embedding_triggers(embedding_ids: list[int] | None, db: Session) -> list[str]:
    """Resolve embedding IDs to trigger words."""
    if not embedding_ids:
        return []
    from models.sd_model import Embedding

    embs = db.query(Embedding).filter(Embedding.id.in_(embedding_ids), Embedding.is_active).all()
    return [e.trigger_word for e in embs if e.trigger_word]


def _resolve_profile_from_config(cfg: dict, db: Session):
    """Resolve StyleProfile from effective config dict. Returns None if not found."""
    from models import StyleProfile

    style_profile_id = cfg["values"].get("style_profile_id")
    if not style_profile_id:
        return None
    return db.query(StyleProfile).filter(StyleProfile.id == style_profile_id).first()


def _build_style_context(profile, db: Session) -> StyleContext:
    """Build StyleContext from a resolved StyleProfile ORM object."""
    from models import LoRA

    loras = []
    if profile.loras:
        for lora_config in profile.loras:
            lora_id = lora_config.get("lora_id")
            weight = lora_config.get("weight", 0.7)
            if not lora_id:
                continue
            lora_obj = db.query(LoRA).filter(LoRA.id == lora_id).first()
            if not lora_obj:
                continue
            loras.append({
                "lora_id": lora_id,
                "weight": weight,
                "name": lora_obj.name,
                "trigger_words": list(lora_obj.trigger_words) if lora_obj.trigger_words else [],
            })

    return StyleContext(
        profile_id=profile.id,
        profile_name=profile.name,
        loras=loras,
        positive_embeddings=_resolve_embedding_triggers(profile.positive_embeddings, db),
        negative_embeddings=_resolve_embedding_triggers(profile.negative_embeddings, db),
        default_positive=profile.default_positive or "",
        default_negative=profile.default_negative or "",
    )


def resolve_style_context(storyboard_id: int | None, db: Session) -> StyleContext | None:
    """Storyboard -> Group -> Config cascade -> StyleProfile + LoRA/Embedding resolve."""
    if not storyboard_id:
        return None

    from models import Storyboard
    from models.group import Group
    from services.config_resolver import resolve_effective_config

    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard:
        return None

    group = (
        db.query(Group)
        .options(joinedload(Group.config), joinedload(Group.project))
        .filter(Group.id == storyboard.group_id)
        .first()
    )
    if not group:
        return None

    cfg = resolve_effective_config(group.project, group)
    profile = _resolve_profile_from_config(cfg, db)
    if not profile:
        return None

    return _build_style_context(profile, db)


def resolve_style_context_from_group(group_id: int, db: Session) -> StyleContext | None:
    """Group -> Config -> StyleProfile 직접 조회."""
    from models.group import Group
    from services.config_resolver import resolve_effective_config

    group = (
        db.query(Group)
        .options(joinedload(Group.config), joinedload(Group.project))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        logger.warning("Group %d not found", group_id)
        return None

    cfg = resolve_effective_config(group.project, group)
    profile = _resolve_profile_from_config(cfg, db)
    if not profile:
        logger.warning("Group %d has no style_profile_id (cascade)", group_id)
        return None

    return _build_style_context(profile, db)


def extract_style_loras(ctx: StyleContext | None) -> list[dict]:
    """StyleContext에서 [{name, weight, trigger_words}] 추출."""
    if not ctx:
        return []
    return [
        {"name": lr["name"], "weight": lr["weight"], "trigger_words": lr.get("trigger_words", [])}
        for lr in ctx.loras
    ]
