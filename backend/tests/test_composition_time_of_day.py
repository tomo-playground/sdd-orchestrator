"""Composition 레이어의 time_of_day 기본값 주입 테스트 (SP-117)."""

from __future__ import annotations

from config import DEFAULT_TIME_OF_DAY_TAG
from services.keywords.patterns import CATEGORY_PATTERNS
from services.prompt.composition import LAYER_ENVIRONMENT, PromptBuilder


def _make_layers(env_tags: list[str]) -> list[list[str]]:
    """LAYER_ENVIRONMENT 위치에 env_tags를 넣은 12-레이어 리스트 생성."""
    layers: list[list[str]] = [[] for _ in range(12)]
    layers[LAYER_ENVIRONMENT] = list(env_tags)
    return layers


class TestInjectDefaultTimeIfNeeded:
    """PromptBuilder._inject_default_time_if_needed 테스트."""

    def test_no_time_tag_injects_day(self):
        """환경 레이어에 time 태그 없음 → 'day' 주입."""
        layers = _make_layers(["indoor", "office"])
        PromptBuilder._inject_default_time_if_needed(layers)
        assert DEFAULT_TIME_OF_DAY_TAG in layers[LAYER_ENVIRONMENT]

    def test_time_tag_present_no_injection(self):
        """환경 레이어에 'night' 존재 → 주입 안 함."""
        layers = _make_layers(["indoor", "night"])
        original_len = len(layers[LAYER_ENVIRONMENT])
        PromptBuilder._inject_default_time_if_needed(layers)
        assert len(layers[LAYER_ENVIRONMENT]) == original_len
        assert DEFAULT_TIME_OF_DAY_TAG not in layers[LAYER_ENVIRONMENT]

    def test_weighted_time_tag_no_injection(self):
        """가중치 time 태그 '(sunset:1.2)' → _dedup_key가 'sunset' 인식 → 주입 안 함."""
        layers = _make_layers(["(sunset:1.2)"])
        original_len = len(layers[LAYER_ENVIRONMENT])
        PromptBuilder._inject_default_time_if_needed(layers)
        assert len(layers[LAYER_ENVIRONMENT]) == original_len

    def test_all_valid_time_tags_recognized(self):
        """모든 유효 time 태그 각각 존재 시 주입 안 함 (SSOT: CATEGORY_PATTERNS)."""
        for tag in CATEGORY_PATTERNS["time_of_day"]:
            layers = _make_layers([tag])
            PromptBuilder._inject_default_time_if_needed(layers)
            assert DEFAULT_TIME_OF_DAY_TAG not in layers[LAYER_ENVIRONMENT] or tag == DEFAULT_TIME_OF_DAY_TAG, (
                f"'{tag}' should prevent injection"
            )

    def test_empty_env_injects_day(self):
        """환경 레이어가 비어 있으면 'day' 주입."""
        layers = _make_layers([])
        PromptBuilder._inject_default_time_if_needed(layers)
        assert layers[LAYER_ENVIRONMENT] == [DEFAULT_TIME_OF_DAY_TAG]

    def test_only_non_time_tags_injects(self):
        """non-time 태그만 있으면 'day' 주입."""
        layers = _make_layers(["cafe", "indoors", "wooden_floor"])
        PromptBuilder._inject_default_time_if_needed(layers)
        assert DEFAULT_TIME_OF_DAY_TAG in layers[LAYER_ENVIRONMENT]
        assert len(layers[LAYER_ENVIRONMENT]) == 4  # 3 original + day
