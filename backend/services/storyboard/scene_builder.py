from __future__ import annotations

import os
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from config import logger
from models.associations import SceneCharacterAction, SceneTag
from models.media_asset import MediaAsset
from models.scene import Scene
from schemas import SceneActionSave
from services.storyboard.helpers import _sanitize_candidates_for_db


def resolve_action_tag_ids(actions: list[SceneActionSave], db: Session) -> list[SceneActionSave]:
    """Resolve tag_id=0 entries by looking up tag_name in DB.

    Frontend AddTagInput sends tag_name without knowing tag_id.
    This batch-resolves names and drops unresolvable entries.
    """
    names_to_resolve = {a.tag_name for a in actions if a.tag_id == 0 and a.tag_name}
    if not names_to_resolve:
        return actions

    from models.tag import Tag

    rows = db.query(Tag.id, Tag.name).filter(Tag.name.in_(names_to_resolve)).all()
    name_to_id = {r.name: r.id for r in rows}

    resolved: list[SceneActionSave] = []
    for a in actions:
        if a.tag_id == 0 and a.tag_name:
            tid = name_to_id.get(a.tag_name)
            if tid:
                resolved.append(
                    SceneActionSave(
                        character_id=a.character_id,
                        tag_id=tid,
                        tag_name=a.tag_name,
                        weight=a.weight,
                    )
                )
            else:
                logger.warning("[resolve_action_tag_ids] Unknown tag: %s", a.tag_name)
        else:
            resolved.append(a)
    return resolved


def serialize_scene(
    scene: Scene,
    asset_url_map: dict[int, str] | None = None,
    auto_pin_previous: bool = False,
) -> dict:
    """Serialize a Scene ORM object to dict for API response.

    Args:
        scene: Scene ORM object
        asset_url_map: Optional mapping of media_asset_id -> URL for candidates
        auto_pin_previous: Whether this scene should auto-pin to previous scene's environment
    """
    # Enrich candidates with URLs if asset_url_map is provided
    candidates_with_url = None
    if scene.candidates:
        candidates_with_url = []
        for c in scene.candidates:
            enriched = dict(c)  # Copy to avoid mutating DB data
            asset_id = c.get("media_asset_id")
            if asset_id and asset_url_map and asset_id in asset_url_map:
                enriched["image_url"] = asset_url_map[asset_id]
            candidates_with_url.append(enriched)

    return {
        "id": scene.id,
        "client_id": scene.client_id,
        "scene_id": scene.order,
        "script": scene.script,
        "speaker": scene.speaker,
        "duration": scene.duration,
        "description": scene.description,
        "image_prompt": scene.image_prompt,
        "image_prompt_ko": scene.image_prompt_ko,
        "negative_prompt": scene.negative_prompt,
        "scene_mode": scene.scene_mode,
        "image_url": scene.image_asset.url if scene.image_asset else scene.image_url,
        "width": scene.width,
        "height": scene.height,
        "context_tags": scene.context_tags,
        "tags": [{"tag_id": t.tag_id, "weight": t.weight} for t in scene.tags],
        "character_actions": [
            {
                "character_id": a.character_id,
                "tag_id": a.tag_id,
                "tag_name": a.tag.name if a.tag else None,
                "weight": a.weight,
            }
            for a in scene.character_actions
        ],
        "use_reference_only": scene.use_reference_only,
        "reference_only_weight": scene.reference_only_weight,
        "environment_reference_id": scene.environment_reference_id,
        "environment_reference_weight": scene.environment_reference_weight,
        "image_asset_id": scene.image_asset_id,
        "candidates": candidates_with_url,
        "_auto_pin_previous": auto_pin_previous,
        # Per-scene generation settings override
        "use_controlnet": scene.use_controlnet,
        "controlnet_weight": scene.controlnet_weight,
        "use_ip_adapter": scene.use_ip_adapter,
        "ip_adapter_reference": scene.ip_adapter_reference,
        "ip_adapter_weight": scene.ip_adapter_weight,
        "multi_gen_enabled": scene.multi_gen_enabled,
    }


def _link_media_asset(db: Session, db_scene: Scene, image_url: str) -> None:
    """Link or create a MediaAsset for a scene's image_url."""
    from config import MINIO_BUCKET

    path = urlparse(image_url).path
    if path.startswith("/"):
        path = path[1:]
    if path.startswith(f"{MINIO_BUCKET}/"):
        path = path.replace(f"{MINIO_BUCKET}/", "", 1)
    if path.startswith("assets/"):
        path = path.replace("assets/", "", 1)
    storage_key = path

    asset = db.query(MediaAsset).filter(MediaAsset.storage_key == storage_key).first()

    if not asset:
        asset = MediaAsset(
            file_type="image",
            storage_key=storage_key,
            file_name=os.path.basename(storage_key),
            mime_type="image/png",
            owner_type="scene",
            owner_id=db_scene.id,
        )
        db.add(asset)
        db.flush()

    db_scene.image_asset_id = asset.id


def create_scenes(db: Session, storyboard_id: int, scenes_data: list) -> None:
    """Create scenes with tags and character actions for a storyboard."""
    # Track old→new asset ID mapping for environment_reference_id remapping
    asset_id_remap: dict[int, int] = {}
    created_scenes: list[Scene] = []
    # Defer environment_reference_id assignment to avoid FK violation
    # when old MediaAssets have been deleted (e.g. during storyboard update)
    deferred_env_refs: list[int | None] = []

    for idx, s_data in enumerate(scenes_data):
        image_url = s_data.image_url
        if image_url and image_url.startswith("data:"):
            image_url = None

        # Convert Pydantic SceneCandidate models to dicts for JSONB storage
        candidates_for_db = None
        if s_data.candidates:
            candidates_for_db = _sanitize_candidates_for_db(s_data.candidates)

        # Store requested environment_reference_id for deferred assignment
        deferred_env_refs.append(s_data.environment_reference_id)

        db_scene = Scene(
            storyboard_id=storyboard_id,
            client_id=getattr(s_data, "client_id", None) or str(uuid4()),
            order=idx,
            script=s_data.script,
            speaker=s_data.speaker,
            duration=s_data.duration,
            scene_mode=getattr(s_data, "scene_mode", "single") or "single",
            description=s_data.description,
            image_prompt=s_data.image_prompt,
            image_prompt_ko=s_data.image_prompt_ko,
            negative_prompt=s_data.negative_prompt,
            width=s_data.width,
            height=s_data.height,
            context_tags=s_data.context_tags,
            use_reference_only=s_data.use_reference_only if s_data.use_reference_only is not None else True,
            reference_only_weight=s_data.reference_only_weight or 0.5,
            background_id=getattr(s_data, "background_id", None),
            environment_reference_id=None,  # Deferred — set after asset remap
            environment_reference_weight=s_data.environment_reference_weight or 0.3,
            candidates=candidates_for_db,
            # Per-scene generation settings override
            use_controlnet=getattr(s_data, "use_controlnet", None),
            controlnet_weight=getattr(s_data, "controlnet_weight", None),
            use_ip_adapter=getattr(s_data, "use_ip_adapter", None),
            ip_adapter_reference=getattr(s_data, "ip_adapter_reference", None),
            ip_adapter_weight=getattr(s_data, "ip_adapter_weight", None),
            multi_gen_enabled=getattr(s_data, "multi_gen_enabled", None),
        )
        db.add(db_scene)
        db.flush()

        if s_data.tags:
            for t_data in s_data.tags:
                db.add(SceneTag(scene_id=db_scene.id, tag_id=t_data.tag_id, weight=t_data.weight))

        if s_data.character_actions:
            resolved = resolve_action_tag_ids(s_data.character_actions, db)
            for a_data in resolved:
                db.add(
                    SceneCharacterAction(
                        scene_id=db_scene.id,
                        character_id=a_data.character_id,
                        tag_id=a_data.tag_id,
                        weight=a_data.weight,
                    )
                )

        # Link image asset: prefer image_asset_id (direct), fallback to image_url
        old_asset_id = getattr(s_data, "image_asset_id", None)
        if old_asset_id:
            # Verify asset exists before setting FK
            if db.query(MediaAsset.id).filter(MediaAsset.id == old_asset_id).first():
                db_scene.image_asset_id = old_asset_id
                # Update asset owner to new scene
                db.query(MediaAsset).filter(MediaAsset.id == old_asset_id).update(
                    {"owner_type": "scene", "owner_id": db_scene.id},
                    synchronize_session=False,
                )
            else:
                logger.warning(
                    "[Scene %d] image_asset_id %d not found, skipping",
                    idx,
                    old_asset_id,
                )
        elif image_url:
            _link_media_asset(db, db_scene, image_url)

        # Update candidate asset owners to point to new scene
        if s_data.candidates:
            candidate_asset_ids = []
            for c in s_data.candidates:
                mid = c.media_asset_id if hasattr(c, "media_asset_id") else c.get("media_asset_id")
                if mid:
                    candidate_asset_ids.append(mid)
            if candidate_asset_ids:
                db.query(MediaAsset).filter(MediaAsset.id.in_(candidate_asset_ids)).update(
                    {"owner_type": "scene", "owner_id": db_scene.id},
                    synchronize_session=False,
                )

        # Build old→new asset ID mapping for reference remapping
        if old_asset_id and db_scene.image_asset_id and old_asset_id != db_scene.image_asset_id:
            asset_id_remap[old_asset_id] = db_scene.image_asset_id
        created_scenes.append(db_scene)

    # Apply deferred environment_reference_id with remapping
    for i, scene in enumerate(created_scenes):
        ref_id = deferred_env_refs[i]
        if ref_id is None:
            continue
        # Remap old asset ID to new one if available
        remapped_id = asset_id_remap.get(ref_id, ref_id)
        # Verify the target asset exists before setting FK
        if db.query(MediaAsset.id).filter(MediaAsset.id == remapped_id).first():
            scene.environment_reference_id = remapped_id
        else:
            logger.warning(
                "[Scene %d] environment_reference_id %d not found (deleted), skipping",
                scene.order,
                ref_id,
            )
