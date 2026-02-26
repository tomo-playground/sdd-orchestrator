"""FFmpeg command construction and async encoding.

Builds the FFmpeg command line from the VideoBuilder state and runs
the encode as an async subprocess with real-time progress parsing.
Each function receives the VideoBuilder instance as its first argument.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from config import (
    AUDIO_BITRATE,
    AUDIO_CODEC,
    FFMPEG_TIMEOUT_SECONDS,
    VIDEO_CODEC,
    VIDEO_CRF,
    VIDEO_FPS,
    VIDEO_PIX_FMT,
    VIDEO_PRESET,
    logger,
)
from services.video.progress import calc_overall_percent

if TYPE_CHECKING:
    from services.video.builder import VideoBuilder


def _classify_filter(f: str) -> str:
    """Classify a filter string for debug logging."""
    if "zoompan" in f:
        return "KenBurns"
    if "xfade" in f:
        return "Transition"
    if "acrossfade" in f:
        return "AudioXfade"
    if "overlay" in f:
        return "Overlay"
    if "sidechaincompress" in f:
        return "Ducking"
    if "amix" in f:
        return "AudioMix"
    if "scale" in f or "crop" in f:
        return "Scale/Crop"
    if "aresample" in f or "adelay" in f:
        return "AudioProc"
    if "atrim" in f or "trim" in f:
        return "Trim"
    if "fade" in f:
        return "Fade"
    if "volume" in f:
        return "Volume"
    if "eq=" in f or "vignette" in f:
        return "ColorGrade"
    if "asplit" in f:
        return "AudioSplit"
    if "null" in f:
        return "Passthrough"
    return "Other"


def build_ffmpeg_cmd(builder: VideoBuilder) -> list[str]:
    """Build the FFmpeg command arguments."""
    filter_complex_str = ";".join(builder.filters)

    logger.info("FFmpeg Filter Chain (%d filters):", len(builder.filters))
    logger.info("-" * 80)
    for idx, f in enumerate(builder.filters):
        label = _classify_filter(f)
        logger.info(f"  [{idx:02d}/{len(builder.filters) - 1:02d}] ({label:12s}) {f}")
    logger.info("-" * 80)
    logger.info(f"Video map: {builder._map_v}")
    logger.info(f"Audio map: {builder._map_a}")
    logger.info(f"Total duration: {builder._total_dur:.2f}s")
    logger.info(f"Include subtitles: {builder.request.include_scene_text}")
    logger.info("=" * 80)

    # Store for error diagnostics
    builder._filter_debug_dump = "\n".join(
        f"  [{idx:02d}] ({_classify_filter(f):12s}) {f}" for idx, f in enumerate(builder.filters)
    )

    return [
        "ffmpeg",
        "-y",
        *builder.input_args,
        "-filter_complex",
        filter_complex_str,
        "-map",
        builder._map_v,
        "-map",
        builder._map_a,
        "-r",
        str(VIDEO_FPS),
        "-c:v",
        VIDEO_CODEC,
        "-pix_fmt",
        VIDEO_PIX_FMT,
        "-preset",
        VIDEO_PRESET,
        "-crf",
        str(VIDEO_CRF),
        "-movflags",
        "+faststart",
        "-c:a",
        AUDIO_CODEC,
        "-b:a",
        AUDIO_BITRATE,
        str(builder.video_path),
    ]


async def encode_async(builder: VideoBuilder) -> None:
    """Encode using async subprocess with real-time progress parsing."""
    cmd = build_ffmpeg_cmd(builder)
    logger.info("Running FFmpeg async (timeout=%ds)", FFMPEG_TIMEOUT_SECONDS)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Parse FFmpeg stderr for time= progress
    _TIME_RE = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
    total_dur = builder._total_dur or 1.0
    stderr_lines: list[str] = []

    async def _read_stderr():
        if proc.stderr is None:
            return
        buf = b""
        while True:
            chunk = await proc.stderr.read(512)
            if not chunk:
                break
            buf += chunk
            # Process complete lines/carriage returns
            while b"\r" in buf or b"\n" in buf:
                sep = buf.find(b"\r")
                if sep == -1:
                    sep = buf.find(b"\n")
                line = buf[:sep].decode("utf-8", errors="replace")
                buf = buf[sep + 1 :]
                if line.strip():
                    stderr_lines.append(line)
                m = _TIME_RE.search(line)
                if m and builder._progress:
                    secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 100
                    enc_pct = min(int(secs / total_dur * 100), 99)
                    builder._progress.encode_percent = enc_pct
                    builder._progress.percent = calc_overall_percent(builder._progress)
                    builder._progress.notify()

    try:
        await asyncio.wait_for(
            asyncio.gather(_read_stderr(), proc.wait()),
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        proc.kill()
        logger.error("FFmpeg timed out after %d seconds", FFMPEG_TIMEOUT_SECONDS)
        raise RuntimeError(f"FFmpeg process timed out after {FFMPEG_TIMEOUT_SECONDS} seconds") from None

    if proc.returncode != 0:
        stderr_tail = "\n".join(stderr_lines[-10:])
        filter_dump = getattr(builder, "_filter_debug_dump", "")
        logger.error("FFmpeg failed (rc=%d). Filter chain:\n%s", proc.returncode, filter_dump)
        logger.error("FFmpeg stderr (last 10 lines):\n%s", stderr_tail)
        raise RuntimeError(f"FFmpeg failed with exit code {proc.returncode}: {stderr_tail[:500]}")
