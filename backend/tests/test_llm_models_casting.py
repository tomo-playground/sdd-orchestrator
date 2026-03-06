"""Phase 20-A: CastingRecommendation Pydantic 모델 단위 테스트."""

from __future__ import annotations

from services.agent.llm_models import CastingRecommendation, DirectorPlanOutput


class TestCastingRecommendation:
    def test_valid_monologue(self):
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 1,
                "character_a_name": "미도리야",
                "structure": "monologue",
                "reasoning": "1인 독백에 적합",
            }
        )
        assert m.character_a_id == 1
        assert m.structure == "monologue"

    def test_valid_dialogue_two_chars(self):
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 1,
                "character_a_name": "A",
                "character_b_id": 2,
                "character_b_name": "B",
                "structure": "dialogue",
                "reasoning": "대화 구조",
            }
        )
        assert m.character_b_id == 2

    def test_dialogue_missing_char_b_degrades_to_monologue(self):
        """dialogue + character_b 없음 → monologue로 강등 (에러 아님)."""
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 1,
                "character_a_name": "A",
                "structure": "dialogue",
            }
        )
        assert m.structure == "monologue"
        assert m.character_b_id is None

    def test_narrated_dialogue_missing_char_b_degrades_to_monologue(self):
        """narrated_dialogue + character_b 없음 → monologue로 강등."""
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 1,
                "character_a_name": "A",
                "structure": "narrated_dialogue",
            }
        )
        assert m.structure == "monologue"

    def test_duplicate_ids_degrades(self):
        """중복 ID → character_b 제거 + monologue 강등."""
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 1,
                "character_a_name": "A",
                "character_b_id": 1,
                "character_b_name": "A",
                "structure": "dialogue",
            }
        )
        assert m.character_b_id is None
        assert m.character_b_name == ""
        assert m.structure == "monologue"

    def test_all_none_defaults(self):
        m = CastingRecommendation.model_validate({})
        assert m.character_a_id is None
        assert m.structure is None
        assert m.reasoning == ""

    def test_confession_single_char_ok(self):
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 5,
                "character_a_name": "고백자",
                "structure": "confession",
            }
        )
        assert m.structure == "confession"

    def test_dialogue_no_char_id_ok(self):
        """character_a_id가 없으면 2인 구조 검증 스킵."""
        m = CastingRecommendation.model_validate(
            {
                "structure": "dialogue",
            }
        )
        assert m.structure == "dialogue"

    def test_none_coercion(self):
        """Gemini가 null 반환 시 빈 문자열로 변환."""
        m = CastingRecommendation.model_validate(
            {
                "character_a_id": 1,
                "character_a_name": None,
                "character_b_name": None,
                "reasoning": None,
            }
        )
        assert m.character_a_name == ""
        assert m.character_b_name == ""
        assert m.reasoning == ""


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
                    "character_a_id": 1,
                    "character_a_name": "주인공",
                    "structure": "monologue",
                    "reasoning": "적합",
                },
            }
        )
        assert m.casting is not None
        assert m.casting.character_a_id == 1
