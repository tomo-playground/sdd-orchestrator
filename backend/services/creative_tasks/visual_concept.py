"""Visual Concept task-type: cinematic mood and visual design generation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "originality": {"weight": 0.3, "description": "Novel and unique visual ideas"},
    "sd_feasibility": {"weight": 0.4, "description": "Feasibility with Stable Diffusion rendering"},
    "mood_coherence": {"weight": 0.3, "description": "Consistent mood and visual atmosphere"},
}


async def send_to_studio(
    db: Session,
    session_id: int,
    storyboard_id: int | None = None,
    group_id: int = 1,
) -> dict[str, Any]:
    """Convert visual concept output to storyboard scenes as descriptions."""
    from models.scene import Scene
    from services.creative_tasks._base import commit_and_report, prepare_studio_context

    ctx = prepare_studio_context(db, session_id, storyboard_id, group_id, "Visual concept")
    content = ctx.session_output.get("content", "")

    # Split visual concept sections by double newline
    sections = [s.strip() for s in content.split("\n\n") if s.strip()]
    if not sections:
        sections = [content]

    for i, text in enumerate(sections):
        db.add(Scene(storyboard_id=ctx.storyboard.id, order=ctx.existing_scene_count + i, description=text))

    return commit_and_report(db, session_id, ctx.storyboard.id, len(sections), "Visual concept")
