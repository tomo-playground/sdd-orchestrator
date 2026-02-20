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
    """run_production_step에 model을 전달하면 해당 모델로 Gemini를 호출하는지 검증."""
    mock_response = MagicMock()
    mock_response.text = '{"observe": "ok", "think": "ok", "act": "approve"}'

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with (
        patch("services.agent.nodes._production_utils.gemini_client", mock_client),
        patch("services.agent.nodes._production_utils.template_env") as mock_env,
        patch("services.agent.nodes._production_utils.trace_llm_call") as mock_trace,
    ):
        mock_tmpl = MagicMock()
        mock_tmpl.render.return_value = "test prompt"
        mock_env.get_template.return_value = mock_tmpl

        # trace_llm_call을 async context manager로 모킹
        mock_llm = MagicMock()
        mock_llm.record = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_llm)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_trace.return_value = mock_ctx

        from services.agent.nodes._production_utils import run_production_step

        result = await run_production_step(
            template_name="test.j2",
            template_vars={},
            validate_fn=lambda x: {"ok": True, "issues": []},
            extract_key="",
            step_name="test",
            model="gemini-2.5-pro",
        )

        # Gemini 호출 시 model 확인
        call_kwargs = mock_client.aio.models.generate_content.call_args
        assert call_kwargs.kwargs.get("model") == "gemini-2.5-pro"


@pytest.mark.asyncio
async def test_run_production_step_default_model_fallback():
    """model=None일 때 GEMINI_TEXT_MODEL로 폴백하는지 검증."""
    mock_response = MagicMock()
    mock_response.text = '{"scenes": [{"script": "test"}]}'

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with (
        patch("services.agent.nodes._production_utils.gemini_client", mock_client),
        patch("services.agent.nodes._production_utils.GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
        patch("services.agent.nodes._production_utils.template_env") as mock_env,
        patch("services.agent.nodes._production_utils.trace_llm_call") as mock_trace,
    ):
        mock_tmpl = MagicMock()
        mock_tmpl.render.return_value = "test prompt"
        mock_env.get_template.return_value = mock_tmpl

        mock_llm = MagicMock()
        mock_llm.record = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_llm)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_trace.return_value = mock_ctx

        from services.agent.nodes._production_utils import run_production_step

        await run_production_step(
            template_name="test.j2",
            template_vars={},
            validate_fn=lambda x: {"ok": True, "issues": []},
            extract_key="scenes",
            step_name="test",
        )

        call_kwargs = mock_client.aio.models.generate_content.call_args
        assert call_kwargs.kwargs.get("model") == "gemini-2.5-flash"


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
