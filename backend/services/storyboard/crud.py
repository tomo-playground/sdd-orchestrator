from __future__ import annotations

from datetime import UTC

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from config import (
    SPEAKER_A,
    SPEAKER_B,
    logger,
)
from models.associations import SceneCharacterAction, SceneTag
from models.media_asset import MediaAsset
from models.scene import Scene
from models.storyboard import Storyboard
from schemas import StoryboardSave, StoryboardUpdate
from services.storyboard.helpers import calculate_auto_pin_flags, truncate_title
from services.storyboard.scene_builder import create_scenes, serialize_scene


def _sync_speaker_mappings(
    db: Session,
    storyboard_id: int,
    character_id: int | None,
    character_b_id: int | None,
) -> None:
    """Sync speaker→character mappings for a storyboard.

    Mapping rules:
    - Monologue (character_id only): A → character_id
    - Dialogue (both): A → character_id, B → character_b_id
    - Both None: do not change existing mappings (avoids wiping when save omits character IDs)
    """
    if character_id is None and character_b_id is None:
        logger.debug("[SpeakerMapping] Skipping sync (both character_id and character_b_id omitted)")
        return

    from services.characters import assign_speakers

    speaker_map: dict[str, int] = {}

    # Map Speaker A to character_id (Monologue or Dialogue)
    if character_id:
        speaker_map[SPEAKER_A] = character_id

    # Map Speaker B to character_b_id (Dialogue only)
    if character_b_id:
        speaker_map[SPEAKER_B] = character_b_id

    # assign_speakers handles deletion of old mappings before inserting new ones
    assign_speakers(storyboard_id, speaker_map, db)


def save_storyboard_to_db(db: Session, request: StoryboardSave) -> dict:
    """Save a full storyboard and its scenes to the DB."""
    safe_title = truncate_title(request.title)
    logger.info("\U0001f4be [Storyboard Save] %s (truncated from %d chars)", safe_title, len(request.title))

    if not request.group_id:
        raise HTTPException(status_code=400, detail="group_id is required")

    db_storyboard = Storyboard(
        title=safe_title,
        description=request.description,
        group_id=request.group_id,
        caption=request.caption,
        structure=request.structure,
        duration=request.duration,
        language=request.language,
    )
    db.add(db_storyboard)
    db.flush()

    create_scenes(db, db_storyboard.id, request.scenes)

    # Save speaker→character mappings if character_b_id is provided (Dialogue)
    _sync_speaker_mappings(db, db_storyboard.id, request.character_id, request.character_b_id)

    db.commit()
    db.refresh(db_storyboard)

    scenes_sorted = sorted(db_storyboard.scenes, key=lambda s: s.order)
    scene_ids = [scene.id for scene in scenes_sorted]
    client_ids = [scene.client_id for scene in scenes_sorted]

    return {"status": "success", "storyboard_id": db_storyboard.id, "scene_ids": scene_ids, "client_ids": client_ids}


def _derive_kanban_status(storyboard: Storyboard, image_count: int) -> str:
    """Derive kanban status from render history and image count."""
    render_history = storyboard.render_history or []
    if any(rh.youtube_video_id for rh in render_history):
        return "published"
    if render_history:
        return "rendered"
    if image_count > 0:
        return "in_prod"
    return "draft"


def list_storyboards_from_db(
    db: Session,
    group_id: int | None = None,
    project_id: int | None = None,
) -> list[dict]:
    """List all storyboards with scene/image counts."""
    from models.group import Group
    from models.storyboard_character import StoryboardCharacter

    query = (
        db.query(Storyboard)
        .options(
            joinedload(Storyboard.scenes).joinedload(Scene.image_asset),
            joinedload(Storyboard.characters).joinedload(StoryboardCharacter.character),
            joinedload(Storyboard.render_history),
        )
        .filter(Storyboard.deleted_at.is_(None))
    )
    if group_id is not None:
        query = query.filter(Storyboard.group_id == group_id)
    elif project_id is not None:
        group_ids = [g.id for g in db.query(Group.id).filter(Group.project_id == project_id).all()]
        if group_ids:
            query = query.filter(Storyboard.group_id.in_(group_ids))
        else:
            return []
    # Sort by updated_at DESC (most recently edited first)
    query = query.order_by(Storyboard.updated_at.desc())
    storyboards = query.all()

    result = []
    for s in storyboards:
        scenes = s.scenes or []
        image_count = sum(1 for sc in scenes if sc.image_url)
        # Extract cast (characters) with preview thumbnails — deduplicate by character id
        cast = []
        seen_char_ids: set[int] = set()
        for sc in sorted(s.characters or [], key=lambda x: x.speaker):
            char = sc.character
            if char and char.id not in seen_char_ids:
                seen_char_ids.add(char.id)
                cast.append(
                    {
                        "id": char.id,
                        "name": char.name,
                        "speaker": sc.speaker,
                        "preview_url": char.preview_image_url,
                    }
                )
        result.append(
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "scene_count": len(scenes),
                "image_count": image_count,
                "cast": cast,
                "kanban_status": _derive_kanban_status(s, image_count),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
        )
    return result


def get_storyboard_by_id(db: Session, storyboard_id: int) -> dict:
    """Get a storyboard with all scenes, tags, and character actions."""
    from models.render_history import RenderHistory
    from models.storyboard_character import StoryboardCharacter

    storyboard = (
        db.query(Storyboard)
        .options(
            joinedload(Storyboard.scenes).joinedload(Scene.tags).joinedload(SceneTag.tag),
            joinedload(Storyboard.scenes).joinedload(Scene.character_actions).joinedload(SceneCharacterAction.tag),
            joinedload(Storyboard.scenes).joinedload(Scene.image_asset),
            joinedload(Storyboard.render_history).joinedload(RenderHistory.media_asset),
            joinedload(Storyboard.characters).joinedload(StoryboardCharacter.character),
        )
        .filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None))
        .first()
    )

    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    # Resolve settings from cascade (group_config → project)
    from models.group import Group
    from services.config_resolver import resolve_effective_config

    group = (
        db.query(Group)
        .options(joinedload(Group.config), joinedload(Group.project))
        .filter(Group.id == storyboard.group_id)
        .first()
    )
    effective = resolve_effective_config(group.project, group) if group else {"values": {}}

    scenes = sorted(storyboard.scenes, key=lambda s: s.order)

    # Collect all candidate asset IDs for batch query (N+1 prevention)
    candidate_asset_ids: set[int] = set()
    for sc in scenes:
        if sc.candidates:
            for c in sc.candidates:
                asset_id = c.get("media_asset_id")
                if asset_id:
                    candidate_asset_ids.add(asset_id)

    # Batch fetch candidate assets and build URL map
    asset_url_map: dict[int, str] = {}
    if candidate_asset_ids:
        candidate_assets = db.query(MediaAsset).filter(MediaAsset.id.in_(candidate_asset_ids)).all()
        asset_url_map = {a.id: a.url for a in candidate_assets}

    recent_videos = [
        {"url": rh.media_asset.url, "label": rh.label, "createdAt": int(rh.created_at.timestamp() * 1000)}
        for rh in storyboard.render_history[:10]
        if rh.created_at
    ]

    # Resolve character_id and character_b_id from storyboard_characters
    from services.characters import resolve_speaker_to_character

    character_id = resolve_speaker_to_character(storyboard.id, SPEAKER_A, db)
    character_b_id = resolve_speaker_to_character(storyboard.id, SPEAKER_B, db)

    # Calculate _auto_pin_previous for each scene based on structure type
    # Dialogue/Narrated Dialogue: all scenes share same background (auto-pin all)
    # Monologue: use environment tag overlap logic
    auto_pin_flags = calculate_auto_pin_flags(scenes, storyboard.structure)

    # Build characters cast list from storyboard_characters relationship
    characters_list = []
    for sc in sorted(storyboard.characters or [], key=lambda x: x.speaker):
        char = sc.character
        if char:
            characters_list.append(
                {
                    "speaker": sc.speaker,
                    "character_id": char.id,
                    "character_name": char.name,
                    "preview_image_url": char.preview_image_url,
                }
            )

    return {
        "id": storyboard.id,
        "title": storyboard.title,
        "description": storyboard.description,
        "group_id": storyboard.group_id,
        "project_id": group.project_id if group else None,
        "structure": storyboard.structure,
        "duration": storyboard.duration,
        "language": storyboard.language,
        "character_id": character_id,
        "character_b_id": character_b_id,
        "style_profile_id": effective["values"].get("style_profile_id"),
        "narrator_voice_preset_id": effective["values"].get("narrator_voice_preset_id"),
        "video_url": storyboard.video_url,
        "recent_videos": recent_videos,
        "caption": storyboard.caption,
        "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
        "updated_at": storyboard.updated_at.isoformat() if storyboard.updated_at else None,
        "characters": characters_list,
        "scenes": [serialize_scene(sc, asset_url_map, auto_pin_flags.get(sc.id, False)) for sc in scenes],
    }


def update_storyboard_in_db(db: Session, storyboard_id: int, request: StoryboardSave) -> dict:
    """Update a storyboard by replacing all scenes."""
    storyboard = (
        db.query(Storyboard)
        .options(
            selectinload(Storyboard.scenes),
        )
        .filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None))
        .first()
    )
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    safe_title = truncate_title(request.title)
    logger.info("\u270f\ufe0f [Storyboard Update] id=%d title=%s", storyboard_id, safe_title)

    storyboard.title = safe_title
    storyboard.description = request.description
    if request.group_id is not None:
        storyboard.group_id = request.group_id
    storyboard.caption = request.caption
    # Keep structure in sync with latest request (Monologue / Dialogue / Narrated Dialogue)
    storyboard.structure = request.structure
    if request.duration is not None:
        storyboard.duration = request.duration
    if request.language is not None:
        storyboard.language = request.language

    # Collect asset IDs referenced by incoming scenes (to preserve them)
    preserved_asset_ids: set[int] = set()
    for s_data in request.scenes:
        if s_data.image_asset_id:
            preserved_asset_ids.add(s_data.image_asset_id)
        if s_data.environment_reference_id:
            preserved_asset_ids.add(s_data.environment_reference_id)
        if s_data.candidates:
            for c in s_data.candidates:
                mid = c.media_asset_id if hasattr(c, "media_asset_id") else c.get("media_asset_id")
                if mid:
                    preserved_asset_ids.add(mid)

    # Nullify asset FK references on scenes first
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None)).update(
        {Scene.image_asset_id: None, Scene.environment_reference_id: None},
        synchronize_session=False,
    )
    db.flush()

    scene_ids = [
        s.id for s in db.query(Scene.id).filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None)).all()
    ]
    db.query(Scene).filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None)).delete(
        synchronize_session=False
    )

    # Delete storyboard-owned media assets (videos etc.)
    db.query(MediaAsset).filter(
        MediaAsset.owner_type == "storyboard",
        MediaAsset.owner_id == storyboard_id,
    ).delete(synchronize_session=False)

    # Delete scene media assets that are NOT referenced by incoming scenes
    if scene_ids:
        if preserved_asset_ids:
            db.query(MediaAsset).filter(
                MediaAsset.owner_type == "scene",
                MediaAsset.owner_id.in_(scene_ids),
                ~MediaAsset.id.in_(preserved_asset_ids),
            ).delete(synchronize_session=False)
        else:
            db.query(MediaAsset).filter(
                MediaAsset.owner_type == "scene",
                MediaAsset.owner_id.in_(scene_ids),
            ).delete(synchronize_session=False)

    db.flush()

    create_scenes(db, storyboard_id, request.scenes)

    # Update speaker→character mappings (Dialogue)
    _sync_speaker_mappings(db, storyboard_id, request.character_id, request.character_b_id)

    db.commit()
    db.refresh(storyboard)

    # Return new scene IDs ordered by scene.order (relationship now has order_by,
    # but explicit sort as belt-and-suspenders to prevent ID/order mismatch on frontend)
    scenes_sorted = sorted(storyboard.scenes, key=lambda s: s.order)
    scene_ids = [scene.id for scene in scenes_sorted]
    client_ids = [scene.client_id for scene in scenes_sorted]

    return {"status": "success", "storyboard_id": storyboard.id, "scene_ids": scene_ids, "client_ids": client_ids}


def update_storyboard_metadata(db: Session, storyboard_id: int, request: StoryboardUpdate) -> dict:
    """Update only storyboard metadata (title, caption, etc) without touching scenes."""
    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id, Storyboard.deleted_at.is_(None)).first()
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f4dd [Storyboard Metadata Update] id=%d", storyboard_id)

    if request.title is not None:
        storyboard.title = truncate_title(request.title)
    if request.description is not None:
        storyboard.description = request.description
    if request.caption is not None:
        storyboard.caption = request.caption

    db.commit()
    return {"status": "success", "storyboard_id": storyboard.id}


def delete_storyboard_from_db(db: Session, storyboard_id: int) -> dict:
    """Soft-delete a storyboard (set deleted_at timestamp)."""
    from datetime import datetime

    storyboard = (
        db.query(Storyboard)
        .filter(
            Storyboard.id == storyboard_id,
            Storyboard.deleted_at.is_(None),
        )
        .first()
    )
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f5d1\ufe0f [Storyboard Soft Delete] id=%d title=%s", storyboard_id, storyboard.title)
    now = datetime.now(UTC)
    storyboard.deleted_at = now
    # Cascade soft-delete to child scenes
    db.query(Scene).filter(
        Scene.storyboard_id == storyboard_id,
        Scene.deleted_at.is_(None),
    ).update({Scene.deleted_at: now}, synchronize_session=False)
    db.commit()
    return {"status": "success"}


def permanent_delete_storyboard(db: Session, storyboard_id: int) -> dict:
    """Permanently delete a storyboard and all its scenes (CASCADE) + cleanup assets."""
    storyboard = (
        db.query(Storyboard)
        .options(
            selectinload(Storyboard.scenes),
        )
        .filter(Storyboard.id == storyboard_id)
        .first()
    )
    if not storyboard:
        raise HTTPException(status_code=404, detail="Storyboard not found")

    logger.info("\U0001f5d1\ufe0f [Storyboard Permanent Delete] id=%d title=%s", storyboard_id, storyboard.title)

    try:
        db.query(Scene).filter(Scene.storyboard_id == storyboard_id).update(
            {Scene.image_asset_id: None, Scene.environment_reference_id: None},
            synchronize_session=False,
        )

        # render_history rows are CASCADE-deleted by DB FK
        # Clean up owned media assets
        db.query(MediaAsset).filter(
            MediaAsset.owner_type == "storyboard",
            MediaAsset.owner_id == storyboard_id,
        ).delete(synchronize_session=False)

        scene_ids = [s.id for s in storyboard.scenes]
        if scene_ids:
            db.query(MediaAsset).filter(
                MediaAsset.owner_type == "scene",
                MediaAsset.owner_id.in_(scene_ids),
            ).delete(synchronize_session=False)

        db.delete(storyboard)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        import sys
        import traceback

        traceback.print_exc(file=sys.stderr)
        logger.exception("Failed to permanently delete storyboard %d", storyboard_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}") from e
