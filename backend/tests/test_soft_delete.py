"""Tests for Soft Delete (Phase 6-7 #4~#6).

Covers:
- Soft delete sets deleted_at, excludes from default queries
- Trash endpoints return only deleted items
- Restore clears deleted_at, item reappears in default queries
- Permanent delete removes from DB completely
- Storyboard soft delete preserves scenes
"""

from tests.conftest import create_test_storyboard

# ============================================================
# Storyboard Soft Delete
# ============================================================


class TestStoryboardSoftDelete:
    def test_soft_delete_excludes_from_list(self, client):
        """Soft-deleted storyboard should not appear in default list."""
        data = create_test_storyboard(client, title="To Delete")
        sb_id = data["storyboard_id"]

        # Delete (soft)
        resp = client.delete(f"/api/v1/storyboards/{sb_id}")
        assert resp.status_code == 200

        # Should not appear in list
        resp = client.get("/api/v1/storyboards?group_id=1")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["items"]]
        assert sb_id not in ids

    def test_soft_delete_excludes_from_get(self, client):
        """Soft-deleted storyboard should return 404 on direct get."""
        data = create_test_storyboard(client, title="Hidden")
        sb_id = data["storyboard_id"]

        client.delete(f"/api/v1/storyboards/{sb_id}")

        resp = client.get(f"/api/v1/storyboards/{sb_id}")
        assert resp.status_code == 404

    def test_trash_returns_deleted(self, client):
        """Trash endpoint should return soft-deleted storyboards."""
        data = create_test_storyboard(client, title="Trashed SB")
        sb_id = data["storyboard_id"]

        client.delete(f"/api/v1/storyboards/{sb_id}")

        resp = client.get("/api/v1/storyboards/trash")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert sb_id in ids

    def test_restore_recovers(self, client):
        """Restored storyboard should reappear in default list."""
        data = create_test_storyboard(client, title="Restore Me")
        sb_id = data["storyboard_id"]

        client.delete(f"/api/v1/storyboards/{sb_id}")

        # Restore
        resp = client.post(f"/api/v1/storyboards/{sb_id}/restore")
        assert resp.status_code == 200

        # Should appear in list again
        resp = client.get("/api/v1/storyboards?group_id=1")
        ids = [s["id"] for s in resp.json()["items"]]
        assert sb_id in ids

        # Should not be in trash
        resp = client.get("/api/v1/storyboards/trash")
        ids = [s["id"] for s in resp.json()]
        assert sb_id not in ids

    def test_permanent_delete_removes(self, client):
        """Permanent delete should remove from DB entirely."""
        data = create_test_storyboard(client, title="Perm Delete")
        sb_id = data["storyboard_id"]

        # Soft delete first
        client.delete(f"/api/v1/storyboards/{sb_id}")

        # Permanent delete (admin endpoint)
        resp = client.delete(f"/api/admin/storyboards/{sb_id}/permanent")
        assert resp.status_code == 200

        # Gone from trash
        resp = client.get("/api/v1/storyboards/trash")
        ids = [s["id"] for s in resp.json()]
        assert sb_id not in ids

        # Gone from direct get (404)
        resp = client.get(f"/api/v1/storyboards/{sb_id}")
        assert resp.status_code == 404

    def test_soft_delete_preserves_scenes(self, client, db_session):
        """Soft-deleted storyboard should keep its scenes intact."""
        from models.scene import Scene

        scenes = [
            {
                "scene_id": 0,
                "script": "Test scene",
                "speaker": "narrator",
                "duration": 3.0,
                "image_prompt": "test",
                "image_prompt_ko": "test",
                "negative_prompt": "",
                "width": 512,
                "height": 768,
            }
        ]
        data = create_test_storyboard(client, title="With Scenes", scenes=scenes)
        sb_id = data["storyboard_id"]

        # Soft delete
        client.delete(f"/api/v1/storyboards/{sb_id}")

        # Scenes still in DB
        count = db_session.query(Scene).filter(Scene.storyboard_id == sb_id).count()
        assert count == 1

    def test_double_soft_delete_returns_404(self, client):
        """Deleting an already soft-deleted storyboard should return 404."""
        data = create_test_storyboard(client, title="Double Delete")
        sb_id = data["storyboard_id"]

        client.delete(f"/api/v1/storyboards/{sb_id}")
        resp = client.delete(f"/api/v1/storyboards/{sb_id}")
        assert resp.status_code == 404

    def test_restore_only_batch_deleted_scenes(self, client, db_session):
        """Restore should only recover scenes deleted with the storyboard, not individually deleted scenes."""
        import time
        from datetime import UTC, datetime

        from models.scene import Scene

        scenes = [
            {
                "scene_id": 0,
                "script": "Scene A",
                "speaker": "narrator",
                "duration": 3.0,
                "image_prompt": "a",
                "image_prompt_ko": "a",
                "negative_prompt": "",
                "width": 512,
                "height": 768,
            },
            {
                "scene_id": 0,
                "script": "Scene B",
                "speaker": "narrator",
                "duration": 3.0,
                "image_prompt": "b",
                "image_prompt_ko": "b",
                "negative_prompt": "",
                "width": 512,
                "height": 768,
            },
        ]
        data = create_test_storyboard(client, title="Batch Test", scenes=scenes)
        sb_id = data["storyboard_id"]
        scene_ids = data["scene_ids"]
        assert len(scene_ids) == 2

        # Individually soft-delete Scene A (earlier, separate timestamp)
        scene_a = db_session.query(Scene).filter(Scene.id == scene_ids[0]).first()
        scene_a.deleted_at = datetime(2020, 1, 1, tzinfo=UTC)
        db_session.commit()

        # Small delay so storyboard gets a different timestamp
        time.sleep(0.01)

        # Now soft-delete the storyboard (cascade deletes Scene B)
        resp = client.delete(f"/api/v1/storyboards/{sb_id}")
        assert resp.status_code == 200

        # Verify: both scenes have deleted_at set but with different timestamps
        db_session.expire_all()
        scene_a = db_session.query(Scene).filter(Scene.id == scene_ids[0]).first()
        scene_b = db_session.query(Scene).filter(Scene.id == scene_ids[1]).first()
        assert scene_a.deleted_at is not None
        assert scene_b.deleted_at is not None
        assert scene_a.deleted_at != scene_b.deleted_at  # Different timestamps

        # Restore storyboard
        resp = client.post(f"/api/v1/storyboards/{sb_id}/restore")
        assert resp.status_code == 200

        # Scene B (batch-deleted) should be restored
        db_session.expire_all()
        scene_b = db_session.query(Scene).filter(Scene.id == scene_ids[1]).first()
        assert scene_b.deleted_at is None, "Batch-deleted scene should be restored"

        # Scene A (individually deleted) should remain deleted
        scene_a = db_session.query(Scene).filter(Scene.id == scene_ids[0]).first()
        assert scene_a.deleted_at is not None, "Individually deleted scene should stay deleted"

    def test_scenes_soft_deleted_with_same_timestamp(self, client, db_session):
        """Storyboard soft-delete should set same deleted_at on parent and child scenes."""
        from models.scene import Scene
        from models.storyboard import Storyboard

        scenes = [
            {
                "scene_id": 0,
                "script": "Test",
                "speaker": "N",
                "duration": 3.0,
                "image_prompt": "x",
                "image_prompt_ko": "x",
                "negative_prompt": "",
                "width": 512,
                "height": 768,
            },
        ]
        data = create_test_storyboard(client, title="Timestamp Test", scenes=scenes)
        sb_id = data["storyboard_id"]
        scene_id = data["scene_ids"][0]

        client.delete(f"/api/v1/storyboards/{sb_id}")

        db_session.expire_all()
        sb = db_session.query(Storyboard).filter(Storyboard.id == sb_id).first()
        scene = db_session.query(Scene).filter(Scene.id == scene_id).first()

        assert sb.deleted_at is not None
        assert scene.deleted_at is not None
        assert sb.deleted_at == scene.deleted_at, "Parent and child should share same timestamp"


# ============================================================
# Character Soft Delete
# ============================================================


class TestCharacterSoftDelete:
    def _create_character(self, client, name: str) -> int:
        resp = client.post("/api/v1/characters", json={"name": name, "group_id": 1})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_soft_delete_excludes_from_list(self, client):
        cid = self._create_character(client, "DelChar")
        client.delete(f"/api/v1/characters/{cid}")

        resp = client.get("/api/v1/characters")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["items"]]
        assert cid not in ids

    def test_soft_delete_excludes_from_get(self, client):
        cid = self._create_character(client, "HiddenChar")
        client.delete(f"/api/v1/characters/{cid}")

        resp = client.get(f"/api/v1/characters/{cid}")
        assert resp.status_code == 404

    def test_trash_returns_deleted(self, client):
        cid = self._create_character(client, "TrashChar")
        client.delete(f"/api/v1/characters/{cid}")

        resp = client.get("/api/v1/characters/trash")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert cid in ids

    def test_restore_recovers(self, client):
        cid = self._create_character(client, "RestoreChar")
        client.delete(f"/api/v1/characters/{cid}")

        resp = client.post(f"/api/v1/characters/{cid}/restore")
        assert resp.status_code == 200

        resp = client.get("/api/v1/characters")
        ids = [c["id"] for c in resp.json()["items"]]
        assert cid in ids

    def test_permanent_delete_removes(self, client):
        cid = self._create_character(client, "PermChar")
        client.delete(f"/api/v1/characters/{cid}")

        resp = client.delete(f"/api/admin/characters/{cid}/permanent")
        assert resp.status_code == 200

        resp = client.get("/api/v1/characters/trash")
        ids = [c["id"] for c in resp.json()]
        assert cid not in ids
