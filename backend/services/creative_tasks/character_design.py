"""Character Design task-type: unique character profile generation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "uniqueness": {"weight": 0.3, "description": "Distinctive and memorable character design"},
    "visual_consistency": {"weight": 0.4, "description": "Consistent visual traits across descriptions"},
    "tag_expressibility": {"weight": 0.3, "description": "Expressible as Danbooru/SD tags"},
}


async def send_to_studio(
    db: Session,
    session_id: int,
    storyboard_id: int | None = None,
    group_id: int = 1,
) -> dict[str, Any]:
    """Convert character design output to storyboard scenes as character memos."""
    from models.scene import Scene
    from services.creative_tasks._base import commit_and_report, prepare_studio_context

    ctx = prepare_studio_context(db, session_id, storyboard_id, group_id, "Character design")
    content = ctx.session_output.get("content", "")

    # Character design → single scene with full description
    db.add(Scene(
        storyboard_id=ctx.storyboard.id,
        order=ctx.existing_scene_count,
        description=content,
        script=ctx.session_output.get("title", f"Character Design #{session_id}"),
    ))

    return commit_and_report(db, session_id, ctx.storyboard.id, 1, "Character design")
