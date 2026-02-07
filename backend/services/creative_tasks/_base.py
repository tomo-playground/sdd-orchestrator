"""Shared helpers for creative task modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from config import logger


@dataclass
class StudioContext:
    """Resolved context for send_to_studio operations."""

    session_output: dict[str, Any]
    storyboard: Any  # Storyboard ORM instance
    existing_scene_count: int


def prepare_studio_context(
    db: Session,
    session_id: int,
    storyboard_id: int | None = None,
    group_id: int = 1,
    title_prefix: str = "Creative",
) -> StudioContext:
    """Validate session + resolve or create storyboard.

    Returns a StudioContext with the session output, storyboard, and existing scene count.
    Raises ValueError on invalid session or storyboard.
    """
    from models.creative import CreativeSession
    from models.scene import Scene
    from models.storyboard import Storyboard

    session = db.get(CreativeSession, session_id)
    if not session or session.deleted_at or not session.final_output:
        msg = f"Session {session_id} not found or not finalized"
        raise ValueError(msg)

    output = session.final_output

    if storyboard_id:
        storyboard = db.get(Storyboard, storyboard_id)
        if not storyboard or storyboard.deleted_at:
            msg = f"Storyboard {storyboard_id} not found"
            raise ValueError(msg)
    else:
        storyboard = Storyboard(
            title=output.get("title", f"{title_prefix} #{session_id}"),
            description=f"{title_prefix} by Creative Engine (session {session_id})",
            group_id=group_id,
        )
        db.add(storyboard)
        db.flush()

    existing_count = (
        db.query(Scene).filter(Scene.storyboard_id == storyboard.id, Scene.deleted_at.is_(None)).count()
    )

    return StudioContext(
        session_output=output,
        storyboard=storyboard,
        existing_scene_count=existing_count,
    )


def commit_and_report(
    db: Session,
    session_id: int,
    storyboard_id: int,
    scenes_created: int,
    label: str = "Creative",
) -> dict[str, int]:
    """Commit DB changes and log the result."""
    db.commit()
    logger.info(
        "[Creative] %s session %d -> Storyboard %d: %d scenes",
        label, session_id, storyboard_id, scenes_created,
    )
    return {"storyboard_id": storyboard_id, "scenes_created": scenes_created}
