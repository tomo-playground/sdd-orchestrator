"""인라인 편집용 옵션 목록 빌더 (SSOT 소비)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from config import SHORTS_DURATIONS, STORYBOARD_LANGUAGES
from models.character import Character
from schemas import AvailableOptions
from services.presets import PRESETS


def build_available_options(group_id: int | None, db: Session) -> AvailableOptions:
    """Frontend 인라인 드롭다운에 필요한 옵션 목록을 구성한다."""
    structures = [{"value": p.structure, "label": p.name_ko} for p in PRESETS.values()]

    characters = []
    if group_id:
        rows = (
            db.query(Character.id, Character.name)
            .filter(Character.group_id == group_id, Character.deleted_at.is_(None))
            .order_by(Character.id)
            .all()
        )
        characters = [{"id": r.id, "name": r.name} for r in rows]

    return AvailableOptions(
        durations=SHORTS_DURATIONS,
        structures=structures,
        languages=STORYBOARD_LANGUAGES,
        characters=characters,
    )
