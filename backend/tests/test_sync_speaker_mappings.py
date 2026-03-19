"""Tests for _sync_speaker_mappings behavior in storyboard service.

These tests verify that speaker→character mappings are correctly managed:
- Monologue: Speaker A → character_id (single character)
- Dialogue: Speaker A → character_id, Speaker B → character_b_id
- Narrated Dialogue: Speaker A → character_id, Speaker B → character_b_id
"""

from sqlalchemy.orm import Session


class TestSyncSpeakerMappingsMonologue:
    """Test speaker mapping for Monologue structure (single character)."""

    def test_monologue_preserves_speaker_a_mapping(self, client, db_session: Session):
        """Monologue with character_id should map Speaker A to that character."""
        from models.character import Character
        from models.storyboard_character import StoryboardCharacter

        # Create a character
        char = Character(name="Solo Character", gender="female", group_id=1)
        db_session.add(char)
        db_session.flush()

        # Create storyboard with character_id only (Monologue)
        payload = {
            "title": "Monologue Test",
            "description": "Test",
            "group_id": 1,
            "character_id": char.id,
            "character_b_id": None,  # Explicitly None = Monologue
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "내 이야기를 들어줘",
                    "speaker": "A",
                    "duration": 3.0,
                    "image_prompt": "1girl",
                    "width": 512,
                    "height": 768,
                }
            ],
        }
        resp = client.post("/api/v1/storyboards", json=payload)
        assert resp.status_code == 200
        sb_id = resp.json()["storyboard_id"]

        # Verify speaker A is mapped to character_id
        mapping = (
            db_session.query(StoryboardCharacter)
            .filter(
                StoryboardCharacter.storyboard_id == sb_id,
                StoryboardCharacter.speaker == "A",
            )
            .first()
        )
        assert mapping is not None, "Monologue should have Speaker A mapping"
        assert mapping.character_id == char.id

    def test_monologue_without_character_has_no_mapping(self, client, db_session: Session):
        """Monologue without character_id should have no mappings."""
        from models.storyboard_character import StoryboardCharacter

        # Create storyboard without character (Narrator-only)
        payload = {
            "title": "Narrator Only",
            "description": "Test",
            "group_id": 1,
            "character_id": None,
            "character_b_id": None,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "나레이션",
                    "speaker": "Narrator",
                    "duration": 3.0,
                    "image_prompt": "landscape",
                    "width": 512,
                    "height": 768,
                }
            ],
        }
        resp = client.post("/api/v1/storyboards", json=payload)
        assert resp.status_code == 200
        sb_id = resp.json()["storyboard_id"]

        # Verify no mappings exist
        mappings = db_session.query(StoryboardCharacter).filter(StoryboardCharacter.storyboard_id == sb_id).all()
        assert len(mappings) == 0, "No character → no mappings"


class TestSyncSpeakerMappingsDialogue:
    """Test speaker mapping for Dialogue structure (two characters)."""

    def test_dialogue_maps_both_speakers(self, client, db_session: Session):
        """Dialogue should map Speaker A and B to their respective characters."""
        from models.character import Character
        from models.storyboard_character import StoryboardCharacter

        # Create two characters
        char_a = Character(name="Character A", gender="female", group_id=1)
        char_b = Character(name="Character B", gender="male", group_id=1)
        db_session.add_all([char_a, char_b])
        db_session.flush()

        # Create storyboard with both characters (Dialogue)
        payload = {
            "title": "Dialogue Test",
            "description": "Test",
            "group_id": 1,
            "structure": "dialogue",
            "character_id": char_a.id,
            "character_b_id": char_b.id,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "안녕하세요",
                    "speaker": "A",
                    "duration": 3.0,
                    "image_prompt": "1girl",
                    "width": 512,
                    "height": 768,
                },
                {
                    "scene_id": 1,
                    "script": "반갑습니다",
                    "speaker": "B",
                    "duration": 3.0,
                    "image_prompt": "1boy",
                    "width": 512,
                    "height": 768,
                },
            ],
        }
        resp = client.post("/api/v1/storyboards", json=payload)
        assert resp.status_code == 200
        sb_id = resp.json()["storyboard_id"]

        # Verify both mappings
        mappings = db_session.query(StoryboardCharacter).filter(StoryboardCharacter.storyboard_id == sb_id).all()
        assert len(mappings) == 2

        speaker_map = {m.speaker: m.character_id for m in mappings}
        assert speaker_map["A"] == char_a.id
        assert speaker_map["B"] == char_b.id


class TestSyncSpeakerMappingsUpdate:
    """Test speaker mapping updates when storyboard is modified."""

    def test_update_dialogue_to_monologue_keeps_speaker_a(self, client, db_session: Session):
        """When updating from Dialogue to Monologue, Speaker A mapping should be preserved."""
        from models.character import Character
        from models.storyboard_character import StoryboardCharacter

        # Create characters
        char_a = Character(name="Character A", gender="female", group_id=1)
        char_b = Character(name="Character B", gender="male", group_id=1)
        db_session.add_all([char_a, char_b])
        db_session.flush()

        # Create Dialogue storyboard
        payload = {
            "title": "Dialogue→Monologue",
            "description": "Test",
            "group_id": 1,
            "structure": "dialogue",
            "character_id": char_a.id,
            "character_b_id": char_b.id,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "대화",
                    "speaker": "A",
                    "duration": 3.0,
                    "image_prompt": "1girl",
                    "width": 512,
                    "height": 768,
                }
            ],
        }
        resp = client.post("/api/v1/storyboards", json=payload)
        sb_id = resp.json()["storyboard_id"]

        # Update to Monologue (remove character_b_id)
        update_payload = {
            "title": "Now Monologue",
            "description": "Test",
            "character_id": char_a.id,
            "character_b_id": None,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "모놀로그로 변환",
                    "speaker": "A",
                    "duration": 3.0,
                    "image_prompt": "1girl",
                    "width": 512,
                    "height": 768,
                }
            ],
        }
        resp = client.put(f"/api/v1/storyboards/{sb_id}", json=update_payload)
        assert resp.status_code == 200

        # Speaker A should still be mapped
        mapping_a = (
            db_session.query(StoryboardCharacter)
            .filter(
                StoryboardCharacter.storyboard_id == sb_id,
                StoryboardCharacter.speaker == "A",
            )
            .first()
        )
        assert mapping_a is not None, "Speaker A mapping should be preserved"
        assert mapping_a.character_id == char_a.id

        # Speaker B should be removed
        mapping_b = (
            db_session.query(StoryboardCharacter)
            .filter(
                StoryboardCharacter.storyboard_id == sb_id,
                StoryboardCharacter.speaker == "B",
            )
            .first()
        )
        assert mapping_b is None, "Speaker B mapping should be removed"


class TestVoicePresetResolution:
    """Test that voice preset is correctly resolved from character mapping."""

    def test_monologue_voice_uses_character_preset(self, client, db_session: Session):
        """In Monologue, Speaker A scenes should use character's voice preset."""
        from models.character import Character
        from models.voice_preset import VoicePreset

        # Create voice preset
        voice = VoicePreset(
            name="Actor A Voice",
            source_type="generated",
            tts_engine="qwen",
            language="korean",
        )
        db_session.add(voice)
        db_session.flush()

        # Create character with voice preset
        char = Character(
            name="Actor A",
            gender="female",
            group_id=1,
            voice_preset_id=voice.id,
        )
        db_session.add(char)
        db_session.flush()

        # Create Monologue storyboard
        payload = {
            "title": "Voice Test",
            "description": "Test",
            "group_id": 1,
            "character_id": char.id,
            "character_b_id": None,
            "scenes": [
                {
                    "scene_id": 0,
                    "script": "내 목소리야",
                    "speaker": "A",
                    "duration": 3.0,
                    "image_prompt": "1girl",
                    "width": 512,
                    "height": 768,
                }
            ],
        }
        resp = client.post("/api/v1/storyboards", json=payload)
        assert resp.status_code == 200
        sb_id = resp.json()["storyboard_id"]

        # Verify via API response
        get_resp = client.get(f"/api/v1/storyboards/{sb_id}")
        data = get_resp.json()

        # character_id should be resolved from storyboard_characters
        assert data["character_id"] == char.id


class TestTTSWarningOnMissingMapping:
    """Test that TTS logs warnings when speaker→character mapping is missing."""

    def test_tts_logs_warning_when_no_character_mapping(self, client, db_session: Session):
        """TTS should log warning when Speaker A has no character mapping.

        Since _get_speaker_voice_preset uses its own DB session via get_db(),
        we test by mocking the logger and verifying the warning is called.
        """
        from unittest.mock import MagicMock, patch

        from models.storyboard import Storyboard

        # Create storyboard directly in test DB (no character mapping)
        storyboard = Storyboard(
            title="Missing Mapping Test",
            description="Test",
            group_id=1,  # Uses default group from seed
            structure="monologue",
        )
        db_session.add(storyboard)
        db_session.commit()
        sb_id = storyboard.id

        # Mock the logger and database session
        mock_logger = MagicMock()
        mock_db = MagicMock()
        mock_storyboard = MagicMock()
        mock_storyboard.group_id = 1
        mock_db.get.return_value = mock_storyboard

        # Mock resolve_speaker_to_character to return None (no mapping)
        # The function imports resolve_speaker_to_character inside, so patch the source module
        with (
            patch("services.video.tts_helpers.logger", mock_logger),
            patch("services.characters.resolve_speaker_to_character", return_value=None),
            patch("services.config_resolver.resolve_effective_config", return_value={"values": {}}),
            patch("database.SessionLocal", return_value=mock_db),
        ):
            from services.video.tts_helpers import get_speaker_voice_preset

            result = get_speaker_voice_preset(sb_id, "A")

        # Should return None (no preset found)
        assert result is None

        # Should have logged a warning about missing mapping
        mock_logger.warning.assert_called_once()
        warning_args = mock_logger.warning.call_args[0]
        assert "could not be resolved to a character" in warning_args[0]
        # %s and %d params: speaker='A', storyboard_id=sb_id
        assert warning_args[1] == "A"
        assert warning_args[2] == sb_id
