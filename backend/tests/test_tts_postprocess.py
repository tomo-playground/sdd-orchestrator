"""Tests for TTS audio post-processing utilities."""

import numpy as np

from services.video.tts_postprocess import validate_tts_duration


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
