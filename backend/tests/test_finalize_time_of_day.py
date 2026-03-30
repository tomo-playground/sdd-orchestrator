"""Finalize 노드의 time_of_day 검증 로직 테스트 (SP-117)."""

from __future__ import annotations

from config import DEFAULT_TIME_OF_DAY_TAG
from services.agent.nodes.finalize import _validate_context_tag_values
from services.keywords.patterns import CATEGORY_PATTERNS


def _make_scenes(time_of_day_val: object) -> list[dict]:
    """time_of_day 값만 포함하는 최소 scenes 리스트를 생성."""
    return [{"context_tags": {"time_of_day": time_of_day_val}}]


class TestFinalizeTimeOfDay:
    """_validate_context_tag_values의 time_of_day 검증 블록 테스트."""

    def test_valid_value_passes(self):
        """유효값 'night'는 그대로 통과."""
        scenes = _make_scenes("night")
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] == "night"

    def test_valid_values_all_pass(self):
        """모든 유효값 통과 (SSOT: CATEGORY_PATTERNS)."""
        for val in CATEGORY_PATTERNS["time_of_day"]:
            scenes = _make_scenes(val)
            _validate_context_tag_values(scenes)
            assert scenes[0]["context_tags"]["time_of_day"] == val, f"'{val}' should pass"

    def test_list_normalization(self):
        """리스트 ['sunset'] → 'sunset'으로 정규화."""
        scenes = _make_scenes(["sunset"])
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] == "sunset"

    def test_empty_list_unchanged(self):
        """빈 리스트 [] → _coerce_str 빈 문자열 → falsy이므로 원값 유지."""
        scenes = _make_scenes([])
        _validate_context_tag_values(scenes)
        # Composition 레이어의 _inject_default_time_if_needed가 안전망 역할
        assert scenes[0]["context_tags"]["time_of_day"] == []

    def test_non_standard_value_fallback(self):
        """비표준값 'afternoon_light' → fallback 'day'."""
        scenes = _make_scenes("afternoon_light")
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] == DEFAULT_TIME_OF_DAY_TAG

    def test_space_to_underscore(self):
        """공백 'golden hour' → 'golden_hour' 정규화."""
        scenes = _make_scenes("golden hour")
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] == "golden_hour"

    def test_uppercase_normalized(self):
        """대문자 'SUNSET' → 'sunset' 소문자 정규화."""
        scenes = _make_scenes("SUNSET")
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] == "sunset"

    def test_no_context_tags_skipped(self):
        """context_tags 없는 씬은 스킵."""
        scenes = [{"speaker": "speaker_1"}]
        _validate_context_tag_values(scenes)
        assert "context_tags" not in scenes[0]

    def test_no_time_of_day_skipped(self):
        """time_of_day 없는 context_tags는 스킵."""
        scenes = [{"context_tags": {"emotion": "happy"}}]
        _validate_context_tag_values(scenes)
        assert "time_of_day" not in scenes[0]["context_tags"]

    def test_none_value_skipped(self):
        """None 값은 falsy이므로 스킵."""
        scenes = _make_scenes(None)
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] is None

    def test_multi_scene_independent(self):
        """여러 씬의 time_of_day는 독립적으로 검증."""
        scenes = [
            {"context_tags": {"time_of_day": "night"}},
            {"context_tags": {"time_of_day": "invalid_time"}},
            {"context_tags": {"time_of_day": "sunset"}},
        ]
        _validate_context_tag_values(scenes)
        assert scenes[0]["context_tags"]["time_of_day"] == "night"
        assert scenes[1]["context_tags"]["time_of_day"] == DEFAULT_TIME_OF_DAY_TAG
        assert scenes[2]["context_tags"]["time_of_day"] == "sunset"
