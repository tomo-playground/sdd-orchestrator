"""Tests for TTS audio post-processing utilities."""

import numpy as np

from services.tts_postprocess import normalize_audio, trim_tts_audio, validate_tts_duration, validate_tts_quality


class TestValidateTtsDuration:
    """validate_tts_duration: minimum duration check."""

    def test_above_threshold(self):
        wav = np.zeros(24000, dtype=np.float32)
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is True

    def test_below_threshold(self):
        wav = np.zeros(7200, dtype=np.float32)
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is False

    def test_exact_boundary(self):
        wav = np.zeros(12000, dtype=np.float32)
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is True

    def test_empty_wav(self):
        wav = np.zeros(0, dtype=np.float32)
        assert validate_tts_duration(wav, sr=24000, min_sec=0.5) is False


class TestValidateTtsQuality:
    """validate_tts_quality: silence ratio and SNR checks."""

    def test_normal_speech(self):
        sr = 24000
        t = np.linspace(0, 1.0, sr, dtype=np.float32)
        envelope = np.where(np.sin(2 * np.pi * 3 * t) > 0, 1.0, 0.05)
        wav = (0.5 * np.sin(2 * np.pi * 440 * t) * envelope).astype(np.float32)
        assert validate_tts_quality(wav, sr) is True

    def test_empty_wav_fails(self):
        wav = np.zeros(0, dtype=np.float32)
        assert validate_tts_quality(wav, sr=24000) is False

    def test_silence_fails(self):
        wav = np.zeros(24000, dtype=np.float32)
        assert validate_tts_quality(wav, sr=24000) is False

    def test_excessive_silence_fails(self):
        sr = 24000
        wav = np.zeros(sr, dtype=np.float32)
        voiced_len = int(sr * 0.1)
        wav[:voiced_len] = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, voiced_len, dtype=np.float32))
        assert validate_tts_quality(wav, sr) is False

    def test_noisy_audio_fails(self):
        sr = 24000
        wav = np.full(sr, 0.4, dtype=np.float32)
        wav[0] = 0.5
        assert validate_tts_quality(wav, sr) is False


class TestAudioNormalization:
    """Test audio normalization functionality."""

    def test_normalize_audio_basic(self):
        sr = 22050
        wav = np.random.randn(int(sr * 1.0)).astype(np.float32) * 0.1
        normalized = normalize_audio(wav, target_dbfs=-20.0)
        rms = np.sqrt(np.mean(normalized**2))
        dbfs = 20 * np.log10(rms)
        assert abs(dbfs - (-20.0)) < 1.0

    def test_normalize_audio_clipping(self):
        wav = np.random.randn(1000).astype(np.float32) * 0.5
        normalized = normalize_audio(wav, target_dbfs=-5.0)
        assert np.all(normalized >= -1.0)
        assert np.all(normalized <= 1.0)

    def test_normalize_audio_silence(self):
        wav = np.zeros(1000, dtype=np.float32)
        normalized = normalize_audio(wav, target_dbfs=-20.0)
        assert np.allclose(normalized, wav)

    def test_trim_tts_audio_with_normalization(self):
        sr = 22050
        signal = np.random.randn(int(sr * 0.5)).astype(np.float32) * 0.01
        silence = np.zeros(int(sr * 0.25), dtype=np.float32)
        wav = np.concatenate([silence, signal, silence])
        processed = trim_tts_audio(wav, sr, normalize=True)
        assert len(processed) < len(wav)
        original_rms = np.sqrt(np.mean(signal**2))
        processed_rms = np.sqrt(np.mean(processed**2))
        assert processed_rms > original_rms

    def test_trim_tts_audio_without_normalization(self):
        sr = 22050
        signal = np.random.randn(int(sr * 0.5)).astype(np.float32) * 0.1
        silence = np.zeros(int(sr * 0.25), dtype=np.float32)
        wav = np.concatenate([silence, signal, silence])
        processed = trim_tts_audio(wav, sr, normalize=False)
        assert len(processed) < len(wav)
