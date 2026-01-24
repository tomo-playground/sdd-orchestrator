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
    "japanese_lesson": StoryboardPreset(
        id="japanese_lesson",
        name="Japanese Lesson",
        name_ko="일본어 강좌",
        description="Japanese language learning content for Korean speakers",
        structure="Japanese Lesson",
        template="create_storyboard_japanese_lesson.j2",
        sample_topics=[
            "기본 인사말 (あいさつ)",
            "숫자 세기 1-10 (かず)",
            "자기소개 하기 (じこしょうかい)",
            "음식 주문하기 (ちゅうもん)",
            "길 물어보기 (みちをきく)",
            "날씨 표현 (てんき)",
            "감정 표현 (かんじょう)",
            "쇼핑할 때 쓰는 표현",
            "시간 말하기 (じかん)",
            "가족 호칭 (かぞく)",
        ],
        default_duration=35,
        default_language="Korean",
        extra_fields={"difficulty": "beginner"},
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
    "math_elementary": StoryboardPreset(
        id="math_elementary",
        name="Math - Elementary",
        name_ko="수학 강좌 (초등)",
        description="Elementary school math formulas and concepts",
        structure="Math Lesson",
        template="create_storyboard_math_lesson.j2",
        sample_topics=[
            "덧셈과 뺄셈의 기초",
            "구구단 외우기",
            "분수의 개념",
            "도형의 넓이 구하기",
            "시계 보는 법",
            "소수점 이해하기",
            "평균 구하기",
            "비와 비율",
        ],
        default_duration=35,
        extra_fields={"level": "elementary"},
    ),
    "math_middle": StoryboardPreset(
        id="math_middle",
        name="Math - Middle School",
        name_ko="수학 강좌 (중등)",
        description="Middle school math formulas and concepts",
        structure="Math Lesson",
        template="create_storyboard_math_lesson.j2",
        sample_topics=[
            "피타고라스 정리",
            "일차방정식 풀이",
            "연립방정식",
            "인수분해 기초",
            "제곱근과 실수",
            "일차함수 그래프",
            "삼각형의 합동조건",
            "원의 성질",
            "확률의 기초",
            "통계와 대표값",
        ],
        default_duration=40,
        extra_fields={"level": "middle_school"},
    ),
    "math_high": StoryboardPreset(
        id="math_high",
        name="Math - High School",
        name_ko="수학 강좌 (고등)",
        description="High school math formulas and concepts",
        structure="Math Lesson",
        template="create_storyboard_math_lesson.j2",
        sample_topics=[
            "이차방정식의 근의 공식",
            "삼각함수 기초 (sin, cos, tan)",
            "로그와 지수함수",
            "미분의 개념",
            "적분의 기초",
            "수열과 급수",
            "벡터의 기초",
            "행렬과 연산",
            "확률분포",
            "삼각함수의 덧셈정리",
        ],
        default_duration=45,
        extra_fields={"level": "high_school"},
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
