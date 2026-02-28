"""Cascading config resolver: GroupConfig only.

For each CASCADING_FIELDS entry, the most specific non-None value wins.
Currently only the GroupConfig layer provides config values.
The Project model does not carry config fields directly.
"""

from __future__ import annotations

from typing import Any

CASCADING_FIELDS = [
    "render_preset_id",
    "style_profile_id",
    "narrator_voice_preset_id",
    "language",
    "duration",
]


def resolve_effective_config(
    _project: Any,
    group: Any | None = None,
) -> dict:
    """Return resolved config dict with ``values`` and ``sources``.

    Each source entry records which level the value came from.
    The group layer reads from group.config (GroupConfig) if available.
    Note: Project model has no config fields; only GroupConfig is resolved.
    """
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}

    group_config = _get_group_config(group)

    for field in CASCADING_FIELDS:
        if group_config is not None:
            val = getattr(group_config, field, None)
            if val is not None:
                values[field] = val
                sources[field] = "group"

    # JSONB fields: extracted directly (not in CASCADING_FIELDS)
    channel_dna = None
    if group_config is not None:
        channel_dna = getattr(group_config, "channel_dna", None)

    return {"values": values, "sources": sources, "channel_dna": channel_dna}


def _get_group_config(group: Any | None) -> Any | None:
    """Extract GroupConfig from a Group object."""
    if group is None:
        return None
    return getattr(group, "config", None)


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
