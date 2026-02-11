"""Speaker-to-Character resolver for Dialogue storyboards."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def resolve_speaker_to_character(
    storyboard_id: int,
    speaker: str,
    db: Session,
) -> int | None:
    """Resolve a speaker label to a character_id via storyboard_characters table.

    Returns character_id if mapping exists, None otherwise.
    """
    from models.storyboard_character import StoryboardCharacter

    row = (
        db.query(StoryboardCharacter.character_id)
        .filter(
            StoryboardCharacter.storyboard_id == storyboard_id,
            StoryboardCharacter.speaker == speaker,
        )
        .first()
    )
    return row[0] if row else None


def resolve_all_speakers(
    storyboard_id: int,
    db: Session,
) -> dict[str, int]:
    """Return all speaker→character_id mappings for a storyboard."""
    from models.storyboard_character import StoryboardCharacter

    rows = (
        db.query(StoryboardCharacter.speaker, StoryboardCharacter.character_id)
        .filter(StoryboardCharacter.storyboard_id == storyboard_id)
        .all()
    )
    return {row[0]: row[1] for row in rows}


def assign_speakers(
    storyboard_id: int,
    speaker_map: dict[str, int],
    db: Session,
) -> None:
    """Upsert speaker→character_id mappings for a storyboard.

    Deletes existing mappings first, then inserts new ones.
    """
    from models.storyboard_character import StoryboardCharacter

    # Delete existing mappings
    db.query(StoryboardCharacter).filter(
        StoryboardCharacter.storyboard_id == storyboard_id,
    ).delete(synchronize_session=False)

    # Insert new mappings
    for speaker, character_id in speaker_map.items():
        db.add(
            StoryboardCharacter(
                storyboard_id=storyboard_id,
                speaker=speaker,
                character_id=character_id,
            )
        )
    db.flush()
    logger.info("[SpeakerResolver] Assigned speakers for storyboard %d: %s", storyboard_id, speaker_map)
