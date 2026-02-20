"""Finalize 노드 — negative_prompt 주입 테스트."""

from __future__ import annotations

import pytest

from config import DEFAULT_SCENE_NEGATIVE_PROMPT


@pytest.mark.asyncio
async def test_finalize_injects_negative_prompt():
    """Full 모드: 빈 negative_prompt에 DEFAULT 값을 주입한다."""
    from services.agent.nodes.finalize import finalize_node

    state = {
        "mode": "full",
        "cinematographer_result": {
            "scenes": [
                {"order": 0, "script": "씬1", "image_prompt": "1girl, smile"},
                {"order": 1, "script": "씬2", "image_prompt": "1girl, sad"},
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }
    result = await finalize_node(state)
    for scene in result["final_scenes"]:
        assert scene["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT


@pytest.mark.asyncio
async def test_finalize_preserves_existing_negative():
    """기존 negative_prompt가 있으면 그대로 유지한다."""
    from services.agent.nodes.finalize import finalize_node

    custom_negative = "lowres, bad_hands"
    state = {
        "mode": "full",
        "cinematographer_result": {
            "scenes": [
                {"order": 0, "script": "씬1", "negative_prompt": custom_negative},
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }
    result = await finalize_node(state)
    assert result["final_scenes"][0]["negative_prompt"] == custom_negative


@pytest.mark.asyncio
async def test_finalize_quick_mode_also_injects():
    """Quick 모드에서도 빈 negative_prompt에 기본값을 주입한다."""
    from services.agent.nodes.finalize import finalize_node

    state = {
        "mode": "quick",
        "draft_scenes": [
            {"order": 0, "script": "퀵 씬1"},
            {"order": 1, "script": "퀵 씬2", "negative_prompt": ""},
        ],
    }
    result = await finalize_node(state)
    for scene in result["final_scenes"]:
        assert scene["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT
