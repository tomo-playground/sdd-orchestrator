"""Transition, overlay, and BGM effects for the video pipeline.

Handles scene transitions (xfade/acrossfade), overlay graphics
(header/footer slide-in), and background music mixing with optional
audio ducking. Each function receives the VideoBuilder instance
as its first argument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import logger
from services.storage import get_storage
from services.video.utils import resolve_bgm_file

if TYPE_CHECKING:
    from services.video.builder import VideoBuilder


def resolve_scene_transition(builder: VideoBuilder, scene_idx: int) -> str:
    """Resolve transition for a specific scene pair.

    Auto mode: same background -> fade, different background -> slide/wipe.
    """
    import random

    from constants.transition import LOCATION_CHANGE_TRANSITIONS, RANDOM_ELIGIBLE, get_transition_name

    if builder.transition_type == "random":
        seed = hash(f"{builder.project_id}_{scene_idx}")
        return random.Random(seed).choice(RANDOM_ELIGIBLE)

    if builder.transition_type != "auto":
        return get_transition_name(builder.transition_type)

    # Auto mode: detect location change via background_id
    prev_bg = getattr(builder.request.scenes[scene_idx - 1], "background_id", None)
    curr_bg = getattr(builder.request.scenes[scene_idx], "background_id", None)

    if prev_bg and curr_bg and prev_bg != curr_bg:
        seed = hash(f"{builder.project_id}_{scene_idx}")
        return random.Random(seed).choice(LOCATION_CHANGE_TRANSITIONS)

    return "fade"


def apply_transitions(builder: VideoBuilder) -> None:
    """Apply transitions between scenes."""
    if builder.num_scenes > 1:
        curr_v, curr_a, acc_offset = "[v0_raw]", "[a0_raw]", 0
        for i in range(1, builder.num_scenes):
            transition = resolve_scene_transition(builder, i)
            logger.info(f"Scene {i}: transition -> {transition}")

            prev_dur = builder.scene_durations[i - 1]
            # xfade consumes transition_dur from the previous stream
            delta = prev_dur - builder.transition_dur
            if delta <= 0:
                logger.warning(
                    "Scene %d: xfade delta=%.3f (prev_dur=%.3f - transition=%.3f) <= 0, "
                    "clamping to 0.05s to avoid Invalid argument",
                    i,
                    delta,
                    prev_dur,
                    builder.transition_dur,
                )
                delta = 0.05
            acc_offset += delta
            builder.filters.append(
                f"{curr_v}[v{i}_raw]xfade=transition={transition}:"
                f"duration={builder.transition_dur}:offset={acc_offset}[v{i}_m]"
            )
            curr_v = f"[v{i}_m]"
            builder.filters.append(f"{curr_a}[a{i}_raw]acrossfade=d={builder.transition_dur}:o=1:c1=tri:c2=tri[a{i}_m]")
            curr_a = f"[a{i}_m]"
        builder._map_v = curr_v
        builder._map_a = curr_a
        builder._total_dur = acc_offset + builder.scene_durations[-1]
    else:
        builder._map_v = "[v0_raw]"
        builder._map_a = "[a0_raw]"
        builder._total_dur = builder.scene_durations[0] if builder.scene_durations else 0


def apply_overlays(builder: VideoBuilder) -> None:
    """Apply overlay graphics to video with slide-in animation."""
    next_input_idx = builder.num_scenes * 2
    # Subtitle inputs only exist for Full layout
    if builder.request.include_scene_text and not builder.use_post_layout:
        next_input_idx += builder.num_scenes

    if not builder.request.overlay_settings:
        builder._next_input_idx = next_input_idx
        return

    if builder.request.layout_style == "post":
        logger.info("Overlay disabled for post layout to avoid double UI.")
        builder._next_input_idx = next_input_idx
        return

    # Create separate header and footer overlay images
    header_path = builder.temp_dir / "overlay_header.png"
    footer_path = builder.temp_dir / "overlay_footer.png"

    builder._create_overlay_header(
        builder.request.overlay_settings,
        builder.out_w,
        builder.out_h,
        header_path,
        builder.request.layout_style,
    )
    builder._create_overlay_footer(
        builder.request.overlay_settings,
        builder.out_w,
        builder.out_h,
        footer_path,
        builder.request.layout_style,
    )

    # Add header and footer as inputs
    builder.input_args.extend(["-i", str(header_path)])
    builder.input_args.extend(["-i", str(footer_path)])

    header_idx = next_input_idx
    footer_idx = next_input_idx + 1

    # Header animation: slide in from top (0.5 seconds)
    builder.filters.append(f"[{header_idx}:v]format=rgba,colorchannelmixer=aa=1.6[ovr_h]")
    builder.filters.append(f"{builder._map_v}[ovr_h]overlay=0:'if(lt(t,0.5),-h*(1-t*2),0)':format=auto[v_h]")

    # Footer animation: slide in from bottom (0.5 seconds)
    builder.filters.append(f"[{footer_idx}:v]format=rgba,colorchannelmixer=aa=1.6[ovr_f]")
    builder.filters.append("[v_h][ovr_f]overlay=0:'if(lt(t,0.5),h*(1-t*2),0)':format=auto[vid_o]")

    builder._map_v = "[vid_o]"
    builder._next_input_idx = footer_idx + 1


def apply_bgm(builder: VideoBuilder) -> None:
    """Apply background music with optional audio ducking."""
    bgm_path = _resolve_bgm_path(builder)
    if not bgm_path:
        return

    builder.input_args.extend(["-i", str(bgm_path)])
    bgm_idx = builder._next_input_idx
    bgm_vol = builder.request.bgm_volume

    # Build looped BGM stream (crossfade at loop seams)
    bgm_label = _build_bgm_loop_filters(builder, bgm_idx, bgm_path)

    if builder.request.audio_ducking:
        _apply_ducked_bgm(builder, bgm_label, bgm_vol)
    else:
        _apply_simple_bgm(builder, bgm_label, bgm_vol)

    builder._map_a = "[a_f]"


def _resolve_bgm_path(builder: VideoBuilder) -> str | None:
    """Resolve BGM file path based on bgm_mode (manual or auto)."""
    bgm_mode = getattr(builder.request, "bgm_mode", "manual")
    # Backward compat: map legacy values
    if bgm_mode in ("file", "ai"):
        bgm_mode = "manual"

    if bgm_mode == "auto":
        return builder._ai_bgm_path

    # Manual mode: preset path first, then bgm_file fallback
    if builder._ai_bgm_path:
        return builder._ai_bgm_path

    storage = get_storage()
    seed = hash(builder.project_id)
    resolved_bgm = resolve_bgm_file(builder.request.bgm_file, seed=seed)
    if not resolved_bgm:
        return None

    storage_key = f"shared/audio/{resolved_bgm}"
    if not storage.exists(storage_key):
        logger.warning(f"[Video Build] BGM file not found in storage: {storage_key}")
        return None

    return str(storage.get_local_path(storage_key))


_BGM_CROSSFADE_SEC = 2.0


def _probe_duration(path: str) -> float:
    """Return audio duration in seconds via ffprobe. Returns 0 on failure."""
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            logger.warning("[BGM] ffprobe non-zero exit (%d) for %s: %s", result.returncode, path, stderr)
            return 0.0
        raw = result.stdout.strip()
        if not raw:
            logger.warning("[BGM] ffprobe returned empty output for %s", path)
            return 0.0
        return float(raw)
    except Exception as e:
        logger.warning("[BGM] Failed to probe duration for %s: %s", path, e)
        return 0.0


def _build_bgm_loop_filters(builder: VideoBuilder, bgm_idx: int, bgm_path: str) -> str:
    """Build filter chain that loops BGM with crossfade at seams.

    Returns the FFmpeg stream label to use downstream (e.g. ``"[bgm_looped]"``
    or ``f"[{bgm_idx}:a]"`` when no looping is needed).
    """
    import math

    bgm_dur = _probe_duration(bgm_path)
    if bgm_dur <= 0 or bgm_dur >= builder._total_dur:
        return f"[{bgm_idx}:a]"

    xfade = min(_BGM_CROSSFADE_SEC, bgm_dur * 0.4)
    effective_dur = bgm_dur - xfade
    copies = max(2, math.ceil(builder._total_dur / effective_dur))
    logger.info(
        "[BGM] bgm=%.1fs, video=%.1fs, xfade=%.1fs → %d copies",
        bgm_dur,
        builder._total_dur,
        xfade,
        copies,
    )

    # asplit into N copies
    labels = [f"[bgm_{i}]" for i in range(copies)]
    builder.filters.append(f"[{bgm_idx}:a]asplit={copies}{''.join(labels)}")

    # Chain acrossfade between consecutive copies
    curr = labels[0]
    for i in range(1, copies):
        out = f"[bgm_cf{i}]" if i < copies - 1 else "[bgm_looped]"
        builder.filters.append(f"{curr}{labels[i]}acrossfade=d={xfade}:c1=tri:c2=tri{out}")
        curr = out

    return "[bgm_looped]"


def _apply_ducked_bgm(builder: VideoBuilder, bgm_label: str, bgm_vol: float) -> None:
    """Apply BGM with sidechain compression (audio ducking)."""
    # 1. Split narration as sidechain key signal
    builder.filters.append(f"{builder._map_a}asplit=2[narr_out][narr_key]")
    # 2. Prepare BGM with volume, trim, and fade
    builder.filters.append(
        f"{bgm_label}atrim=duration={builder._total_dur},asetpts=PTS-STARTPTS,"
        f"volume={bgm_vol},afade=t=out:st={max(0, builder._total_dur - 2)}:d=2[bgm_vol]"
    )
    # 3. Apply sidechain compression
    threshold = builder.request.ducking_threshold
    builder.filters.append(
        f"[bgm_vol][narr_key]sidechaincompress="
        f"threshold={threshold}:ratio=10:attack=50:release=500:"
        f"level_sc=1:makeup=1[bgm_ducked]"
    )
    # 4. Mix ducked BGM with narration (normalize=0: prevent automatic 1/N volume scaling)
    builder.filters.append("[narr_out][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a_f]")


def _apply_simple_bgm(builder: VideoBuilder, bgm_label: str, bgm_vol: float) -> None:
    """Apply BGM with simple fixed-volume mixing."""
    builder.filters.append(
        f"{bgm_label}atrim=duration={builder._total_dur},asetpts=PTS-STARTPTS,"
        f"volume={bgm_vol},afade=t=out:st={max(0, builder._total_dur - 2)}:d=2[bgm_f]"
    )
    builder.filters.append(f"{builder._map_a}[bgm_f]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[a_f]")
