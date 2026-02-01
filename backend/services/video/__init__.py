"""Video service package.

Re-exports public API for backward compatibility so that existing
``from services.video import X`` statements continue to work.
"""

from services.video.builder import VideoBuilder, create_video_task
from services.video.utils import (
    calculate_scene_durations,
    calculate_speed_params,
    clean_script_for_tts,
    generate_video_filename,
    resolve_bgm_file,
    sanitize_filename,
)

__all__ = [
    "sanitize_filename",
    "resolve_bgm_file",
    "generate_video_filename",
    "calculate_speed_params",
    "calculate_scene_durations",
    "clean_script_for_tts",
    "VideoBuilder",
    "create_video_task",
]
