"""Unit tests for services.tts_core — TTS 생성 통합 래퍼."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.video.tts_helpers import TtsAudioResult


def _make_result(*, was_gemini: bool = False, voice_design: str | None = None) -> TtsAudioResult:
    return TtsAudioResult(
        audio_bytes=b"fake-wav",
        duration=2.5,
        cache_key="test-key",
        cached=False,
        voice_seed=42,
        voice_design=voice_design,
        was_gemini_generated=was_gemini,
    )


@pytest.mark.asyncio
class TestGenerateSceneTts:
    """generate_scene_tts 통합 래퍼 파라미터 전달 검증."""

    @patch("services.tts_core.persist_voice_design")
    @patch("services.tts_core.generate_tts_audio", new_callable=AsyncMock)
    @patch("services.tts_core.get_speaker_voice_preset", return_value=99)
    async def test_passes_all_params_to_generate_tts_audio(self, mock_preset, mock_gen, mock_persist):
        """모든 파라미터가 generate_tts_audio에 올바르게 전달되는지 검증."""
        from config import TTS_MAX_RETRIES
        from services.tts_core import generate_scene_tts

        mock_gen.return_value = _make_result()

        await generate_scene_tts(
            script="안녕하세요",
            speaker="A",
            storyboard_id=1,
            scene_db_id=10,
            voice_design_prompt="gentle",
            scene_emotion="happy",
            image_prompt_ko="소녀가 웃고 있다",
            language="korean",
        )

        mock_preset.assert_called_once_with(1, "A")
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args.kwargs
        assert call_kwargs["script"] == "안녕하세요"
        assert call_kwargs["speaker"] == "A"
        assert call_kwargs["voice_preset_id"] == 99
        assert call_kwargs["scene_voice_design"] == "gentle"
        assert call_kwargs["scene_emotion"] == "happy"
        assert call_kwargs["image_prompt_ko"] == "소녀가 웃고 있다"
        assert call_kwargs["language"] == "korean"
        assert call_kwargs["max_retries"] == TTS_MAX_RETRIES
        assert call_kwargs["force_regenerate"] is False

    @patch("services.tts_core.persist_voice_design")
    @patch("services.tts_core.generate_tts_audio", new_callable=AsyncMock)
    @patch("services.tts_core.get_speaker_voice_preset", return_value=None)
    async def test_writeback_when_gemini_generated_and_scene_db_id(self, mock_preset, mock_gen, mock_persist):
        """was_gemini_generated=True + scene_db_id → persist_voice_design 호출."""
        from services.tts_core import generate_scene_tts

        mock_gen.return_value = _make_result(was_gemini=True, voice_design="auto-gen")

        await generate_scene_tts(
            script="테스트",
            speaker="A",
            storyboard_id=1,
            scene_db_id=5,
        )

        mock_persist.assert_called_once_with(5, "auto-gen")

    @patch("services.tts_core.persist_voice_design")
    @patch("services.tts_core.generate_tts_audio", new_callable=AsyncMock)
    @patch("services.tts_core.get_speaker_voice_preset", return_value=None)
    async def test_no_writeback_when_scene_db_id_is_none(self, mock_preset, mock_gen, mock_persist):
        """was_gemini_generated=True + scene_db_id=None → persist_voice_design 미호출."""
        from services.tts_core import generate_scene_tts

        mock_gen.return_value = _make_result(was_gemini=True, voice_design="auto-gen")

        await generate_scene_tts(
            script="테스트",
            speaker="A",
            storyboard_id=1,
            scene_db_id=None,
        )

        mock_persist.assert_not_called()

    @patch("services.tts_core.persist_voice_design")
    @patch("services.tts_core.generate_tts_audio", new_callable=AsyncMock)
    @patch("services.tts_core.get_speaker_voice_preset", return_value=None)
    async def test_no_writeback_when_not_gemini_generated(self, mock_preset, mock_gen, mock_persist):
        """was_gemini_generated=False → persist_voice_design 미호출."""
        from services.tts_core import generate_scene_tts

        mock_gen.return_value = _make_result(was_gemini=False, voice_design="preset")

        await generate_scene_tts(
            script="테스트",
            speaker="A",
            storyboard_id=1,
            scene_db_id=5,
        )

        mock_persist.assert_not_called()

    @patch("services.tts_core.persist_voice_design")
    @patch("services.tts_core.generate_tts_audio", new_callable=AsyncMock)
    @patch("services.tts_core.get_speaker_voice_preset", return_value=None)
    async def test_storyboard_id_none_returns_preset_none(self, mock_preset, mock_gen, mock_persist):
        """storyboard_id=None → voice_preset_id=None으로 호출."""
        from services.tts_core import generate_scene_tts

        mock_gen.return_value = _make_result()

        await generate_scene_tts(
            script="테스트",
            speaker="A",
            storyboard_id=None,
        )

        mock_preset.assert_called_once_with(None, "A")
        assert mock_gen.call_args.kwargs["voice_preset_id"] is None
