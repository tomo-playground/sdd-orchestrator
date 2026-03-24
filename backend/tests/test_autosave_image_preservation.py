"""Tests for autoSave image/tts asset preservation during storyboard update.

Bug: PUT /storyboards/{id} with scenes missing image_asset_id would delete
existing scenes and create new ones without re-linking assets → image loss.

Fix: Backend collects existing scene asset mappings (by client_id) before
deletion and re-links them to new scenes when incoming data has no asset_id.
"""

from models.media_asset import MediaAsset
from models.scene import Scene
from tests.conftest import create_test_storyboard


def _create_media_asset(db, owner_type="scene", owner_id=1, file_type="image"):
    """Create a MediaAsset for testing."""
    asset = MediaAsset(
        file_type=file_type,
        storage_key=f"test/{owner_type}_{owner_id}.png",
        file_name=f"{owner_type}_{owner_id}.png",
        mime_type="image/png",
        owner_type=owner_type,
        owner_id=owner_id,
    )
    db.add(asset)
    db.flush()
    return asset


def test_autosave_preserves_image_asset_id(client, db_session):
    """autoSave(PUT /storyboards/{id}) 시 scene에 image_asset_id가 없으면
    기존 DB의 image_asset_id를 보존해야 한다."""
    # 1. Create storyboard with scenes that have client_id
    scenes = [
        {
            "scene_id": 0,
            "script": "Scene A",
            "speaker": "narrator",
            "duration": 3,
            "image_prompt": "cafe",
            "client_id": "client-a",
        },
        {
            "scene_id": 1,
            "script": "Scene B",
            "speaker": "speaker_1",
            "duration": 4,
            "image_prompt": "park",
            "client_id": "client-b",
        },
    ]
    data = create_test_storyboard(client, scenes=scenes)
    sb_id = data["storyboard_id"]

    # 2. Attach image_asset_id to scenes directly in DB (simulates image generation)
    db_scenes = (
        db_session.query(Scene)
        .filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )
    assert len(db_scenes) == 2

    asset_a = _create_media_asset(db_session, owner_type="scene", owner_id=db_scenes[0].id)
    asset_b = _create_media_asset(db_session, owner_type="scene", owner_id=db_scenes[1].id)
    db_scenes[0].image_asset_id = asset_a.id
    db_scenes[1].image_asset_id = asset_b.id
    db_session.commit()

    # 3. PUT with same client_ids but NO image_asset_id (simulates stale autoSave)
    stale_scenes = [
        {
            "scene_id": 0,
            "script": "Scene A",
            "speaker": "narrator",
            "duration": 3,
            "image_prompt": "cafe",
            "client_id": "client-a",
        },
        {
            "scene_id": 1,
            "script": "Scene B",
            "speaker": "speaker_1",
            "duration": 4,
            "image_prompt": "park",
            "client_id": "client-b",
        },
    ]
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Updated",
            "group_id": 1,
            "scenes": stale_scenes,
        },
    )
    assert resp.status_code == 200

    # 4. Verify image_asset_id preserved on new scenes
    new_scenes = (
        db_session.query(Scene)
        .filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )
    assert len(new_scenes) == 2
    assert new_scenes[0].image_asset_id == asset_a.id, (
        f"Scene A lost image_asset_id: expected {asset_a.id}, got {new_scenes[0].image_asset_id}"
    )
    assert new_scenes[1].image_asset_id == asset_b.id, (
        f"Scene B lost image_asset_id: expected {asset_b.id}, got {new_scenes[1].image_asset_id}"
    )


def test_autosave_does_not_replace_scenes_when_explicit_asset(client, db_session):
    """image_asset_id를 명시적으로 보내면 그 값이 사용되어야 한다."""
    scenes = [
        {
            "scene_id": 0,
            "script": "Test",
            "speaker": "narrator",
            "duration": 3,
            "image_prompt": "x",
            "client_id": "client-x",
        },
    ]
    data = create_test_storyboard(client, scenes=scenes)
    sb_id = data["storyboard_id"]

    # Attach old asset
    db_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    old_asset = _create_media_asset(db_session, owner_type="scene", owner_id=db_scene.id)
    db_scene.image_asset_id = old_asset.id
    db_session.commit()

    # Create a new asset to use explicitly
    new_asset = _create_media_asset(db_session, owner_type="scene", owner_id=0)
    db_session.commit()

    # PUT with explicit new image_asset_id
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Updated",
            "group_id": 1,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "Test",
                    "speaker": "narrator",
                    "duration": 3,
                    "image_prompt": "x",
                    "client_id": "client-x",
                    "image_asset_id": new_asset.id,
                },
            ],
        },
    )
    assert resp.status_code == 200

    new_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    assert new_scene.image_asset_id == new_asset.id, "Explicit image_asset_id should be used, not the preserved one"


def test_autosave_preserves_tts_asset_id(client, db_session):
    """autoSave 시 tts_asset_id도 보존되어야 한다."""
    scenes = [
        {
            "scene_id": 0,
            "script": "TTS test",
            "speaker": "narrator",
            "duration": 3,
            "image_prompt": "voice",
            "client_id": "client-tts",
        },
    ]
    data = create_test_storyboard(client, scenes=scenes)
    sb_id = data["storyboard_id"]

    # Attach tts_asset_id directly in DB
    db_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    tts_asset = _create_media_asset(db_session, owner_type="scene", owner_id=db_scene.id, file_type="audio")
    db_scene.tts_asset_id = tts_asset.id
    db_session.commit()

    # PUT without tts_asset_id (stale autoSave)
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Updated",
            "group_id": 1,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "TTS test",
                    "speaker": "narrator",
                    "duration": 3,
                    "image_prompt": "voice",
                    "client_id": "client-tts",
                },
            ],
        },
    )
    assert resp.status_code == 200

    new_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    assert new_scene.tts_asset_id == tts_asset.id, (
        f"tts_asset_id lost: expected {tts_asset.id}, got {new_scene.tts_asset_id}"
    )


def test_autosave_preserves_environment_reference_id(client, db_session):
    """autoSave 시 environment_reference_id도 보존되어야 한다."""
    scenes = [
        {
            "scene_id": 0,
            "script": "Env test",
            "speaker": "narrator",
            "duration": 3,
            "image_prompt": "forest",
            "client_id": "client-env",
        },
    ]
    data = create_test_storyboard(client, scenes=scenes)
    sb_id = data["storyboard_id"]

    # Attach environment_reference_id (an image asset used as env reference)
    db_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    env_asset = _create_media_asset(db_session, owner_type="scene", owner_id=db_scene.id)
    db_scene.environment_reference_id = env_asset.id
    db_session.commit()

    # PUT without environment_reference_id (stale autoSave)
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Updated",
            "group_id": 1,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "Env test",
                    "speaker": "narrator",
                    "duration": 3,
                    "image_prompt": "forest",
                    "client_id": "client-env",
                },
            ],
        },
    )
    assert resp.status_code == 200

    new_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    assert new_scene.environment_reference_id == env_asset.id, (
        f"environment_reference_id lost: expected {env_asset.id}, got {new_scene.environment_reference_id}"
    )


def test_autosave_no_false_preservation_without_client_id(client, db_session):
    """client_id가 없으면 보존하지 않는다 (매칭 불가)."""
    scenes = [
        {"scene_id": 0, "script": "No client", "speaker": "narrator", "duration": 3, "image_prompt": "x"},
    ]
    data = create_test_storyboard(client, scenes=scenes)
    sb_id = data["storyboard_id"]

    db_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    asset = _create_media_asset(db_session, owner_type="scene", owner_id=db_scene.id)
    db_scene.image_asset_id = asset.id
    db_session.commit()

    # PUT with different client_id — no match
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Updated",
            "group_id": 1,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "Different scene",
                    "speaker": "narrator",
                    "duration": 3,
                    "image_prompt": "y",
                    "client_id": "brand-new",
                },
            ],
        },
    )
    assert resp.status_code == 200

    new_scene = db_session.query(Scene).filter(Scene.storyboard_id == sb_id, Scene.deleted_at.is_(None)).first()
    # New client_id → old asset must NOT be carried over to a different scene
    assert new_scene.image_asset_id is None, (
        f"Old asset incorrectly assigned to new scene: got {new_scene.image_asset_id}"
    )
