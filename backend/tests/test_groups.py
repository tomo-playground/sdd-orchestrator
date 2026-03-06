"""Tests for Group API — config update + defaults endpoint."""

import pytest
from sqlalchemy.orm import Session


class TestGroupConfigUpdate:
    """Test PUT /groups/{id} with config fields (previously in group_config)."""

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
        """PUT with narrator_voice_preset_id should update the group."""
        group_id = self._create_group(db_session)
        voice_preset_id = self._create_voice_preset(db_session)

        resp = client.put(
            f"/api/v1/groups/{group_id}",
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
            f"/api/v1/groups/{group_id}",
            json={"narrator_voice_preset_id": voice_preset_id},
        )

        # Clear it
        resp = client.put(
            f"/api/v1/groups/{group_id}",
            json={"narrator_voice_preset_id": None},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] is None

    def test_update_preserves_other_fields(self, client, db_session):
        """PUT with only narrator_voice_preset_id should preserve other fields."""
        group_id = self._create_group(db_session)

        # Update only voice preset
        voice_preset_id = self._create_voice_preset(db_session)
        resp = client.put(
            f"/api/v1/groups/{group_id}",
            json={"narrator_voice_preset_id": voice_preset_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] == voice_preset_id
        assert data["name"] == "Test Group"  # preserved

    def test_update_nonexistent_voice_preset_id_fails(self, client, db_session):
        """PUT with nonexistent narrator_voice_preset_id should fail (FK constraint).

        SQLite enforces FK constraint → IntegrityError propagates through TestClient.
        """
        from sqlalchemy.exc import IntegrityError

        group_id = self._create_group(db_session)

        with pytest.raises(IntegrityError):
            client.put(
                f"/api/v1/groups/{group_id}",
                json={"narrator_voice_preset_id": 99999},
            )

    def test_update_nonexistent_group_returns_404(self, client):
        """PUT on nonexistent group should return 404."""
        resp = client.put(
            "/api/v1/groups/99999",
            json={"narrator_voice_preset_id": 1},
        )
        assert resp.status_code == 404

    def test_get_effective_config_includes_narrator_voice_preset_id(self, client, db_session):
        """GET /groups/{id}/effective-config should include narrator_voice_preset_id."""
        group_id = self._create_group(db_session)
        voice_preset_id = self._create_voice_preset(db_session)

        # Set on group directly
        client.put(
            f"/api/v1/groups/{group_id}",
            json={"narrator_voice_preset_id": voice_preset_id},
        )

        # Get effective config
        resp = client.get(f"/api/v1/groups/{group_id}/effective-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["narrator_voice_preset_id"] == voice_preset_id


class TestGroupDefaults:
    """Test GET /groups/{id}/defaults — 시리즈 이력 기반 기본값."""

    def _setup(self, db_session: Session) -> int:
        from models import Group, Project

        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)

        group = Group(project_id=project.id, name="Test Group")
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        return group.id

    def _add_storyboard(self, db_session: Session, group_id: int, **overrides):
        from models.storyboard import Storyboard

        defaults = {
            "group_id": group_id,
            "title": "Test SB",
            "structure": "Monologue",
            "duration": 30,
            "language": "Korean",
        }
        defaults.update(overrides)
        sb = Storyboard(**defaults)
        db_session.add(sb)
        db_session.commit()

    def test_defaults_no_history(self, client, db_session):
        """이력 없는 그룹은 has_history=false + 전역 기본값."""
        group_id = self._setup(db_session)
        resp = client.get(f"/api/v1/groups/{group_id}/defaults")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_history"] is False
        assert data["structure"] == "Monologue"
        assert "available_options" in data
        assert len(data["available_options"]["durations"]) > 0

    def test_defaults_with_history(self, client, db_session):
        """이력 있는 그룹은 has_history=true + 최빈값."""
        group_id = self._setup(db_session)
        for _ in range(3):
            self._add_storyboard(
                db_session, group_id, duration=45, structure="Dialogue", language="Korean",
            )
        self._add_storyboard(
            db_session, group_id, duration=30, structure="Monologue", language="English",
        )

        resp = client.get(f"/api/v1/groups/{group_id}/defaults")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_history"] is True
        assert data["duration"] == 45
        assert data["structure"] == "Dialogue"
        assert data["language"] == "Korean"

    def test_defaults_404_nonexistent(self, client):
        """존재하지 않는 그룹은 404."""
        resp = client.get("/api/v1/groups/99999/defaults")
        assert resp.status_code == 404

    def test_defaults_available_options_structures(self, client, db_session):
        """available_options.structures는 presets에서 가져온 목록."""
        group_id = self._setup(db_session)
        resp = client.get(f"/api/v1/groups/{group_id}/defaults")
        data = resp.json()
        structures = data["available_options"]["structures"]
        values = [s["value"] for s in structures]
        assert "Monologue" in values
        assert "Dialogue" in values

    def test_defaults_dialogue_with_characters(self, client, db_session):
        """Dialogue 이력 + 캐릭터 2명 → character_b_id 반환."""
        from models import Character

        group_id = self._setup(db_session)
        char_a = Character(group_id=group_id, name="Alice")
        char_b = Character(group_id=group_id, name="Bob")
        db_session.add_all([char_a, char_b])
        db_session.commit()
        db_session.refresh(char_a)
        db_session.refresh(char_b)

        for _ in range(3):
            self._add_storyboard(
                db_session, group_id, duration=45, structure="Dialogue", language="Korean",
            )

        resp = client.get(f"/api/v1/groups/{group_id}/defaults")
        data = resp.json()
        assert data["has_history"] is True
        assert data["character_a_id"] == char_a.id
        assert data["character_a_name"] == "Alice"
        assert data["character_b_id"] == char_b.id
        assert data["character_b_name"] == "Bob"

    def test_defaults_monologue_no_character_b(self, client, db_session):
        """Monologue → character_b는 None."""
        from models import Character

        group_id = self._setup(db_session)
        char_a = Character(group_id=group_id, name="Solo")
        char_b = Character(group_id=group_id, name="Extra")
        db_session.add_all([char_a, char_b])
        db_session.commit()

        for _ in range(3):
            self._add_storyboard(
                db_session, group_id, duration=30, structure="Monologue", language="Korean",
            )

        resp = client.get(f"/api/v1/groups/{group_id}/defaults")
        data = resp.json()
        assert data["character_b_id"] is None
        assert data["character_b_name"] is None

    def test_defaults_narrated_dialogue_with_characters(self, client, db_session):
        """Narrated Dialogue → character_b 포함."""
        from models import Character

        group_id = self._setup(db_session)
        char_a = Character(group_id=group_id, name="Jiho")
        char_b = Character(group_id=group_id, name="Subin")
        db_session.add_all([char_a, char_b])
        db_session.commit()
        db_session.refresh(char_a)

        for _ in range(3):
            self._add_storyboard(
                db_session, group_id, duration=45, structure="Narrated Dialogue", language="Korean",
            )

        resp = client.get(f"/api/v1/groups/{group_id}/defaults")
        data = resp.json()
        assert data["character_b_id"] is not None
