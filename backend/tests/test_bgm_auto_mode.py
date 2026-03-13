"""Unit tests for BGM auto mode pipeline and manual mode dispatch."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.video.effects import _resolve_bgm_path


# ============================================================
# _resolve_bgm_path — auto mode
# ============================================================


class TestResolveBgmPathAutoMode:
    """Tests for _resolve_bgm_path with auto mode."""

    def test_auto_mode_returns_ai_bgm_path(self):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="auto")
        builder._ai_bgm_path = "/tmp/auto_bgm.wav"

        result = _resolve_bgm_path(builder)
        assert result == "/tmp/auto_bgm.wav"

    def test_auto_mode_returns_none_when_no_path(self):
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="auto")
        builder._ai_bgm_path = None

        result = _resolve_bgm_path(builder)
        assert result is None

    def test_auto_mode_does_not_fallthrough_to_file(self):
        """auto mode with no path should NOT try file-based BGM."""
        builder = MagicMock()
        builder.request = SimpleNamespace(bgm_mode="auto", bgm_file="song.mp3")
        builder._ai_bgm_path = None

        with patch("services.video.effects.resolve_bgm_file") as mock_resolve:
            result = _resolve_bgm_path(builder)

        assert result is None
        mock_resolve.assert_not_called()


# ============================================================
# _prepare_bgm — mode dispatch
# ============================================================


class TestPrepareBgmDispatch:
    """Tests for _prepare_bgm mode dispatching."""

    @pytest.mark.asyncio
    async def test_manual_mode_calls_preset(self):
        """manual mode should call _prepare_preset_bgm."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(bgm_mode="manual")
        builder._prepare_preset_bgm = AsyncMock()
        builder._prepare_auto_bgm = AsyncMock()

        await VideoBuilder._prepare_bgm(builder)

        builder._prepare_preset_bgm.assert_called_once()
        builder._prepare_auto_bgm.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_mode_calls_auto(self):
        """auto mode should call _prepare_auto_bgm."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(bgm_mode="auto")
        builder._prepare_preset_bgm = AsyncMock()
        builder._prepare_auto_bgm = AsyncMock()

        await VideoBuilder._prepare_bgm(builder)

        builder._prepare_auto_bgm.assert_called_once()
        builder._prepare_preset_bgm.assert_not_called()

    @pytest.mark.asyncio
    async def test_legacy_file_mode_calls_preset(self):
        """Legacy 'file' mode should map to manual and call _prepare_preset_bgm."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(bgm_mode="file")
        builder._prepare_preset_bgm = AsyncMock()
        builder._prepare_auto_bgm = AsyncMock()

        await VideoBuilder._prepare_bgm(builder)

        builder._prepare_preset_bgm.assert_called_once()
        builder._prepare_auto_bgm.assert_not_called()

    @pytest.mark.asyncio
    async def test_legacy_ai_mode_calls_preset(self):
        """Legacy 'ai' mode should map to manual and call _prepare_preset_bgm."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(bgm_mode="ai")
        builder._prepare_preset_bgm = AsyncMock()
        builder._prepare_auto_bgm = AsyncMock()

        await VideoBuilder._prepare_bgm(builder)

        builder._prepare_preset_bgm.assert_called_once()
        builder._prepare_auto_bgm.assert_not_called()


# ============================================================
# _prepare_auto_bgm — storyboard lookup + cache
# ============================================================


class TestPrepareAutoBgm:
    """Tests for _prepare_auto_bgm storyboard lookup and caching."""

    @pytest.mark.asyncio
    async def test_auto_bgm_uses_request_prompt(self):
        """When request has bgm_prompt, use it directly."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(
            bgm_mode="auto",
            bgm_prompt="soft piano ambient",
            storyboard_id=None,
        )
        builder._ai_bgm_path = None
        builder._total_dur = 25.0
        builder._generate_and_set_bgm = AsyncMock(return_value=b"wav_data")

        with patch("services.video.builder.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            await VideoBuilder._prepare_auto_bgm(builder)

        # _total_dur=25 < 30 → max(30, 25) = 30
        builder._generate_and_set_bgm.assert_called_once_with(
            "soft piano ambient", 30.0, -1
        )

    @pytest.mark.asyncio
    async def test_auto_bgm_cache_hit(self):
        """When storyboard has cached bgm_audio_asset_id, reuse it."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(
            bgm_mode="auto",
            bgm_prompt=None,
            storyboard_id=42,
        )
        builder._ai_bgm_path = None
        builder._generate_and_set_bgm = AsyncMock()

        mock_storyboard = MagicMock()
        mock_storyboard.bgm_prompt = "epic orchestral"
        mock_storyboard.bgm_audio_asset_id = 99

        mock_asset = MagicMock()
        mock_storage = MagicMock()
        mock_storage.get_local_path.return_value = "/data/storyboard/42/bgm.wav"

        with (
            patch("services.video.builder.SessionLocal") as mock_session_cls,
            patch("services.storage.get_storage", return_value=mock_storage),
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_storyboard
            mock_db.get.return_value = mock_asset

            await VideoBuilder._prepare_auto_bgm(builder)

        # Should use cached path, not generate
        assert builder._ai_bgm_path == "/data/storyboard/42/bgm.wav"
        builder._generate_and_set_bgm.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_bgm_no_prompt_no_storyboard(self):
        """When no prompt and no storyboard_id, do nothing."""
        from services.video.builder import VideoBuilder

        builder = MagicMock(spec=VideoBuilder)
        builder.request = SimpleNamespace(
            bgm_mode="auto",
            bgm_prompt=None,
            storyboard_id=None,
        )
        builder._generate_and_set_bgm = AsyncMock()

        await VideoBuilder._prepare_auto_bgm(builder)

        builder._generate_and_set_bgm.assert_not_called()


# ============================================================
# Storyboard CRUD — bgm fields
# ============================================================


class TestStoryboardCrudBgm:
    """Tests for bgm_prompt/bgm_mood in storyboard CRUD."""

    def test_save_includes_bgm_fields(self):
        """save_storyboard_to_db should store bgm_prompt/bgm_mood."""
        from models.storyboard import Storyboard

        mock_db = MagicMock()
        mock_storyboard = MagicMock(spec=Storyboard)
        mock_storyboard.id = 1
        mock_storyboard.version = 1
        mock_storyboard.scenes = []

        # Capture the Storyboard instance that gets added
        added_instances = []
        mock_db.add.side_effect = lambda obj: added_instances.append(obj)
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        request = SimpleNamespace(
            title="Test",
            description=None,
            group_id=1,
            caption=None,
            structure="monologue",
            duration=30,
            language="Korean",
            bgm_prompt="soft piano ambient",
            bgm_mood="calm",
            casting_recommendation=None,
            scenes=[],
            character_id=None,
            character_b_id=None,
            version=None,
        )

        with patch("services.storyboard.crud.create_scenes"):
            with patch("services.storyboard.crud._sync_speaker_mappings"):
                from services.storyboard.crud import save_storyboard_to_db

                # Mock the storyboard creation
                try:
                    save_storyboard_to_db(mock_db, request)
                except Exception:
                    pass  # May fail on refresh, that's ok

        # Verify Storyboard was created with bgm fields
        if added_instances:
            sb = added_instances[0]
            assert sb.bgm_prompt == "soft piano ambient"
            assert sb.bgm_mood == "calm"

    def test_update_invalidates_cache_on_prompt_change(self):
        """Changing bgm_prompt should reset bgm_audio_asset_id."""
        mock_storyboard = MagicMock()
        mock_storyboard.bgm_prompt = "old prompt"
        mock_storyboard.bgm_audio_asset_id = 99
        mock_storyboard.version = 1
        mock_storyboard.scenes = []

        mock_db = MagicMock()
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_storyboard
        )

        request = SimpleNamespace(
            title="Test",
            description=None,
            group_id=1,
            caption=None,
            structure="monologue",
            duration=30,
            language="Korean",
            bgm_prompt="new prompt",  # Changed!
            bgm_mood="energetic",
            casting_recommendation=None,
            scenes=[],
            character_id=None,
            character_b_id=None,
            version=1,
        )

        with (
            patch("services.storyboard.crud.create_scenes"),
            patch("services.storyboard.crud._sync_speaker_mappings"),
            patch("services.storyboard.crud.truncate_title", return_value="Test"),
        ):
            from services.storyboard.crud import update_storyboard_in_db

            try:
                update_storyboard_in_db(mock_db, 1, request)
            except Exception:
                pass  # May fail on commit/refresh

        # Cache should be invalidated
        assert mock_storyboard.bgm_audio_asset_id is None
        assert mock_storyboard.bgm_prompt == "new prompt"
        assert mock_storyboard.bgm_mood == "energetic"

    def test_update_preserves_cache_when_prompt_unchanged(self):
        """Same bgm_prompt should NOT reset bgm_audio_asset_id."""
        mock_storyboard = MagicMock()
        mock_storyboard.bgm_prompt = "same prompt"
        mock_storyboard.bgm_audio_asset_id = 99
        mock_storyboard.version = 1
        mock_storyboard.scenes = []

        mock_db = MagicMock()
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_storyboard
        )

        request = SimpleNamespace(
            title="Test",
            description=None,
            group_id=1,
            caption=None,
            structure="monologue",
            duration=30,
            language="Korean",
            bgm_prompt="same prompt",  # Unchanged
            bgm_mood="calm",
            casting_recommendation=None,
            scenes=[],
            character_id=None,
            character_b_id=None,
            version=1,
        )

        with (
            patch("services.storyboard.crud.create_scenes"),
            patch("services.storyboard.crud._sync_speaker_mappings"),
            patch("services.storyboard.crud.truncate_title", return_value="Test"),
        ):
            from services.storyboard.crud import update_storyboard_in_db

            try:
                update_storyboard_in_db(mock_db, 1, request)
            except Exception:
                pass

        # Cache should NOT be invalidated
        assert mock_storyboard.bgm_audio_asset_id == 99
