"""Storyboard service package — re-exports all public functions for backward compatibility."""

from services.storyboard.crud import (
    _sync_speaker_mappings,
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

# Lazy imports for services.script to avoid circular import:
# storyboard/__init__ -> script/gemini_generator -> storyboard/helpers -> storyboard/__init__ (cycle)
_SCRIPT_ATTRS = {
    "create_storyboard",
    "_call_gemini_with_retry",
    "_load_character_context",
    "_check_multi_character_capable",
}


def __getattr__(name: str):
    if name in _SCRIPT_ATTRS:
        from services.script import gemini_generator

        if name == "create_storyboard":
            return gemini_generator.generate_script
        return getattr(gemini_generator, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # script (backward compat alias — lazy)
    "create_storyboard",
    "_call_gemini_with_retry",
    "_load_character_context",
    "_check_multi_character_capable",
    # helpers
    "strip_markdown_codeblock",
    "normalize_scene_tags_key",
    "calculate_min_scenes",
    "calculate_max_scenes",
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
    "save_storyboard_to_db",
    "list_storyboards_from_db",
    "get_storyboard_by_id",
    "update_storyboard_in_db",
    "update_storyboard_metadata",
    "delete_storyboard_from_db",
    "restore_storyboard_from_db",
    "permanent_delete_storyboard",
]
