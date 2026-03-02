"""Tests for TTS Designer _load_character_voice_context."""

from unittest.mock import patch

from services.agent.nodes.tts_designer import _load_character_voice_context


def _mock_char(char_id, name, gender, voice_preset_id=None):
    from unittest.mock import MagicMock

    c = MagicMock()
    c.id = char_id
    c.name = name
    c.gender = gender
    c.voice_preset_id = voice_preset_id
    return c


def _mock_preset(preset_id, voice_design_prompt):
    from unittest.mock import MagicMock

    p = MagicMock()
    p.id = preset_id
    p.voice_design_prompt = voice_design_prompt
    return p


class TestLoadCharacterVoiceContext:
    """_load_character_voice_context: 캐릭터 음성 컨텍스트 로딩."""

    def test_no_character_id_returns_none(self):
        state = {}
        result = _load_character_voice_context(state)
        assert result is None

    @patch("database.get_db_session")
    def test_single_character_basic(self, mock_db_ctx):
        from unittest.mock import MagicMock

        db = MagicMock()
        mock_db_ctx.return_value.__enter__ = lambda s: db
        mock_db_ctx.return_value.__exit__ = lambda s, *a: None

        char = _mock_char(3, "미도리", "male")
        db.query.return_value.filter.return_value.first.return_value = char

        state = {"character_id": 3}
        result = _load_character_voice_context(state)

        assert result is not None
        assert len(result) == 1
        assert result[0]["speaker"] == "A"
        assert result[0]["name"] == "미도리"
        assert result[0]["gender"] == "male"
        assert "reference_voice" not in result[0]
        assert result[0]["has_preset"] is False

    @patch("database.get_db_session")
    def test_two_characters_with_voice_preset(self, mock_db_ctx):
        from unittest.mock import MagicMock

        db = MagicMock()
        mock_db_ctx.return_value.__enter__ = lambda s: db
        mock_db_ctx.return_value.__exit__ = lambda s, *a: None

        char_a = _mock_char(3, "미도리", "male", voice_preset_id=20)
        char_b = _mock_char(19, "유카리", "female", voice_preset_id=23)
        preset_a = _mock_preset(20, "Deep masculine voice")
        preset_b = _mock_preset(23, "Soft feminine voice")

        # Setup query chain for Character and VoicePreset
        char_calls = {"count": 0}
        preset_calls = {"count": 0}

        def side_effect(model):
            mock_q = MagicMock()
            if model.__name__ == "Character":
                char_filter = MagicMock()

                def char_first():
                    char_calls["count"] += 1
                    return char_a if char_calls["count"] <= 1 else char_b

                char_filter.first = char_first
                mock_q.filter.return_value = char_filter
            else:
                preset_filter = MagicMock()

                def preset_first():
                    preset_calls["count"] += 1
                    return preset_a if preset_calls["count"] <= 1 else preset_b

                preset_filter.first = preset_first
                mock_q.filter.return_value = preset_filter
            return mock_q

        db.query.side_effect = side_effect

        state = {"character_id": 3, "character_b_id": 19}
        result = _load_character_voice_context(state)

        assert result is not None
        assert len(result) == 2
        assert result[0]["speaker"] == "A"
        assert result[0]["gender"] == "male"
        assert result[0]["reference_voice"] == "Deep masculine voice"
        assert result[0]["has_preset"] is True
        assert result[1]["speaker"] == "B"
        assert result[1]["gender"] == "female"
        assert result[1]["reference_voice"] == "Soft feminine voice"
        assert result[1]["has_preset"] is True

    @patch("database.get_db_session")
    def test_character_not_found_skipped(self, mock_db_ctx):
        from unittest.mock import MagicMock

        db = MagicMock()
        mock_db_ctx.return_value.__enter__ = lambda s: db
        mock_db_ctx.return_value.__exit__ = lambda s, *a: None

        db.query.return_value.filter.return_value.first.return_value = None

        state = {"character_id": 999}
        result = _load_character_voice_context(state)
        assert result is None

    @patch("database.get_db_session")
    def test_gender_none_defaults_to_female(self, mock_db_ctx):
        from unittest.mock import MagicMock

        db = MagicMock()
        mock_db_ctx.return_value.__enter__ = lambda s: db
        mock_db_ctx.return_value.__exit__ = lambda s, *a: None

        char = _mock_char(1, "NoGender", None)
        db.query.return_value.filter.return_value.first.return_value = char

        state = {"character_id": 1}
        result = _load_character_voice_context(state)
        assert result[0]["gender"] == "female"
