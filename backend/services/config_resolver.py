"""Cascading config resolver: Project < Group < Storyboard.

For each CASCADING_FIELDS entry, the most specific non-None value wins:
  Storyboard (if given) > Group (if given) > Project.
"""

from __future__ import annotations

from typing import Any

CASCADING_FIELDS = [
    "render_preset_id",
    "default_character_id",
    "default_style_profile_id",
]

def resolve_effective_config(
    project: Any,
    group: Any | None = None,
    storyboard: Any | None = None,
) -> dict:
    """Return resolved config dict with ``values`` and ``sources``.

    Each source entry records which level the value came from.
    """
    layers = [
        ("project", project),
        ("group", group),
        ("storyboard", storyboard),
    ]

    values: dict[str, Any] = {}
    sources: dict[str, str] = {}

    for field in CASCADING_FIELDS:
        for level_name, obj in layers:
            if obj is None:
                continue
            val = getattr(obj, field, None)
            if val is not None:
                values[field] = val
                sources[field] = level_name

    return {"values": values, "sources": sources}


def apply_system_defaults(result: dict, db: Any) -> dict:
    """Apply system-level defaults for fields not resolved by cascading.

    Falls back to is_default=true records in DB.
    """
    values = result["values"]
    sources = result["sources"]

    if "default_style_profile_id" not in values:
        from models import StyleProfile
        default_profile = (
            db.query(StyleProfile.id)
            .filter(StyleProfile.is_default.is_(True))
            .first()
        )
        if default_profile:
            values["default_style_profile_id"] = default_profile.id
            sources["default_style_profile_id"] = "system_default"

    return result
