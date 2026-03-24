"""Tests for scene_ids ordering in storyboard POST/PUT responses.

Bug: Storyboard.scenes relationship had no order_by, causing scene_ids
to be returned in undefined order. Frontend maps scene_ids[i] → scenes[i],
so wrong ordering leads to ID/asset mismatch (Scene 1 gets Scene 2's ID, etc).

Fix: Added order_by=Scene.order to relationship + explicit sorted() in responses.
"""

from tests.conftest import create_test_storyboard


def test_post_scene_ids_match_creation_order(client):
    """POST /storyboards returns scene_ids in the same order as the input scenes array."""
    scenes = [
        {"scene_id": 0, "script": "Scene A", "speaker": "narrator", "duration": 3, "image_prompt": "cafe"},
        {"scene_id": 1, "script": "Scene B", "speaker": "speaker_1", "duration": 4, "image_prompt": "park"},
        {"scene_id": 2, "script": "Scene C", "speaker": "speaker_2", "duration": 2, "image_prompt": "school"},
    ]
    data = create_test_storyboard(client, scenes=scenes)
    scene_ids = data["scene_ids"]

    assert len(scene_ids) == 3
    # IDs must be strictly ascending (created sequentially → sequential IDs → order matches)
    assert scene_ids == sorted(scene_ids), f"scene_ids not in ascending order: {scene_ids}"


def test_put_scene_ids_match_creation_order(client):
    """PUT /storyboards/{id} returns scene_ids in the same order as the input scenes array."""
    # Create initial storyboard with 3 scenes
    initial = create_test_storyboard(
        client,
        scenes=[
            {"scene_id": 0, "script": "Old A", "speaker": "narrator", "duration": 3, "image_prompt": "a"},
            {"scene_id": 1, "script": "Old B", "speaker": "speaker_1", "duration": 3, "image_prompt": "b"},
            {"scene_id": 2, "script": "Old C", "speaker": "speaker_2", "duration": 3, "image_prompt": "c"},
        ],
    )
    sb_id = initial["storyboard_id"]
    old_ids = initial["scene_ids"]
    assert len(old_ids) == 3

    # Update with new scenes (simulates autopilot persist after images)
    new_scenes = [
        {"scene_id": 0, "script": "New A", "speaker": "narrator", "duration": 3, "image_prompt": "x"},
        {"scene_id": 1, "script": "New B", "speaker": "speaker_1", "duration": 4, "image_prompt": "y"},
        {"scene_id": 2, "script": "New C", "speaker": "speaker_2", "duration": 2, "image_prompt": "z"},
        {"scene_id": 3, "script": "New D", "speaker": "narrator", "duration": 3, "image_prompt": "w"},
    ]
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Updated",
            "group_id": 1,
            "scenes": new_scenes,
        },
    )
    assert resp.status_code == 200

    new_ids = resp.json()["scene_ids"]
    assert len(new_ids) == 4
    # New IDs must be in ascending order (matches scene order)
    assert new_ids == sorted(new_ids), f"PUT scene_ids not in ascending order: {new_ids}"


def test_put_scene_ids_sequential_matches_order_column(client, db_session):
    """Verify scene_ids[i] corresponds to scene with order=i in the DB."""
    from models.scene import Scene

    data = create_test_storyboard(
        client,
        scenes=[
            {"scene_id": 0, "script": "First", "speaker": "narrator", "duration": 3, "image_prompt": "a"},
            {"scene_id": 1, "script": "Second", "speaker": "speaker_1", "duration": 3, "image_prompt": "b"},
            {"scene_id": 2, "script": "Third", "speaker": "speaker_2", "duration": 3, "image_prompt": "c"},
        ],
    )
    sb_id = data["storyboard_id"]

    # Now PUT to recreate scenes
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "Re-created",
            "group_id": 1,
            "scenes": [
                {"scene_id": 0, "script": "New First", "speaker": "narrator", "duration": 3, "image_prompt": "x"},
                {"scene_id": 1, "script": "New Second", "speaker": "speaker_1", "duration": 4, "image_prompt": "y"},
                {"scene_id": 2, "script": "New Third", "speaker": "speaker_2", "duration": 2, "image_prompt": "z"},
            ],
        },
    )
    assert resp.status_code == 200
    scene_ids = resp.json()["scene_ids"]

    # Verify each scene_ids[i] has order=i in the DB
    for i, sid in enumerate(scene_ids):
        scene = db_session.query(Scene).filter(Scene.id == sid).first()
        assert scene is not None, f"Scene {sid} not found in DB"
        assert scene.order == i, f"scene_ids[{i}]={sid} has order={scene.order}, expected {i}"


def test_put_preserves_image_asset_id_mapping(client, db_session):
    """PUT preserves image_asset_id for each scene in the correct order."""
    from models.media_asset import MediaAsset

    # Create storyboard
    data = create_test_storyboard(
        client,
        scenes=[
            {"scene_id": 0, "script": "S1", "speaker": "narrator", "duration": 3, "image_prompt": "a"},
            {"scene_id": 1, "script": "S2", "speaker": "speaker_1", "duration": 3, "image_prompt": "b"},
            {"scene_id": 2, "script": "S3", "speaker": "speaker_2", "duration": 3, "image_prompt": "c"},
        ],
    )
    sb_id = data["storyboard_id"]
    scene_ids = data["scene_ids"]

    # Simulate image storage: create MediaAssets for scene 0 and scene 2 (not 1)
    asset_for_scene_0 = MediaAsset(
        file_name="scene_0.png",
        file_type="image",
        storage_key="test/s0.png",
        owner_type="scene",
        owner_id=scene_ids[0],
        file_size=100,
        mime_type="image/png",
    )
    asset_for_scene_2 = MediaAsset(
        file_name="scene_2.png",
        file_type="image",
        storage_key="test/s2.png",
        owner_type="scene",
        owner_id=scene_ids[2],
        file_size=100,
        mime_type="image/png",
    )
    db_session.add_all([asset_for_scene_0, asset_for_scene_2])
    db_session.flush()

    # PUT with image_asset_id: scene 0 and 2 have assets, scene 1 does not
    resp = client.put(
        f"/api/v1/storyboards/{sb_id}",
        json={
            "title": "With Images",
            "group_id": 1,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "S1",
                    "speaker": "narrator",
                    "duration": 3,
                    "image_prompt": "a",
                    "image_asset_id": asset_for_scene_0.id,
                },
                {
                    "scene_id": 1,
                    "script": "S2",
                    "speaker": "speaker_1",
                    "duration": 3,
                    "image_prompt": "b",
                    "image_asset_id": None,
                },
                {
                    "scene_id": 2,
                    "script": "S3",
                    "speaker": "speaker_2",
                    "duration": 3,
                    "image_prompt": "c",
                    "image_asset_id": asset_for_scene_2.id,
                },
            ],
        },
    )
    assert resp.status_code == 200
    new_scene_ids = resp.json()["scene_ids"]
    assert len(new_scene_ids) == 3

    # Verify: scene at order=0 has asset_for_scene_0, order=1 has NULL, order=2 has asset_for_scene_2
    from models.scene import Scene

    for i, sid in enumerate(new_scene_ids):
        scene = db_session.query(Scene).filter(Scene.id == sid).first()
        assert scene is not None
        if i == 0:
            assert scene.image_asset_id == asset_for_scene_0.id, (
                f"Scene order=0 should have asset {asset_for_scene_0.id}, got {scene.image_asset_id}"
            )
        elif i == 1:
            assert scene.image_asset_id is None, f"Scene order=1 should have no asset, got {scene.image_asset_id}"
        elif i == 2:
            assert scene.image_asset_id == asset_for_scene_2.id, (
                f"Scene order=2 should have asset {asset_for_scene_2.id}, got {scene.image_asset_id}"
            )


def test_multiple_puts_maintain_order_consistency(client):
    """Multiple consecutive PUTs always return scene_ids in correct order."""
    data = create_test_storyboard(
        client,
        scenes=[
            {"scene_id": 0, "script": "A", "speaker": "narrator", "duration": 3, "image_prompt": "a"},
        ],
    )
    sb_id = data["storyboard_id"]

    # Do 5 consecutive PUTs, each time adding a scene
    for n in range(2, 7):
        scenes = [
            {"scene_id": i, "script": f"S{i}", "speaker": "narrator", "duration": 3, "image_prompt": f"p{i}"}
            for i in range(n)
        ]
        resp = client.put(
            f"/api/v1/storyboards/{sb_id}",
            json={
                "title": f"Round {n}",
                "group_id": 1,
                "scenes": scenes,
            },
        )
        assert resp.status_code == 200
        ids = resp.json()["scene_ids"]
        assert len(ids) == n, f"Round {n}: expected {n} scene_ids, got {len(ids)}"
        assert ids == sorted(ids), f"Round {n}: scene_ids not in order: {ids}"
