"""TTS audio post-processing: trimming, hallucination detection, silence compression.

Provides a 4-step pipeline for cleaning Qwen-TTS output:
1. Leading/trailing silence removal (librosa.effects.trim)
2. Trailing hallucination detection (energy decay→re-rise pattern)
3. Internal silence compression (cap gaps at TTS_SILENCE_MAX_MS)
4. Fade-in/out (smooth click artifacts)
"""

from __future__ import annotations

import numpy as np

from config import (
    TTS_AUDIO_FADE_MS,
    TTS_AUDIO_TRIM_TOP_DB,
    TTS_SILENCE_MAX_MS,
    logger,
)


def _strip_trailing_hallucination(wav: np.ndarray, sr: int) -> np.ndarray:
    """Cut audio at energy valley near the end (decay->re-rise = hallucination)."""
    frame_len = int(sr * 0.05)  # 50ms frames
    if len(wav) < frame_len * 4:
        return wav
    n_frames = len(wav) // frame_len
    rms = np.array([np.sqrt(np.mean(wav[i * frame_len : (i + 1) * frame_len] ** 2)) for i in range(n_frames)])
    if len(rms) < 4:
        return wav
    # Scan last 30% for valley->rise pattern
    # Hallucination often manifests as a re-rising energy after a natural decay
    scan_start = max(int(len(rms) * 0.7), len(rms) - 15)
    min_idx = scan_start + np.argmin(rms[scan_start:])

    if min_idx < len(rms) - 2:  # Must have at least a few frames after valley
        valley_rms = rms[min_idx]
        peak_after = np.max(rms[min_idx + 1 :])
        median_rms = np.median(rms[:scan_start]) if scan_start > 0 else np.median(rms)

        # Criteria: sharp rise (>3x valley) and significant energy (>15% median)
        if valley_rms < median_rms * 0.05 and peak_after > median_rms * 0.15:
            cut_sample = min_idx * frame_len
            logger.info(
                "[TTS] Trailing hallucination cut: valley=%.4f, peak=%.4f (median=%.4f) at %.2fs",
                valley_rms,
                peak_after,
                median_rms,
                cut_sample / sr,
            )
            return wav[:cut_sample]
    return wav


def _compress_internal_silence(wav: np.ndarray, sr: int) -> np.ndarray:
    """Compress internal silence gaps exceeding TTS_SILENCE_MAX_MS.

    Uses librosa.effects.split to identify voiced segments. Gaps between
    segments that exceed the configured maximum are replaced with silence
    of exactly max_ms length (sub-threshold audio below -30dB is zeroed).
    """
    import librosa

    max_silence = int(sr * TTS_SILENCE_MAX_MS / 1000)
    intervals = librosa.effects.split(wav, top_db=TTS_AUDIO_TRIM_TOP_DB)
    if len(intervals) <= 1:
        return wav
    parts: list[np.ndarray] = []
    for idx, (start, end) in enumerate(intervals):
        if idx > 0:
            prev_end = intervals[idx - 1][1]
            gap = start - prev_end
            silence_len = min(gap, max_silence)
            parts.append(np.zeros(silence_len, dtype=wav.dtype))
        parts.append(wav[start:end])
    result = np.concatenate(parts)
    removed = len(wav) - len(result)
    if removed > 0:
        logger.info("[TTS] Internal silence compressed: removed %.2fs", removed / sr)
    return result


def trim_tts_audio(wav: np.ndarray, sr: int) -> np.ndarray:
    """Trim silence/artifacts, compress internal gaps, apply fade."""
    import librosa

    # Step 1: trim leading/trailing silence
    trimmed, _ = librosa.effects.trim(wav, top_db=TTS_AUDIO_TRIM_TOP_DB)
    trimmed = trimmed.copy()

    # Step 2: cut trailing hallucination (energy decay->re-rise)
    trimmed = _strip_trailing_hallucination(trimmed, sr)

    # Step 3: compress internal silence gaps
    trimmed = _compress_internal_silence(trimmed, sr)

    # Step 4: fade-in/out
    fade_samples = int(sr * TTS_AUDIO_FADE_MS / 1000)
    if len(trimmed) > fade_samples * 2:
        trimmed[:fade_samples] *= np.linspace(0, 1, fade_samples)
        trimmed[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    return trimmed


def validate_tts_duration(wav: np.ndarray, sr: int, min_sec: float) -> bool:
    """Check if TTS audio meets minimum duration requirement."""
    return len(wav) / sr >= min_sec


def validate_tts_quality(wav: np.ndarray, sr: int) -> bool:
    """Perform basic quality checks on TTS audio.

    Checks for:
    1. Excessive silence ratio (>50% of audio)
    2. Signal-to-noise ratio (SNR) proxy (max energy vs median noise)
    """
    if len(wav) == 0:
        return False

    # Check silence ratio
    max_val = np.max(np.abs(wav))
    if max_val < 1e-4:
        return False

    threshold = max_val * 0.05
    voiced_samples = np.sum(np.abs(wav) > threshold)
    silence_ratio = 1.0 - (voiced_samples / len(wav))

    if silence_ratio > 0.8:  # Over 80% silence is suspicious (relaxed for short Korean scripts)
        logger.warning("[TTS] Quality check failed: excessive silence (%.1f%%)", silence_ratio * 100)
        return False

    # Check energy spread (proxy for SNR/hallucination noise)
    # If the median absolute energy is too high relative to peak, it might be noise/hum
    median_abs = np.median(np.abs(wav))
    if median_abs > max_val * 0.3:
        logger.warning("[TTS] Quality check failed: poor SNR (median/peak = %.2f)", median_abs / max_val)
        return False

    return True
