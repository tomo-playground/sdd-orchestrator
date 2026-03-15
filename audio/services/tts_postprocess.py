"""TTS audio post-processing: trimming, hallucination detection, silence compression, normalization.

Provides a 6-step pipeline for cleaning Qwen-TTS output:
1. Leading/trailing silence removal (librosa.effects.trim)
2. Trailing hallucination detection (energy decay->re-rise pattern)
3. Internal silence compression (cap gaps at TTS_SILENCE_MAX_MS)
4. Decrackle: median filter to remove impulse noise spikes
5. Fade-in/out (smooth click artifacts)
6. Audio normalization (RMS-based dBFS targeting)
"""

from __future__ import annotations

import logging

import numpy as np

from config import TTS_AUDIO_FADE_MS, TTS_AUDIO_TRIM_TOP_DB, TTS_SILENCE_MAX_MS

logger = logging.getLogger("audio-server")


def _strip_trailing_hallucination(wav: np.ndarray, sr: int) -> np.ndarray:
    """Cut audio at energy valley near the end (decay->re-rise = hallucination)."""
    frame_len = int(sr * 0.05)  # 50ms frames
    if len(wav) < frame_len * 4:
        return wav
    n_frames = len(wav) // frame_len
    rms = np.array([np.sqrt(np.mean(wav[i * frame_len : (i + 1) * frame_len] ** 2)) for i in range(n_frames)])
    if len(rms) < 4:
        return wav
    scan_start = max(int(len(rms) * 0.7), len(rms) - 15)
    min_idx = scan_start + np.argmin(rms[scan_start:])

    if min_idx < len(rms) - 2:
        valley_rms = rms[min_idx]
        peak_after = np.max(rms[min_idx + 1 :])
        median_rms = np.median(rms[:scan_start]) if scan_start > 0 else np.median(rms)

        remaining_frames = len(rms) - min_idx - 1
        if remaining_frames >= 3 and valley_rms < median_rms * 0.01 and peak_after > median_rms * 0.4:
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
    """Compress internal silence gaps exceeding TTS_SILENCE_MAX_MS."""
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


def _decrackle(wav: np.ndarray, sr: int, kernel_size: int = 3) -> np.ndarray:
    """Remove impulse noise (crackling) via median filter on spike regions only.

    Instead of applying median filter to the entire signal (which softens
    transients), we detect sample-to-sample spikes that exceed a threshold
    and only smooth those regions. This preserves speech quality while
    removing crackling artifacts from autoregressive TTS generation.
    """
    from scipy.signal import medfilt

    diffs = np.abs(np.diff(wav))
    # Adaptive threshold: spikes > 8x the median difference
    median_diff = np.median(diffs)
    threshold = max(median_diff * 8, 0.02)  # floor at 0.02 for very quiet audio

    spike_mask = np.zeros(len(wav), dtype=bool)
    spike_indices = np.where(diffs > threshold)[0]

    if len(spike_indices) == 0:
        return wav

    # Expand spike regions by ±2 samples for smooth blending
    for idx in spike_indices:
        start = max(0, idx - 2)
        end = min(len(wav), idx + 3)
        spike_mask[start:end] = True

    spike_count = len(spike_indices)
    filtered = medfilt(wav, kernel_size=kernel_size)

    result = wav.copy()
    result[spike_mask] = filtered[spike_mask]

    if spike_count > 0:
        logger.info("[TTS] Decrackle: smoothed %d spike regions (threshold=%.4f)", spike_count, threshold)

    return result


def normalize_audio(wav: np.ndarray, target_dbfs: float = -23.0, peak_limit_db: float = -1.0) -> np.ndarray:
    """Normalize audio to target dBFS with peak limiting (no hard clipping)."""
    rms = np.sqrt(np.mean(wav**2))

    if rms < 1e-6:
        logger.warning("[TTS] Audio normalization skipped: RMS too low (%.6f)", rms)
        return wav

    current_dbfs = 20 * np.log10(rms)
    gain_db = target_dbfs - current_dbfs

    # 피크 제한: 증폭 후 피크가 peak_limit_db를 넘지 않도록
    peak = np.max(np.abs(wav))
    if peak > 1e-6:
        max_gain_db = peak_limit_db - 20 * np.log10(peak)
        gain_db = min(gain_db, max_gain_db)

    gain_linear = 10 ** (gain_db / 20)
    normalized = wav * gain_linear

    logger.info(
        "[TTS] Audio normalized: %.1f dBFS -> %.1f dBFS (gain: %.1f dB, peak: %.3f)",
        current_dbfs,
        target_dbfs,
        gain_db,
        np.max(np.abs(normalized)),
    )
    return normalized


def trim_tts_audio(wav: np.ndarray, sr: int, normalize: bool = True) -> np.ndarray:
    """5-step post-processing pipeline."""
    import librosa

    # Step 1: trim leading/trailing silence
    trimmed, _ = librosa.effects.trim(wav, top_db=TTS_AUDIO_TRIM_TOP_DB)
    trimmed = trimmed.copy()

    # Step 2: cut trailing hallucination
    trimmed = _strip_trailing_hallucination(trimmed, sr)

    # Step 3: compress internal silence gaps
    trimmed = _compress_internal_silence(trimmed, sr)

    # Step 4: decrackle — remove impulse noise spikes
    trimmed = _decrackle(trimmed, sr)

    # Step 5: fade-in/out
    fade_samples = int(sr * TTS_AUDIO_FADE_MS / 1000)
    if len(trimmed) > fade_samples * 2:
        trimmed[:fade_samples] *= np.linspace(0, 1, fade_samples)
        trimmed[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    # Step 6: normalize audio
    if normalize:
        trimmed = normalize_audio(trimmed)

    return trimmed


def validate_tts_duration(wav: np.ndarray, sr: int, min_sec: float) -> bool:
    """Check if TTS audio meets minimum duration requirement."""
    return len(wav) / sr >= min_sec


def validate_tts_quality(wav: np.ndarray, sr: int) -> bool:
    """Quality checks: silence ratio, SNR proxy, and crackling detection."""
    if len(wav) == 0:
        return False

    max_val = np.max(np.abs(wav))
    if max_val < 1e-4:
        return False

    threshold = max_val * 0.05
    voiced_samples = np.sum(np.abs(wav) > threshold)
    silence_ratio = 1.0 - (voiced_samples / len(wav))

    if silence_ratio > 0.8:
        logger.warning("[TTS] Quality check failed: excessive silence (%.1f%%)", silence_ratio * 100)
        return False

    median_abs = np.median(np.abs(wav))
    if median_abs > max_val * 0.3:
        logger.warning("[TTS] Quality check failed: poor SNR (median/peak = %.2f)", median_abs / max_val)
        return False

    # Crackling detection: count residual spike clusters after decrackle
    diffs = np.abs(np.diff(wav))
    median_diff = np.median(diffs)
    spike_threshold = max(median_diff * 12, 0.03)
    spikes = np.sum(diffs > spike_threshold)
    spike_ratio = spikes / len(wav)
    if spike_ratio > 0.02:
        logger.warning(
            "[TTS] Quality check failed: excessive crackling (spikes=%d, ratio=%.3f)",
            spikes,
            spike_ratio,
        )
        return False

    return True
