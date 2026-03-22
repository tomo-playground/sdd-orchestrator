"""BGM Prebuild 서비스 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture()
def mock_db():
    return MagicMock()


@pytest.fixture()
def mock_storyboard():
    sb = MagicMock()
    sb.id = 1
    sb.bgm_prompt = "soft background music"
    sb.bgm_audio_asset_id = None
    sb.deleted_at = None
    return sb


class TestPrebuildBgm:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_skipped(self, mock_db, mock_storyboard):
        """bgm_audio_asset_id가 이미 있으면 skipped 반환."""
        mock_storyboard.bgm_audio_asset_id = 42
        mock_asset = MagicMock()
        mock_asset.id = 42
        mock_asset.deleted_at = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_storyboard
        mock_db.get.return_value = mock_asset

        from services.bgm_prebuild import prebuild_bgm

        result = await prebuild_bgm(1, None, mock_db)
        assert result.status == "skipped"
        assert result.bgm_audio_asset_id == 42

    @pytest.mark.asyncio
    async def test_no_prompt_returns_no_prompt(self, mock_db, mock_storyboard):
        """bgm_prompt가 없으면 no_prompt 반환."""
        mock_storyboard.bgm_prompt = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_storyboard

        from services.bgm_prebuild import prebuild_bgm

        result = await prebuild_bgm(1, None, mock_db)
        assert result.status == "no_prompt"

    @pytest.mark.asyncio
    async def test_storyboard_not_found(self, mock_db):
        """존재하지 않는 storyboard는 failed 반환."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from services.bgm_prebuild import prebuild_bgm

        result = await prebuild_bgm(999, None, mock_db)
        assert result.status == "failed"
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild._generate_bgm", new_callable=AsyncMock)
    @patch("services.bgm_prebuild._save_bgm_asset")
    @patch("services.bgm_prebuild._link_to_storyboard")
    async def test_successful_prebuild(self, mock_link, mock_save, mock_gen, mock_db, mock_storyboard):
        """정상 생성 시 prebuilt + asset_id 반환."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_storyboard
        mock_gen.return_value = b"fake-wav-data"
        mock_save.return_value = 100

        from services.bgm_prebuild import prebuild_bgm

        result = await prebuild_bgm(1, "test prompt", mock_db)
        assert result.status == "prebuilt"
        assert result.bgm_audio_asset_id == 100
        mock_gen.assert_called_once_with("test prompt", None)

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild._generate_bgm", new_callable=AsyncMock)
    @patch("services.bgm_prebuild._save_bgm_asset")
    @patch("services.bgm_prebuild._link_to_storyboard")
    async def test_total_duration_passed_to_generate(self, mock_link, mock_save, mock_gen, mock_db, mock_storyboard):
        """total_duration이 _generate_bgm에 전달된다."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_storyboard
        mock_gen.return_value = b"fake-wav-data"
        mock_save.return_value = 100

        from services.bgm_prebuild import prebuild_bgm

        await prebuild_bgm(1, "test prompt", mock_db, total_duration=45.0)
        mock_gen.assert_called_once_with("test prompt", 45.0)

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild._generate_bgm", new_callable=AsyncMock)
    async def test_generation_failure_returns_failed(self, mock_gen, mock_db, mock_storyboard):
        """MusicGen 호출 실패 시 failed 반환."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_storyboard
        mock_gen.side_effect = ConnectionError("Audio server down")

        from services.bgm_prebuild import prebuild_bgm

        result = await prebuild_bgm(1, None, mock_db)
        assert result.status == "failed"
        assert "Audio server" in (result.error or "")


class TestGenerateBgmDuration:
    """_generate_bgm의 duration 계산 단위 테스트."""

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild.generate_music", new_callable=AsyncMock)
    async def test_total_duration_none_uses_default(self, mock_music):
        """total_duration=None → MUSICGEN_DEFAULT_DURATION 사용."""
        mock_music.return_value = (b"wav", None, None)
        from config import MUSICGEN_DEFAULT_DURATION
        from services.bgm_prebuild import _generate_bgm

        await _generate_bgm("prompt", None)
        called_duration = mock_music.call_args.kwargs["duration"]
        assert called_duration == MUSICGEN_DEFAULT_DURATION

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild.generate_music", new_callable=AsyncMock)
    async def test_short_duration_used_directly(self, mock_music):
        """total_duration=10.0 → 하한선 없이 10.0 그대로 사용."""
        mock_music.return_value = (b"wav", None, None)
        from services.bgm_prebuild import _generate_bgm

        await _generate_bgm("prompt", 10.0)
        called_duration = mock_music.call_args.kwargs["duration"]
        assert called_duration == 10.0

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild.generate_music", new_callable=AsyncMock)
    async def test_duration_capped_by_max(self, mock_music, monkeypatch):
        """total_duration이 MUSICGEN_MAX_DURATION 초과 시 상한으로 자름."""
        mock_music.return_value = (b"wav", None, None)
        import services.bgm_prebuild as mod

        monkeypatch.setattr(mod, "MUSICGEN_MAX_DURATION", 60.0)
        from services.bgm_prebuild import _generate_bgm

        await _generate_bgm("prompt", 80.0)
        called_duration = mock_music.call_args.kwargs["duration"]
        assert called_duration == 60.0

    @pytest.mark.asyncio
    @patch("services.bgm_prebuild.generate_music", new_callable=AsyncMock)
    async def test_exact_max_duration(self, mock_music, monkeypatch):
        """total_duration == MUSICGEN_MAX_DURATION → 그대로 통과."""
        mock_music.return_value = (b"wav", None, None)
        import services.bgm_prebuild as mod

        monkeypatch.setattr(mod, "MUSICGEN_MAX_DURATION", 60.0)
        from services.bgm_prebuild import _generate_bgm

        await _generate_bgm("prompt", 60.0)
        called_duration = mock_music.call_args.kwargs["duration"]
        assert called_duration == 60.0
