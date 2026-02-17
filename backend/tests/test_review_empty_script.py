"""Review 노드 빈 스크립트 검증 테스트.

"...", "... ..." 등 무대사 씬과 짧은 스크립트를 Review 규칙이 정확히 잡는지 검증한다.
"""

from __future__ import annotations

from services.agent.nodes.review import _validate_scenes


def _make_scene(script: str, speaker: str = "A", **kwargs) -> dict:
    return {
        "scene_id": 1,
        "script": script,
        "speaker": speaker,
        "duration": 3,
        "image_prompt": "smile, standing, indoors",
        **kwargs,
    }


def _make_scenes(scripts: list[str]) -> list[dict]:
    return [
        {
            "scene_id": i + 1,
            "script": s,
            "speaker": "A" if i % 2 == 0 else "Narrator",
            "duration": 3,
            "image_prompt": "smile, standing, indoors",
        }
        for i, s in enumerate(scripts)
    ]


class TestEmptyScriptDetection:
    """빈/무대사 스크립트를 error로 잡는다."""

    def test_dots_only(self):
        scenes = [_make_scene("...")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert not result["passed"]
        assert any("빈 스크립트" in e for e in result["errors"])

    def test_spaced_dots(self):
        scenes = [_make_scene("... ...")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert not result["passed"]
        assert any("빈 스크립트" in e for e in result["errors"])

    def test_single_dot(self):
        scenes = [_make_scene(".")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert not result["passed"]

    def test_empty_string(self):
        scenes = [_make_scene("")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert not result["passed"]

    def test_spaces_only(self):
        scenes = [_make_scene("   ")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert not result["passed"]


class TestShortScriptWarning:
    """짧은 스크립트를 warning으로 잡는다."""

    def test_very_short(self):
        scenes = [_make_scene("안녕")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert result["passed"]  # warning이지 error가 아님
        assert any("너무 짧음" in w for w in result["warnings"])

    def test_ok_length(self):
        scenes = [_make_scene("오늘 하루도 정말 힘들었다.")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert result["passed"]
        assert not any("너무 짧음" in w for w in result["warnings"])


class TestMixedScenesDetection:
    """정상 + 빈 씬이 섞여 있을 때 빈 씬만 에러로 잡는다."""

    def test_mixed(self):
        scripts = [
            "오늘 회사에서 큰일이 있었어.",
            "...",
            "팀장님이 나한테 그러더라.",
            "... ...",
            "진짜 화가 났지만 참았어.",
        ]
        result = _validate_scenes(_make_scenes(scripts), 10, "Korean", "Monologue")
        assert not result["passed"]
        empty_errors = [e for e in result["errors"] if "빈 스크립트" in e]
        assert len(empty_errors) == 2

    def test_all_valid(self):
        scripts = [
            "오늘 회사에서 큰일이 있었어.",
            "팀장님이 나한테 그러더라.",
            "진짜 화가 났지만 참았어.",
        ]
        result = _validate_scenes(_make_scenes(scripts), 5, "Korean", "Monologue")
        assert result["passed"]


class TestNarratorFallbackPattern:
    """내레이션으로 대체된 패턴은 정상 통과."""

    def test_narrator_description(self):
        scenes = [_make_scene("그녀는 아무 말도 하지 못했다.", speaker="Narrator")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert result["passed"]

    def test_interjection_ok(self):
        scenes = [_make_scene("아... 진짜 이런 건가.")]
        result = _validate_scenes(scenes, 2, "Korean", "Monologue")
        assert result["passed"]
