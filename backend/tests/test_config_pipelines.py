"""config_pipelines.py 기본값 검증 테스트 (SP-043).

REVIEW_MODEL, CREATIVE_LEADER_MODEL 기본값이 gemini-2.5-flash인지,
FLASH_THINKING_BUDGET 기본값이 2048인지 확인한다.
"""

from __future__ import annotations

import importlib
import os
from unittest.mock import patch


def test_review_model_default_is_flash():
    """REVIEW_MODEL 기본값이 gemini-2.5-flash인지 확인."""
    env = {k: v for k, v in os.environ.items() if k != "REVIEW_MODEL"}
    with patch.dict(os.environ, env, clear=True):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.REVIEW_MODEL == "gemini-2.5-flash", (
            f"기본값이 gemini-2.5-flash여야 함, 실제: {config_pipelines.REVIEW_MODEL}"
        )


def test_creative_leader_model_default_is_flash():
    """CREATIVE_LEADER_MODEL 기본값이 gemini-2.5-flash인지 확인."""
    env = {k: v for k, v in os.environ.items() if k != "CREATIVE_LEADER_MODEL"}
    with patch.dict(os.environ, env, clear=True):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.CREATIVE_LEADER_MODEL == "gemini-2.5-flash", (
            f"기본값이 gemini-2.5-flash여야 함, 실제: {config_pipelines.CREATIVE_LEADER_MODEL}"
        )


def test_review_model_env_override():
    """환경변수로 REVIEW_MODEL을 Pro로 오버라이드할 수 있는지 확인."""
    with patch.dict(os.environ, {"REVIEW_MODEL": "gemini-2.5-pro"}):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.REVIEW_MODEL == "gemini-2.5-pro"


def test_creative_leader_model_env_override():
    """환경변수로 CREATIVE_LEADER_MODEL을 Pro로 오버라이드할 수 있는지 확인."""
    with patch.dict(os.environ, {"CREATIVE_LEADER_MODEL": "gemini-2.5-pro"}):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.CREATIVE_LEADER_MODEL == "gemini-2.5-pro"


def test_flash_thinking_budget_default():
    """FLASH_THINKING_BUDGET 기본값이 2048인지 확인."""
    env = {k: v for k, v in os.environ.items() if k != "FLASH_THINKING_BUDGET"}
    with patch.dict(os.environ, env, clear=True):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.FLASH_THINKING_BUDGET == 2048


def test_flash_thinking_budget_env_override():
    """환경변수로 FLASH_THINKING_BUDGET을 변경할 수 있는지 확인."""
    with patch.dict(os.environ, {"FLASH_THINKING_BUDGET": "4096"}):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.FLASH_THINKING_BUDGET == 4096


def test_flash_thinking_budget_disabled():
    """FLASH_THINKING_BUDGET=0이면 thinking 비활성화."""
    with patch.dict(os.environ, {"FLASH_THINKING_BUDGET": "0"}):
        import config_pipelines

        importlib.reload(config_pipelines)
        assert config_pipelines.FLASH_THINKING_BUDGET == 0
