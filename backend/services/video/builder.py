"""VideoBuilder: state container and pipeline orchestrator.

The VideoBuilder class holds all state for a video build and delegates
processing to module-level functions in scene_processing, filters, and
effects. The ``create_video_task`` entry-point creates a builder and
runs the full pipeline.
"""

from __future__ import annotations

import random
import shutil
import subprocess
import time
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from config import (
    AUDIO_BITRATE,
    AUDIO_CODEC,
    BUILD_DIR,
    FFMPEG_TIMEOUT_SECONDS,
    VIDEO_CODEC,
    VIDEO_CRF,
    VIDEO_DIR,
    VIDEO_FPS,
    VIDEO_PIX_FMT,
    VIDEO_PRESET,
    logger,
)
from database import SessionLocal
from services.asset_service import AssetService
from services.motion import resolve_preset_name
from services.video.utils import (
    calculate_scene_durations,
    calculate_speed_params,
    generate_video_filename,
    sanitize_filename,
)

if TYPE_CHECKING:
    from schemas import VideoRequest


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
            calculate_optimal_scene_text_y,
            load_image_bytes,
        )
        from services.rendering import (
            _random_meta_values,
            apply_post_overlay_mask,
            calculate_post_layout_metrics,
            compose_post_frame,
            create_overlay_footer,
            create_overlay_header,
            render_scene_text_image,
            resolve_overlay_frame,
            resolve_scene_text_font_path,
        )
        from services.utils import (
            get_audio_duration,
            wrap_text,
            wrap_text_by_font,
        )

        self.request = request
        self._ensure_avatar_file = ensure_avatar_file
        self._load_image_bytes = load_image_bytes
        self._calculate_optimal_scene_text_y = calculate_optimal_scene_text_y
        self._random_meta_values = _random_meta_values
        self._apply_post_overlay_mask = apply_post_overlay_mask
        self._calculate_post_layout_metrics = calculate_post_layout_metrics
        self._compose_post_frame = compose_post_frame
        self._create_overlay_header = create_overlay_header
        self._create_overlay_footer = create_overlay_footer
        self._render_scene_text_image = render_scene_text_image
        self._resolve_overlay_frame = resolve_overlay_frame
        self._resolve_scene_text_font_path = resolve_scene_text_font_path
        self._get_audio_duration = get_audio_duration
        self._wrap_text = wrap_text
        self._wrap_text_by_font = wrap_text_by_font
        self._FullLayout = FullLayout
        self._PostLayout = PostLayout
        self._OverlaySettings = OverlaySettings
        self._PostCardSettings = PostCardSettings

        # State
        self.project_id = f"build_{int(time.time())}"
        self.temp_dir = BUILD_DIR / self.project_id
        self.safe_title = sanitize_filename(request.storyboard_title)
        self.video_filename = generate_video_filename(self.safe_title, request.layout_style)
        self.video_path = VIDEO_DIR / self.video_filename
        self.font_path = self._resolve_scene_text_font_path(request.scene_text_font)

        # Calculated values
        self.num_scenes = len(request.scenes)
        self.transition_dur, self.tts_padding, self.speed_multiplier = calculate_speed_params(
            request.speed_multiplier or 1.0
        )
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

        # Per-scene data (populated during build)
        self.input_args: list[str] = []
        self.filters: list[str] = []
        self.tts_valid: list[bool] = []
        self.tts_durations: list[float] = []
        self.subtitle_lines: list[list[str]] = []
        self.scene_text_font_sizes: list[int] = []
        self.scene_durations: list[float] = []
        self.avatar_file: str | None = None
        self.post_avatar_file: str | None = None
        self.post_layout_metrics: dict[str, Any] | None = None
        self._ai_bgm_path: str | None = None  # Set by _prepare_bgm for AI BGM

        # Filter chain state (populated by effects module)
        self._map_v: str = ""
        self._map_a: str = ""
        self._total_dur: float = 0.0
        self._next_input_idx: int = 0

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    async def build(self) -> dict:
        """Execute the video build pipeline."""
        logger.info("Video build started: %s", self.request.storyboard_title)
        if self.num_scenes == 0:
            raise ValueError("Cannot render video: no scenes provided")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        try:
            await self._setup_avatars()
            await self._process_scenes()
            self._calculate_durations()
            await self._prepare_bgm()
            self._build_filters()
            self._encode()
            return self._upload_result()
        except Exception as exc:
            logger.exception("Video Create Error")
            raise exc
        finally:
            self._cleanup()

    # ------------------------------------------------------------------
    # Delegating methods
    # ------------------------------------------------------------------

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
            self.avatar_file = await self._ensure_avatar_file(self.request.overlay_settings.avatar_key)
            if self.avatar_file:
                self.request.overlay_settings.avatar_file = self.avatar_file

        if self.request.post_card_settings:
            self.post_avatar_file = await self._ensure_avatar_file(self.request.post_card_settings.avatar_key)

    async def _process_scenes(self) -> None:
        from services.video.scene_processing import process_scenes

        await process_scenes(self)

    def _calculate_durations(self) -> None:
        self.scene_durations = calculate_scene_durations(
            self.request.scenes,
            self.tts_valid,
            self.tts_durations,
            self.speed_multiplier,
            self.tts_padding,
        )

    async def _prepare_bgm(self) -> None:
        """Prepare AI-generated BGM if bgm_mode is 'ai'."""
        if getattr(self.request, "bgm_mode", "file") != "ai":
            return
        preset_id = getattr(self.request, "music_preset_id", None)
        if not preset_id:
            return

        from models.media_asset import MediaAsset
        from models.music_preset import MusicPreset
        from services.storage import get_storage

        db = SessionLocal()
        try:
            preset = db.query(MusicPreset).filter(MusicPreset.id == preset_id).first()
            if not preset:
                logger.warning("[Video Build] Music preset %d not found", preset_id)
                return

            # If preset has a cached audio asset, use it directly
            if preset.audio_asset_id:
                asset = db.get(MediaAsset, preset.audio_asset_id)
                if asset:
                    storage = get_storage()
                    local_path = storage.get_local_path(asset.storage_key)
                    if local_path:
                        self._ai_bgm_path = str(local_path)
                        logger.info("[Video Build] Using cached AI BGM from asset %d", asset.id)
                        return

            # No cached asset — generate on the fly
            if preset.prompt:
                import asyncio

                from services.audio.music_generator import generate_music

                loop = asyncio.get_event_loop()
                wav_bytes, _, _ = await loop.run_in_executor(
                    None,
                    lambda: generate_music(
                        prompt=preset.prompt,
                        duration=preset.duration or 30.0,
                        seed=preset.seed or -1,
                    ),
                )
                out_path = self.temp_dir / "ai_bgm.wav"
                out_path.write_bytes(wav_bytes)
                self._ai_bgm_path = str(out_path)
                logger.info("[Video Build] Generated AI BGM on the fly (%d bytes)", len(wav_bytes))
        finally:
            db.close()

    def _build_filters(self) -> None:
        from services.video.effects import (
            apply_bgm,
            apply_overlays,
            apply_transitions,
        )
        from services.video.filters import build_filters

        build_filters(self)
        apply_transitions(self)
        apply_overlays(self)
        apply_bgm(self)

    def _encode(self) -> None:
        """Encode the final video using FFmpeg."""
        filter_complex_str = ";".join(self.filters)

        logger.info("FFmpeg Filter Chain Debug:")
        logger.info("-" * 80)
        for idx, f in enumerate(self.filters):
            logger.info(f"Filter {idx:2d}: {f}")
        logger.info("-" * 80)
        logger.info(f"Video map: {self._map_v}")
        logger.info(f"Audio map: {self._map_a}")
        logger.info(f"Include subtitles: {self.request.include_scene_text}")
        logger.info("=" * 80)

        cmd = [
            "ffmpeg",
            "-y",
            *self.input_args,
            "-filter_complex",
            filter_complex_str,
            "-map",
            self._map_v,
            "-map",
            self._map_a,
            "-s",
            f"{self.out_w}x{self.out_h}",
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
            str(self.video_path),
        ]

        logger.info("Running FFmpeg (timeout=%ds)", FFMPEG_TIMEOUT_SECONDS)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out after %d seconds", FFMPEG_TIMEOUT_SECONDS)
            raise Exception(f"FFmpeg process timed out after {FFMPEG_TIMEOUT_SECONDS} seconds") from None
        if result.returncode != 0:
            logger.error("FFmpeg failed: %s", result.stderr)
            raise Exception(result.stderr)

    def _upload_result(self) -> dict:
        """Upload and register the final video, return URL dict."""
        if self.project_id_int and self.group_id_int and self.request.storyboard_id:
            db = SessionLocal()
            try:
                asset_service = AssetService(db)
                asset = asset_service.save_rendered_video(
                    video_path=self.video_path,
                    project_id=self.project_id_int,
                    group_id=self.group_id_int,
                    storyboard_id=self.request.storyboard_id,
                    file_name=self.video_filename,
                )
                db.commit()

                url = asset_service.get_asset_url(asset.storage_key)
                logger.info(
                    "[Video Build] Video uploaded and registered: %s",
                    asset.storage_key,
                )
                return {"video_url": url, "media_asset_id": asset.id}
            finally:
                db.close()

        return {"video_url": f"/outputs/videos/{self.video_filename}"}

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
