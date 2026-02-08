"""Tests for TTS audio post-processing utilities."""

import numpy as np

from schemas import VideoScene
from services.video.tts_postprocess import validate_tts_duration, validate_tts_quality


class TestValidateTtsDuration:
    """validate_tts_duration: minimum duration check."""

    def test_above_threshold(self):
        wav = np.zeros(24000, dtype=np.float32)  # 1.0s at 24kHz
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is True

    def test_below_threshold(self):
        wav = np.zeros(7200, dtype=np.float32)  # 0.3s at 24kHz
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is False

    def test_exact_boundary(self):
        wav = np.zeros(12000, dtype=np.float32)  # 0.5s at 24kHz
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is True

    def test_empty_wav(self):
        wav = np.zeros(0, dtype=np.float32)
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is False


class TestValidateTtsQuality:
    """validate_tts_quality: silence ratio and SNR checks."""

    def test_normal_speech(self):
        """Simulated speech audio (amplitude-modulated) should pass quality check."""
        sr = 24000
        t = np.linspace(0, 1.0, sr, dtype=np.float32)
        # Amplitude-modulated signal: silence gaps simulate natural speech pauses
        envelope = np.where(np.sin(2 * np.pi * 3 * t) > 0, 1.0, 0.05)
        wav = (0.5 * np.sin(2 * np.pi * 440 * t) * envelope).astype(np.float32)
        assert validate_tts_quality(wav, sr) is True

    def test_empty_wav_fails(self):
        wav = np.zeros(0, dtype=np.float32)
        assert validate_tts_quality(wav, sr=24000) is False

    def test_silence_fails(self):
        """All-silent audio should fail."""
        wav = np.zeros(24000, dtype=np.float32)
        assert validate_tts_quality(wav, sr=24000) is False

    def test_excessive_silence_fails(self):
        """Audio with >80% silence should fail."""
        sr = 24000
        wav = np.zeros(sr, dtype=np.float32)
        # Only 10% voiced (90% silence > 80% threshold)
        voiced_len = int(sr * 0.1)
        wav[:voiced_len] = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, voiced_len, dtype=np.float32))
        assert validate_tts_quality(wav, sr) is False

    def test_noisy_audio_fails(self):
        """Audio with high median energy (noise/hum) should fail."""
        sr = 24000
        wav = np.full(sr, 0.4, dtype=np.float32)  # Constant high amplitude = noise
        wav[0] = 0.5  # Slight peak
        assert validate_tts_quality(wav, sr) is False


class TestVideoSceneExtraFields:
    """VideoScene with extra='allow' should handle missing fields safely."""

    def test_access_defined_fields(self):
        scene = VideoScene(image_url="http://example.com/img.png", script="Hello")
        assert scene.script == "Hello"
        assert scene.speaker == "Narrator"

    def test_getattr_missing_field_returns_default(self):
        """image_prompt_ko is NOT in VideoScene schema — getattr must be used."""
        scene = VideoScene(image_url="http://example.com/img.png")
        assert getattr(scene, "image_prompt_ko", "") == ""
        assert getattr(scene, "image_prompt", "") == ""

    def test_extra_allow_stores_extra_fields(self):
        """VideoScene with extra='allow' stores fields passed in constructor."""
        scene = VideoScene(
            image_url="http://example.com/img.png",
            image_prompt_ko="한국어 프롬프트",
        )
        assert scene.image_prompt_ko == "한국어 프롬프트"
