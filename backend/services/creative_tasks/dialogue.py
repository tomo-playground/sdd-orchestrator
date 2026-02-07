"""Dialogue task-type: multi-agent character dialogue generation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "naturalness": {"weight": 0.35, "description": "Natural speech flow and rhythm"},
    "character_voice": {"weight": 0.35, "description": "Distinct character voices and personality"},
    "conflict": {"weight": 0.3, "description": "Dramatic tension and conversational conflict"},
}


async def send_to_studio(
    db: Session,
    session_id: int,
    storyboard_id: int | None = None,
    group_id: int = 1,
) -> dict[str, Any]:
    """Convert dialogue output to storyboard scenes — each dialogue line becomes a scene."""
    from models.scene import Scene
    from services.creative_tasks._base import commit_and_report, prepare_studio_context

    ctx = prepare_studio_context(db, session_id, storyboard_id, group_id, "Dialogue")
    content = ctx.session_output.get("content", "")

    # Parse dialogue lines (split by newline, skip empty)
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        lines = [content]

    for i, text in enumerate(lines):
        db.add(Scene(storyboard_id=ctx.storyboard.id, order=ctx.existing_scene_count + i, script=text))

    return commit_and_report(db, session_id, ctx.storyboard.id, len(lines), "Dialogue")
