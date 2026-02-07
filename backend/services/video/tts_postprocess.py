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
    rms = np.array(
        [np.sqrt(np.mean(wav[i * frame_len : (i + 1) * frame_len] ** 2)) for i in range(n_frames)]
    )
    if len(rms) < 4:
        return wav
    # Scan last 25% for valley->rise pattern
    scan_start = max(len(rms) // 2, len(rms) - 20)
    min_idx = scan_start + np.argmin(rms[scan_start:])
    if min_idx < len(rms) - 1:
        valley_rms = rms[min_idx]
        peak_after = np.max(rms[min_idx + 1 :])
        median_rms = np.median(rms[:scan_start]) if scan_start > 0 else np.median(rms)
        if valley_rms < median_rms * 0.1 and peak_after > median_rms * 0.3:
            cut_sample = min_idx * frame_len
            logger.info("[TTS] Trailing hallucination cut at %.2fs", cut_sample / sr)
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
