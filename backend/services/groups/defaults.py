"""시리즈 이력 기반 기본값 추론 서비스."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from config import DEFAULT_LANGUAGE, DEFAULT_STRUCTURE, MULTI_CHAR_STRUCTURES, SHORTS_DURATIONS, coerce_structure_id
from models.character import Character
from models.storyboard import Storyboard
from schemas import GroupDefaultsResponse
from services.groups.options import build_available_options

_RECENT_LIMIT = 10


def infer_group_defaults(group_id: int, db: Session) -> GroupDefaultsResponse:
    """최근 스토리보드 이력에서 최빈 설정을 추출한다.

    이력이 없으면 config.py 전역 기본값을 반환한다.
    """
    recent = (
        db.query(Storyboard.duration, Storyboard.structure, Storyboard.language)
        .filter(Storyboard.group_id == group_id, Storyboard.deleted_at.is_(None))
        .order_by(Storyboard.created_at.desc())
        .limit(_RECENT_LIMIT)
        .all()
    )

    options = build_available_options(group_id, db)

    if not recent:
        # 이력 없음 → 전역 기본값 + 캐릭터
        chars = _group_characters(group_id, db)
        return GroupDefaultsResponse(
            duration=SHORTS_DURATIONS[1] if len(SHORTS_DURATIONS) > 1 else 30,
            structure=DEFAULT_STRUCTURE,
            language=DEFAULT_LANGUAGE,
            **_chars_to_fields(chars, DEFAULT_STRUCTURE),
            has_history=False,
            available_options=options,
        )

    duration = _most_common([r.duration for r in recent if r.duration], default=30)
    structure = _most_common([r.structure for r in recent if r.structure], default=DEFAULT_STRUCTURE)
    language = _most_common([r.language for r in recent if r.language], default=DEFAULT_LANGUAGE)
    chars = _group_characters(group_id, db)

    return GroupDefaultsResponse(
        duration=duration,
        structure=structure,
        language=language,
        **_chars_to_fields(chars, structure),
        has_history=True,
        available_options=options,
    )


def _most_common(values: list, default=None):
    """리스트에서 최빈값을 반환한다."""
    if not values:
        return default
    counter = Counter(values)
    return counter.most_common(1)[0][0]


def _group_characters(
    group_id: int,
    db: Session,
) -> list[tuple[int, str]]:
    """그룹의 활성 캐릭터 목록을 반환한다 (최대 2명)."""
    rows = (
        db.query(Character.id, Character.name)
        .filter(Character.group_id == group_id, Character.deleted_at.is_(None))
        .order_by(Character.id)
        .limit(2)
        .all()
    )
    return [(r.id, r.name) for r in rows]


def _chars_to_fields(chars: list[tuple[int, str]], structure: str) -> dict:
    """캐릭터 목록을 character_a_id/character_b_id 필드 dict로 변환."""
    result: dict = {
        "character_a_id": None,
        "character_a_name": None,
        "character_b_id": None,
        "character_b_name": None,
    }
    if chars:
        result["character_a_id"] = chars[0][0]
        result["character_a_name"] = chars[0][1]
    if len(chars) > 1 and coerce_structure_id(structure) in MULTI_CHAR_STRUCTURES:
        result["character_b_id"] = chars[1][0]
        result["character_b_name"] = chars[1][1]
    return result
