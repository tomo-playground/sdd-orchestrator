"""Tests for audio_client — HTTP client to Audio Server sidecar."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.audio_client import (
    _CIRCUIT_SCENE_FAILURE_THRESHOLD,
    check_health,
    generate_music,
    record_scene_failure,
    record_scene_success,
    synthesize_tts,
)


@pytest.fixture(autouse=True)
def _reset_circuit():
    """Reset circuit breaker state before each test."""
    import services.audio_client as mod

    mod._circuit_state.clear()
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
    async def test_naturalness_suffix_skipped_when_instruct_present(self):
        """instruct가 있으면 TTS_NATURALNESS_SUFFIX를 추가하지 않는다."""
        resp_data = {
            "audio_base64": base64.b64encode(b"wav").decode(),
            "sample_rate": 24000,
            "duration": 1.0,
            "quality_passed": True,
        }
        client_instance = _make_mock_client("post", resp_data)

        with (
            patch("services.audio_client.httpx.AsyncClient", return_value=client_instance),
            patch("services.audio_client.TTS_NATURALNESS_SUFFIX", "speak naturally"),
        ):
            await synthesize_tts(text="hello", instruct="A calm female voice")

        sent_payload = client_instance.post.call_args[1]["json"]
        assert sent_payload["instruct"] == "A calm female voice"
        assert "speak naturally" not in sent_payload["instruct"]

    @pytest.mark.asyncio
    async def test_naturalness_suffix_alone_when_no_instruct(self):
        """instruct가 빈 문자열이면 suffix만 사용된다."""
        resp_data = {
            "audio_base64": base64.b64encode(b"wav").decode(),
            "sample_rate": 24000,
            "duration": 1.0,
            "quality_passed": True,
        }
        client_instance = _make_mock_client("post", resp_data)

        with (
            patch("services.audio_client.httpx.AsyncClient", return_value=client_instance),
            patch("services.audio_client.TTS_NATURALNESS_SUFFIX", "speak naturally"),
        ):
            await synthesize_tts(text="hello", instruct="")

        sent_payload = client_instance.post.call_args[1]["json"]
        assert sent_payload["instruct"] == "speak naturally"

    @pytest.mark.asyncio
    async def test_server_error_raises(self):
        """HTTP errors propagate without affecting scene-level circuit breaker."""
        client_instance = _make_mock_client("post", side_effect=httpx.ConnectError("connection refused"))

        with patch("services.audio_client.httpx.AsyncClient", return_value=client_instance):
            import services.audio_client as mod

            with pytest.raises(httpx.ConnectError):
                await synthesize_tts(text="hello")

            # Scene-level counter NOT incremented (caller is responsible)
            state = mod._circuit_state.get("default", {})
            assert state.get("failures", 0) == 0


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

        with (
            patch("services.audio_client.httpx.AsyncClient", return_value=client_instance),
            patch("services.audio_client._ensure_server_reachable", new_callable=AsyncMock),
        ):
            wav_bytes, sr, seed = await generate_music(prompt="lo-fi chill")

        assert wav_bytes == wav_data
        assert sr == 32000
        assert seed == 42


class TestCircuitBreaker:
    """Tests for scene-level circuit breaker."""

    def test_scene_failures_open_circuit(self):
        import services.audio_client as mod

        for _ in range(_CIRCUIT_SCENE_FAILURE_THRESHOLD):
            record_scene_failure()

        state = mod._circuit_state.get("default", {})
        assert state.get("failures", 0) >= _CIRCUIT_SCENE_FAILURE_THRESHOLD
        assert state.get("open_until", 0) > 0

    def test_scene_success_resets_counter(self):
        import services.audio_client as mod

        record_scene_failure()
        record_scene_failure()
        record_scene_success()

        state = mod._circuit_state.get("default", {})
        assert state.get("failures", 0) == 0

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_requests(self):
        for _ in range(_CIRCUIT_SCENE_FAILURE_THRESHOLD):
            record_scene_failure()

        with pytest.raises(RuntimeError, match="circuit breaker"):
            await synthesize_tts(text="hello")

    def test_single_scene_retries_dont_trip_breaker(self):
        """Simulates one scene failing 3 retries — should NOT open circuit.

        Only record_scene_failure() after all retries exhausted counts.
        """
        import services.audio_client as mod

        # One scene failed all retries → 1 scene failure
        record_scene_failure()
        state = mod._circuit_state["default"]
        assert state["failures"] == 1
        # Circuit still closed (threshold is 3)
        assert state["failures"] < _CIRCUIT_SCENE_FAILURE_THRESHOLD

    def test_multiple_scene_failures_trip_breaker(self):
        """3 consecutive scenes failing → circuit opens."""
        import services.audio_client as mod

        record_scene_failure()  # scene 1 failed
        record_scene_failure()  # scene 2 failed
        assert mod._circuit_state["default"]["failures"] == 2

        record_scene_failure()  # scene 3 failed → OPEN
        state = mod._circuit_state["default"]
        assert state["failures"] == 3
        assert state["open_until"] > 0

    def test_success_between_failures_resets(self):
        """Success between failures prevents breaker from tripping."""
        import services.audio_client as mod

        record_scene_failure()  # scene 1 failed
        record_scene_failure()  # scene 2 failed
        record_scene_success()  # scene 3 succeeded → reset
        record_scene_failure()  # scene 4 failed

        assert mod._circuit_state["default"]["failures"] == 1

    def test_per_task_isolation(self):
        """Different task_ids have independent circuit breaker state."""
        import services.audio_client as mod

        record_scene_failure("task_a")
        record_scene_failure("task_a")
        record_scene_failure("task_a")  # task_a opens

        # task_b is still closed
        state_b = mod._circuit_state.get("task_b", {"failures": 0})
        assert state_b["failures"] == 0

        state_a = mod._circuit_state["task_a"]
        assert state_a["failures"] == _CIRCUIT_SCENE_FAILURE_THRESHOLD


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
