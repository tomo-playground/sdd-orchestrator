"""Tests for Audio Server API endpoints using FastAPI TestClient.

These tests mock the ML models to avoid requiring actual model downloads.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a TestClient with mocked model loading."""
    with (
        patch("services.tts_engine.load_model") as mock_tts_load,
        patch("services.music_engine.load_model") as mock_music_load,
    ):
        mock_tts_load.return_value = MagicMock()
        mock_music_load.return_value = (MagicMock(), MagicMock())

        from main import app

        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    """GET /health tests."""

    def test_health_returns_model_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "loading")
        assert len(data["models"]) == 2

    def test_health_model_names(self, client):
        resp = client.get("/health")
        data = resp.json()
        names = {m["name"] for m in data["models"]}
        assert "qwen3-tts" in names
        assert "musicgen-small" in names


class TestTTSSynthesizeEndpoint:
    """POST /tts/synthesize tests."""

    def test_missing_text_returns_422(self, client):
        resp = client.post("/tts/synthesize", json={"text": ""})
        assert resp.status_code == 422

    @patch("main.tts_engine")
    def test_successful_synthesis(self, mock_engine, client):
        """Test full synthesis pipeline with mocked model."""
        sr = 24000
        wav = np.random.randn(sr).astype(np.float32) * 0.3
        mock_engine.get_model.return_value = MagicMock()
        mock_engine.synthesize.return_value = ([wav], sr)
        mock_engine.tts_cache_key.return_value = "test_cache_key"

        # Mock cache miss
        with patch("main.TTS_CACHE_DIR") as mock_cache_dir:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_cache_dir.__truediv__ = MagicMock(return_value=mock_path)

            resp = client.post(
                "/tts/synthesize",
                json={
                    "text": "Hello world test speech",
                    "instruct": "A calm male voice",
                    "seed": 42,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "audio_base64" in data
        assert data["sample_rate"] > 0
        assert data["duration"] > 0


class TestMusicGenerateEndpoint:
    """POST /music/generate tests."""

    def test_missing_prompt_returns_422(self, client):
        resp = client.post("/music/generate", json={"prompt": ""})
        assert resp.status_code == 422

    @patch("main.music_engine")
    def test_successful_generation(self, mock_engine, client):
        """Test full generation pipeline with mocked model."""
        import io

        import scipy.io.wavfile

        # Create valid WAV bytes
        sr = 32000
        audio = np.random.randn(sr * 5).astype(np.float32) * 0.3
        buf = io.BytesIO()
        scipy.io.wavfile.write(buf, sr, audio)
        wav_bytes = buf.getvalue()

        mock_engine.generate_music.return_value = (wav_bytes, sr, 42)
        mock_engine.music_cache_key.return_value = "test_key"
        mock_engine._cache_path.return_value = MagicMock(exists=MagicMock(return_value=False))

        resp = client.post(
            "/music/generate",
            json={"prompt": "lo-fi chill beats", "duration": 10.0, "seed": 42},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "audio_base64" in data
        assert data["actual_seed"] == 42
        assert data["sample_rate"] == sr
