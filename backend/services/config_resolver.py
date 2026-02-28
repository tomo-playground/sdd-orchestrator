"""Cascading config resolver: Group fields only.

For each CASCADING_FIELDS entry, the most specific non-None value wins.
The Group model directly carries config fields (render_preset_id, etc.).
"""

from __future__ import annotations

from typing import Any

CASCADING_FIELDS = [
    "render_preset_id",
    "style_profile_id",
    "narrator_voice_preset_id",
]


def resolve_effective_config(
    _project: Any,
    group: Any | None = None,
) -> dict:
    """Return resolved config dict with ``values`` and ``sources``.

    Each source entry records which level the value came from.
    Config fields are read directly from the Group model.
    """
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}

    if group is not None:
        for field in CASCADING_FIELDS:
            val = getattr(group, field, None)
            if val is not None:
                values[field] = val
                sources[field] = "group"

    # JSONB fields: extracted directly (not in CASCADING_FIELDS)
    channel_dna = None
    if group is not None:
        channel_dna = getattr(group, "channel_dna", None)

    return {"values": values, "sources": sources, "channel_dna": channel_dna}


def apply_system_defaults(result: dict, db: Any) -> dict:
    """Apply system-level defaults for fields not resolved by cascading.

    Falls back to is_default=true records in DB.
    """
    values = result["values"]
    sources = result["sources"]

    if "style_profile_id" not in values:
        from models import StyleProfile

        default_profile = db.query(StyleProfile.id).filter(StyleProfile.is_default.is_(True)).first()
        if default_profile:
            values["style_profile_id"] = default_profile.id
            sources["style_profile_id"] = "system_default"

    return result
