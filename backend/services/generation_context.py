"""GenerationContext — pipeline state container.

Replaces direct request mutation with explicit, staged context building.
Each pipeline stage reads from context and writes its results to context fields.
The original request is preserved read-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from schemas import SceneGenerateRequest
from services.character_consistency import ConsistencyStrategy

if TYPE_CHECKING:
    from services.style_context import StyleContext


@dataclass
class GenerationContext:
    """Mutable pipeline state — built stage by stage, then consumed."""

    # ── Input (set once at init, then read-only) ────────────────────────
    request: SceneGenerateRequest
    character: object | None = None  # Character ORM object
    character_b_id: int | None = None
    consistency: ConsistencyStrategy = field(default_factory=ConsistencyStrategy)
    style_loras: list[dict] = field(default_factory=list)
    style_context: StyleContext | None = None

    # ── Stage 1: Composed (prompt preparation) ──────────────────────────
    prompt: str = ""
    negative_prompt: str = ""

    # ── Stage 2: Adjusted (complexity/calibration) ──────────────────────
    steps: int = 20
    cfg_scale: float = 7.0

    # ── Stage 3: ControlNet results ─────────────────────────────────────
    controlnet_used: str | None = None
    ip_adapter_used: str | None = None

    # ── Output ──────────────────────────────────────────────────────────
    warnings: list[str] = field(default_factory=list)

    # ── Convenience ─────────────────────────────────────────────────────
    @property
    def character_name(self) -> str | None:
        return self.character.name if self.character else None  # type: ignore[union-attr]
