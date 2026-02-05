"""Tests for speaker_resolver service."""

from unittest.mock import MagicMock


class TestResolveSpeakerToCharacter:
    """Test resolve_speaker_to_character()."""

    def test_returns_character_id_for_existing_mapping(self):
        from services.speaker_resolver import resolve_speaker_to_character

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = (42,)

        result = resolve_speaker_to_character(1, "A", mock_db)
        assert result == 42

    def test_returns_none_for_missing_mapping(self):
        from services.speaker_resolver import resolve_speaker_to_character

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = resolve_speaker_to_character(1, "B", mock_db)
        assert result is None


class TestResolveAllSpeakers:
    """Test resolve_all_speakers()."""

    def test_returns_all_mappings(self):
        from services.speaker_resolver import resolve_all_speakers

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [
            ("A", 10),
            ("B", 20),
        ]

        result = resolve_all_speakers(1, mock_db)
        assert result == {"A": 10, "B": 20}

    def test_returns_empty_dict_for_no_mappings(self):
        from services.speaker_resolver import resolve_all_speakers

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = resolve_all_speakers(1, mock_db)
        assert result == {}


class TestAssignSpeakers:
    """Test assign_speakers()."""

    def test_deletes_existing_and_inserts_new(self):
        from services.speaker_resolver import assign_speakers

        mock_db = MagicMock()

        assign_speakers(1, {"A": 10, "B": 20}, mock_db)

        # Should delete existing mappings
        mock_db.query.return_value.filter.return_value.delete.assert_called_once()
        # Should add 2 new mappings
        assert mock_db.add.call_count == 2
        # Should flush
        mock_db.flush.assert_called_once()

    def test_empty_speaker_map_clears_all(self):
        from services.speaker_resolver import assign_speakers

        mock_db = MagicMock()

        assign_speakers(1, {}, mock_db)

        # Should delete existing
        mock_db.query.return_value.filter.return_value.delete.assert_called_once()
        # Should not add any
        assert mock_db.add.call_count == 0
        mock_db.flush.assert_called_once()
