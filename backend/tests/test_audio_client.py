"""Tests for audio_client — HTTP client to Audio Server sidecar."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.audio_client import (
    _CIRCUIT_FAILURE_THRESHOLD,
    _record_failure,
    _record_success,
    check_health,
    generate_music,
    synthesize_tts,
)


@pytest.fixture(autouse=True)
def _reset_circuit():
    """Reset circuit breaker state before each test."""
    import services.audio_client as mod

    mod._circuit_failures = 0
    mod._circuit_open_until = 0.0
    yield


def _make_mock_client(method: str, response_data: dict | None = None, side_effect=None):
    """Create a properly mocked httpx.AsyncClient context manager.

    httpx.Response.json() and raise_for_status() are synchronous methods,
    so they must use MagicMock (not AsyncMock).
    """
    mock_response = MagicMock()
    if response_data is not None:
        mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    client_instance = AsyncMock()
    if side_effect:
        getattr(client_instance, method).side_effect = side_effect
    else:
        getattr(client_instance, method).return_value = mock_response
    client_instance.__aenter__ = AsyncMock(return_value=client_instance)
    client_instance.__aexit__ = AsyncMock(return_value=False)
    return client_instance


class TestSynthesizeTTS:
    """Tests for synthesize_tts HTTP call."""

    @pytest.mark.asyncio
    async def test_success(self):
        audio_data = b"fake-wav-data"
        resp_data = {
            "audio_base64": base64.b64encode(audio_data).decode(),
            "sample_rate": 24000,
            "duration": 2.5,
            "quality_passed": True,
            "cache_hit": False,
        }
        client_instance = _make_mock_client("post", resp_data)

        with patch("services.audio_client.httpx.AsyncClient", return_value=client_instance):
            audio_bytes, sr, dur, quality = await synthesize_tts(text="hello", instruct="test")

        assert audio_bytes == audio_data
        assert sr == 24000
        assert dur == 2.5
        assert quality is True

    @pytest.mark.asyncio
    async def test_server_error_records_failure(self):
        client_instance = _make_mock_client("post", side_effect=httpx.ConnectError("connection refused"))

        with patch("services.audio_client.httpx.AsyncClient", return_value=client_instance):
            import services.audio_client as mod

            mod._circuit_failures = 0

            with pytest.raises(httpx.ConnectError):
                await synthesize_tts(text="hello")

            assert mod._circuit_failures == 1


class TestGenerateMusic:
    """Tests for generate_music HTTP call."""

    @pytest.mark.asyncio
    async def test_success(self):
        wav_data = b"RIFF-fake-wav"
        resp_data = {
            "audio_base64": base64.b64encode(wav_data).decode(),
            "sample_rate": 32000,
            "actual_seed": 42,
            "duration": 10.0,
            "cache_hit": False,
        }
        client_instance = _make_mock_client("post", resp_data)

        with patch("services.audio_client.httpx.AsyncClient", return_value=client_instance):
            wav_bytes, sr, seed = await generate_music(prompt="lo-fi chill")

        assert wav_bytes == wav_data
        assert sr == 32000
        assert seed == 42


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""

    def test_failures_open_circuit(self):
        import services.audio_client as mod

        for _ in range(_CIRCUIT_FAILURE_THRESHOLD):
            _record_failure()

        assert mod._circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD
        assert mod._circuit_open_until > 0

    def test_success_resets_circuit(self):
        import services.audio_client as mod

        _record_failure()
        _record_failure()
        _record_success()

        assert mod._circuit_failures == 0

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_requests(self):
        for _ in range(_CIRCUIT_FAILURE_THRESHOLD):
            _record_failure()

        with pytest.raises(RuntimeError, match="circuit breaker"):
            await synthesize_tts(text="hello")


class TestCheckHealth:
    """Tests for check_health."""

    @pytest.mark.asyncio
    async def test_healthy_server(self):
        resp_data = {
            "status": "ok",
            "models": [
                {"name": "qwen3-tts", "loaded": True, "device": "cpu"},
                {"name": "musicgen-small", "loaded": True, "device": "cpu"},
            ],
        }
        client_instance = _make_mock_client("get", resp_data)

        with patch("services.audio_client.httpx.AsyncClient", return_value=client_instance):
            result = await check_health()

        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_unreachable_server_returns_error(self):
        client_instance = _make_mock_client("get", side_effect=httpx.ConnectError("refused"))

        with patch("services.audio_client.httpx.AsyncClient", return_value=client_instance):
            result = await check_health()

        assert result["status"] == "error"
