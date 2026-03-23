"""Phase 37: 8차원 NarrativeScore 테스트."""


class TestNarrativeWeights:
    """_NARRATIVE_WEIGHTS 가중치 검증."""

    def test_weights_sum_to_one(self):
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        total = sum(_NARRATIVE_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"가중치 합계 {total} != 1.0"

    def test_weights_all_positive(self):
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        for key, val in _NARRATIVE_WEIGHTS.items():
            assert val > 0, f"{key} 가중치가 0 이하: {val}"

    def test_weights_has_9_dimensions(self):
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        assert len(_NARRATIVE_WEIGHTS) == 9, f"차원 수 {len(_NARRATIVE_WEIGHTS)} != 9"

    def test_new_dimensions_exist(self):
        from services.agent.nodes.review import _NARRATIVE_WEIGHTS

        for dim in ("spoken_naturalness", "retention_flow", "pacing_rhythm"):
            assert dim in _NARRATIVE_WEIGHTS, f"{dim} 누락"


class TestNarrativeScoreOutput:
    """NarrativeScoreOutput 신규 필드 파싱 검증."""

    def test_parses_8_dimensions(self):
        from services.agent.llm_models import NarrativeScoreOutput

        data = {
            "hook": 0.8,
            "emotional_arc": 0.7,
            "twist_payoff": 0.6,
            "speaker_tone": 0.9,
            "script_image_sync": 0.7,
            "spoken_naturalness": 0.4,
            "retention_flow": 0.5,
            "pacing_rhythm": 0.3,
            "feedback": "테스트 피드백",
        }
        parsed = NarrativeScoreOutput.model_validate(data)
        assert parsed.spoken_naturalness == 0.4
        assert parsed.retention_flow == 0.5
        assert parsed.pacing_rhythm == 0.3

    def test_defaults_to_zero(self):
        from services.agent.llm_models import NarrativeScoreOutput

        parsed = NarrativeScoreOutput.model_validate({})
        assert parsed.spoken_naturalness == 0.0
        assert parsed.retention_flow == 0.0
        assert parsed.pacing_rhythm == 0.0

    def test_clamps_out_of_range(self):
        from services.agent.llm_models import NarrativeScoreOutput

        parsed = NarrativeScoreOutput.model_validate(
            {
                "spoken_naturalness": 1.5,
                "retention_flow": -0.3,
                "pacing_rhythm": 2.0,
            }
        )
        assert parsed.spoken_naturalness == 1.0
        assert parsed.retention_flow == 0.0
        assert parsed.pacing_rhythm == 1.0

    def test_backward_compat_5dim(self):
        """기존 5차원만 있는 응답도 정상 파싱."""
        from services.agent.llm_models import NarrativeScoreOutput

        data = {
            "hook": 0.8,
            "emotional_arc": 0.7,
            "twist_payoff": 0.6,
            "speaker_tone": 0.9,
            "script_image_sync": 0.7,
            "feedback": "기존 형식",
        }
        parsed = NarrativeScoreOutput.model_validate(data)
        assert parsed.hook == 0.8
        assert parsed.spoken_naturalness == 0.0  # default


class TestBuildNarrativeScore:
    """_build_narrative_score() 8차원 overall 계산 검증."""

    def test_overall_calculation(self):
        from services.agent.llm_models import NarrativeScoreOutput
        from services.agent.nodes.review import _build_narrative_score

        parsed = NarrativeScoreOutput.model_validate(
            {
                "hook": 1.0,
                "emotional_arc": 1.0,
                "twist_payoff": 1.0,
                "speaker_tone": 1.0,
                "script_image_sync": 1.0,
                "spoken_naturalness": 1.0,
                "retention_flow": 1.0,
                "pacing_rhythm": 1.0,
                "situational_specificity": 1.0,
                "feedback": "",
            }
        )
        score = _build_narrative_score(parsed)
        assert abs(score["overall"] - 1.0) < 1e-9

    def test_zero_scores(self):
        from services.agent.llm_models import NarrativeScoreOutput
        from services.agent.nodes.review import _build_narrative_score

        parsed = NarrativeScoreOutput.model_validate({})
        score = _build_narrative_score(parsed)
        assert score["overall"] == 0.0

    def test_includes_new_dimensions(self):
        from services.agent.llm_models import NarrativeScoreOutput
        from services.agent.nodes.review import _build_narrative_score

        parsed = NarrativeScoreOutput.model_validate(
            {
                "spoken_naturalness": 0.8,
                "retention_flow": 0.6,
                "pacing_rhythm": 0.7,
            }
        )
        score = _build_narrative_score(parsed)
        assert "spoken_naturalness" in score
        assert "retention_flow" in score
        assert "pacing_rhythm" in score
        assert score["overall"] > 0


class TestBuildFeedback:
    """_build_feedback() 숏폼 품질 피드백 검증."""

    def _make_state(self, **ns_overrides):
        ns = {
            "hook": 0.8,
            "emotional_arc": 0.7,
            "twist_payoff": 0.6,
            "speaker_tone": 0.9,
            "script_image_sync": 0.7,
            "spoken_naturalness": 0.8,
            "retention_flow": 0.7,
            "pacing_rhythm": 0.8,
            "overall": 0.75,
            "feedback": "테스트",
            **ns_overrides,
        }
        return {"review_result": {"narrative_score": ns}}

    def test_no_feedback_when_scores_high(self):
        from services.agent.nodes.revise import _build_feedback

        state = self._make_state()
        result = _build_feedback(state)
        assert "숏폼 품질 개선" not in result

    def test_spoken_naturalness_feedback(self):
        from services.agent.nodes.revise import _build_feedback

        state = self._make_state(spoken_naturalness=0.3)
        result = _build_feedback(state)
        assert "TTS 낭독 자연스러움 부족" in result

    def test_retention_flow_feedback(self):
        from services.agent.nodes.revise import _build_feedback

        state = self._make_state(retention_flow=0.2)
        result = _build_feedback(state)
        assert "씬 간 호기심 연결 약함" in result

    def test_pacing_rhythm_feedback(self):
        from services.agent.nodes.revise import _build_feedback

        state = self._make_state(pacing_rhythm=0.1)
        result = _build_feedback(state)
        assert "템포/리듬 단조로움" in result

    def test_multiple_low_dimensions(self):
        from services.agent.nodes.revise import _build_feedback

        state = self._make_state(spoken_naturalness=0.2, retention_flow=0.3, pacing_rhythm=0.1)
        result = _build_feedback(state)
        assert "TTS 낭독" in result
        assert "호기심 연결" in result
        assert "템포/리듬" in result
