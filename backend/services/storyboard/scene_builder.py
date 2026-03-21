from __future__ import annotations

import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from config import DEFAULT_ENVIRONMENT_REFERENCE_WEIGHT, DEFAULT_REFERENCE_ONLY_WEIGHT, logger
from models.associations import SceneCharacterAction, SceneTag
from models.media_asset import MediaAsset
from models.scene import Scene
from schemas import SceneActionSave

if TYPE_CHECKING:
    from schemas import StoryboardScene
from services.asset_service import AssetService
from services.storage import get_storage
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

    Spread Passthrough: Scene.__table__.columns 자동 수집 후
    관계/계산 필드만 오버라이드. 신규 컬럼 추가 시 매핑 누락 방지.

    Args:
        scene: Scene ORM object
        asset_url_map: Optional mapping of media_asset_id -> URL for candidates
        auto_pin_previous: Whether this scene should auto-pin to previous scene's environment
    """
    # 1. 모든 DB 컬럼 자동 수집
    base = {c.key: getattr(scene, c.key) for c in Scene.__table__.columns}

    # 2. 별칭 필드
    base["scene_id"] = scene.order  # order → scene_id alias

    # 3. 관계 기반 파생 필드
    base["image_url"] = scene.image_url  # @property: image_asset.url
    base["tags"] = [{"tag_id": t.tag_id, "weight": t.weight} for t in scene.tags]
    base["character_actions"] = [
        {
            "character_id": a.character_id,
            "tag_id": a.tag_id,
            "tag_name": a.tag.name if a.tag else None,
            "weight": a.weight,
        }
        for a in scene.character_actions
    ]

    # 4. candidates: 방어 복사 (ORM JSONB 참조 mutation 방지) + URL enrichment
    if scene.candidates:
        if asset_url_map:
            enriched_candidates = []
            for c in scene.candidates:
                enriched = dict(c)
                asset_id = c.get("media_asset_id")
                if asset_id and asset_id in asset_url_map:
                    enriched["image_url"] = asset_url_map[asset_id]
                enriched_candidates.append(enriched)
            base["candidates"] = enriched_candidates
        else:
            base["candidates"] = [dict(c) for c in scene.candidates]

    # 5. 추가 파생 필드
    base["_auto_pin_previous"] = auto_pin_previous
    # ken_burns_preset: DB 컬럼 미존재 — Frontend Scene 타입 호환용 (Cinematographer 출력)
    base["ken_burns_preset"] = getattr(scene, "ken_burns_preset", None)

    return base


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
        # Compute checksum + file_size from storage
        checksum = None
        file_size = None
        try:
            local_path = get_storage().get_local_path(storage_key)
            image_bytes = local_path.read_bytes()
            checksum = AssetService.compute_checksum(image_bytes)
            file_size = len(image_bytes)
        except Exception as e:
            logger.warning("[_link_media_asset] Failed to compute checksum for %s: %s", storage_key, e)

        asset = MediaAsset(
            file_type="image",
            storage_key=storage_key,
            file_name=os.path.basename(storage_key),
            mime_type="image/png",
            owner_type="scene",
            owner_id=db_scene.id,
            checksum=checksum,
            file_size=file_size,
        )
        db.add(asset)
        db.flush()

    db_scene.image_asset_id = asset.id


_SCENE_COLUMN_KEYS: set[str] | None = None


def _get_scene_column_keys() -> set[str]:
    """Scene 모델의 DB 컬럼 이름 집합 (모듈 레벨 캐시)."""
    global _SCENE_COLUMN_KEYS  # noqa: PLW0603
    if _SCENE_COLUMN_KEYS is None:
        _SCENE_COLUMN_KEYS = {c.key for c in Scene.__table__.columns}
    return _SCENE_COLUMN_KEYS


def _build_scene_kwargs(s_data: StoryboardScene, storyboard_id: int, idx: int) -> dict:
    """Pydantic schema → Scene 컬럼 kwargs (Spread Passthrough).

    schema.model_dump()에서 Scene 컬럼에 해당하는 필드만 필터 후
    필수 오버라이드만 적용. 신규 컬럼 추가 시 매핑 누락 방지.
    """
    # 1. schema → dict (관계/특수 필드 제외)
    # image_asset_id: Scene 생성 후 별도 asset linking 로직에서 설정
    _exclude = {
        "tags",
        "character_actions",
        "scene_id",
        "image_asset_id",
        "tts_asset_id",
        "background_id",
        "candidates",
    }
    raw = s_data.model_dump(exclude=_exclude)

    # 2. Scene 컬럼에 해당하는 필드만 필터
    col_keys = _get_scene_column_keys()
    kwargs = {k: v for k, v in raw.items() if k in col_keys}

    # 3. 필수 오버라이드
    kwargs["storyboard_id"] = storyboard_id
    kwargs["order"] = idx
    kwargs["client_id"] = getattr(s_data, "client_id", None) or str(uuid4())
    kwargs["scene_mode"] = getattr(s_data, "scene_mode", "single") or "single"
    kwargs["environment_reference_id"] = None  # Deferred — set after asset remap

    # 4. 기본값 방어
    if kwargs.get("use_reference_only") is None:
        kwargs["use_reference_only"] = True
    if kwargs.get("reference_only_weight") is None:
        kwargs["reference_only_weight"] = DEFAULT_REFERENCE_ONLY_WEIGHT
    if kwargs.get("environment_reference_weight") is None:
        kwargs["environment_reference_weight"] = DEFAULT_ENVIRONMENT_REFERENCE_WEIGHT

    # 5. negative_prompt 방어: 빈 값이면 기본값 주입
    neg = kwargs.get("negative_prompt")
    if not neg or not neg.strip():
        from config import DEFAULT_SCENE_NEGATIVE_PROMPT  # noqa: PLC0415

        kwargs["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT

    # 6. image_url data: URI 방어 (property이므로 kwargs에서 제거)
    kwargs.pop("image_url", None)

    # 7. candidates JSONB 변환
    if s_data.candidates:
        kwargs["candidates"] = _sanitize_candidates_for_db(s_data.candidates)
    else:
        kwargs["candidates"] = None

    return kwargs


def _verify_asset_fks(db: Session, s_data: StoryboardScene, scene_kwargs: dict, idx: int) -> None:
    """Verify tts_asset_id and background_id FK references, set to kwargs if valid."""
    tts_asset_id = getattr(s_data, "tts_asset_id", None)
    if tts_asset_id:
        if db.query(MediaAsset.id).filter(MediaAsset.id == tts_asset_id).first():
            scene_kwargs["tts_asset_id"] = tts_asset_id
        else:
            logger.warning("[Scene %d] tts_asset_id %d not found → null", idx, tts_asset_id)

    background_id = getattr(s_data, "background_id", None)
    if background_id:
        from models.background import Background  # noqa: PLC0415

        if db.query(Background.id).filter(Background.id == background_id).first():
            scene_kwargs["background_id"] = background_id
        else:
            logger.warning("[Scene %d] background_id %d not found → null", idx, background_id)


def _insert_scene_tags_safe(db: Session, db_scene: Scene, tags: list, idx: int) -> None:
    """Insert SceneTag rows, skipping any with invalid tag_id FK."""
    from models.tag import Tag  # noqa: PLC0415

    tag_ids = {t.tag_id for t in tags}
    existing = {r[0] for r in db.query(Tag.id).filter(Tag.id.in_(tag_ids)).all()}
    for t in tags:
        if t.tag_id in existing:
            db.add(SceneTag(scene_id=db_scene.id, tag_id=t.tag_id, weight=t.weight))
        else:
            logger.warning("[Scene %d] tag_id %d not found, skipping", idx, t.tag_id)


def _insert_scene_actions_safe(db: Session, db_scene: Scene, actions: list[SceneActionSave], idx: int) -> None:
    """Insert SceneCharacterAction rows, skipping invalid character_id FK."""
    from models.character import Character  # noqa: PLC0415

    resolved = resolve_action_tag_ids(actions, db)
    char_ids = {a.character_id for a in resolved}
    existing = {r[0] for r in db.query(Character.id).filter(Character.id.in_(char_ids)).all()}
    for a in resolved:
        if a.character_id not in existing:
            logger.warning("[Scene %d] character_id %d not found, skipping", idx, a.character_id)
            continue
        db.add(
            SceneCharacterAction(
                scene_id=db_scene.id,
                character_id=a.character_id,
                tag_id=a.tag_id,
                weight=a.weight,
            )
        )


def create_scenes(
    db: Session,
    storyboard_id: int,
    scenes_data: list[StoryboardScene],
    existing_asset_map: dict[str, dict[str, int | None]] | None = None,
) -> None:
    """Create scenes with tags and character actions for a storyboard.

    Args:
        existing_asset_map: Optional mapping of client_id → {image_asset_id, tts_asset_id}
            from previously existing scenes. Used to preserve assets when Frontend sends
            stale autoSave payloads without asset IDs.
    """
    asset_id_remap: dict[int, int] = {}
    created_scenes: list[Scene] = []
    deferred_env_refs: list[int | None] = []

    for idx, s_data in enumerate(scenes_data):
        image_url = s_data.image_url
        if image_url and image_url.startswith("data:"):
            image_url = None

        deferred_env_refs.append(s_data.environment_reference_id)
        scene_kwargs = _build_scene_kwargs(s_data, storyboard_id, idx)

        # Verify FK references (tts_asset_id, background_id) before Scene creation
        _verify_asset_fks(db, s_data, scene_kwargs, idx)

        db_scene = Scene(**scene_kwargs)
        db.add(db_scene)
        db.flush()

        if s_data.tags:
            _insert_scene_tags_safe(db, db_scene, s_data.tags, idx)

        if s_data.character_actions:
            _insert_scene_actions_safe(db, db_scene, s_data.character_actions, idx)

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

        # Stale-payload recovery: re-link assets from existing scenes by client_id.
        # When Frontend sends autoSave without image_asset_id (e.g. after server restart),
        # match by client_id and preserve the existing asset.
        if existing_asset_map and s_data.client_id and s_data.client_id in existing_asset_map:
            prev = existing_asset_map[s_data.client_id]
            if not db_scene.image_asset_id and prev.get("image_asset_id"):
                prev_img = prev["image_asset_id"]
                if db.query(MediaAsset.id).filter(MediaAsset.id == prev_img).first():
                    db_scene.image_asset_id = prev_img
                    db.query(MediaAsset).filter(MediaAsset.id == prev_img).update(
                        {"owner_type": "scene", "owner_id": db_scene.id},
                        synchronize_session=False,
                    )
                    logger.info("[Scene %d] Preserved image_asset_id %d from previous scene", idx, prev_img)
            if not db_scene.tts_asset_id and prev.get("tts_asset_id"):
                prev_tts = prev["tts_asset_id"]
                if db.query(MediaAsset.id).filter(MediaAsset.id == prev_tts).first():
                    db_scene.tts_asset_id = prev_tts
                    db.query(MediaAsset).filter(MediaAsset.id == prev_tts).update(
                        {"owner_type": "scene", "owner_id": db_scene.id},
                        synchronize_session=False,
                    )
                    logger.info("[Scene %d] Preserved tts_asset_id %d from previous scene", idx, prev_tts)
            if not deferred_env_refs[idx] and prev.get("environment_reference_id"):
                deferred_env_refs[idx] = prev["environment_reference_id"]
                logger.info(
                    "[Scene %d] Preserved environment_reference_id %d from previous scene",
                    idx,
                    prev["environment_reference_id"],
                )

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
