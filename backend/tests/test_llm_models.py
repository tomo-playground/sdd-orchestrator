"""llm_models.py 단위 테스트 — Pydantic LLM 출력 검증 모델."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.agent.llm_models import (
    DirectorCheckpointOutput,
    DirectorPlanOutput,
    DirectorReActOutput,
    NarrativeScoreOutput,
    WriterPlanOutput,
    validate_with_model,
)

# ── DirectorPlanOutput ──


class TestDirectorPlanOutput:
    def test_valid_full(self):
        data = {
            "creative_goal": "공포 분위기 극대화",
            "target_emotion": "불안",
            "quality_criteria": ["몰입도", "반전"],
            "risk_areas": ["폭력성"],
            "style_direction": "어두운 톤",
        }
        m = DirectorPlanOutput.model_validate(data)
        assert m.creative_goal == "공포 분위기 극대화"
        assert len(m.quality_criteria) == 2

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            DirectorPlanOutput.model_validate({"creative_goal": "x"})

    def test_empty_creative_goal(self):
        with pytest.raises(ValidationError):
            DirectorPlanOutput.model_validate({"creative_goal": "", "target_emotion": "x", "quality_criteria": ["a"]})

    def test_empty_quality_criteria(self):
        with pytest.raises(ValidationError):
            DirectorPlanOutput.model_validate({"creative_goal": "x", "target_emotion": "y", "quality_criteria": []})

    def test_defaults(self):
        m = DirectorPlanOutput.model_validate({"creative_goal": "g", "target_emotion": "e", "quality_criteria": ["c"]})
        assert m.risk_areas == []
        assert m.style_direction == ""


# ── DirectorReActOutput ──


class TestDirectorReActOutput:
    def test_approve_ok(self):
        m = DirectorReActOutput.model_validate({"observe": "관찰", "think": "사고", "act": "approve"})
        assert m.act == "approve"
        assert m.feedback == ""

    def test_revise_with_feedback_ok(self):
        m = DirectorReActOutput.model_validate(
            {"observe": "관찰", "think": "사고", "act": "revise_tts", "feedback": "음성 수정"}
        )
        assert m.act == "revise_tts"

    def test_revise_no_feedback_fail(self):
        with pytest.raises(ValidationError, match="feedback"):
            DirectorReActOutput.model_validate({"observe": "관찰", "think": "사고", "act": "revise_script"})

    def test_approve_with_null_feedback_ok(self):
        """Gemini가 feedback: null을 반환해도 approve는 통과해야 한다."""
        m = DirectorReActOutput.model_validate({"observe": "관찰", "think": "사고", "act": "approve", "feedback": None})
        assert m.feedback == ""

    def test_revise_with_null_feedback_fails(self):
        """feedback: null + revise_* 조합은 ValidationError가 발생해야 한다."""
        with pytest.raises(ValidationError, match="feedback"):
            DirectorReActOutput.model_validate(
                {"observe": "관찰", "think": "사고", "act": "revise_script", "feedback": None}
            )

    def test_invalid_act(self):
        with pytest.raises(ValidationError):
            DirectorReActOutput.model_validate({"observe": "관찰", "think": "사고", "act": "invalid_action"})


# ── DirectorCheckpointOutput ──


class TestDirectorCheckpointOutput:
    def test_proceed_ok(self):
        m = DirectorCheckpointOutput.model_validate({"decision": "proceed", "score": 0.85, "reasoning": "품질 충분"})
        assert m.decision == "proceed"
        assert m.score == 0.85

    def test_revise_with_feedback_ok(self):
        m = DirectorCheckpointOutput.model_validate(
            {"decision": "revise", "score": 0.4, "reasoning": "부족", "feedback": "구조 개선"}
        )
        assert m.feedback == "구조 개선"

    def test_revise_no_feedback_fail(self):
        with pytest.raises(ValidationError, match="feedback"):
            DirectorCheckpointOutput.model_validate({"decision": "revise", "score": 0.3, "reasoning": "부족"})

    def test_score_out_of_range(self):
        with pytest.raises(ValidationError):
            DirectorCheckpointOutput.model_validate({"decision": "proceed", "score": 1.5, "reasoning": "r"})

    def test_score_negative(self):
        with pytest.raises(ValidationError):
            DirectorCheckpointOutput.model_validate({"decision": "proceed", "score": -0.1, "reasoning": "r"})


# ── NarrativeScoreOutput ──


class TestNarrativeScoreOutput:
    def test_clamp_values(self):
        m = NarrativeScoreOutput.model_validate({"hook": 1.5, "emotional_arc": -0.3})
        assert m.hook == 1.0
        assert m.emotional_arc == 0.0

    def test_defaults_zero(self):
        m = NarrativeScoreOutput.model_validate({})
        assert m.hook == 0.0
        assert m.twist_payoff == 0.0

    def test_feedback(self):
        m = NarrativeScoreOutput.model_validate({"hook": 0.9, "feedback": "훅이 강렬합니다"})
        assert m.feedback == "훅이 강렬합니다"

    def test_normal_values_preserved(self):
        m = NarrativeScoreOutput.model_validate({"hook": 0.8, "emotional_arc": 0.7, "twist_payoff": 0.6})
        assert m.hook == 0.8
        assert m.emotional_arc == 0.7
        assert m.twist_payoff == 0.6


# ── WriterPlanOutput ──


class TestWriterPlanOutput:
    def test_valid(self):
        m = WriterPlanOutput.model_validate(
            {
                "hook_strategy": "질문형",
                "emotional_arc": ["기대", "놀람"],
                "scene_distribution": {"intro": 1, "rising": 2},
            }
        )
        assert m.hook_strategy == "질문형"
        assert len(m.emotional_arc) == 2

    def test_all_defaults(self):
        m = WriterPlanOutput.model_validate({})
        assert m.hook_strategy == ""
        assert m.emotional_arc == []
        assert m.scene_distribution == {}


# ── validate_with_model ──


class TestValidateWithModel:
    def test_valid_ok(self):
        qc = validate_with_model(
            DirectorPlanOutput,
            {"creative_goal": "g", "target_emotion": "e", "quality_criteria": ["c"]},
        )
        assert qc.ok is True
        assert qc.issues == []

    def test_invalid_issues(self):
        qc = validate_with_model(DirectorPlanOutput, {"creative_goal": ""})
        assert qc.ok is False
        assert len(qc.issues) > 0

    def test_non_dict(self):
        qc = validate_with_model(DirectorPlanOutput, "not a dict")
        assert qc.ok is False
        assert "JSON object" in qc.issues[0]

    def test_non_dict_list(self):
        qc = validate_with_model(DirectorPlanOutput, [1, 2, 3])
        assert qc.ok is False

    def test_model_dump_compat(self):
        qc = validate_with_model(
            DirectorPlanOutput,
            {"creative_goal": "g", "target_emotion": "e", "quality_criteria": ["c"]},
        )
        d = qc.model_dump()
        assert d["ok"] is True
        assert isinstance(d["issues"], list)
        assert isinstance(d["checks"], dict)
