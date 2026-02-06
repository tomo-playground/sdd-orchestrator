"""Preset templates for storyboard generation.

Provides sample inputs and configurations for different content types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StoryboardPreset:
    """A preset configuration for storyboard generation."""

    id: str
    name: str
    name_ko: str
    description: str
    structure: str
    template: str  # Template file name
    sample_topics: list[str] = field(default_factory=list)
    default_duration: int = 30
    default_style: str = "Anime"
    default_language: str = "Korean"
    extra_fields: dict = field(default_factory=dict)


# Available presets (Monologue + Dialogue + Narrated Dialogue)
PRESETS: dict[str, StoryboardPreset] = {
    "monologue": StoryboardPreset(
        id="monologue",
        name="Monologue",
        name_ko="독백",
        description="Single narrator storytelling",
        structure="Monologue",
        template="create_storyboard.j2",
        sample_topics=[
            "오늘 하루 있었던 일",
            "내가 좋아하는 계절",
            "처음 요리를 해본 날",
            "잊을 수 없는 여행 이야기",
            "나의 취미 생활",
        ],
        default_duration=30,
    ),
    "dialogue": StoryboardPreset(
        id="dialogue",
        name="Dialogue",
        name_ko="대화",
        description="Two-character conversation",
        structure="Dialogue",
        template="create_storyboard_dialogue.j2",
        sample_topics=[
            "첫 만남에서 어색한 대화",
            "오래된 친구와의 재회",
            "선생님과 학생의 상담",
            "카페에서 우연히 만난 두 사람",
            "형제자매의 말다툼",
        ],
        default_duration=30,
    ),
    "narrated_dialogue": StoryboardPreset(
        id="narrated_dialogue",
        name="Narrated Dialogue",
        name_ko="내레이션 대화",
        description="Two characters with narrator commentary",
        structure="Narrated Dialogue",
        template="create_storyboard_narrated.j2",
        sample_topics=[
            "10년 후 재회한 첫사랑",
            "면접관이 알아본 지원자의 비밀",
            "부모님이 몰래 보는 SNS",
            "카페 알바생이 본 이별 장면",
            "퇴사 전날 사수와의 대화",
        ],
        default_duration=45,
    ),
}


def get_all_presets() -> list[dict]:
    """Get all available presets as a list of dictionaries."""
    return [
        {
            "id": preset.id,
            "name": preset.name,
            "name_ko": preset.name_ko,
            "description": preset.description,
            "structure": preset.structure,
            "sample_topics": preset.sample_topics,
            "default_duration": preset.default_duration,
            "default_style": preset.default_style,
            "default_language": preset.default_language,
        }
        for preset in PRESETS.values()
    ]


def get_preset(preset_id: str) -> StoryboardPreset | None:
    """Get a specific preset by ID."""
    return PRESETS.get(preset_id)


def get_preset_by_structure(structure: str) -> StoryboardPreset | None:
    """Get a preset by its structure name."""
    for preset in PRESETS.values():
        if preset.structure.lower() == structure.lower():
            return preset
    return None


def get_sample_topics(preset_id: str) -> list[str]:
    """Get sample topics for a preset."""
    preset = PRESETS.get(preset_id)
    return preset.sample_topics if preset else []
