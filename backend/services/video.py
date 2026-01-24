"""Video service for video creation helpers.

Provides utility functions for video rendering pipeline.
"""

from __future__ import annotations

import hashlib
import random
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import edge_tts

from config import (
    API_PUBLIC_URL,
    AUDIO_DIR,
    IMAGE_DIR,
    VIDEO_DIR,
    logger,
)

if TYPE_CHECKING:
    from schemas import VideoRequest, VideoScene


def sanitize_project_name(project_name: str, max_length: int = 40) -> str:
    """Sanitize project name for use in filenames.

    Args:
        project_name: Raw project name from request
        max_length: Maximum length of sanitized name

    Returns:
        Safe filename-friendly project name
    """
    safe_name = re.sub(r"[^\w가-힣]+", "_", project_name).strip("_")
    if not safe_name:
        safe_name = "my_shorts"
    return safe_name[:max_length]


def generate_video_filename(
    project_name: str,
    layout_style: str,
    timestamp: int | None = None,
) -> str:
    """Generate a unique video filename.

    Args:
        project_name: Sanitized project name
        layout_style: "post" or "full"
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Unique video filename with hash
    """
    if timestamp is None:
        timestamp = int(time.time())
    layout_tag = "post" if layout_style == "post" else "full"
    hash_seed = f"{project_name}|{layout_tag}|{timestamp}"
    hash_value = hashlib.sha1(hash_seed.encode("utf-8")).hexdigest()[:12]
    return f"{project_name}_{layout_tag}_{hash_value}.mp4"


def calculate_speed_params(speed_multiplier: float) -> tuple[float, float, float]:
    """Calculate timing parameters based on speed multiplier.

    Args:
        speed_multiplier: Speed factor (0.25 to 2.0)

    Returns:
        Tuple of (transition_duration, tts_padding, clamped_speed_multiplier)
    """
    clamped = max(0.25, min(speed_multiplier or 1.0, 2.0))
    transition_dur = max(0.1, 0.5 / clamped)
    tts_padding = 0.5 / clamped
    return transition_dur, tts_padding, clamped


def calculate_scene_durations(
    scenes: list[VideoScene],
    tts_valid: list[bool],
    tts_durations: list[float],
    speed_multiplier: float,
    tts_padding: float,
) -> list[float]:
    """Calculate final duration for each scene.

    Args:
        scenes: List of video scenes
        tts_valid: Whether TTS was generated for each scene
        tts_durations: TTS audio duration for each scene
        speed_multiplier: Speed factor
        tts_padding: Extra padding after TTS

    Returns:
        List of scene durations in seconds
    """
    durations: list[float] = []
    for i, scene in enumerate(scenes):
        base_duration = (scene.duration or 3) / speed_multiplier
        if tts_valid[i] and tts_durations[i] > 0:
            base_duration = max(base_duration, tts_durations[i] + tts_padding)
        durations.append(base_duration)
    return durations


def clean_script_for_tts(raw_script: str) -> str:
    """Clean script text for TTS generation.

    Removes special characters that might cause TTS issues.

    Args:
        raw_script: Raw script text

    Returns:
        Cleaned script text
    """
    # Remove problematic characters while keeping common punctuation and CJK
    clean = re.sub(
        r"[^\w\s.,!?가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥+\-=×÷²³¹⁰()%<>]",
        "",
        raw_script
    )
    return clean.replace("'", "").strip()


class VideoBuilder:
    """Builder class for creating videos from scenes.

    Encapsulates the video creation pipeline including:
    - Scene image processing
    - TTS audio generation
    - Subtitle rendering
    - FFmpeg filter construction
    - Video encoding
    """

    def __init__(self, request: VideoRequest):
        from constants.layout import FullLayout, PostLayout
        from schemas import OverlaySettings, PostCardSettings
        from services.avatar import ensure_avatar_file
        from services.image import load_image_bytes
        from services.rendering import (
            _random_meta_values,
            apply_post_overlay_mask,
            calculate_post_layout_metrics,
            compose_post_frame,
            render_subtitle_image,
            resolve_overlay_frame,
            resolve_subtitle_font_path,
        )
        from services.utils import get_audio_duration, to_edge_tts_rate, wrap_text, wrap_text_by_font

        self.request = request
        self._ensure_avatar_file = ensure_avatar_file
        self._load_image_bytes = load_image_bytes
        self._random_meta_values = _random_meta_values
        self._apply_post_overlay_mask = apply_post_overlay_mask
        self._calculate_post_layout_metrics = calculate_post_layout_metrics
        self._compose_post_frame = compose_post_frame
        self._render_subtitle_image = render_subtitle_image
        self._resolve_overlay_frame = resolve_overlay_frame
        self._resolve_subtitle_font_path = resolve_subtitle_font_path
        self._get_audio_duration = get_audio_duration
        self._to_edge_tts_rate = to_edge_tts_rate
        self._wrap_text = wrap_text
        self._wrap_text_by_font = wrap_text_by_font
        self._FullLayout = FullLayout
        self._PostLayout = PostLayout
        self._OverlaySettings = OverlaySettings
        self._PostCardSettings = PostCardSettings

        # State
        self.project_id = f"build_{int(time.time())}"
        self.temp_dir = IMAGE_DIR / self.project_id
        self.safe_project_name = sanitize_project_name(request.project_name)
        self.video_filename = generate_video_filename(
            self.safe_project_name, request.layout_style
        )
        self.video_path = VIDEO_DIR / self.video_filename
        self.font_path = self._resolve_subtitle_font_path(request.subtitle_font)

        # Calculated values
        self.num_scenes = len(request.scenes)
        self.transition_dur, self.tts_padding, self.speed_multiplier = (
            calculate_speed_params(request.speed_multiplier or 1.0)
        )
        self.tts_rate = self._to_edge_tts_rate(self.speed_multiplier)
        self.use_post_layout = request.layout_style == "post"
        self.out_w = request.width
        self.out_h = request.height

        # Per-scene data
        self.input_args: list[str] = []
        self.filters: list[str] = []
        self.tts_valid: list[bool] = []
        self.tts_durations: list[float] = []
        self.subtitle_lines: list[list[str]] = []
        self.subtitle_font_sizes: list[int] = []  # Dynamic font size per scene
        self.scene_durations: list[float] = []
        self.avatar_file: str | None = None
        self.post_avatar_file: str | None = None
        self.post_layout_metrics: dict[str, Any] | None = None

    async def build(self) -> dict[str, str]:
        """Execute the video build pipeline."""
        logger.info("Video build started: %s", self.request.project_name)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        try:
            await self._setup_avatars()
            await self._process_scenes()
            self._calculate_durations()
            self._build_filters()
            self._encode()
            return {"video_url": f"{API_PUBLIC_URL}/outputs/videos/{self.video_filename}"}
        except Exception as exc:
            logger.exception("Video Create Error")
            raise exc
        finally:
            self._cleanup()

    async def _setup_avatars(self) -> None:
        """Set up avatar files and random meta values."""
        meta_rng = random.Random(time.time_ns())
        full_views, full_time = self._random_meta_values(meta_rng)
        post_views, post_time = self._random_meta_values(meta_rng)
        self._full_views = full_views
        self._full_time = full_time
        self._post_views = post_views
        self._post_time = post_time

        if self.request.overlay_settings:
            self.request.overlay_settings.likes_count = full_views
            self.request.overlay_settings.posted_time = full_time
            self.avatar_file = await self._ensure_avatar_file(
                self.request.overlay_settings.avatar_key
            )
            if self.avatar_file:
                self.request.overlay_settings.avatar_file = self.avatar_file

        if self.request.post_card_settings:
            self.post_avatar_file = await self._ensure_avatar_file(
                self.request.post_card_settings.avatar_key
            )

    async def _process_scenes(self) -> None:
        """Process all scenes: images, TTS, and subtitles."""
        for i, scene in enumerate(self.request.scenes):
            img_path = self.temp_dir / f"scene_{i}.png"
            tts_path = self.temp_dir / f"tts_{i}.mp3"

            # Load and process image
            image_bytes = self._load_image_bytes(scene.image_url)
            raw_script = scene.script or ""
            logger.info(f"Scene {i}: script='{raw_script}', len={len(raw_script)}")
            clean_script = clean_script_for_tts(raw_script)

            # Apply post layout if needed
            if self.use_post_layout:
                self._process_post_layout_image(i, image_bytes, img_path)
            else:
                img_path.write_bytes(image_bytes)

            # Process subtitles with pixel-based wrapping and dynamic font sizing
            if self.request.include_subtitles:
                lines, font_size = self._wrap_subtitle_text(clean_script)
                self.subtitle_lines.append(lines)
                self.subtitle_font_sizes.append(font_size)
            else:
                self.subtitle_lines.append([])
                self.subtitle_font_sizes.append(0)

            # Generate TTS
            has_valid_tts, tts_duration = await self._generate_tts(
                i, raw_script, tts_path
            )

            # Add to input args
            self.input_args.extend(["-loop", "1", "-i", str(img_path)])
            if has_valid_tts:
                self.input_args.extend(["-i", str(tts_path)])
            else:
                self.input_args.extend([
                    "-f", "lavfi", "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100"
                ])

            self.tts_valid.append(has_valid_tts)
            self.tts_durations.append(tts_duration)

    def _wrap_subtitle_text(self, text: str) -> tuple[list[str], int]:
        """Wrap subtitle text based on font pixel width with dynamic font sizing.

        Calculates max width and font size based on layout type,
        then wraps text to fit within the available space.
        If text doesn't fit, reduces font size until it fits or minimum is reached.

        Returns:
            Tuple of (lines, font_size)
        """
        from PIL import ImageFont

        if not text:
            return [], 0

        # Determine font size range and max width based on layout
        if self.use_post_layout:
            base_font_size = int(self.out_h * self._PostLayout.SUBTITLE_FONT_RATIO)
            min_font_size = int(self.out_h * self._PostLayout.SUBTITLE_MIN_FONT_RATIO)
            if self.post_layout_metrics:
                card_width = self.post_layout_metrics["card_width"]
                card_padding = self.post_layout_metrics["card_padding"]
                text_area_width = card_width - (card_padding * 2)
            else:
                card_width = int(self.out_w * self._PostLayout.CARD_WIDTH_RATIO)
                card_padding = int(card_width * self._PostLayout.CARD_PADDING_RATIO)
                text_area_width = card_width - (card_padding * 2)
            max_width_px = int(text_area_width * self._PostLayout.SUBTITLE_MAX_WIDTH_RATIO)
            max_lines = self._PostLayout.SUBTITLE_MAX_LINES
        else:
            base_font_size = int(self.out_h * self._FullLayout.SUBTITLE_FONT_RATIO)
            min_font_size = int(self.out_h * self._FullLayout.SUBTITLE_MIN_FONT_RATIO)
            max_width_px = int(self.out_w * self._FullLayout.SUBTITLE_MAX_WIDTH_RATIO)
            max_lines = self._FullLayout.SUBTITLE_MAX_LINES

        # Try wrapping with decreasing font sizes
        font_size = base_font_size
        font_step = 2  # Decrease by 2px each iteration

        while font_size >= min_font_size:
            try:
                font = ImageFont.truetype(self.font_path, font_size)
            except Exception:
                logger.warning("Font loading failed, using character-based wrapping")
                wrapped = self._wrap_text(text, width=20, max_lines=max_lines)
                lines = [line for line in wrapped.splitlines() if line.strip()]
                return lines, base_font_size

            lines = self._wrap_text_by_font(text, font, max_width_px, max_lines)

            # Check if all text fits properly
            if len(lines) <= max_lines:
                # Verify all lines fit within max_width
                all_fit = True
                for line in lines:
                    bbox = font.getbbox(line)
                    if bbox and (bbox[2] - bbox[0]) > max_width_px:
                        all_fit = False
                        break

                if all_fit:
                    if font_size < base_font_size:
                        logger.info(
                            f"Dynamic font: {base_font_size}px -> {font_size}px for text: {text[:30]}..."
                        )
                    return lines, font_size

            # Reduce font size and try again
            font_size -= font_step

        # Minimum font size reached, return best effort
        try:
            font = ImageFont.truetype(self.font_path, min_font_size)
            lines = self._wrap_text_by_font(text, font, max_width_px, max_lines)
            logger.warning(f"Using minimum font size {min_font_size}px for: {text[:30]}...")
            return lines, min_font_size
        except Exception:
            wrapped = self._wrap_text(text, width=20, max_lines=max_lines)
            lines = [line for line in wrapped.splitlines() if line.strip()]
            return lines, base_font_size

    def _process_post_layout_image(
        self, i: int, image_bytes: bytes, img_path: Path
    ) -> None:
        """Process image for post layout."""
        try:
            overlay_settings = self.request.overlay_settings or self._OverlaySettings()
            post_settings = self.request.post_card_settings or self._PostCardSettings(
                channel_name=overlay_settings.channel_name,
                avatar_key=overlay_settings.avatar_key,
                caption=overlay_settings.caption,
            )
            composed = self._compose_post_frame(
                image_bytes, self.out_w, self.out_h,
                post_settings.channel_name, post_settings.caption,
                "", self.font_path,
                self.post_avatar_file or self.avatar_file,
                self._post_views, self._post_time,
            )
            composed.save(img_path, "PNG")
        except Exception:
            img_path.write_bytes(image_bytes)

    async def _generate_tts(
        self, i: int, raw_script: str, tts_path: Path
    ) -> tuple[bool, float]:
        """Generate TTS audio for a scene."""
        has_valid_tts = False
        tts_duration = 0.0

        if raw_script.strip():
            try:
                voice = self.request.narrator_voice
                logger.info(f"TTS 생성 시도: voice={voice}, script={raw_script[:50]}...")
                communicate = edge_tts.Communicate(raw_script, voice, rate=self.tts_rate)
                await communicate.save(str(tts_path))
                if tts_path.exists() and tts_path.stat().st_size > 0:
                    has_valid_tts = True
                    tts_duration = self._get_audio_duration(tts_path)
                    logger.info(f"TTS 생성 성공: duration={tts_duration}s")
                else:
                    logger.warning("TTS 파일 생성 실패 또는 빈 파일")
            except Exception as e:
                logger.error(f"TTS 생성 에러: {e}")
        else:
            logger.warning(f"Scene {i}: 스크립트가 비어있어 TTS 생략")

        return has_valid_tts, tts_duration

    def _calculate_durations(self) -> None:
        """Calculate scene durations based on TTS and settings."""
        self.scene_durations = calculate_scene_durations(
            self.request.scenes,
            self.tts_valid,
            self.tts_durations,
            self.speed_multiplier,
            self.tts_padding,
        )

    def _build_filters(self) -> None:
        """Build all FFmpeg filters."""
        if self.use_post_layout:
            self.post_layout_metrics = self._calculate_post_layout_metrics(
                self.out_w, self.out_h
            )

        self._add_subtitle_inputs()
        self._build_video_filters()
        self._build_audio_filters()
        self._apply_transitions()
        self._apply_overlays()
        self._apply_bgm()

    def _add_subtitle_inputs(self) -> None:
        """Add subtitle image inputs."""
        if not self.request.include_subtitles:
            return

        for i in range(self.num_scenes):
            subtitle_path = self.temp_dir / f"subtitle_{i}.png"
            font_size = self.subtitle_font_sizes[i] if self.subtitle_font_sizes[i] > 0 else None
            subtitle_img = self._render_subtitle_image(
                self.subtitle_lines[i],
                self.out_w, self.out_h,
                self.font_path,
                self.use_post_layout,
                self.post_layout_metrics,
                font_size,
            )
            subtitle_img.save(subtitle_path, "PNG")
            self.input_args.extend(["-loop", "1", "-i", str(subtitle_path)])

    def _build_video_filters(self) -> None:
        """Build video processing filters for each scene."""
        subtitle_base_idx = self.num_scenes * 2

        for i in range(self.num_scenes):
            v_idx = i * 2
            base_dur = self.scene_durations[i]
            clip_dur = base_dur + (
                self.transition_dur if i < self.num_scenes - 1 else 0
            )
            motion_frames = max(1, int(clip_dur * 25))

            if self.use_post_layout:
                self._build_post_layout_filter(i, v_idx, motion_frames)
            else:
                self._build_full_layout_filter(i, v_idx, motion_frames)

            # Apply subtitles and trim
            if self.request.include_subtitles:
                sub_idx = subtitle_base_idx + i
                self.filters.append(
                    f"[{sub_idx}:v]scale={self.out_w}:{self.out_h},format=rgba[sub{i}]"
                )
                self.filters.append(
                    f"[v{i}_base][sub{i}]overlay=0:0:format=auto[v{i}_text]"
                )
                self.filters.append(
                    f"[v{i}_text]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]"
                )
            else:
                self.filters.append(
                    f"[v{i}_base]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]"
                )

    def _build_post_layout_filter(
        self, i: int, v_idx: int, motion_frames: int
    ) -> None:
        """Build filter for post layout style."""
        if self.request.motion_style == "slow_zoom":
            self.filters.append(
                f"[{v_idx}:v]scale={self.out_w}:{self.out_h},"
                f"zoompan=z='min(zoom+0.0008,1.08)':d={motion_frames}"
                f":s={self.out_w}x{self.out_h}:fps=25[v{i}_base]"
            )
        else:
            self.filters.append(
                f"[{v_idx}:v]scale={self.out_w}:{self.out_h}[v{i}_base]"
            )

    def _build_full_layout_filter(
        self, i: int, v_idx: int, motion_frames: int
    ) -> None:
        """Build filter for full layout style with blur background."""
        self.filters.append(f"[{v_idx}:v]split=2[v{i}_in_1][v{i}_in_2]")

        bg_scale = (
            f"[v{i}_in_1]scale={self.out_w}:{self.out_h}:force_original_aspect_ratio=increase,"
            f"crop={self.out_w}:{self.out_h},boxblur=40:20"
        )

        if self.request.motion_style == "slow_zoom":
            self.filters.append(
                f"{bg_scale},"
                f"zoompan=z='min(zoom+0.0008,1.08)':d={motion_frames}"
                f":s={self.out_w}x{self.out_h}:fps=25[v{i}_bg]"
            )
        else:
            self.filters.append(f"{bg_scale}[v{i}_bg]")

        # Square image overlay
        sq_size = self.out_w
        sq_y = int(self.out_h * 0.10)
        self.filters.append(
            f"[v{i}_in_2]scale={sq_size}:{sq_size}:force_original_aspect_ratio=decrease,"
            f"pad={sq_size}:{sq_size}:(ow-iw)/2:(oh-ih)/2[v{i}_sq]"
        )
        self.filters.append(
            f"[v{i}_bg][v{i}_sq]overlay=0:{sq_y}:format=auto[v{i}_base]"
        )

    def _build_audio_filters(self) -> None:
        """Build audio processing filters for each scene."""
        for i in range(self.num_scenes):
            a_idx = i * 2 + 1
            clip_dur = self.scene_durations[i] + (
                self.transition_dur if i < self.num_scenes - 1 else 0
            )
            self.filters.append(
                f"[{a_idx}:a]aresample=44100,aformat=channel_layouts=stereo,apad,"
                f"atrim=duration={clip_dur},asetpts=PTS-STARTPTS[a{i}_raw]"
            )

    def _apply_transitions(self) -> None:
        """Apply crossfade transitions between scenes."""
        if self.num_scenes > 1:
            curr_v, curr_a, acc_offset = "[v0_raw]", "[a0_raw]", 0
            for i in range(1, self.num_scenes):
                prev_dur = self.scene_durations[i - 1]
                acc_offset += prev_dur
                self.filters.append(
                    f"{curr_v}[v{i}_raw]xfade=transition=fade:"
                    f"duration={self.transition_dur}:offset={acc_offset}[v{i}_m]"
                )
                curr_v = f"[v{i}_m]"
                self.filters.append(
                    f"{curr_a}[a{i}_raw]acrossfade=d={self.transition_dur}:"
                    f"o=1:c1=tri:c2=tri[a{i}_m]"
                )
                curr_a = f"[a{i}_m]"
            self._map_v = curr_v
            self._map_a = curr_a
            self._total_dur = acc_offset + self.scene_durations[-1]
        else:
            self._map_v = "[v0_raw]"
            self._map_a = "[a0_raw]"
            self._total_dur = self.scene_durations[0] if self.scene_durations else 0

    def _apply_overlays(self) -> None:
        """Apply overlay graphics to video."""
        next_input_idx = self.num_scenes * 2
        if self.request.include_subtitles:
            next_input_idx += self.num_scenes

        if not self.request.overlay_settings:
            self._next_input_idx = next_input_idx
            return

        if self.request.layout_style == "post":
            logger.info("Overlay disabled for post layout to avoid double UI.")
            self._next_input_idx = next_input_idx
            return

        overlay_path = self.temp_dir / "overlay.png"
        self._resolve_overlay_frame(
            self.request.overlay_settings,
            self.out_w, self.out_h,
            overlay_path,
            self.request.layout_style,
        )

        if self.request.layout_style == "post":
            self._apply_post_overlay_mask(overlay_path, self.out_w, self.out_h)

        self.input_args.extend(["-i", str(overlay_path)])

        if self.request.layout_style == "full":
            self.filters.append(
                f"[{next_input_idx}:v]scale={self.out_w}:{self.out_h},format=rgba,"
                f"colorchannelmixer=aa=1.6[ovr]"
            )
        else:
            self.filters.append(
                f"[{next_input_idx}:v]scale={self.out_w}:{self.out_h}[ovr]"
            )

        self.filters.append(f"{self._map_v}[ovr]overlay=0:0[vid_o]")
        self._map_v = "[vid_o]"
        self._next_input_idx = next_input_idx + 1

    def _apply_bgm(self) -> None:
        """Apply background music with optional audio ducking."""
        bgm_path = AUDIO_DIR / self.request.bgm_file if self.request.bgm_file else None
        if not bgm_path or not bgm_path.exists():
            return

        self.input_args.extend(["-i", str(bgm_path)])
        bgm_idx = self._next_input_idx
        bgm_vol = self.request.bgm_volume

        if self.request.audio_ducking:
            # Audio Ducking: BGM volume drops when narration plays
            # 1. Prepare narration as sidechain key signal
            self.filters.append(f"{self._map_a}asplit=2[narr_out][narr_key]")
            # 2. Prepare BGM with volume and fade
            self.filters.append(
                f"[{bgm_idx}:a]volume={bgm_vol},"
                f"afade=t=out:st={max(0, self._total_dur - 2)}:d=2[bgm_vol]"
            )
            # 3. Apply sidechain compression (duck BGM when narration detected)
            threshold = self.request.ducking_threshold
            self.filters.append(
                f"[bgm_vol][narr_key]sidechaincompress="
                f"threshold={threshold}:ratio=10:attack=50:release=500:"
                f"level_sc=1:makeup=1[bgm_ducked]"
            )
            # 4. Mix ducked BGM with narration
            self.filters.append(
                "[narr_out][bgm_ducked]amix=inputs=2:duration=first:"
                "dropout_transition=2[a_f]"
            )
        else:
            # No ducking - simple mix with fixed volume
            self.filters.append(
                f"[{bgm_idx}:a]volume={bgm_vol},"
                f"afade=t=out:st={max(0, self._total_dur - 2)}:d=2[bgm_f]"
            )
            self.filters.append(
                f"{self._map_a}[bgm_f]amix=inputs=2:duration=first:"
                "dropout_transition=2[a_f]"
            )
        self._map_a = "[a_f]"

    def _encode(self) -> None:
        """Encode the final video using FFmpeg."""
        filter_complex_str = ";".join(self.filters)
        cmd = ["ffmpeg", "-y"] + self.input_args + [
            "-filter_complex", filter_complex_str,
            "-map", self._map_v,
            "-map", self._map_a,
            "-s", f"{self.out_w}x{self.out_h}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            str(self.video_path),
        ]

        logger.info("Running FFmpeg")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg failed: %s", result.stderr)
            raise Exception(result.stderr)

    def _cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
