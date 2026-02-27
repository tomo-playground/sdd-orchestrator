"""Phase 20-A: CastingRecommendation Pydantic 모델 단위 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.agent.llm_models import CastingRecommendation, DirectorPlanOutput


class TestCastingRecommendation:
    def test_valid_monologue(self):
        m = CastingRecommendation.model_validate(
            {
                "character_id": 1,
                "character_name": "미도리야",
                "structure": "monologue",
                "reasoning": "1인 독백에 적합",
            }
        )
        assert m.character_id == 1
        assert m.structure == "monologue"

    def test_valid_dialogue_two_chars(self):
        m = CastingRecommendation.model_validate(
            {
                "character_id": 1,
                "character_name": "A",
                "character_b_id": 2,
                "character_b_name": "B",
                "structure": "dialogue",
                "reasoning": "대화 구조",
            }
        )
        assert m.character_b_id == 2

    def test_dialogue_missing_char_b_fails(self):
        with pytest.raises(ValidationError, match="character_b_id"):
            CastingRecommendation.model_validate(
                {
                    "character_id": 1,
                    "character_name": "A",
                    "structure": "dialogue",
                }
            )

    def test_narrated_dialogue_missing_char_b_fails(self):
        with pytest.raises(ValidationError, match="character_b_id"):
            CastingRecommendation.model_validate(
                {
                    "character_id": 1,
                    "character_name": "A",
                    "structure": "narrated_dialogue",
                }
            )

    def test_duplicate_ids_fails(self):
        with pytest.raises(ValidationError, match="달라야"):
            CastingRecommendation.model_validate(
                {
                    "character_id": 1,
                    "character_name": "A",
                    "character_b_id": 1,
                    "character_b_name": "A",
                    "structure": "dialogue",
                }
            )

    def test_all_none_defaults(self):
        m = CastingRecommendation.model_validate({})
        assert m.character_id is None
        assert m.structure is None
        assert m.reasoning == ""

    def test_confession_single_char_ok(self):
        m = CastingRecommendation.model_validate(
            {
                "character_id": 5,
                "character_name": "고백자",
                "structure": "confession",
            }
        )
        assert m.structure == "confession"

    def test_dialogue_no_char_id_ok(self):
        """character_id가 없으면 2인 구조 검증 스킵."""
        m = CastingRecommendation.model_validate(
            {
                "structure": "dialogue",
            }
        )
        assert m.structure == "dialogue"


class TestDirectorPlanOutputWithCasting:
    def test_casting_none_default(self):
        m = DirectorPlanOutput.model_validate(
            {
                "creative_goal": "목표",
                "target_emotion": "감정",
                "quality_criteria": ["기준"],
            }
        )
        assert m.casting is None

    def test_casting_included(self):
        m = DirectorPlanOutput.model_validate(
            {
                "creative_goal": "목표",
                "target_emotion": "감정",
                "quality_criteria": ["기준"],
                "casting": {
                    "character_id": 1,
                    "character_name": "주인공",
                    "structure": "monologue",
                    "reasoning": "적합",
                },
            }
        )
        assert m.casting is not None
        assert m.casting.character_id == 1
