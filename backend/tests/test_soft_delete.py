"""Tests for Soft Delete (Phase 6-7 #4~#6).

Covers:
- Soft delete sets deleted_at, excludes from default queries
- Trash endpoints return only deleted items
- Restore clears deleted_at, item reappears in default queries
- Permanent delete removes from DB completely
- Storyboard soft delete preserves scenes
"""

import pytest
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
        resp = client.delete(f"/storyboards/{sb_id}")
        assert resp.status_code == 200

        # Should not appear in list
        resp = client.get("/storyboards?group_id=1")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert sb_id not in ids

    def test_soft_delete_excludes_from_get(self, client):
        """Soft-deleted storyboard should return 404 on direct get."""
        data = create_test_storyboard(client, title="Hidden")
        sb_id = data["storyboard_id"]

        client.delete(f"/storyboards/{sb_id}")

        resp = client.get(f"/storyboards/{sb_id}")
        assert resp.status_code == 404

    def test_trash_returns_deleted(self, client):
        """Trash endpoint should return soft-deleted storyboards."""
        data = create_test_storyboard(client, title="Trashed SB")
        sb_id = data["storyboard_id"]

        client.delete(f"/storyboards/{sb_id}")

        resp = client.get("/storyboards/trash")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()]
        assert sb_id in ids

    def test_restore_recovers(self, client):
        """Restored storyboard should reappear in default list."""
        data = create_test_storyboard(client, title="Restore Me")
        sb_id = data["storyboard_id"]

        client.delete(f"/storyboards/{sb_id}")

        # Restore
        resp = client.post(f"/storyboards/{sb_id}/restore")
        assert resp.status_code == 200

        # Should appear in list again
        resp = client.get("/storyboards?group_id=1")
        ids = [s["id"] for s in resp.json()]
        assert sb_id in ids

        # Should not be in trash
        resp = client.get("/storyboards/trash")
        ids = [s["id"] for s in resp.json()]
        assert sb_id not in ids

    def test_permanent_delete_removes(self, client):
        """Permanent delete should remove from DB entirely."""
        data = create_test_storyboard(client, title="Perm Delete")
        sb_id = data["storyboard_id"]

        # Soft delete first
        client.delete(f"/storyboards/{sb_id}")

        # Permanent delete
        resp = client.delete(f"/storyboards/{sb_id}/permanent")
        assert resp.status_code == 200

        # Gone from trash
        resp = client.get("/storyboards/trash")
        ids = [s["id"] for s in resp.json()]
        assert sb_id not in ids

        # Gone from direct get (404)
        resp = client.get(f"/storyboards/{sb_id}")
        assert resp.status_code == 404

    def test_soft_delete_preserves_scenes(self, client, db_session):
        """Soft-deleted storyboard should keep its scenes intact."""
        from models.scene import Scene

        scenes = [
            {
                "scene_id": 0,
                "script": "Test scene",
                "speaker": "Narrator",
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
        client.delete(f"/storyboards/{sb_id}")

        # Scenes still in DB
        count = db_session.query(Scene).filter(Scene.storyboard_id == sb_id).count()
        assert count == 1

    def test_double_soft_delete_returns_404(self, client):
        """Deleting an already soft-deleted storyboard should return 404."""
        data = create_test_storyboard(client, title="Double Delete")
        sb_id = data["storyboard_id"]

        client.delete(f"/storyboards/{sb_id}")
        resp = client.delete(f"/storyboards/{sb_id}")
        assert resp.status_code == 404


# ============================================================
# Character Soft Delete
# ============================================================


class TestCharacterSoftDelete:
    def _create_character(self, client, name: str) -> int:
        resp = client.post("/characters", json={"name": name})
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_soft_delete_excludes_from_list(self, client):
        cid = self._create_character(client, "DelChar")
        client.delete(f"/characters/{cid}")

        resp = client.get("/characters")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert cid not in ids

    def test_soft_delete_excludes_from_get(self, client):
        cid = self._create_character(client, "HiddenChar")
        client.delete(f"/characters/{cid}")

        resp = client.get(f"/characters/{cid}")
        assert resp.status_code == 404

    def test_trash_returns_deleted(self, client):
        cid = self._create_character(client, "TrashChar")
        client.delete(f"/characters/{cid}")

        resp = client.get("/characters/trash")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert cid in ids

    def test_restore_recovers(self, client):
        cid = self._create_character(client, "RestoreChar")
        client.delete(f"/characters/{cid}")

        resp = client.post(f"/characters/{cid}/restore")
        assert resp.status_code == 200

        resp = client.get("/characters")
        ids = [c["id"] for c in resp.json()]
        assert cid in ids

    def test_permanent_delete_removes(self, client):
        cid = self._create_character(client, "PermChar")
        client.delete(f"/characters/{cid}")

        resp = client.delete(f"/characters/{cid}/permanent")
        assert resp.status_code == 200

        resp = client.get("/characters/trash")
        ids = [c["id"] for c in resp.json()]
        assert cid not in ids


# ============================================================
# PromptHistory Soft Delete
# ============================================================


class TestPromptHistorySoftDelete:
    def _create_history(self, client, name: str) -> int:
        resp = client.post("/prompt-histories", json={
            "name": name,
            "positive_prompt": "test prompt",
        })
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_soft_delete_excludes_from_list(self, client):
        pid = self._create_history(client, "DelPrompt")
        client.delete(f"/prompt-histories/{pid}")

        resp = client.get("/prompt-histories")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert pid not in ids

    def test_trash_returns_deleted(self, client):
        pid = self._create_history(client, "TrashPrompt")
        client.delete(f"/prompt-histories/{pid}")

        resp = client.get("/prompt-histories/trash")
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert pid in ids

    def test_restore_recovers(self, client):
        pid = self._create_history(client, "RestorePrompt")
        client.delete(f"/prompt-histories/{pid}")

        resp = client.post(f"/prompt-histories/{pid}/restore")
        assert resp.status_code == 200

        resp = client.get("/prompt-histories")
        ids = [p["id"] for p in resp.json()]
        assert pid in ids

    def test_permanent_delete_removes(self, client):
        pid = self._create_history(client, "PermPrompt")
        client.delete(f"/prompt-histories/{pid}")

        resp = client.delete(f"/prompt-histories/{pid}/permanent")
        assert resp.status_code == 200

        resp = client.get("/prompt-histories/trash")
        ids = [p["id"] for p in resp.json()]
        assert pid not in ids
