"""Scenario task-type: creative multi-agent story generation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "originality": {"weight": 0.3, "description": "Novel and surprising ideas"},
    "coherence": {"weight": 0.4, "description": "Logical flow and structure"},
    "engagement": {"weight": 0.3, "description": "Audience appeal and emotional impact"},
}


async def send_to_studio(
    db: Session,
    session_id: int,
    storyboard_id: int | None = None,
    group_id: int = 1,
) -> dict[str, Any]:
    """Convert creative session output to storyboard scenes in Studio."""
    from models.scene import Scene
    from services.creative_tasks._base import commit_and_report, prepare_studio_context

    ctx = prepare_studio_context(db, session_id, storyboard_id, group_id, "Scenario")
    content = ctx.session_output.get("content", "")

    # Parse content into scenes (split by double newline)
    scene_texts = [s.strip() for s in content.split("\n\n") if s.strip()]
    if not scene_texts:
        scene_texts = [content]

    for i, text in enumerate(scene_texts):
        db.add(Scene(storyboard_id=ctx.storyboard.id, order=ctx.existing_scene_count + i, script=text))

    return commit_and_report(db, session_id, ctx.storyboard.id, len(scene_texts), "Scenario")
