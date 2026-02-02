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
