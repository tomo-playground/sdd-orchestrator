"""Business logic services for Shorts Producer Backend."""

from .avatar import (
    avatar_filename,
    ensure_avatar_file,
)
from .cleanup import (
    CleanupOptions,
    CleanupResult,
    cleanup_all,
    cleanup_cache,
    cleanup_candidates,
    cleanup_old_videos,
    cleanup_test_folders,
    get_storage_stats,
)
from .image import (
    decode_data_url,
    load_image_bytes,
)
from .keywords import (
    load_known_keywords,
    # These are currently slimmed/disabled in Pure V3
    # update_tag_effectiveness,
    # get_tag_effectiveness_report,
    normalize_prompt_token,
)
from .prompt import (
    is_scene_token,
    merge_prompt_tokens,
    normalize_negative_prompt,
    normalize_prompt_tokens,
    split_prompt_tokens,
)
from .rendering import (
    apply_post_overlay_mask,
    compose_post_frame,
    create_overlay_image,
    load_avatar_image,
    render_scene_text_image,
    render_subtitle_image,  # Deprecated alias
    resolve_overlay_frame,
    resolve_subtitle_font_path,
)
from .utils import (
    get_audio_duration,
    parse_json_payload,
    scrub_payload,
    to_edge_tts_rate,
    wrap_text,
    wrap_text_by_font,
)
from .validation import (
    cache_key_for_validation,
    compare_prompt_to_tags,
    load_wd14_model,
    resolve_image_mime,
    wd14_predict_tags,
)
from .video import (
    calculate_scene_durations,
    calculate_speed_params,
    clean_script_for_tts,
    generate_video_filename,
    sanitize_filename,
)

__all__ = [
    # Cleanup
    "CleanupOptions",
    "CleanupResult",
    "cleanup_all",
    "cleanup_cache",
    "cleanup_candidates",
    "cleanup_old_videos",
    "cleanup_test_folders",
    "get_storage_stats",
    # Keywords
    "normalize_prompt_token",
    "load_known_keywords",
    # Validation
    "cache_key_for_validation",
    "compare_prompt_to_tags",
    "load_wd14_model",
    "resolve_image_mime",
    "wd14_predict_tags",
    # Rendering
    "apply_post_overlay_mask",
    "compose_post_frame",
    "create_overlay_image",
    "load_avatar_image",
    "render_scene_text_image",
    "render_subtitle_image",  # Deprecated alias
    "resolve_overlay_frame",
    "resolve_subtitle_font_path",
    # Image
    "decode_data_url",
    "load_image_bytes",
    # Avatar
    "avatar_filename",
    "ensure_avatar_file",
    # Prompt
    "is_scene_token",
    "merge_prompt_tokens",
    "normalize_negative_prompt",
    "normalize_prompt_tokens",
    "split_prompt_tokens",
    # Utils
    "get_audio_duration",
    "parse_json_payload",
    "scrub_payload",
    "to_edge_tts_rate",
    "wrap_text",
    "wrap_text_by_font",
    # Video
    "calculate_scene_durations",
    "calculate_speed_params",
    "clean_script_for_tts",
    "generate_video_filename",
    "sanitize_filename",
]
