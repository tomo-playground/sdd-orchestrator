"""Storyboard service package — re-exports all public functions for backward compatibility."""

from services.storyboard.crud import (
    _sync_speaker_mappings,
    create_draft,
    delete_storyboard_from_db,
    get_storyboard_by_id,
    list_storyboards_from_db,
    permanent_delete_storyboard,
    restore_storyboard_from_db,
    save_storyboard_to_db,
    update_storyboard_in_db,
    update_storyboard_metadata,
)
from services.storyboard.helpers import (
    _sanitize_candidates_for_db,
    calculate_auto_pin_flags,
    calculate_max_scenes,
    calculate_min_scenes,
    estimate_reading_duration,
    normalize_scene_tags_key,
    strip_markdown_codeblock,
    trim_scenes_to_duration,
    truncate_title,
)
from services.storyboard.scene_builder import (
    _link_media_asset,
    create_scenes,
    resolve_action_tag_ids,
    serialize_scene,
)

__all__ = [
    # helpers
    "strip_markdown_codeblock",
    "normalize_scene_tags_key",
    "calculate_min_scenes",
    "calculate_max_scenes",
    "estimate_reading_duration",
    "trim_scenes_to_duration",
    "truncate_title",
    "calculate_auto_pin_flags",
    "_sanitize_candidates_for_db",
    # scene_builder
    "resolve_action_tag_ids",
    "serialize_scene",
    "_link_media_asset",
    "create_scenes",
    # crud
    "_sync_speaker_mappings",
    "create_draft",
    "save_storyboard_to_db",
    "list_storyboards_from_db",
    "get_storyboard_by_id",
    "update_storyboard_in_db",
    "update_storyboard_metadata",
    "delete_storyboard_from_db",
    "restore_storyboard_from_db",
    "permanent_delete_storyboard",
]
