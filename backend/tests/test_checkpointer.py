"""LangGraph Checkpointer 통합 테스트.

실제 PostgreSQL로 checkpoint 저장/조회를 검증한다.
"""

from __future__ import annotations

import uuid

import pytest

from services.agent.checkpointer import get_checkpointer
from services.agent.script_graph import build_script_graph


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_save_and_resume():
    """thread_id 기반 상태 저장 후 재개를 확인한다."""
    from unittest.mock import AsyncMock, patch

    checkpointer = await get_checkpointer()
    graph = build_script_graph().compile(checkpointer=checkpointer)

    thread_id = f"test-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    mock_scenes = [{"scene_number": 1, "script": "통합 테스트 씬"}]

    with (
        patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock) as mock_gen,
        patch("services.agent.nodes.draft.SessionLocal"),
    ):
        mock_gen.return_value = {"scenes": mock_scenes}
        result = await graph.ainvoke({"topic": "체크포인트 테스트"}, config)

    assert result["final_scenes"] == mock_scenes

    # checkpoint에서 상태 조회
    saved = await checkpointer.aget(config)
    assert saved is not None
    assert saved["channel_values"]["final_scenes"] == mock_scenes
