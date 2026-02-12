"""VideoBuilder: state container and pipeline orchestrator.

The VideoBuilder class holds all state for a video build and delegates
processing to module-level functions in scene_processing, filters,
effects, encoding, and upload. The ``create_video_task`` entry-point
creates a builder and runs the full pipeline.
"""

from __future__ import annotations

import random
import shutil
import time
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException

from config import BUILD_DIR, VIDEO_DIR, logger
from database import SessionLocal
from services.motion import resolve_preset_name
from services.video.progress import (  # noqa: TC004 - used at runtime
    RenderStage,
    TaskProgress,
    calc_overall_percent,
)
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
        self._progress: TaskProgress | None = None  # SSE progress tracking

        # Filter chain state (populated by effects module)
        self._map_v: str = ""
        self._map_a: str = ""
        self._total_dur: float = 0.0
        self._next_input_idx: int = 0

    # ------------------------------------------------------------------
    # Progress reporting
    # ------------------------------------------------------------------

    def set_progress(self, progress: TaskProgress) -> None:
        """Attach SSE progress tracker to this builder."""
        self._progress = progress

    def _report(self, stage: RenderStage, detail: str = "") -> None:
        """Update progress state and notify SSE consumers."""
        if not self._progress:
            return
        self._progress.stage = stage
        self._progress.message = detail
        self._progress.percent = calc_overall_percent(self._progress)
        self._progress.notify()

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
            self._report(RenderStage.SETUP_AVATARS)
            await self._setup_avatars()
            self._report(RenderStage.PROCESS_SCENES)
            await self._process_scenes()
            self._report(RenderStage.CALCULATE_DURATIONS)
            self._calculate_durations()
            self._report(RenderStage.PREPARE_BGM)
            await self._prepare_bgm()
            self._report(RenderStage.BUILD_FILTERS)
            self._build_filters()
            self._report(RenderStage.ENCODE)
            await self._encode_async()
            self._report(RenderStage.UPLOAD)
            result = self._upload_result()

            if self._progress:
                self._progress.stage = RenderStage.COMPLETED
                self._progress.result = result
                self._progress.percent = 100
                self._progress.notify()

            return result
        except Exception as exc:
            if self._progress:
                self._progress.stage = RenderStage.FAILED
                self._progress.error = str(exc)
                self._progress.notify()
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

    async def _encode_async(self) -> None:
        from services.video.encoding import encode_async

        await encode_async(self)

    def _upload_result(self) -> dict:
        from services.video.upload import upload_result

        return upload_result(self)

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
