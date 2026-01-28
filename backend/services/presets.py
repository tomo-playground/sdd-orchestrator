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


# Available presets
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
    "storytelling": StoryboardPreset(
        id="storytelling",
        name="Storytelling",
        name_ko="스토리텔링",
        description="Narrative story with beginning, middle, end",
        structure="Storytelling",
        template="create_storyboard.j2",
        sample_topics=[
            "마법의 숲에서 길을 잃은 소녀",
            "시간여행자의 첫 번째 모험",
            "외로운 로봇의 친구 찾기",
            "비 오는 날 우연한 만남",
            "꿈에서 만난 신비로운 존재",
        ],
        default_duration=45,
    ),
    "tutorial": StoryboardPreset(
        id="tutorial",
        name="Tutorial",
        name_ko="튜토리얼",
        description="Step-by-step instructional content",
        structure="Tutorial",
        template="create_storyboard.j2",
        sample_topics=[
            "맛있는 계란찜 만들기",
            "종이접기로 학 접기",
            "기초 스트레칭 루틴",
            "스마트폰 사진 잘 찍는 법",
            "집에서 하는 간단한 운동",
        ],
        default_duration=40,
    ),
    "facts": StoryboardPreset(
        id="facts",
        name="Fun Facts",
        name_ko="재미있는 사실",
        description="Interesting facts and trivia",
        structure="Facts",
        template="create_storyboard.j2",
        sample_topics=[
            "우주에 대한 놀라운 사실들",
            "동물들의 신기한 능력",
            "역사 속 재미있는 이야기",
            "과학이 밝힌 일상의 비밀",
            "세계의 독특한 문화",
        ],
        default_duration=30,
    ),
    "motivation": StoryboardPreset(
        id="motivation",
        name="Motivation",
        name_ko="동기부여",
        description="Inspirational and motivational content",
        structure="Motivation",
        template="create_storyboard.j2",
        sample_topics=[
            "포기하고 싶을 때 기억할 것",
            "작은 시작의 힘",
            "실패는 성공의 어머니",
            "오늘을 살아가는 이유",
            "꿈을 향한 한 걸음",
        ],
        default_duration=25,
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
