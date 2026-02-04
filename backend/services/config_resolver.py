"""Cascading config resolver: Project < GroupConfig < Storyboard.

For each CASCADING_FIELDS entry, the most specific non-None value wins:
  Storyboard (if given) > GroupConfig (if given) > Project.
"""

from __future__ import annotations

from typing import Any

CASCADING_FIELDS = [
    "render_preset_id",
    "default_character_id",
    "default_style_profile_id",
    "narrator_voice_preset_id",
    "language",
    "structure",
    "duration",
]


def resolve_effective_config(
    project: Any,
    group: Any | None = None,
    storyboard: Any | None = None,
) -> dict:
    """Return resolved config dict with ``values`` and ``sources``.

    Each source entry records which level the value came from.
    The group layer reads from group.config (GroupConfig) if available.
    """
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}

    # Build layers: project -> group_config -> storyboard
    group_config = _get_group_config(group)
    layers = [
        ("project", project),
        ("group", group_config),
        ("storyboard", storyboard),
    ]

    for field in CASCADING_FIELDS:
        for level_name, obj in layers:
            if obj is None:
                continue
            val = getattr(obj, field, None)
            if val is not None:
                values[field] = val
                sources[field] = level_name

    return {"values": values, "sources": sources}


def _get_group_config(group: Any | None) -> Any | None:
    """Extract GroupConfig from a Group object, falling back to group itself."""
    if group is None:
        return None
    config = getattr(group, "config", None)
    if config is not None:
        return config
    # Fallback: group still has config columns during migration period
    return group


def apply_system_defaults(result: dict, db: Any) -> dict:
    """Apply system-level defaults for fields not resolved by cascading.

    Falls back to is_default=true records in DB.
    """
    values = result["values"]
    sources = result["sources"]

    if "default_style_profile_id" not in values:
        from models import StyleProfile

        default_profile = db.query(StyleProfile.id).filter(StyleProfile.is_default.is_(True)).first()
        if default_profile:
            values["default_style_profile_id"] = default_profile.id
            sources["default_style_profile_id"] = "system_default"

    return result
