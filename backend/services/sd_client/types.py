"""SD Client result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SDTxt2ImgResult:
    """Result from txt2img generation."""

    images: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)
    seed: int | None = None

    @property
    def image(self) -> str:
        """Return the first generated image (base64), or empty string."""
        return self.images[0] if self.images else ""


@dataclass
class SDProgressResult:
    """Result from progress polling."""

    progress: float = 0.0
    textinfo: str = ""
    current_image: str | None = None
