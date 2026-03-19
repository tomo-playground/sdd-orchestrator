"""Test: Storyboard update preserves video/audio assets (render outputs).

Root cause regression test for the bug where every storyboard save deleted
all storyboard-owned MediaAssets (including videos), causing render_history
CASCADE deletion.
"""

from fastapi.testclient import TestClient


def _create_storyboard(client: TestClient) -> int:
    payload = {"title": "Video Preserve Test", "description": "test", "group_id": 1, "scenes": []}
    res = client.post("/api/v1/storyboards", json=payload)
    assert res.status_code == 200
    return res.json()["storyboard_id"]


def _seed_media_asset(db_session, storyboard_id: int, file_type: str, suffix: str = "") -> int:
    from models.media_asset import MediaAsset

    asset = MediaAsset(
        owner_type="storyboard",
        owner_id=storyboard_id,
        file_type=file_type,
        storage_key=f"test/{storyboard_id}/{file_type}{suffix}.dat",
        file_name=f"{file_type}{suffix}.dat",
    )
    db_session.add(asset)
    db_session.commit()
    return asset.id


class TestVideoPreservationOnUpdate:
    """Storyboard PUT must NOT delete video/audio assets."""

    def test_video_asset_survives_update(self, client: TestClient, db_session):
        """video file_type asset is preserved after storyboard update."""
        from models.media_asset import MediaAsset

        sb_id = _create_storyboard(client)
        video_id = _seed_media_asset(db_session, sb_id, "video")

        # Update storyboard
        res = client.put(
            f"/api/v1/storyboards/{sb_id}",
            json={
                "title": "Updated",
                "description": "test",
                "scenes": [],
            },
        )
        assert res.status_code == 200

        # Video asset must still exist
        asset = db_session.get(MediaAsset, video_id)
        assert asset is not None, "Video MediaAsset was deleted during storyboard update!"

    def test_audio_asset_survives_update(self, client: TestClient, db_session):
        """audio file_type asset (BGM) is preserved after storyboard update."""
        from models.media_asset import MediaAsset

        sb_id = _create_storyboard(client)
        audio_id = _seed_media_asset(db_session, sb_id, "audio")

        res = client.put(
            f"/api/v1/storyboards/{sb_id}",
            json={
                "title": "Updated",
                "description": "test",
                "scenes": [],
            },
        )
        assert res.status_code == 200

        asset = db_session.get(MediaAsset, audio_id)
        assert asset is not None, "Audio MediaAsset was deleted during storyboard update!"

    def test_non_render_asset_deleted_on_update(self, client: TestClient, db_session):
        """Non-render assets (cache, image) are still deleted on update."""
        from models.media_asset import MediaAsset

        sb_id = _create_storyboard(client)
        cache_id = _seed_media_asset(db_session, sb_id, "cache")

        res = client.put(
            f"/api/v1/storyboards/{sb_id}",
            json={
                "title": "Updated",
                "description": "test",
                "scenes": [],
            },
        )
        assert res.status_code == 200

        asset = db_session.get(MediaAsset, cache_id)
        assert asset is None, "Cache asset should be deleted during update"

    def test_mixed_assets_selective_deletion(self, client: TestClient, db_session):
        """Video + audio survive, cache + image deleted — selective preservation."""
        from models.media_asset import MediaAsset

        sb_id = _create_storyboard(client)
        video_id = _seed_media_asset(db_session, sb_id, "video")
        audio_id = _seed_media_asset(db_session, sb_id, "audio")
        cache_id = _seed_media_asset(db_session, sb_id, "cache")
        image_id = _seed_media_asset(db_session, sb_id, "image", "_thumb")

        res = client.put(
            f"/api/v1/storyboards/{sb_id}",
            json={
                "title": "Updated",
                "description": "test",
                "scenes": [],
            },
        )
        assert res.status_code == 200

        # Render outputs preserved
        assert db_session.get(MediaAsset, video_id) is not None
        assert db_session.get(MediaAsset, audio_id) is not None
        # Non-render assets deleted
        assert db_session.get(MediaAsset, cache_id) is None
        assert db_session.get(MediaAsset, image_id) is None
