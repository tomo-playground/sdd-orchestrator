"""Tests for Voice Preset CRUD API (PUT /voice-presets/{id}).

Covers voice_design_prompt update via VoicePresetUpdate schema,
and verifies partial update behavior (exclude_unset).
"""

from sqlalchemy.orm import Session


class TestVoicePresetUpdate:
    """Test PUT /voice-presets/{id} with voice_design_prompt field."""

    def _create_preset(self, db_session: Session, **overrides) -> int:
        from models.voice_preset import VoicePreset

        defaults = {
            "name": "Test Voice",
            "description": "Test description",
            "source_type": "generated",
            "tts_engine": "qwen",
            "language": "korean",
            "voice_design_prompt": "Original prompt",
            "voice_seed": 12345,
        }
        defaults.update(overrides)
        preset = VoicePreset(**defaults)
        db_session.add(preset)
        db_session.commit()
        db_session.refresh(preset)
        return preset.id

    def test_update_voice_design_prompt(self, client, db_session):
        """PUT with voice_design_prompt should update the prompt."""
        preset_id = self._create_preset(db_session)

        resp = client.put(
            f"/api/admin/voice-presets/{preset_id}",
            json={"voice_design_prompt": "A warm female voice in her 30s"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["voice_design_prompt"] == "A warm female voice in her 30s"
        assert data["name"] == "Test Voice"  # unchanged

    def test_update_name_only_preserves_prompt(self, client, db_session):
        """PUT with only name should not change voice_design_prompt."""
        preset_id = self._create_preset(
            db_session,
            voice_design_prompt="Should stay unchanged",
        )

        resp = client.put(
            f"/api/admin/voice-presets/{preset_id}",
            json={"name": "Renamed Voice"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Renamed Voice"
        assert data["voice_design_prompt"] == "Should stay unchanged"

    def test_update_all_fields(self, client, db_session):
        """PUT with all fields should update everything."""
        preset_id = self._create_preset(db_session)

        resp = client.put(
            f"/api/admin/voice-presets/{preset_id}",
            json={
                "name": "Updated Name",
                "description": "Updated desc",
                "voice_design_prompt": "Updated prompt",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"
        assert data["voice_design_prompt"] == "Updated prompt"

    def test_update_nonexistent_returns_404(self, client):
        """PUT on nonexistent preset should return 404."""
        resp = client.put(
            "/api/admin/voice-presets/99999",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    def test_update_prompt_persists_in_db(self, client, db_session):
        """Updated voice_design_prompt should persist in DB."""
        from models.voice_preset import VoicePreset

        preset_id = self._create_preset(db_session)

        client.put(
            f"/api/admin/voice-presets/{preset_id}",
            json={"voice_design_prompt": "Persisted prompt"},
        )

        # Re-fetch from DB directly
        db_session.expire_all()
        preset = db_session.get(VoicePreset, preset_id)
        assert preset.voice_design_prompt == "Persisted prompt"

    def test_get_returns_updated_prompt(self, client, db_session):
        """GET after PUT should return the updated voice_design_prompt."""
        preset_id = self._create_preset(db_session)

        client.put(
            f"/api/admin/voice-presets/{preset_id}",
            json={"voice_design_prompt": "New prompt for GET"},
        )

        resp = client.get(f"/api/v1/voice-presets/{preset_id}")
        assert resp.status_code == 200
        assert resp.json()["voice_design_prompt"] == "New prompt for GET"
