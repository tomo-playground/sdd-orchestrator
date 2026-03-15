"""Phase 33 Hybrid Match Rate 관련 단위 테스트.

coverage:
- classify_prompt_tokens() — token routing (wd14/gemini/skipped)
- apply_gemini_evaluation() — 비동기 Gemini 평가 + 결합 match_rate
- _update_db_match_rate() — DB 업데이트 경로
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
            _make_cache({
                "blue_hair": "hair_color",       # WD14
                "cowboy_shot": "camera",          # Gemini
                "masterpiece": "quality",         # Skipped
            }),
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
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=gemini_results),
        ), patch("services.validation._update_db_match_rate") as mock_update:
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
        with patch(
            "services.validation.evaluate_tags_with_gemini",
            new=AsyncMock(return_value=gemini_results),
        ), patch("services.validation._update_db_match_rate") as mock_update:
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
            {"tag": "tag_a", "present": True, "confidence": 0.8},   # counted
            {"tag": "tag_b", "present": True, "confidence": 0.3},   # not counted (low conf)
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
