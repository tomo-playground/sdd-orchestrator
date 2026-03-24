"""Tests for _prompt_conflict_resolver — Finalize 노드 프롬프트 충돌 감지/제거."""

from unittest.mock import patch

from services.agent.nodes._prompt_conflict_resolver import (
    _resolve_positive_internal_conflicts,
    _resolve_positive_negative_conflicts,
    resolve_prompt_conflicts,
)


class _FakeRuleCache:
    """TagRuleCache mock — 테스트용 충돌 규칙."""

    _initialized = True
    _pairs = {
        ("sitting", "standing"),
        ("1girl", "1boy"),
        ("crying", "laughing"),
        ("looking_up", "looking_away"),
    }

    @classmethod
    def is_conflicting(cls, tag1: str, tag2: str) -> bool:
        t1, t2 = tag1.lower(), tag2.lower()
        return (t1, t2) in cls._pairs or (t2, t1) in cls._pairs


def _scenes(prompts: list[str], negatives: list[str] | None = None) -> list[dict]:
    """헬퍼 — 간단한 씬 리스트 생성."""
    scenes = [{"image_prompt": p} for p in prompts]
    if negatives:
        for s, n in zip(scenes, negatives):
            s["negative_prompt"] = n
    return scenes


class TestPositiveInternalConflicts:
    """positive 내부 상호배타 태그 제거."""

    def test_removes_later_conflicting_tag(self):
        scenes = _scenes(["1girl, smile, sitting, standing, blue_hair"])
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            _resolve_positive_internal_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "sitting" in tokens
        assert "standing" not in tokens

    def test_no_conflict_no_change(self):
        original = "1girl, smile, blue_hair, indoors"
        scenes = _scenes([original])
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            _resolve_positive_internal_conflicts(scenes)
        assert scenes[0]["image_prompt"] == original

    def test_preserves_lora_tags(self):
        scenes = _scenes(["<lora:style:0.8>, 1girl, smile"])
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            _resolve_positive_internal_conflicts(scenes)
        assert "<lora:style:0.8>" in scenes[0]["image_prompt"]

    def test_multiple_conflicts(self):
        scenes = _scenes(["1girl, 1boy, sitting, standing"])
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            _resolve_positive_internal_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "1girl" in tokens
        assert "1boy" not in tokens
        assert "sitting" in tokens
        assert "standing" not in tokens

    def test_gaze_conflict(self):
        scenes = _scenes(["1girl, looking_up, looking_away"])
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            _resolve_positive_internal_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "looking_up" in tokens
        assert "looking_away" not in tokens


class TestPositiveNegativeConflicts:
    """positive↔negative 교차 태그 제거."""

    def test_removes_overlapping_tag_from_positive(self):
        scenes = _scenes(
            ["1girl, smile, outdoors"],
            ["lowres, outdoors, blurry"],
        )
        _resolve_positive_negative_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "outdoors" not in tokens
        assert "1girl" in tokens
        assert "smile" in tokens

    def test_weighted_tag_matches_plain(self):
        scenes = _scenes(
            ["1girl, (smile:1.2), blue_hair"],
            ["smile, blurry"],
        )
        _resolve_positive_negative_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert all("smile" not in t for t in tokens)

    def test_no_overlap_no_change(self):
        original = "1girl, smile, blue_hair"
        scenes = _scenes([original], ["lowres, blurry"])
        _resolve_positive_negative_conflicts(scenes)
        assert scenes[0]["image_prompt"] == original

    def test_empty_negative_skips(self):
        original = "1girl, smile"
        scenes = _scenes([original], [""])
        _resolve_positive_negative_conflicts(scenes)
        assert scenes[0]["image_prompt"] == original

    def test_lora_preserved_even_if_in_negative(self):
        scenes = _scenes(
            ["<lora:style:0.8>, 1girl"],
            ["<lora:style:0.8>"],
        )
        _resolve_positive_negative_conflicts(scenes)
        assert "<lora:style:0.8>" in scenes[0]["image_prompt"]


class TestResolvePromptConflictsIntegration:
    """resolve_prompt_conflicts 통합 테스트."""

    def test_both_checks_applied(self):
        scenes = [
            {
                "image_prompt": "1girl, sitting, standing, outdoors",
                "negative_prompt": "lowres, outdoors, blurry",
            }
        ]
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            resolve_prompt_conflicts(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "standing" not in tokens  # internal conflict
        assert "outdoors" not in tokens  # cross conflict
        assert "1girl" in tokens
        assert "sitting" in tokens

    def test_empty_prompt_scene(self):
        scenes = [{"image_prompt": ""}]
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            resolve_prompt_conflicts(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_no_image_prompt_key(self):
        scenes = [{"speaker": "narrator"}]
        with patch(
            "services.keywords.db_cache.TagRuleCache",
            _FakeRuleCache,
        ):
            resolve_prompt_conflicts(scenes)
        assert "image_prompt" not in scenes[0]
