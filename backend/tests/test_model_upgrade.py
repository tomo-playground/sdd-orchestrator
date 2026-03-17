"""Phase 12-D: Gemini Model Upgrade 테스트.

config 기본값, run_production_step model 파라미터, Director/Review 모델 전달,
groupthink 카운트, revision accuracy 계산 검증.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# --- Step 1: Config 기본값 검증 ---


def test_config_creative_leader_model_default():
    """CREATIVE_LEADER_MODEL 기본값이 gemini-2.5-pro인지 검증."""
    from config_pipelines import CREATIVE_LEADER_MODEL

    assert CREATIVE_LEADER_MODEL == "gemini-2.5-pro"


def test_config_director_model_default():
    """DIRECTOR_MODEL 기본값이 gemini-2.5-pro인지 검증."""
    from config_pipelines import DIRECTOR_MODEL

    assert DIRECTOR_MODEL == "gemini-2.5-pro"


def test_config_review_model_default():
    """REVIEW_MODEL 기본값이 gemini-2.5-pro인지 검증."""
    from config_pipelines import REVIEW_MODEL

    assert REVIEW_MODEL == "gemini-2.5-pro"


# --- Step 2: run_production_step model 파라미터 ---


def test_run_production_step_has_model_param():
    """run_production_step에 model 파라미터가 존재하는지 검증."""
    from services.agent.nodes._production_utils import run_production_step

    sig = inspect.signature(run_production_step)
    assert "model" in sig.parameters
    param = sig.parameters["model"]
    assert param.default is None


@pytest.mark.asyncio
async def test_run_production_step_uses_custom_model():
    """run_production_step에 model을 전달하면 provider.generate(model=)로 전달되는지 검증."""
    mock_llm_resp = MagicMock()
    mock_llm_resp.text = '{"observe": "ok", "think": "ok", "act": "approve"}'
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

    mock_compiled = MagicMock(system="sys", user="test prompt", langfuse_prompt=None)

    with (
        patch("services.agent.nodes._production_utils.get_llm_provider", return_value=mock_provider),
        patch("services.agent.nodes._production_utils.compile_prompt", return_value=mock_compiled),
    ):
        from services.agent.nodes._production_utils import run_production_step

        await run_production_step(
            template_name="test",
            template_vars={},
            validate_fn=lambda x: {"ok": True, "issues": []},
            extract_key="",
            step_name="test",
            model="gemini-2.5-pro",
        )

        call_kwargs = mock_provider.generate.call_args
        assert call_kwargs.kwargs.get("model") == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_run_production_step_default_model_fallback():
    """model=None일 때 provider.generate(model=None)이 전달되는지 검증."""
    mock_llm_resp = MagicMock()
    mock_llm_resp.text = '{"scenes": [{"script": "test"}]}'
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_llm_resp)

    mock_compiled = MagicMock(system="sys", user="test prompt", langfuse_prompt=None)

    with (
        patch("services.agent.nodes._production_utils.get_llm_provider", return_value=mock_provider),
        patch("services.agent.nodes._production_utils.compile_prompt", return_value=mock_compiled),
    ):
        from services.agent.nodes._production_utils import run_production_step

        await run_production_step(
            template_name="test",
            template_vars={},
            validate_fn=lambda x: {"ok": True, "issues": []},
            extract_key="scenes",
            step_name="test",
        )

        call_kwargs = mock_provider.generate.call_args
        # model=None이 그대로 전달됨 (실제 해소는 GeminiProvider 내부)
        assert call_kwargs.kwargs.get("model") is None


# --- Step 3: Director → DIRECTOR_MODEL 전달 ---


def test_director_imports_director_model():
    """director.py가 DIRECTOR_MODEL을 import하는지 검증."""
    import services.agent.nodes.director as director_mod

    assert hasattr(director_mod, "DIRECTOR_MODEL")
    assert director_mod.DIRECTOR_MODEL == "gemini-2.5-pro"


# --- Step 4: Review → REVIEW_MODEL 전달 ---


def test_review_imports_review_model():
    """review.py가 REVIEW_MODEL을 import하는지 검증."""
    import services.agent.nodes.review as review_mod

    assert hasattr(review_mod, "REVIEW_MODEL")
    assert review_mod.REVIEW_MODEL == "gemini-2.5-pro"


# --- Step 5: Groupthink 카운트 ---


def test_count_groupthink_empty():
    """빈 debate_log에서 groupthink 카운트가 0인지 검증."""
    from services.agent.nodes.learn import _count_groupthink

    assert _count_groupthink([]) == 0


def test_count_groupthink_with_detections():
    """groupthink_detected=True인 항목을 정확히 세는지 검증."""
    from services.agent.nodes.learn import _count_groupthink

    debate_log = [
        {"round": 1, "action": "propose"},
        {"round": 2, "action": "critique_refine", "groupthink_detected": True},
        {"round": 3, "action": "critique_refine", "groupthink_detected": False},
        {"round": 4, "action": "critique_refine", "groupthink_detected": True},
    ]
    assert _count_groupthink(debate_log) == 2


# --- Step 6: Revision Accuracy ---


def test_calc_revision_accuracy_no_revision():
    """revision이 0이면 None을 반환하는지 검증."""
    from services.agent.nodes.learn import _calc_revision_accuracy

    state = {"revision_count": 0}
    assert _calc_revision_accuracy(state) is None


def test_calc_revision_accuracy_with_scores():
    """점수가 있을 때 개선율을 올바르게 계산하는지 검증."""
    from services.agent.nodes.learn import _calc_revision_accuracy

    state = {
        "revision_count": 2,
        "director_checkpoint_score": 0.5,
        "review_result": {"narrative_score": {"overall": 0.75}},
    }
    result = _calc_revision_accuracy(state)
    assert result == 0.5  # (0.75 - 0.5) / 0.5 = 0.5


def test_calc_revision_accuracy_zero_checkpoint():
    """checkpoint_score가 0이면 None을 반환하는지 검증."""
    from services.agent.nodes.learn import _calc_revision_accuracy

    state = {
        "revision_count": 1,
        "director_checkpoint_score": 0,
        "review_result": {"narrative_score": {"overall": 0.8}},
    }
    assert _calc_revision_accuracy(state) is None
