"""Character Design task-type: unique character profile generation."""

from __future__ import annotations

from typing import Any

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "uniqueness": {"weight": 0.3, "description": "Distinctive and memorable character design"},
    "visual_consistency": {"weight": 0.4, "description": "Consistent visual traits across descriptions"},
    "tag_expressibility": {"weight": 0.3, "description": "Expressible as Danbooru/SD tags"},
}
