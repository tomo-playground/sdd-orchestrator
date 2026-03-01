"""Phase 20-A: Director Inventory Loading.

Director Plan 노드에 인벤토리 인지 능력을 부여하기 위해
캐릭터·구조·스타일 목록을 DB에서 로드하는 서비스.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from config_pipelines import INVENTORY_MAX_CHARACTERS
from models.associations import CharacterTag
from models.character import Character
from models.sd_model import StyleProfile
from models.storyboard_character import StoryboardCharacter


@dataclass
class CharacterSummary:
    """Director에게 제공할 캐릭터 요약."""

    id: int
    name: str
    gender: str
    appearance_summary: str
    has_lora: bool
    has_reference: bool
    usage_count: int = 0


@dataclass
class StructureMeta:
    """구조 메타데이터 (인메모리 상수)."""

    id: str
    name: str
    requires_two_characters: bool
    tone: str


@dataclass
class StyleSummary:
    """Director에게 제공할 스타일 요약."""

    id: int
    name: str
    description: str


STRUCTURE_METADATA: list[StructureMeta] = [
    StructureMeta(id="monologue", name="Monologue", requires_two_characters=False, tone="intimate"),
    StructureMeta(id="dialogue", name="Dialogue", requires_two_characters=True, tone="dynamic"),
    StructureMeta(id="narrated_dialogue", name="Narrated Dialogue", requires_two_characters=True, tone="narrative"),
    StructureMeta(id="confession", name="Confession", requires_two_characters=False, tone="emotional"),
]


def _build_appearance_summary(character: Character) -> str:
    """캐릭터의 permanent 태그를 요약 문자열로 변환."""
    if not character.tags:
        return ""
    permanent_tags = [ct.tag.name for ct in character.tags if ct.is_permanent and ct.tag]
    return ", ".join(permanent_tags[:10])


def load_characters(
    db: Session,
    group_id: int | None = None,
    max_count: int | None = None,
) -> list[CharacterSummary]:
    """활성 캐릭터 목록을 usage_count 기준 정렬로 로드.

    group_id가 주어지면 해당 그룹 스토리보드에 사용된 캐릭터만 반환.
    해당 그룹에 캐릭터가 없으면(신규 그룹) 전체 캐릭터로 폴백.
    """
    if max_count is None:
        max_count = INVENTORY_MAX_CHARACTERS

    if group_id is not None:
        group_results = _load_characters_for_group(db, group_id, max_count)
        if group_results:
            return group_results

    return _load_all_characters(db, max_count)


def _build_character_summary(char: Character, count: int) -> CharacterSummary:
    return CharacterSummary(
        id=char.id,
        name=char.name,
        gender=char.gender or "unknown",
        appearance_summary=_build_appearance_summary(char),
        has_lora=bool(char.loras),
        has_reference=bool(char.preview_image_asset_id),
        usage_count=count,
    )


def _load_characters_for_group(db: Session, group_id: int, max_count: int) -> list[CharacterSummary]:
    """그룹에서 실제 사용된 캐릭터만 usage_count 내림차순으로 로드."""
    from models.storyboard import Storyboard  # noqa: PLC0415

    usage_subq = (
        select(
            StoryboardCharacter.character_id,
            func.count().label("usage_count"),
        )
        .join(Storyboard, StoryboardCharacter.storyboard_id == Storyboard.id)
        .where(Storyboard.group_id == group_id)
        .group_by(StoryboardCharacter.character_id)
        .subquery()
    )
    query = (
        select(Character, usage_subq.c.usage_count)
        .join(usage_subq, Character.id == usage_subq.c.character_id)
        .where(Character.deleted_at.is_(None))
        .options(selectinload(Character.tags).selectinload(CharacterTag.tag))
        .order_by(usage_subq.c.usage_count.desc(), Character.created_at.desc())
        .limit(max_count)
    )
    rows = db.execute(query).all()
    return [_build_character_summary(row[0], row[1]) for row in rows]


def _load_all_characters(db: Session, max_count: int) -> list[CharacterSummary]:
    """전체 캐릭터를 글로벌 usage_count 내림차순으로 로드."""
    usage_subq = (
        select(
            StoryboardCharacter.character_id,
            func.count().label("usage_count"),
        )
        .group_by(StoryboardCharacter.character_id)
        .subquery()
    )
    query = (
        select(Character, func.coalesce(usage_subq.c.usage_count, 0).label("usage_count"))
        .outerjoin(usage_subq, Character.id == usage_subq.c.character_id)
        .where(Character.deleted_at.is_(None))
        .options(selectinload(Character.tags).selectinload(CharacterTag.tag))
        .order_by(
            func.coalesce(usage_subq.c.usage_count, 0).desc(),
            Character.created_at.desc(),
        )
        .limit(max_count)
    )
    rows = db.execute(query).all()
    return [_build_character_summary(row[0], row[1]) for row in rows]


def load_styles(db: Session) -> list[StyleSummary]:
    """활성 스타일 프로필 목록을 로드."""
    profiles = db.execute(select(StyleProfile).where(StyleProfile.is_active.is_(True))).scalars().all()
    return [
        StyleSummary(
            id=p.id,
            name=p.display_name or p.name,
            description=p.description or "",
        )
        for p in profiles
    ]


def load_structures() -> list[StructureMeta]:
    """인메모리 구조 메타데이터 반환."""
    return list(STRUCTURE_METADATA)


def load_full_inventory(group_id: int | None, max_count: int | None = None) -> dict:
    """DB에서 캐릭터·구조·스타일 인벤토리를 로드하고 세션을 닫는다.

    실패 시 빈 dict 반환. LLM 호출 전에 DB 세션을 해제하기 위해 독립 세션 사용.
    """
    from database import get_db_session  # noqa: PLC0415

    try:
        with get_db_session() as db:
            characters = load_characters(db, group_id=group_id, max_count=max_count)
            styles = load_styles(db)
            structures = load_structures()
        return {
            "characters": characters,
            "styles": styles,
            "structures": structures,
        }
    except Exception as e:
        from config import logger  # noqa: PLC0415

        logger.warning("[Inventory] 인벤토리 로드 실패: %s", e)
        return {}


def load_fallback_character(db: Session) -> dict | None:
    """최근 사용 캐릭터 반환. storyboard_characters → storyboards.created_at DESC."""
    from models.storyboard import Storyboard  # noqa: PLC0415

    row = db.execute(
        select(StoryboardCharacter.character_id, Character.name)
        .join(Storyboard, StoryboardCharacter.storyboard_id == Storyboard.id)
        .join(Character, StoryboardCharacter.character_id == Character.id)
        .where(Character.deleted_at.is_(None))
        .order_by(Storyboard.created_at.desc())
        .limit(1)
    ).first()
    if not row:
        return None
    return {"character_id": row[0], "character_name": row[1]}
