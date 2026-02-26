"""FFmpeg filter chain construction for the video pipeline.

Builds video and audio filter graphs including scaling, Ken Burns effects,
subtitle overlay, and audio resampling. Each function receives the
VideoBuilder instance as its first argument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from config import VIDEO_FPS, logger
from services.motion import build_zoompan_filter, get_preset, get_random_preset

if TYPE_CHECKING:
    from services.video.builder import VideoBuilder


def build_filters(builder: VideoBuilder) -> None:
    """Build all FFmpeg filters (video, subtitle, audio)."""
    if builder.use_post_layout:
        builder.post_layout_metrics = builder._calculate_post_layout_metrics(builder.out_w, builder.out_h)

    add_scene_text_inputs(builder)
    build_video_filters(builder)
    build_audio_filters(builder)


def add_scene_text_inputs(builder: VideoBuilder) -> None:
    """Add subtitle image inputs with dynamic positioning."""
    if not builder.request.include_scene_text:
        logger.info("Subtitles disabled (include_scene_text=False)")
        return

    # For post layout, subtitles are already rendered in compose_post_frame
    if builder.use_post_layout:
        logger.info("Subtitles already in post frame (skipping FFmpeg overlay)")
        return

    for i in range(builder.num_scenes):
        subtitle_path = builder.temp_dir / f"subtitle_{i}.png"
        font_size = builder.scene_text_font_sizes[i] if builder.scene_text_font_sizes[i] > 0 else None

        logger.info(f"Scene {i} subtitle:")
        logger.info(f"  - Lines: {builder.subtitle_lines[i]}")
        logger.info(f"  - Font size: {font_size}")
        logger.info(f"  - Layout: {'Post' if builder.use_post_layout else 'Full'}")

        # Load scene image once for both subtitle Y calculation and adaptive text color
        scene_img_path = builder.temp_dir / f"scene_{i}.png"
        scene_img = None
        if scene_img_path.exists():
            try:
                scene_img = Image.open(scene_img_path)
            except Exception as e:
                logger.warning(f"Scene {i}: failed to load scene image: {e}")

        try:
            subtitle_y_ratio = _calc_subtitle_y(builder, scene_img_path, i, scene_img)

            # Adaptive text color only applies to Full layout
            bg_img_for_color = scene_img if not builder.use_post_layout else None

            subtitle_img = builder._render_scene_text_image(
                builder.subtitle_lines[i],
                builder.out_w,
                builder.out_h,
                builder.font_path,
                builder.use_post_layout,
                builder.post_layout_metrics,
                font_size,
                subtitle_y_ratio,
                bg_img_for_color,  # Pass background image for adaptive text color
            )
            subtitle_img.save(subtitle_path, "PNG")
            logger.info(f"  - Subtitle image saved: {subtitle_path}")
            builder.input_args.extend(["-loop", "1", "-i", str(subtitle_path)])
        finally:
            if scene_img is not None:
                scene_img.close()


def _calc_subtitle_y(
    builder: VideoBuilder,
    scene_img_path,
    scene_idx: int,
    scene_img: Image.Image | None = None,
) -> float | None:
    """Calculate dynamic subtitle Y position from scene image."""
    opened_here = False
    img = scene_img
    try:
        if img is None and scene_img_path.exists():
            img = Image.open(scene_img_path)
            opened_here = True
        if img is not None:
            y_ratio = builder._calculate_optimal_scene_text_y(img, layout_style=builder.request.layout_style)
            logger.info(f"  - Dynamic Y position: {y_ratio:.3f}")
            return y_ratio
    except Exception as e:
        logger.warning(f"Scene {scene_idx}: failed to calculate dynamic subtitle position: {e}")
    finally:
        if opened_here and img is not None:
            img.close()
    return None


def build_video_filters(builder: VideoBuilder) -> None:
    """Build video processing filters for each scene.

    Filter chain order:
    1. Scale/Crop image -> [v{i}_scaled]
    2. Apply Ken Burns effect to scaled image -> [v{i}_kb]
    3. Overlay subtitle on zoomed frame -> [v{i}_base]
    4. Trim to duration -> [v{i}_raw]

    Applying subtitles AFTER zoompan ensures they remain sharp and fixed
    relative to the screen, and prevents them from moving with the motion effect.
    """
    subtitle_base_idx = builder.num_scenes * 2

    for i in range(builder.num_scenes):
        v_idx = i * 2
        base_dur = builder.scene_durations[i]
        clip_dur = base_dur + (builder.transition_dur if i < builder.num_scenes - 1 else 0)
        motion_frames = max(1, int(clip_dur * VIDEO_FPS))

        # Step 1: Scale/Crop image (base preparation)
        if builder.use_post_layout:
            _build_post_layout_base(builder, i, v_idx)
        else:
            _build_full_layout_base(builder, i, v_idx)

        # Step 2: Apply Ken Burns effect
        _apply_ken_burns(builder, i, motion_frames)

        # Step 3: Apply subtitles AFTER Ken Burns (Full layout only)
        _apply_subtitle_overlay(builder, i, subtitle_base_idx, clip_dur)

        # Step 4: Color grade + vignette (Full layout only)
        if not builder.use_post_layout:
            builder.filters.append(f"[v{i}_base]eq=saturation=1.15:contrast=1.05,vignette=PI/5[v{i}_graded]")
            graded = f"[v{i}_graded]"
        else:
            graded = f"[v{i}_base]"

        # Step 5: Trim to duration
        builder.filters.append(f"{graded}trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]")


def _apply_ken_burns(
    builder: VideoBuilder,
    i: int,
    motion_frames: int,
) -> None:
    """Apply Ken Burns (zoompan) effect to a scene."""
    preset_name = resolve_scene_preset(builder, i)
    if preset_name == "none":
        builder.filters.append(f"[v{i}_scaled]null[v{i}_kb]")
    else:
        params = get_preset(preset_name)
        zoompan = build_zoompan_filter(
            params,
            builder.out_w,
            builder.out_h,
            motion_frames,
            builder.ken_burns_intensity,
            fps=VIDEO_FPS,
        )
        builder.filters.append(f"[v{i}_scaled]{zoompan}[v{i}_kb]")


def _apply_subtitle_overlay(builder: VideoBuilder, i: int, subtitle_base_idx: int, clip_dur: float) -> None:
    """Apply subtitle overlay after Ken Burns for Full layout."""
    if builder.request.include_scene_text and not builder.use_post_layout:
        sub_idx = subtitle_base_idx + i
        logger.info(f"Scene {i}: Adding subtitle overlay after Ken Burns (input [{sub_idx}:v])")

        fade_duration = 0.3
        sub_filter = f"[{sub_idx}:v]scale={builder.out_w}:{builder.out_h},format=rgba"

        if clip_dur > fade_duration * 2:
            fade_out_start = clip_dur - fade_duration
            sub_filter += (
                f",fade=t=in:st=0:d={fade_duration}:alpha=1,fade=t=out:st={fade_out_start}:d={fade_duration}:alpha=1"
            )

        builder.filters.append(f"{sub_filter}[sub{i}]")
        builder.filters.append(f"[v{i}_kb]format=rgba[v{i}_kb_rgba]")
        builder.filters.append(f"[v{i}_kb_rgba][sub{i}]overlay=0:0:format=auto[v{i}_base]")
        logger.info(f"Scene {i}: Subtitle overlay complete -> [v{i}_base]")
    else:
        builder.filters.append(f"[v{i}_kb]null[v{i}_base]")
        logger.info(f"Scene {i}: No subtitles (include_scene_text={builder.request.include_scene_text})")


def _build_post_layout_base(builder: VideoBuilder, i: int, v_idx: int) -> None:
    """Build base scaling filter for post layout style."""
    builder.filters.append(f"[{v_idx}:v]scale={builder.out_w}:{builder.out_h}[v{i}_scaled]")


def _build_full_layout_base(builder: VideoBuilder, i: int, v_idx: int) -> None:
    """Build base scaling/cropping filter for full layout style.

    512x768 (2:3) -> 1080x1920 (9:16) conversion:
    - Scale to cover output size (vertical priority)
    - Crop with top-weighted positioning (30% from top)
    """
    crop_y_ratio = builder._FullLayout.CROP_Y_RATIO
    builder.filters.append(
        f"[{v_idx}:v]scale={builder.out_w}:{builder.out_h}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={builder.out_w}:{builder.out_h}:(iw-ow)/2:(ih-oh)*{crop_y_ratio}"
        f"[v{i}_scaled]"
    )


def resolve_scene_preset(builder: VideoBuilder, scene_idx: int) -> str:
    """Resolve Ken Burns preset for a specific scene.

    Priority: scene-level ken_burns_preset > global random > global preset.
    """
    # 1) Per-scene override from Cinematographer agent
    scene = builder.request.scenes[scene_idx]
    per_scene = getattr(scene, "ken_burns_preset", None)
    if per_scene and per_scene != "none":
        logger.info(f"Scene {scene_idx}: per-scene Ken Burns preset -> {per_scene}")
        return per_scene

    # 2) Global random
    if builder.ken_burns_preset == "random":
        seed = hash(f"{builder.project_id}_{scene_idx}")
        name, _ = get_random_preset(seed)
        logger.info(f"Scene {scene_idx}: random Ken Burns preset -> {name}")
        return name

    # 3) Global preset
    return builder.ken_burns_preset


def build_audio_filters(builder: VideoBuilder) -> None:
    """Build audio processing filters for each scene."""
    for i, scene in enumerate(builder.request.scenes):
        a_idx = i * 2 + 1
        clip_dur = builder.scene_durations[i]

        # Delay audio start by transition duration + agent-designed head padding
        h_pad = getattr(scene, "head_padding", 0.0) or 0.0
        delay_ms = int((builder.transition_dur + h_pad) * 1000)

        builder.filters.append(
            f"[{a_idx}:a]aresample=44100,aformat=channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms},apad,"
            f"atrim=duration={clip_dur},asetpts=PTS-STARTPTS[a{i}_raw]"
        )
