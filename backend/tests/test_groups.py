"""Tests for Group Config API (PUT /groups/{id}/config).

Covers narrator_voice_preset_id update and verifies partial update behavior.
"""

import pytest
from sqlalchemy.orm import Session


class TestGroupConfigUpdate:
    """Test PUT /groups/{id}/config with narrator_voice_preset_id field."""

    def _create_group(self, db_session: Session, **overrides) -> int:
        from models import Group, Project

        # Create project first
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        # Create group
        defaults = {
            "project_id": project.id,
            "name": "Test Group",
            "description": "Test description",
        }
        defaults.update(overrides)
        group = Group(**defaults)
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        return group.id

    def _create_voice_preset(self, db_session: Session, **overrides) -> int:
        from models.voice_preset import VoicePreset

        defaults = {
            "name": "Test Voice",
            "source_type": "generated",
            "tts_engine": "qwen",
            "language": "korean",
            "voice_design_prompt": "Test voice prompt",
        }
        defaults.update(overrides)
        preset = VoicePreset(**defaults)
        db_session.add(preset)
        db_session.commit()
        db_session.refresh(preset)
        return preset.id

    def test_update_narrator_voice_preset_id(self, client, db_session):
        """PUT with narrator_voice_preset_id should update the config."""
        group_id = self._create_group(db_session)
        voice_preset_id = self._create_voice_preset(db_session)

        resp = client.put(
            f"/groups/{group_id}/config",
            json={"narrator_voice_preset_id": voice_preset_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] == voice_preset_id

    def test_update_narrator_voice_preset_id_to_null(self, client, db_session):
        """PUT with narrator_voice_preset_id=null should clear the preset."""
        group_id = self._create_group(db_session)
        voice_preset_id = self._create_voice_preset(db_session)

        # Set initial value
        client.put(
            f"/groups/{group_id}/config",
            json={"narrator_voice_preset_id": voice_preset_id},
        )

        # Clear it
        resp = client.put(
            f"/groups/{group_id}/config",
            json={"narrator_voice_preset_id": None},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] is None

    def test_update_preserves_other_fields(self, client, db_session):
        """PUT with only narrator_voice_preset_id should preserve other fields."""
        group_id = self._create_group(db_session)

        # Set initial config
        client.put(
            f"/groups/{group_id}/config",
            json={
                "language": "korean",
                "structure": "story",
                "duration": 60,
            },
        )

        # Update only voice preset
        voice_preset_id = self._create_voice_preset(db_session)
        resp = client.put(
            f"/groups/{group_id}/config",
            json={"narrator_voice_preset_id": voice_preset_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] == voice_preset_id
        assert data["language"] == "korean"  # preserved
        assert data["structure"] == "story"  # preserved
        assert data["duration"] == 60  # preserved

    def test_update_nonexistent_voice_preset_id_fails(self, client, db_session):
        """PUT with nonexistent narrator_voice_preset_id should fail (FK constraint).

        SQLite enforces FK constraint → IntegrityError propagates through TestClient.
        """
        from sqlalchemy.exc import IntegrityError

        group_id = self._create_group(db_session)

        with pytest.raises(IntegrityError):
            client.put(
                f"/groups/{group_id}/config",
                json={"narrator_voice_preset_id": 99999},
            )

    def test_update_nonexistent_group_returns_404(self, client):
        """PUT on nonexistent group should return 404."""
        resp = client.put(
            "/groups/99999/config",
            json={"narrator_voice_preset_id": 1},
        )
        assert resp.status_code == 404

    def test_get_effective_config_includes_narrator_voice_preset_id(self, client, db_session):
        """GET /groups/{id}/effective-config should include narrator_voice_preset_id."""
        group_id = self._create_group(db_session)
        voice_preset_id = self._create_voice_preset(db_session)

        # Set config
        client.put(
            f"/groups/{group_id}/config",
            json={"narrator_voice_preset_id": voice_preset_id},
        )

        # Get effective config
        resp = client.get(f"/groups/{group_id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] == voice_preset_id
