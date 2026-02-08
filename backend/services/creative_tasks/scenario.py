"""Scenario task-type: creative multi-agent story generation."""

from __future__ import annotations

from typing import Any

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "originality": {"weight": 0.3, "description": "Novel and surprising ideas"},
    "coherence": {"weight": 0.4, "description": "Logical flow and structure"},
    "engagement": {"weight": 0.3, "description": "Audience appeal and emotional impact"},
}
