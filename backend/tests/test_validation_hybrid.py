"""Phase 33 Hybrid Match Rate 단위 테스트.

coverage:
- classify_prompt_tokens() — token routing (wd14/gemini/skipped)
- compare_prompt_to_tags() — only_tokens 파라미터
- _parse_gemini_json_array() — Gemini 응답 파싱
- apply_gemini_evaluation() — 비동기 Gemini 평가 + 결합 match_rate
- _update_db_match_rate() — DB 업데이트 경로 + evaluation_details
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.validation import (
    _is_skippable_tag,
    _update_db_match_rate,
    apply_gemini_evaluation,
    classify_prompt_tokens,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cache(mapping: dict[str, str]):
    """Return a fake TagCategoryCache.get_category callable."""
    return staticmethod(lambda t: mapping.get(t))


# ---------------------------------------------------------------------------
# classify_prompt_tokens
# ---------------------------------------------------------------------------


class TestClassifyPromptTokens:
    """classify_prompt_tokens() 토큰 라우팅 검증."""

    def test_wd14_tokens_routed_correctly(self, monkeypatch):
        """WD14_DETECTABLE_GROUPS 소속 태그는 wd14_tokens에 배치."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({"blue_hair": "hair_color", "smile": "expression"}),
        )
        result = classify_prompt_tokens("blue_hair, smile")
        assert "blue_hair" in result["wd14_tokens"]
        assert "smile" in result["wd14_tokens"]
        assert result["gemini_tokens"] == []
        assert result["skipped_tokens"] == []

    def test_gemini_tokens_routed_correctly(self, monkeypatch):
        """GEMINI_DETECTABLE_GROUPS 소속 태그는 gemini_tokens에 배치."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({"cowboy_shot": "camera", "library": "location_indoor_specific"}),
        )
        result = classify_prompt_tokens("cowboy_shot, library")
        assert "cowboy_shot" in result["gemini_tokens"]
        assert "library" in result["gemini_tokens"]
        assert result["wd14_tokens"] == []

    def test_skippable_tags_routed_to_skipped(self, monkeypatch):
        """SKIPPABLE_GROUPS 소속 태그는 skipped_tokens에 배치."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({"masterpiece": "quality", "best_quality": "quality"}),
        )
        result = classify_prompt_tokens("masterpiece, best_quality")
        assert result["skipped_tokens"] == ["masterpiece", "best_quality"]
        assert result["wd14_tokens"] == []
        assert result["gemini_tokens"] == []

    def test_unknown_group_goes_to_skipped(self, monkeypatch):
        """DB에 등록되지 않은 태그(group=None)는 skipped_tokens에 배치."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({}),  # 모두 None 반환
        )
        result = classify_prompt_tokens("some_unknown_tag")
        assert "some_unknown_tag" in result["skipped_tokens"]

    def test_mixed_prompt_routing(self, monkeypatch):
        """혼합 프롬프트에서 세 그룹이 모두 올바르게 분류됨."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache(
                {
                    "blue_hair": "hair_color",  # WD14
                    "cowboy_shot": "camera",  # Gemini
                    "masterpiece": "quality",  # Skipped
                }
            ),
        )
        result = classify_prompt_tokens("blue_hair, cowboy_shot, masterpiece")
        assert result["wd14_tokens"] == ["blue_hair"]
        assert result["gemini_tokens"] == ["cowboy_shot"]
        assert result["skipped_tokens"] == ["masterpiece"]

    def test_empty_prompt_returns_empty_lists(self, monkeypatch):
        """빈 프롬프트는 모두 빈 리스트."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({}),
        )
        result = classify_prompt_tokens("")
        assert result == {"wd14_tokens": [], "gemini_tokens": [], "skipped_tokens": []}


# ---------------------------------------------------------------------------
# _is_skippable_tag
# ---------------------------------------------------------------------------


class TestIsSkippableTag:
    def test_quality_tag_is_skippable(self, monkeypatch):
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({"masterpiece": "quality"}),
        )
        assert _is_skippable_tag("masterpiece") is True

    def test_wd14_tag_is_not_skippable(self, monkeypatch):
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({"blue_hair": "hair_color"}),
        )
        assert _is_skippable_tag("blue_hair") is False

    def test_unregistered_tag_is_skippable(self, monkeypatch):
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({}),
        )
        assert _is_skippable_tag("totally_unknown") is True


# ---------------------------------------------------------------------------
# apply_gemini_evaluation
# ---------------------------------------------------------------------------


class TestApplyGeminiEvaluation:
    """apply_gemini_evaluation() 비동기 배경 태스크 검증."""

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_tokens(self):
        result = await apply_gemini_evaluation(
            storyboard_id=1,
            scene_id=1,
            image_b64="aaa",
            gemini_tokens=[],
            wd14_matched=5,
            wd14_total=8,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_gemini_returns_empty(self):
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=[]),
        ):
            result = await apply_gemini_evaluation(
                storyboard_id=1,
                scene_id=1,
                image_b64="aaa",
                gemini_tokens=["cowboy_shot"],
                wd14_matched=5,
                wd14_total=8,
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_combined_match_rate_calculation(self):
        """WD14 + Gemini 결합 match_rate가 올바르게 계산됨."""
        gemini_results = [
            {"tag": "cowboy_shot", "present": True, "confidence": 0.9},
            {"tag": "library", "present": False, "confidence": 0.2},
        ]
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=gemini_results),
        ):
            result = await apply_gemini_evaluation(
                storyboard_id=1,
                scene_id=2,
                image_b64="aaa",
                gemini_tokens=["cowboy_shot", "library"],
                wd14_matched=4,
                wd14_total=6,
                db_factory=None,
            )

        # WD14: 4/6, Gemini: 1/2 → combined: 5/8 = 0.625
        assert result is not None
        assert result["gemini_matched"] == 1
        assert result["gemini_total"] == 2
        assert abs(result["combined_match_rate"] - 5 / 8) < 0.001

    @pytest.mark.asyncio
    async def test_db_update_called_when_scene_id_provided(self):
        """scene_id가 있을 때 _update_db_match_rate가 호출됨."""
        gemini_results = [{"tag": "cowboy_shot", "present": True, "confidence": 0.8}]
        with (
            patch(
                "services.validation.evaluate_tags_with_gemini",
                new=AsyncMock(return_value=gemini_results),
            ),
            patch("services.validation._update_db_match_rate") as mock_update,
        ):
            await apply_gemini_evaluation(
                storyboard_id=10,
                scene_id=5,
                image_b64="aaa",
                gemini_tokens=["cowboy_shot"],
                wd14_matched=3,
                wd14_total=4,
                db_factory=MagicMock(),
            )
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["scene_id"] == 5
        assert call_kwargs["storyboard_id"] == 10

    @pytest.mark.asyncio
    async def test_no_db_update_when_scene_id_none(self):
        """scene_id가 None이면 _update_db_match_rate 미호출."""
        gemini_results = [{"tag": "cowboy_shot", "present": True, "confidence": 0.8}]
        with (
            patch(
                "services.validation.evaluate_tags_with_gemini",
                new=AsyncMock(return_value=gemini_results),
            ),
            patch("services.validation._update_db_match_rate") as mock_update,
        ):
            await apply_gemini_evaluation(
                storyboard_id=10,
                scene_id=None,
                image_b64="aaa",
                gemini_tokens=["cowboy_shot"],
                wd14_matched=3,
                wd14_total=4,
                db_factory=MagicMock(),
            )
        mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_confidence_threshold_applied(self):
        """confidence < 0.5 태그는 매치로 카운트되지 않음."""
        gemini_results = [
            {"tag": "tag_a", "present": True, "confidence": 0.8},  # counted
            {"tag": "tag_b", "present": True, "confidence": 0.3},  # not counted (low conf)
            {"tag": "tag_c", "present": False, "confidence": 0.9},  # not counted (not present)
        ]
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=gemini_results),
        ):
            result = await apply_gemini_evaluation(
                storyboard_id=1,
                scene_id=None,
                image_b64="aaa",
                gemini_tokens=["tag_a", "tag_b", "tag_c"],
                wd14_matched=0,
                wd14_total=0,
            )
        assert result["gemini_matched"] == 1
        assert result["gemini_total"] == 3


# ---------------------------------------------------------------------------
# _update_db_match_rate
# ---------------------------------------------------------------------------


def _make_db_factory(mock_db: MagicMock):
    """Create a @contextmanager db_factory that yields mock_db."""

    @contextmanager
    def factory():
        yield mock_db

    return factory


class TestUpdateDbMatchRate:
    def test_commit_called_when_score_found(self):
        """SceneQualityScore 레코드가 있을 때 commit이 호출됨."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = MagicMock()

        _update_db_match_rate(
            scene_id=1,
            storyboard_id=10,
            combined_rate=0.75,
            wd14_matched=3,
            wd14_total=4,
            gemini_matched=2,
            gemini_total=3,
            db_factory=_make_db_factory(mock_db),
        )

        mock_db.commit.assert_called_once()

    def test_no_commit_when_score_not_found(self):
        """SceneQualityScore가 없으면 commit하지 않음."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        _update_db_match_rate(
            scene_id=1,
            storyboard_id=10,
            combined_rate=0.75,
            wd14_matched=3,
            wd14_total=4,
            gemini_matched=2,
            gemini_total=3,
            db_factory=_make_db_factory(mock_db),
        )

        mock_db.commit.assert_not_called()

    def test_evaluation_details_stored(self):
        """evaluation_details JSONB가 올바르게 저장됨."""
        mock_score = MagicMock()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_score

        gemini_tags = [{"tag": "cowboy_shot", "present": True, "confidence": 0.9}]
        _update_db_match_rate(
            scene_id=1,
            storyboard_id=10,
            combined_rate=0.75,
            wd14_matched=3,
            wd14_total=4,
            gemini_matched=1,
            gemini_total=1,
            gemini_details=gemini_tags,
            db_factory=_make_db_factory(mock_db),
        )

        details = mock_score.evaluation_details
        assert details["mode"] == "hybrid"
        assert details["wd14"]["matched"] == 3
        assert details["gemini"]["total"] == 1
        assert details["gemini"]["tags"] == gemini_tags

    def test_exception_does_not_propagate(self):
        """예외 발생 시 함수 외부로 전파되지 않음 (graceful degradation)."""
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("query failed")

        # Should NOT raise
        _update_db_match_rate(
            scene_id=1,
            storyboard_id=10,
            combined_rate=0.75,
            wd14_matched=3,
            wd14_total=4,
            gemini_matched=2,
            gemini_total=3,
            db_factory=_make_db_factory(mock_db),
        )


# ---------------------------------------------------------------------------
# compare_prompt_to_tags — only_tokens
# ---------------------------------------------------------------------------


class TestComparePromptToTagsOnlyTokens:
    """compare_prompt_to_tags의 only_tokens 파라미터 검증."""

    def test_only_tokens_limits_comparison(self, monkeypatch):
        """only_tokens를 전달하면 해당 토큰만 비교."""
        monkeypatch.setattr(
            "services.keywords.db_cache.TagCategoryCache.get_category",
            _make_cache({"blue_hair": "hair_color", "smile": "expression"}),
        )
        monkeypatch.setattr(
            "services.keywords.db_cache.TagAliasCache._cache",
            {},
        )
        monkeypatch.setattr(
            "services.keywords.db_cache.TagAliasCache.get_replacement",
            staticmethod(lambda t: ...),
        )

        from services.validation import compare_prompt_to_tags

        tags = [{"tag": "blue_hair", "score": 0.9, "category": "0"}]
        result = compare_prompt_to_tags("ignored", tags, only_tokens=["blue_hair"])
        assert "blue_hair" in result["matched"]
        assert len(result["matched"]) == 1

    def test_only_tokens_empty_returns_empty(self):
        from services.validation import compare_prompt_to_tags

        result = compare_prompt_to_tags("ignored", [], only_tokens=[])
        assert result["matched"] == []
        assert result["missing"] == []


# ---------------------------------------------------------------------------
# _parse_gemini_json_array
# ---------------------------------------------------------------------------


class TestParseGeminiJsonArray:
    """Gemini JSON 파싱 검증."""

    def test_valid_json_array(self):
        from services.validation_gemini import _parse_gemini_json_array

        text = '[{"tag":"a","present":true,"confidence":0.9}]'
        result = _parse_gemini_json_array(text)
        assert len(result) == 1
        assert result[0]["tag"] == "a"

    def test_markdown_code_fence(self):
        from services.validation_gemini import _parse_gemini_json_array

        text = '```json\n[{"tag":"b","present":false,"confidence":0.1}]\n```'
        result = _parse_gemini_json_array(text)
        assert len(result) == 1
        assert result[0]["present"] is False

    def test_invalid_json_returns_empty(self):
        from services.validation_gemini import _parse_gemini_json_array

        assert _parse_gemini_json_array("not json at all") == []

    def test_dict_instead_of_list_returns_empty(self):
        from services.validation_gemini import _parse_gemini_json_array

        assert _parse_gemini_json_array('{"key": "value"}') == []

    def test_missing_required_fields_filtered(self):
        from services.validation_gemini import _parse_gemini_json_array

        text = '[{"tag":"a","present":true},{"no_tag":true,"present":false}]'
        result = _parse_gemini_json_array(text)
        assert len(result) == 1  # second item filtered (no "tag" key)


# ---------------------------------------------------------------------------
# batch_apply_gemini_evaluation (Phase 33 E-2)
# ---------------------------------------------------------------------------


class TestBatchApplyGeminiEvaluation:
    """batch_apply_gemini_evaluation() 배치 Gemini 평가 검증."""

    @pytest.mark.asyncio
    async def test_empty_items_returns_empty(self):
        """빈 items 리스트 → 빈 결과."""
        from services.validation import batch_apply_gemini_evaluation

        result = await batch_apply_gemini_evaluation(items=[])
        assert result == []

    @pytest.mark.asyncio
    async def test_items_without_gemini_tokens_return_none(self):
        """gemini_tokens가 없는 항목은 None 반환."""
        from services.validation import batch_apply_gemini_evaluation

        items = [
            {"image_b64": "aaa", "gemini_tokens": [], "wd14_matched": 3, "wd14_total": 4},
        ]
        result = await batch_apply_gemini_evaluation(items=items)
        assert result == [None]

    @pytest.mark.asyncio
    async def test_single_scene_evaluated(self):
        """단일 씬 → 1회 Gemini 호출."""
        from services.validation import batch_apply_gemini_evaluation

        gemini_results = [
            {"tag": "cowboy_shot", "present": True, "confidence": 0.8},
        ]
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=gemini_results),
        ) as mock_eval:
            items = [{
                "storyboard_id": 1,
                "scene_id": 10,
                "image_b64": "img1_base64",
                "gemini_tokens": ["cowboy_shot"],
                "wd14_matched": 5,
                "wd14_total": 8,
            }]
            result = await batch_apply_gemini_evaluation(items=items)

        mock_eval.assert_called_once()
        assert result[0]["gemini_matched"] == 1
        assert result[0]["gemini_total"] == 1
        assert abs(result[0]["combined_match_rate"] - 6 / 9) < 0.001

    @pytest.mark.asyncio
    async def test_same_image_deduplication(self):
        """동일 이미지 2씬 → Gemini 1회 호출 (태그 합집합)."""
        from services.validation import batch_apply_gemini_evaluation

        gemini_results = [
            {"tag": "cowboy_shot", "present": True, "confidence": 0.9},
            {"tag": "sunset", "present": True, "confidence": 0.7},
            {"tag": "cloudy_sky", "present": False, "confidence": 0.3},
        ]
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=gemini_results),
        ) as mock_eval:
            items = [
                {
                    "storyboard_id": 1, "scene_id": 10,
                    "image_b64": "same_image",
                    "gemini_tokens": ["cowboy_shot", "sunset"],
                    "wd14_matched": 4, "wd14_total": 5,
                },
                {
                    "storyboard_id": 1, "scene_id": 11,
                    "image_b64": "same_image",
                    "gemini_tokens": ["sunset", "cloudy_sky"],
                    "wd14_matched": 3, "wd14_total": 4,
                },
            ]
            result = await batch_apply_gemini_evaluation(items=items)

        # Only 1 Gemini call despite 2 scenes (same image)
        mock_eval.assert_called_once()
        call_tags = mock_eval.call_args[0][1]
        assert set(call_tags) == {"cowboy_shot", "sunset", "cloudy_sky"}

        # Scene 0: cowboy_shot(matched) + sunset(matched) = 2/2
        assert result[0]["gemini_matched"] == 2
        assert result[0]["gemini_total"] == 2

        # Scene 1: sunset(matched) + cloudy_sky(not present) = 1/2
        assert result[1]["gemini_matched"] == 1
        assert result[1]["gemini_total"] == 2

    @pytest.mark.asyncio
    async def test_different_images_parallel_calls(self):
        """다른 이미지 2씬 → Gemini 2회 호출 (병렬)."""
        from services.validation import batch_apply_gemini_evaluation

        call_count = 0

        async def fake_eval(image_b64, tags):
            nonlocal call_count
            call_count += 1
            return [{"tag": t, "present": True, "confidence": 0.8} for t in tags]

        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=fake_eval,
        ):
            items = [
                {
                    "storyboard_id": 1, "scene_id": 10,
                    "image_b64": "image_A",
                    "gemini_tokens": ["tag_a"],
                    "wd14_matched": 2, "wd14_total": 3,
                },
                {
                    "storyboard_id": 1, "scene_id": 11,
                    "image_b64": "image_B",
                    "gemini_tokens": ["tag_b"],
                    "wd14_matched": 4, "wd14_total": 5,
                },
            ]
            result = await batch_apply_gemini_evaluation(items=items)

        assert call_count == 2
        assert result[0] is not None
        assert result[1] is not None

    @pytest.mark.asyncio
    async def test_db_update_called_for_each_scene(self):
        """각 씬마다 _update_db_match_rate 호출됨."""
        from services.validation import batch_apply_gemini_evaluation

        gemini_results = [{"tag": "tag_a", "present": True, "confidence": 0.8}]
        with (
            patch(
                "services.validation.evaluate_tags_with_gemini",
                new=AsyncMock(return_value=gemini_results),
            ),
            patch("services.validation._update_db_match_rate") as mock_update,
        ):
            items = [
                {
                    "storyboard_id": 1, "scene_id": 10,
                    "image_b64": "img",
                    "gemini_tokens": ["tag_a"],
                    "wd14_matched": 3, "wd14_total": 4,
                },
                {
                    "storyboard_id": 1, "scene_id": 11,
                    "image_b64": "img",
                    "gemini_tokens": ["tag_a"],
                    "wd14_matched": 5, "wd14_total": 6,
                },
            ]
            await batch_apply_gemini_evaluation(items=items, db_factory=MagicMock())

        assert mock_update.call_count == 2
        scene_ids = {c.kwargs["scene_id"] for c in mock_update.call_args_list}
        assert scene_ids == {10, 11}

    @pytest.mark.asyncio
    async def test_gemini_failure_graceful(self):
        """Gemini 실패 시 해당 그룹은 None 반환 (graceful degradation)."""
        from services.validation import batch_apply_gemini_evaluation

        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=[]),
        ):
            items = [{
                "storyboard_id": 1, "scene_id": 10,
                "image_b64": "img",
                "gemini_tokens": ["tag_a"],
                "wd14_matched": 3, "wd14_total": 4,
            }]
            result = await batch_apply_gemini_evaluation(items=items)

        # Empty results → gemini_matched=0, still produces summary
        assert result[0]["gemini_matched"] == 0
        assert result[0]["gemini_total"] == 0
