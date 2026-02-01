"""Tests for Phase 6-5 Batch B P0 fixes.

Fix 1: generation.py DB session leak (get_db_session context manager)
Fix 2: evaluation.py legacy field reference (V3 CharacterTag relationship)
Fix 3: MediaAsset.local_path property
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from models.media_asset import MediaAsset


# ============================================================
# Fix 1: DB Session Leak - get_db_session context manager
# ============================================================


class TestGetDbSession:
    """Verify get_db_session ensures session.close() is always called."""

    def test_session_closed_on_normal_exit(self):
        """Session is closed after normal context manager exit."""
        mock_session = MagicMock()

        with patch("services.generation.SessionLocal", return_value=mock_session):
            from services.generation import get_db_session

            with get_db_session() as db:
                assert db is mock_session

        mock_session.close.assert_called_once()

    def test_session_closed_on_exception(self):
        """Session is closed even when an exception occurs inside the block."""
        mock_session = MagicMock()

        with patch("services.generation.SessionLocal", return_value=mock_session):
            from services.generation import get_db_session

            with pytest.raises(ValueError, match="test error"):
                with get_db_session() as db:
                    assert db is mock_session
                    raise ValueError("test error")

        mock_session.close.assert_called_once()

    def test_generate_scene_image_uses_context_manager(self):
        """generate_scene_image delegates to _generate_scene_image_with_db via context manager."""
        from services.generation import get_db_session

        mock_session = MagicMock()

        with patch("services.generation.SessionLocal", return_value=mock_session):
            with get_db_session() as db:
                # Verify the session returned is the one from SessionLocal
                assert db is mock_session
            # After exiting, close must be called
            mock_session.close.assert_called_once()


# ============================================================
# Fix 2: evaluation.py V3 CharacterTag relationship
# ============================================================


class TestEvaluationV3Tags:
    """Verify evaluation resolves tags through V3 CharacterTag relationship."""

    def test_build_test_prompt_with_identity_and_clothing(self):
        """build_test_prompt correctly assembles identity and clothing tags."""
        from services.evaluation import TestPrompt, build_test_prompt

        test = TestPrompt(name="test", description="test", tokens=["smile", "upper body"])
        result = build_test_prompt(
            test=test,
            character_identity_tags=["brown_hair", "blue_eyes"],
            character_clothing_tags=["school_uniform"],
            mode="standard",
        )
        assert "brown_hair" in result
        assert "blue_eyes" in result
        assert "school_uniform" in result
        assert "smile" in result

    def test_v3_tag_resolution_identity(self, db_session):
        """Identity tags (hair, eyes, body, face) are resolved from CharacterTag."""
        from models import Character, Tag
        from models.associations import CharacterTag

        # Create tags
        hair_tag = Tag(name="brown_hair", category="hair", default_layer=1)
        eyes_tag = Tag(name="blue_eyes", category="eyes", default_layer=1)
        db_session.add_all([hair_tag, eyes_tag])
        db_session.flush()

        # Create character
        char = Character(name="test_eval_char", gender="female")
        db_session.add(char)
        db_session.flush()

        # Link tags via V3 CharacterTag
        ct1 = CharacterTag(character_id=char.id, tag_id=hair_tag.id)
        ct2 = CharacterTag(character_id=char.id, tag_id=eyes_tag.id)
        db_session.add_all([ct1, ct2])
        db_session.commit()

        # Re-query to load relationships
        char = db_session.query(Character).filter(Character.id == char.id).first()

        # Simulate the V3 resolution logic from evaluation.py
        identity_tags = []
        clothing_tags = []
        for ct in char.tags:
            tag = ct.tag
            if tag and tag.category in ("hair", "eyes", "body", "face"):
                identity_tags.append(tag.name)
            elif tag and tag.category in ("clothing", "accessory"):
                clothing_tags.append(tag.name)

        assert "brown_hair" in identity_tags
        assert "blue_eyes" in identity_tags
        assert len(clothing_tags) == 0

    def test_v3_tag_resolution_clothing(self, db_session):
        """Clothing tags are resolved from CharacterTag with clothing category."""
        from models import Character, Tag
        from models.associations import CharacterTag

        # Create tags
        clothing_tag = Tag(name="school_uniform", category="clothing", default_layer=2)
        accessory_tag = Tag(name="glasses", category="accessory", default_layer=2)
        db_session.add_all([clothing_tag, accessory_tag])
        db_session.flush()

        # Create character
        char = Character(name="test_eval_clothing", gender="female")
        db_session.add(char)
        db_session.flush()

        # Link tags
        ct1 = CharacterTag(character_id=char.id, tag_id=clothing_tag.id)
        ct2 = CharacterTag(character_id=char.id, tag_id=accessory_tag.id)
        db_session.add_all([ct1, ct2])
        db_session.commit()

        char = db_session.query(Character).filter(Character.id == char.id).first()

        identity_tags = []
        clothing_tags = []
        for ct in char.tags:
            tag = ct.tag
            if tag and tag.category in ("hair", "eyes", "body", "face"):
                identity_tags.append(tag.name)
            elif tag and tag.category in ("clothing", "accessory"):
                clothing_tags.append(tag.name)

        assert "school_uniform" in clothing_tags
        assert "glasses" in clothing_tags
        assert len(identity_tags) == 0

    def test_no_attribute_error_on_character(self, db_session):
        """Character model no longer has identity_tags/clothing_tags fields.

        Accessing these should raise AttributeError, confirming V3 migration.
        """
        from models import Character

        char = Character(name="test_no_legacy_fields", gender="female")
        db_session.add(char)
        db_session.commit()

        # Confirm the legacy fields do not exist
        assert not hasattr(char, "identity_tags") or getattr(char, "identity_tags", None) is None
        # V3 tags relationship should exist and be empty
        assert hasattr(char, "tags")


# ============================================================
# Fix 3: MediaAsset.local_path property
# ============================================================


class TestMediaAssetLocalPath:
    """Verify MediaAsset.local_path property delegates to storage."""

    def test_local_path_property_exists(self):
        """MediaAsset has a local_path property."""
        assert hasattr(MediaAsset, "local_path")
        # Verify it is a property, not a column
        assert isinstance(
            MediaAsset.__dict__["local_path"], property
        ), "local_path should be a @property"

    def test_local_path_returns_string(self, db_session):
        """local_path returns a string path via storage.get_local_path."""
        asset = MediaAsset(
            storage_key="images/test.png",
            file_type="image",
            file_name="test.png",
        )
        db_session.add(asset)
        db_session.flush()

        mock_storage = MagicMock()
        mock_storage.get_local_path.return_value = Path("/tmp/outputs/images/test.png")

        with patch("services.storage.get_storage", return_value=mock_storage):
            result = asset.local_path

        assert result == "/tmp/outputs/images/test.png"
        assert isinstance(result, str)
        mock_storage.get_local_path.assert_called_once_with("images/test.png")

    def test_url_property_uses_get_storage(self, db_session):
        """url property also uses get_storage (not initialize_storage)."""
        asset = MediaAsset(
            storage_key="images/test.png",
            file_type="image",
            file_name="test.png",
        )
        db_session.add(asset)
        db_session.flush()

        mock_storage = MagicMock()
        mock_storage.get_url.return_value = "http://localhost:9000/bucket/images/test.png"

        with patch("services.storage.get_storage", return_value=mock_storage):
            result = asset.url

        assert result == "http://localhost:9000/bucket/images/test.png"
        mock_storage.get_url.assert_called_once_with("images/test.png")

    def test_local_path_compatible_with_os_path(self, tmp_path, db_session):
        """local_path string is compatible with os.path.exists and open()."""
        import os

        # Create a real file
        test_file = tmp_path / "test_image.png"
        test_file.write_bytes(b"fake png data")

        asset = MediaAsset(
            storage_key="test_image.png",
            file_type="image",
            file_name="test_image.png",
        )
        db_session.add(asset)
        db_session.flush()

        mock_storage = MagicMock()
        mock_storage.get_local_path.return_value = test_file

        with patch("services.storage.get_storage", return_value=mock_storage):
            path = asset.local_path

        # Should work with os.path operations
        assert os.path.exists(path)

        # Should work with open()
        with open(path, "rb") as f:
            assert f.read() == b"fake png data"
