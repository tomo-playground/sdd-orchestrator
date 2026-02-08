"""Visual Concept task-type: cinematic mood and visual design generation."""

from __future__ import annotations

from typing import Any

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "originality": {"weight": 0.3, "description": "Novel and unique visual ideas"},
    "sd_feasibility": {"weight": 0.4, "description": "Feasibility with Stable Diffusion rendering"},
    "mood_coherence": {"weight": 0.3, "description": "Consistent mood and visual atmosphere"},
}
