"""Tests for VideoBuilder._check_audio_server retry logic.

Regression test for Sentry issue #7362042564:
  ConnectionError raised immediately on first health check failure.
  Fixed by adding 3-attempt retry with 5s delay between attempts.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.video.builder import VideoBuilder


def _make_builder() -> VideoBuilder:
    """Create a VideoBuilder instance without calling __init__."""
    return object.__new__(VideoBuilder)


class TestCheckAudioServerRetry:
    """_check_audio_server는 일시적 장애 시 재시도해야 한다."""

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        """1회 실패 후 2회에 성공하면 에러 없이 통과한다."""
        call_count = 0

        async def mock_check_health():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "error", "models": []}
            return {"status": "ok", "models": [{"name": "qwen3-tts", "loaded": True}]}

        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("services.audio_client.check_health", side_effect=mock_check_health),
        ):
            await _make_builder()._check_audio_server()

        assert call_count == 2
        mock_sleep.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        """3회 모두 실패하면 ConnectionError를 발생시킨다."""

        async def mock_check_health():
            return {"status": "error", "models": []}

        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("services.audio_client.check_health", side_effect=mock_check_health),
        ):
            with pytest.raises(ConnectionError, match="Audio Server is not reachable"):
                await _make_builder()._check_audio_server()

        # 3회 시도 → 중간에 sleep 2회
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(5)

    @pytest.mark.asyncio
    async def test_no_sleep_on_immediate_success(self):
        """첫 번째 시도에 성공하면 sleep 없이 즉시 통과한다."""

        async def mock_check_health():
            return {"status": "ok", "models": [{"name": "qwen3-tts", "loaded": True}]}

        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("services.audio_client.check_health", side_effect=mock_check_health),
        ):
            await _make_builder()._check_audio_server()

        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_succeeds_on_third_attempt(self):
        """2회 실패 후 3회에 성공하면 에러 없이 통과한다."""
        call_count = 0

        async def mock_check_health():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"status": "error", "models": []}
            return {"status": "ok", "models": [{"name": "qwen3-tts", "loaded": True}]}

        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("services.audio_client.check_health", side_effect=mock_check_health),
        ):
            await _make_builder()._check_audio_server()

        assert call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(5)
