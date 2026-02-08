"""Dialogue task-type: multi-agent character dialogue generation."""

from __future__ import annotations

from typing import Any

DEFAULT_CRITERIA: dict[str, dict[str, Any]] = {
    "naturalness": {"weight": 0.35, "description": "Natural speech flow and rhythm"},
    "character_voice": {"weight": 0.35, "description": "Distinct character voices and personality"},
    "conflict": {"weight": 0.3, "description": "Dramatic tension and conversational conflict"},
}
