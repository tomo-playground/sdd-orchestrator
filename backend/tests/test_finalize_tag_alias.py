"""Tests for _apply_tag_aliases — split 동작, 단일 치환, 제거, 통합."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from services.agent.nodes.finalize import _apply_tag_aliases


def _mock_cache(mapping: dict[str, str | None]):
    """TagAliasCache를 mock하여 주어진 mapping으로 replacement를 반환한다."""

    class FakeCache:
        _initialized = True

        @classmethod
        def get_replacement(cls, tag: str) -> str | None | Any:
            normalized = tag.lower().strip()
            if normalized in mapping:
                return mapping[normalized]
            return ...

    return patch(
        "services.keywords.db_cache.TagAliasCache",
        FakeCache,
    )


class TestApplyTagAliasesSplit:
    """comma-separated target이 여러 토큰으로 분리되는지 검증."""

    def test_compound_pose_splits_into_two(self):
        scenes = [{"image_prompt": "1girl, standing_arms_crossed, smile"}]
        with _mock_cache({"standing_arms_crossed": "standing, crossed_arms"}):
            _apply_tag_aliases(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "standing" in tokens
        assert "crossed_arms" in tokens
        assert "standing_arms_crossed" not in tokens

    def test_triple_split(self):
        scenes = [{"image_prompt": "daylight, 1girl"}]
        with _mock_cache({"daylight": "day, sunlight"}):
            _apply_tag_aliases(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "day" in tokens
        assert "sunlight" in tokens


class TestApplyTagAliasesSingle:
    """단일 치환 (comma 없는 target)."""

    def test_sly_smile_to_smirk(self):
        scenes = [{"image_prompt": "1girl, sly_smile, brown_hair"}]
        with _mock_cache({"sly_smile": "smirk"}):
            _apply_tag_aliases(scenes)
        assert "smirk" in scenes[0]["image_prompt"]
        assert "sly_smile" not in scenes[0]["image_prompt"]


class TestApplyTagAliasesRemoval:
    """target=None일 때 태그 제거."""

    def test_bishoujo_removed(self):
        scenes = [{"image_prompt": "bishoujo, 1girl, smile"}]
        with _mock_cache({"bishoujo": None}):
            _apply_tag_aliases(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert "bishoujo" not in tokens
        assert "1girl" in tokens


class TestApplyTagAliasesIntegration:
    """복수 alias가 혼합된 통합 시나리오."""

    def test_mixed_replace_split_remove(self):
        """female, standing_arms_crossed, happy_smile, daylight → 변환 확인."""
        mapping = {
            "female": "1girl",
            "standing_arms_crossed": "standing, crossed_arms",
            "happy_smile": "smile, happy",
            "daylight": "day, sunlight",
        }
        scenes = [{"image_prompt": "female, standing_arms_crossed, happy_smile, daylight"}]
        with _mock_cache(mapping):
            _apply_tag_aliases(scenes)
        tokens = [t.strip() for t in scenes[0]["image_prompt"].split(",")]
        assert tokens == ["1girl", "standing", "crossed_arms", "smile", "happy", "day", "sunlight"]


class TestApplyTagAliasesCompat:
    """기존 alias (comma 없는 target)가 정상 동작하는지 확인."""

    def test_medium_shot_to_cowboy_shot(self):
        scenes = [{"image_prompt": "1girl, medium_shot, smile"}]
        with _mock_cache({"medium_shot": "cowboy_shot"}):
            _apply_tag_aliases(scenes)
        assert "cowboy_shot" in scenes[0]["image_prompt"]
        assert "medium_shot" not in scenes[0]["image_prompt"]

    def test_no_alias_passthrough(self):
        scenes = [{"image_prompt": "1girl, brown_hair, smile"}]
        with _mock_cache({}):
            _apply_tag_aliases(scenes)
        assert scenes[0]["image_prompt"] == "1girl, brown_hair, smile"

    def test_empty_prompt_skipped(self):
        scenes = [{"image_prompt": ""}]
        with _mock_cache({"female": "1girl"}):
            _apply_tag_aliases(scenes)
        assert scenes[0]["image_prompt"] == ""

    def test_missing_prompt_skipped(self):
        scenes = [{"speaker": "Narrator"}]
        with _mock_cache({"female": "1girl"}):
            _apply_tag_aliases(scenes)
        assert "image_prompt" not in scenes[0]


class TestApplyTagAliasesIdempotent:
    """_apply_tag_aliases 멱등성 검증 — 2회 연속 적용 시 결과가 동일해야 한다."""

    def test_alias_application_is_idempotent(self):
        """치환 후 재적용해도 결과가 변하지 않아야 한다."""
        mapping = {
            "female": "1girl",
            "standing_arms_crossed": "standing, crossed_arms",
            "daylight": "day, sunlight",
        }
        scenes = [{"image_prompt": "female, standing_arms_crossed, daylight"}]
        with _mock_cache(mapping):
            _apply_tag_aliases(scenes)
        first_result = scenes[0]["image_prompt"]

        with _mock_cache(mapping):
            _apply_tag_aliases(scenes)
        second_result = scenes[0]["image_prompt"]

        assert first_result == second_result

    def test_removal_is_idempotent(self):
        """태그 제거 후 재적용해도 결과가 변하지 않아야 한다."""
        mapping = {"bishoujo": None}
        scenes = [{"image_prompt": "bishoujo, 1girl, smile"}]
        with _mock_cache(mapping):
            _apply_tag_aliases(scenes)
        first_result = scenes[0]["image_prompt"]

        with _mock_cache(mapping):
            _apply_tag_aliases(scenes)
        second_result = scenes[0]["image_prompt"]

        assert first_result == second_result
        assert "bishoujo" not in second_result

    def test_no_alias_passthrough_is_idempotent(self):
        """alias가 없는 프롬프트는 항상 변하지 않아야 한다."""
        scenes = [{"image_prompt": "1girl, brown_hair, smile"}]
        with _mock_cache({}):
            _apply_tag_aliases(scenes)
        first_result = scenes[0]["image_prompt"]

        with _mock_cache({}):
            _apply_tag_aliases(scenes)
        second_result = scenes[0]["image_prompt"]

        assert first_result == second_result == "1girl, brown_hair, smile"
