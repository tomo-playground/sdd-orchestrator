"""Unit tests for TTS audio normalization."""

import numpy as np

from services.video.tts_postprocess import normalize_audio, trim_tts_audio


class TestAudioNormalization:
    """Test audio normalization functionality."""

    def test_normalize_audio_basic(self):
        """Test basic audio normalization."""
        # Create test audio with known RMS
        sr = 22050
        duration = 1.0
        # Low volume audio (RMS ~0.1)
        wav = np.random.randn(int(sr * duration)).astype(np.float32) * 0.1

        # Normalize to -20 dBFS
        normalized = normalize_audio(wav, target_dbfs=-20.0)

        # Check RMS is close to target
        rms = np.sqrt(np.mean(normalized**2))
        dbfs = 20 * np.log10(rms)

        # Should be within 1dB of target
        assert abs(dbfs - (-20.0)) < 1.0
        assert normalized.dtype == np.float32

    def test_normalize_audio_clipping(self):
        """Test that normalization clips to prevent overflow."""
        # Create loud audio
        wav = np.random.randn(1000).astype(np.float32) * 0.5

        # Normalize to very high level
        normalized = normalize_audio(wav, target_dbfs=-5.0)

        # Check no values exceed [-1, 1]
        assert np.all(normalized >= -1.0)
        assert np.all(normalized <= 1.0)

    def test_normalize_audio_silence(self):
        """Test that silence is handled gracefully."""
        # Create near-silence
        wav = np.zeros(1000, dtype=np.float32)

        # Normalize (should return unchanged)
        normalized = normalize_audio(wav, target_dbfs=-20.0)

        # Should be unchanged
        assert np.allclose(normalized, wav)

    def test_trim_tts_audio_with_normalization(self):
        """Test trim_tts_audio with normalization enabled."""
        sr = 22050

        # Create quiet audio (RMS ~0.01, -40 dBFS) so normalization to -20 dBFS is clear
        signal = np.random.randn(int(sr * 0.5)).astype(np.float32) * 0.01
        silence = np.zeros(int(sr * 0.25), dtype=np.float32)
        wav = np.concatenate([silence, signal, silence])

        # Process with normalization
        processed = trim_tts_audio(wav, sr, normalize=True)

        # Check that audio was trimmed (shorter than original)
        assert len(processed) < len(wav)

        # Check that audio was normalized (RMS should be higher)
        original_rms = np.sqrt(np.mean(signal**2))
        processed_rms = np.sqrt(np.mean(processed**2))
        assert processed_rms > original_rms

    def test_trim_tts_audio_without_normalization(self):
        """Test trim_tts_audio with normalization disabled."""
        sr = 22050

        # Create test audio
        signal = np.random.randn(int(sr * 0.5)).astype(np.float32) * 0.1
        silence = np.zeros(int(sr * 0.25), dtype=np.float32)
        wav = np.concatenate([silence, signal, silence])

        # Process without normalization
        processed = trim_tts_audio(wav, sr, normalize=False)

        # Check that audio was trimmed
        assert len(processed) < len(wav)

        # RMS should be similar (no normalization)
        original_rms = np.sqrt(np.mean(signal**2))
        processed_rms = np.sqrt(np.mean(processed**2))
        assert abs(processed_rms - original_rms) < 0.1

    def test_normalize_audio_different_targets(self):
        """Test normalization with different target levels."""
        wav = np.random.randn(1000).astype(np.float32) * 0.1

        # Test different target levels
        for target in [-10.0, -15.0, -20.0, -25.0]:
            normalized = normalize_audio(wav, target_dbfs=target)
            rms = np.sqrt(np.mean(normalized**2))
            dbfs = 20 * np.log10(rms)

            # Should be within 1dB of target
            assert abs(dbfs - target) < 1.0
