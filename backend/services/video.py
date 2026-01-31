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
from fastapi import HTTPException

from config import (
    IMAGE_DIR,
    STORAGE_MODE,
    VIDEO_DIR,
    logger,
)
from database import SessionLocal
from services.asset_service import AssetService
from services.motion import (
    build_zoompan_filter,
    get_preset,
    get_random_preset,
    resolve_preset_name,
)
from services.storage import get_storage

if TYPE_CHECKING:
    from schemas import VideoRequest, VideoScene


def sanitize_filename(name: str, max_length: int = 40) -> str:
    """Sanitize name for use in filenames.

    Args:
        name: Raw name from request
        max_length: Maximum length of sanitized name

    Returns:
        Safe filename-friendly name
    """
    safe_name = re.sub(r"[^\w가-힣]+", "_", name).strip("_")
    if not safe_name:
        safe_name = "my_shorts"
    return safe_name[:max_length]


def resolve_bgm_file(
    bgm_file: str | None,
    seed: int | None = None,
) -> str | None:
    """Resolve BGM filename, supporting 'random' selection.

    Args:
        bgm_file: BGM filename or 'random' for random selection
        seed: Optional seed for reproducible random selection

    Returns:
        Resolved BGM filename (storage key suffix) or None
    """
    if not bgm_file or not bgm_file.strip():
        return None

    # Check for random selection (case-insensitive)
    if bgm_file.lower() == "random":
        # Find all mp3 files in shared/audio/ prefix
        prefix = "shared/audio/"
        storage = get_storage()
        all_keys = storage.list_prefix(prefix)
        mp3_keys = [k for k in all_keys if k.lower().endswith(".mp3")]

        if not mp3_keys:
            logger.warning(f"⚠️ [BGM Resolve] No MP3 files found in {prefix}")
            return None

        # Select random key
        rng = random.Random(seed) if seed is not None else random.Random()
        selected_key = rng.choice(mp3_keys)
        # We return just the filename part or the relative path from shared/audio/
        # to keep compatibility or simplify. Let's return the full key for clarity?
        # Actually, previous return was selected.name (just filename).
        # Let's return just the filename for now.
        filename = Path(selected_key).name
        logger.info(f"Random BGM selected: {filename} (from {selected_key})")
        return filename

    return bgm_file


def generate_video_filename(
    safe_title: str,
    layout_style: str,
    timestamp: int | None = None,
) -> str:
    """Generate a unique video filename.

    Args:
        safe_title: Sanitized storyboard title
        layout_style: "post" or "full"
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Unique video filename with hash
    """
    if timestamp is None:
        timestamp = int(time.time())
    layout_tag = "post" if layout_style == "post" else "full"
    hash_seed = f"{safe_title}|{layout_tag}|{timestamp}"
    hash_value = hashlib.sha1(hash_seed.encode("utf-8")).hexdigest()[:12]
    return f"{safe_title}_{layout_tag}_{hash_value}.mp4"


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

    Removes special characters and normalizes text for natural TTS reading.

    Args:
        raw_script: Raw script text

    Returns:
        Cleaned script text optimized for TTS
    """
    text = raw_script

    # Normalize Unicode characters
    text = text.replace("…", "...")  # Ellipsis to periods
    text = text.replace("—", ", ")   # Em-dash to comma
    text = text.replace("–", ", ")   # En-dash to comma
    text = text.replace("「", "")    # Japanese quotes
    text = text.replace("」", "")
    text = text.replace("『", "")
    text = text.replace("』", "")

    # Remove problematic characters while keeping common punctuation and CJK
    text = re.sub(
        r"[^\w\s.,!?/\"':;~가-힣a-zA-Zぁ-ゔァ-ヴー々〆〤一-龥+\-=×÷²³¹⁰()%<>]",
        "",
        text
    )

    # Normalize multiple punctuation for natural pauses
    text = re.sub(r"\.{2,}", ".", text)     # ... -> .
    text = re.sub(r"!{2,}", "!", text)      # !!! -> !
    text = re.sub(r"\?{2,}", "?", text)     # ??? -> ?
    text = re.sub(r"\s+", " ", text)        # Multiple spaces -> single

    return text.strip()


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
        from services.image import (
            calculate_optimal_subtitle_y,
            load_image_bytes,
        )
        from services.rendering import (
            _random_meta_values,
            apply_post_overlay_mask,
            calculate_post_layout_metrics,
            compose_post_frame,
            create_overlay_footer,
            create_overlay_header,
            render_subtitle_image,
            resolve_overlay_frame,
            resolve_subtitle_font_path,
        )
        from services.utils import get_audio_duration, to_edge_tts_rate, wrap_text, wrap_text_by_font

        self.request = request
        self._ensure_avatar_file = ensure_avatar_file
        self._load_image_bytes = load_image_bytes
        self._calculate_optimal_subtitle_y = calculate_optimal_subtitle_y
        self._random_meta_values = _random_meta_values
        self._apply_post_overlay_mask = apply_post_overlay_mask
        self._calculate_post_layout_metrics = calculate_post_layout_metrics
        self._compose_post_frame = compose_post_frame
        self._create_overlay_header = create_overlay_header
        self._create_overlay_footer = create_overlay_footer
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
        self.safe_title = sanitize_filename(request.storyboard_title)
        self.video_filename = generate_video_filename(
            self.safe_title, request.layout_style
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
        self.project_id_int = request.project_id
        self.group_id_int = request.group_id

        # Ken Burns settings
        self.ken_burns_preset = resolve_preset_name(request.ken_burns_preset)
        self.ken_burns_intensity = max(0.5, min(request.ken_burns_intensity or 1.0, 2.0))

        # Transition settings
        self.transition_type = request.transition_type or "fade"

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
        logger.info("Video build started: %s", self.request.storyboard_title)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        try:
            await self._setup_avatars()
            await self._process_scenes()
            self._calculate_durations()
            self._build_filters()
            self._encode()

            # Upload and register final video
            if self.project_id_int and self.group_id_int and self.request.storyboard_id:
                db = SessionLocal()
                try:
                    asset_service = AssetService(db)
                    asset = asset_service.save_rendered_video(
                        video_path=self.video_path,
                        project_id=self.project_id_int,
                        group_id=self.group_id_int,
                        storyboard_id=self.request.storyboard_id,
                        file_name=self.video_filename
                    )

                    # Update Storyboard record
                    from models.storyboard import Storyboard
                    sb = db.query(Storyboard).filter(Storyboard.id == self.request.storyboard_id).first()
                    if sb:
                        sb.video_asset_id = asset.id
                        # sb.video_url = asset_service.get_asset_url(asset.storage_key) # Legacy update? Yes, for compatibility
                        db.add(sb)
                        db.commit()

                    url = asset_service.get_asset_url(asset.storage_key)
                    logger.info("✅ [Video Build] Video uploaded and registered: %s", asset.storage_key)
                    return {"video_url": url}
                finally:
                    db.close()

            return {"video_url": f"/outputs/videos/{self.video_filename}"}
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
            # Try to resolve local path from storage if it's a managed asset
            img_src = scene.image_url
            if img_src and ("/projects/" in img_src or (STORAGE_MODE == "s3" and "shorts-producer" in img_src)):
                try:
                    # Extract storage key from URL
                    # Example URL: http://.../shorts-producer/projects/1/...
                    if "projects/" in img_src:
                        storage_key = img_src.split("projects/", 1)[1]
                        storage_key = "projects/" + storage_key
                        storage = get_storage()
                        local_path = storage.get_local_path(storage_key)
                        image_bytes = local_path.read_bytes()
                        logger.info("📦 [Video Build] Loaded image from storage: %s", storage_key)
                    else:
                        image_bytes = self._load_image_bytes(img_src)
                except Exception as e:
                    logger.warning("📦 [Video Build] Failed to load from storage, fallback to URL: %s", e)
                    image_bytes = self._load_image_bytes(img_src)
            else:
                image_bytes = self._load_image_bytes(img_src)

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

            # Generate TTS (use cleaned script for better pronunciation)
            has_valid_tts, tts_duration = await self._generate_tts(
                i, clean_script, tts_path
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
        """Add subtitle image inputs with dynamic positioning."""
        if not self.request.include_subtitles:
            logger.info("🚫 Subtitles disabled (include_subtitles=False)")
            return

        from PIL import Image

        for i in range(self.num_scenes):
            subtitle_path = self.temp_dir / f"subtitle_{i}.png"
            font_size = self.subtitle_font_sizes[i] if self.subtitle_font_sizes[i] > 0 else None

            logger.info(f"📝 Scene {i} subtitle:")
            logger.info(f"  - Lines: {self.subtitle_lines[i]}")
            logger.info(f"  - Font size: {font_size}")
            logger.info(f"  - Layout: {'Post' if self.use_post_layout else 'Full'}")

            # Calculate dynamic subtitle position based on image content
            scene_img_path = self.temp_dir / f"scene_{i}.png"
            subtitle_y_ratio = None
            try:
                if scene_img_path.exists():
                    scene_img = Image.open(scene_img_path)
                    subtitle_y_ratio = self._calculate_optimal_subtitle_y(
                        scene_img,
                        layout_style=self.request.layout_style
                    )
                    logger.info(f"  - Dynamic Y position: {subtitle_y_ratio:.3f}")
            except Exception as e:
                logger.warning(f"Scene {i}: failed to calculate dynamic subtitle position: {e}")

            subtitle_img = self._render_subtitle_image(
                self.subtitle_lines[i],
                self.out_w, self.out_h,
                self.font_path,
                self.use_post_layout,
                self.post_layout_metrics,
                font_size,
                subtitle_y_ratio,
            )
            subtitle_img.save(subtitle_path, "PNG")

            # Debug: Check if subtitle image has content
            img_pixels = list(subtitle_img.getdata())
            non_transparent = sum(1 for p in img_pixels if len(p) == 4 and p[3] > 0)
            logger.info(f"  - Subtitle image saved: {subtitle_path}")
            logger.info(f"  - Non-transparent pixels: {non_transparent}/{len(img_pixels)}")

            self.input_args.extend(["-loop", "1", "-i", str(subtitle_path)])

    def _build_video_filters(self) -> None:
        """Build video processing filters for each scene.

        Filter chain order (Ken Burns + Subtitle sync):
        1. Scale/Crop image → [v{i}_scaled]
        2. Overlay subtitle on scaled image → [v{i}_with_sub] or [v{i}_presub]
        3. Apply Ken Burns effect to composited image → [v{i}_base]
        4. Trim to duration → [v{i}_raw]

        This ensures subtitles move naturally with Ken Burns effects.
        """
        subtitle_base_idx = self.num_scenes * 2

        for i in range(self.num_scenes):
            v_idx = i * 2
            base_dur = self.scene_durations[i]
            clip_dur = base_dur + (
                self.transition_dur if i < self.num_scenes - 1 else 0
            )
            motion_frames = max(1, int(clip_dur * 25))

            # Step 1: Scale/Crop image (no Ken Burns yet)
            if self.use_post_layout:
                self._build_post_layout_base(i, v_idx)
            else:
                self._build_full_layout_base(i, v_idx)

            # Step 2: Apply subtitles BEFORE Ken Burns
            presub_label = f"v{i}_scaled"
            if self.request.include_subtitles:
                sub_idx = subtitle_base_idx + i
                logger.info(f"🎬 Scene {i}: Adding subtitle overlay (input [{sub_idx}:v])")

                # Build subtitle filter with fade animation
                fade_duration = 0.3  # seconds
                sub_filter = f"[{sub_idx}:v]scale={self.out_w}:{self.out_h},format=rgba"

                # Add fade in/out only if clip is long enough
                if clip_dur > fade_duration * 2:
                    fade_out_start = clip_dur - fade_duration
                    sub_filter += (
                        f",fade=t=in:st=0:d={fade_duration}:alpha=1"
                        f",fade=t=out:st={fade_out_start}:d={fade_duration}:alpha=1"
                    )

                self.filters.append(f"{sub_filter}[sub{i}]")
                self.filters.append(
                    f"[{presub_label}][sub{i}]overlay=0:0:format=auto[v{i}_with_sub]"
                )
                presub_label = f"v{i}_with_sub"
                logger.info(f"🎬 Scene {i}: Subtitle overlay complete → [{presub_label}]")
            else:
                logger.info(f"🎬 Scene {i}: No subtitles (include_subtitles={self.request.include_subtitles})")

            # Step 3: Apply Ken Burns effect to composited image
            preset_name = self._resolve_scene_preset(i)
            if preset_name == "none":
                # No Ken Burns - rename to [v{i}_base]
                self.filters.append(f"[{presub_label}]null[v{i}_base]")
            else:
                params = get_preset(preset_name)
                zoompan = build_zoompan_filter(
                    params, self.out_w, self.out_h, motion_frames, self.ken_burns_intensity
                )
                self.filters.append(f"[{presub_label}]{zoompan}[v{i}_base]")

            # Step 4: Trim to duration
            self.filters.append(
                f"[v{i}_base]trim=duration={clip_dur},setpts=PTS-STARTPTS[v{i}_raw]"
            )

    def _build_post_layout_base(self, i: int, v_idx: int) -> None:
        """Build base scaling filter for post layout style (no Ken Burns yet)."""
        self.filters.append(
            f"[{v_idx}:v]scale={self.out_w}:{self.out_h}[v{i}_scaled]"
        )

    def _build_full_layout_base(self, i: int, v_idx: int) -> None:
        """Build base scaling/cropping filter for full layout style (no Ken Burns yet)."""
        self.filters.append(
            f"[{v_idx}:v]scale={self.out_w}:{self.out_h}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={self.out_w}:{self.out_h}[v{i}_scaled]"
        )

    def _resolve_scene_preset(self, scene_idx: int) -> str:
        """Resolve Ken Burns preset for a specific scene.

        Handles 'random' preset by selecting a different effect per scene.

        Args:
            scene_idx: Scene index for seed generation

        Returns:
            Resolved preset name
        """
        if self.ken_burns_preset == "random":
            # Use scene index + project timestamp for reproducible randomness
            seed = hash(f"{self.project_id}_{scene_idx}")
            name, _ = get_random_preset(seed)
            logger.info(f"Scene {scene_idx}: random Ken Burns preset -> {name}")
            return name
        return self.ken_burns_preset

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
        """Apply transitions between scenes."""
        if self.num_scenes > 1:
            import random

            from constants.transition import RANDOM_ELIGIBLE, get_transition_name

            curr_v, curr_a, acc_offset = "[v0_raw]", "[a0_raw]", 0
            for i in range(1, self.num_scenes):
                # Resolve transition type for this scene
                if self.transition_type == "random":
                    # Use scene index + project ID for reproducible randomness
                    seed = hash(f"{self.project_id}_{i}")
                    rng = random.Random(seed)
                    transition = rng.choice(RANDOM_ELIGIBLE)
                    logger.info(f"Scene {i}: random transition -> {transition}")
                else:
                    transition = get_transition_name(self.transition_type)

                prev_dur = self.scene_durations[i - 1]
                acc_offset += prev_dur
                self.filters.append(
                    f"{curr_v}[v{i}_raw]xfade=transition={transition}:"
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
        """Apply overlay graphics to video with slide-in animation."""
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

        # Create separate header and footer overlay images
        header_path = self.temp_dir / "overlay_header.png"
        footer_path = self.temp_dir / "overlay_footer.png"

        self._create_overlay_header(
            self.request.overlay_settings,
            self.out_w, self.out_h,
            header_path,
            self.request.layout_style,
        )
        self._create_overlay_footer(
            self.request.overlay_settings,
            self.out_w, self.out_h,
            footer_path,
            self.request.layout_style,
        )

        # Add header and footer as inputs
        self.input_args.extend(["-i", str(header_path)])
        self.input_args.extend(["-i", str(footer_path)])

        header_idx = next_input_idx
        footer_idx = next_input_idx + 1

        # Header animation: slide in from top (0.5 seconds)
        # Format and enhance alpha
        self.filters.append(
            f"[{header_idx}:v]format=rgba,colorchannelmixer=aa=1.6[ovr_h]"
        )
        # Slide from top: y starts at -h and moves to 0 over 0.5 seconds
        self.filters.append(
            f"{self._map_v}[ovr_h]overlay=0:'if(lt(t,0.5),-h*(1-t*2),0)':format=auto[v_h]"
        )

        # Footer animation: slide in from bottom (0.5 seconds)
        # Format and enhance alpha
        self.filters.append(
            f"[{footer_idx}:v]format=rgba,colorchannelmixer=aa=1.6[ovr_f]"
        )
        # Slide from bottom: y starts at h and moves to 0 over 0.5 seconds
        self.filters.append(
            "[v_h][ovr_f]overlay=0:'if(lt(t,0.5),h*(1-t*2),0)':format=auto[vid_o]"
        )

        self._map_v = "[vid_o]"
        self._next_input_idx = footer_idx + 1

    def _apply_bgm(self) -> None:
        """Apply background music with optional audio ducking."""
        storage = get_storage()

        # Resolve BGM file (supports 'random' selection with project-based seed)
        seed = hash(self.project_id)
        resolved_bgm = resolve_bgm_file(self.request.bgm_file, seed=seed)
        if not resolved_bgm:
            return

        storage_key = f"shared/audio/{resolved_bgm}"
        if not storage.exists(storage_key):
            logger.warning(f"⚠️ [Video Build] BGM file not found in storage: {storage_key}")
            return

        bgm_path = storage.get_local_path(storage_key)

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

        # Debug: Log filter chain
        logger.info("=" * 80)
        logger.info("🎬 FFmpeg Filter Chain Debug:")
        logger.info("-" * 80)
        for i, f in enumerate(self.filters):
            logger.info(f"Filter {i:2d}: {f}")
        logger.info("-" * 80)
        logger.info(f"Video map: {self._map_v}")
        logger.info(f"Audio map: {self._map_a}")
        logger.info(f"Include subtitles: {self.request.include_subtitles}")
        logger.info("=" * 80)

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

async def create_video_task(request: VideoRequest) -> dict:
    """Create a video from scenes using VideoBuilder."""
    try:
        builder = VideoBuilder(request)
        return await builder.build()
    except Exception as exc:
        logger.exception("Video Create Error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
