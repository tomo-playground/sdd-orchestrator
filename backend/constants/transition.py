"""
Transition effects for scene transitions.

FFmpeg xfade filter supports various transition types.
Reference: https://ffmpeg.org/ffmpeg-filters.html#xfade
"""

from dataclasses import dataclass
from typing import Literal

TransitionType = Literal[
    "fade",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "slideup",
    "slidedown",
    "circleopen",
    "circleclose",
    "dissolve",
    "pixelize",
    "random",
]


@dataclass(frozen=True)
class TransitionPreset:
    """Transition preset with display information."""

    name: str
    description: str
    visual: str  # Simple visual representation


# Transition presets with descriptions
TRANSITIONS: dict[str, TransitionPreset] = {
    "fade": TransitionPreset(
        name="Fade",
        description="Classic cross-fade (default)",
        visual="○ → ●",
    ),
    "wipeleft": TransitionPreset(
        name="Wipe Left",
        description="Wipe from right to left",
        visual="▐← ",
    ),
    "wiperight": TransitionPreset(
        name="Wipe Right",
        description="Wipe from left to right",
        visual=" →▌",
    ),
    "wipeup": TransitionPreset(
        name="Wipe Up",
        description="Wipe from bottom to top",
        visual="▔ ↑",
    ),
    "wipedown": TransitionPreset(
        name="Wipe Down",
        description="Wipe from top to bottom",
        visual="↓ ▁",
    ),
    "slideleft": TransitionPreset(
        name="Slide Left",
        description="Slide scene from right",
        visual="[→]",
    ),
    "slideright": TransitionPreset(
        name="Slide Right",
        description="Slide scene from left",
        visual="[←]",
    ),
    "slideup": TransitionPreset(
        name="Slide Up",
        description="Slide scene from bottom",
        visual="[↑]",
    ),
    "slidedown": TransitionPreset(
        name="Slide Down",
        description="Slide scene from top",
        visual="[↓]",
    ),
    "circleopen": TransitionPreset(
        name="Circle Open",
        description="Circular reveal from center",
        visual="◉ →",
    ),
    "circleclose": TransitionPreset(
        name="Circle Close",
        description="Circular close to center",
        visual="→ ◉",
    ),
    "dissolve": TransitionPreset(
        name="Dissolve",
        description="Pixel-by-pixel dissolve",
        visual="▓▒░",
    ),
    "pixelize": TransitionPreset(
        name="Pixelize",
        description="Pixelation effect",
        visual="█▓▒",
    ),
}

# Transitions eligible for random selection (excludes 'fade' as it's default)
RANDOM_ELIGIBLE = [
    "wipeleft",
    "wiperight",
    "slideup",
    "slidedown",
    "circleopen",
    "dissolve",
]


def get_transition_name(transition_type: str | None) -> str:
    """Get transition name, defaulting to 'fade' if not found."""
    if not transition_type or transition_type not in TRANSITIONS:
        return "fade"
    return transition_type


def get_transition_list() -> list[dict[str, str]]:
    """Get list of all transitions for UI."""
    return [
        {
            "value": key,
            "label": preset.name,
            "description": preset.description,
            "visual": preset.visual,
        }
        for key, preset in TRANSITIONS.items()
    ]
