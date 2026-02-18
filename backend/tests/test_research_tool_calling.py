"""Research Agent Tool-Calling 테스트 (Phase 10-B-2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from langgraph.store.base import BaseStore

from services.agent.nodes.research import research_node
from services.agent.state import ScriptState
from services.agent.tools.research_tools import (
    create_research_executors,
    get_research_tools,
)

# ── 도구 정의 테스트 ──────────────────────────────────────


def test_get_research_tools_returns_5_tools():
    """5개 도구가 정의되어야 한다."""
    tools = get_research_tools()
    assert len(tools) == 5

    tool_names = []
    for tool in tools:
        if tool.function_declarations:
            for decl in tool.function_declarations:
                tool_names.append(decl.name)

    expected = [
        "search_topic_history",
        "search_character_history",
        "fetch_url_content",
        "analyze_trending",
        "get_group_dna",
    ]
    assert set(tool_names) == set(expected)


def test_search_topic_history_tool_definition():
    """search_topic_history 도구 정의가 올바른지 확인."""
    tools = get_research_tools()
    topic_tool = tools[0]
    decl = topic_tool.function_declarations[0]

    assert decl.name == "search_topic_history"
    assert "과거" in decl.description
    assert "topic" in decl.parameters.properties
    assert "limit" in decl.parameters.properties
    assert "topic" in decl.parameters.required


# ── 도구 실행 함수 테스트 ─────────────────────────────────


@pytest.mark.asyncio
async def test_search_topic_history_executor():
    """토픽 히스토리 검색 실행 함수."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {"topic": "외로움", "language": "Korean"}

    # Store에서 히스토리 반환
    mock_item = MagicMock()
    mock_item.value = {"topic": "외로움", "success": True}
    mock_store.asearch.return_value = [mock_item]

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["search_topic_history"](topic="외로움", limit=5)

    assert "[토픽 히스토리]" in result
    mock_store.asearch.assert_called_once()


@pytest.mark.asyncio
async def test_search_topic_history_no_history():
    """히스토리가 없을 때."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {}

    mock_store.asearch.return_value = []

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["search_topic_history"](topic="새 주제", limit=5)

    assert "과거 이력 없음" in result


@pytest.mark.asyncio
async def test_search_character_history_executor():
    """캐릭터 히스토리 검색 실행 함수."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {}

    mock_item = MagicMock()
    mock_item.value = {"character_id": 1, "tone": "친근함"}
    mock_store.asearch.return_value = [mock_item]

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["search_character_history"](character_id=1, limit=5)

    assert "[캐릭터 히스토리]" in result


@pytest.mark.asyncio
async def test_fetch_url_content_executor():
    """URL 콘텐츠 fetch 실행 함수."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {}

    executors = create_research_executors(mock_store, mock_db, state)

    # _fetch_url 모킹
    with patch("services.agent.nodes.research._fetch_url", return_value="테스트 콘텐츠"):
        result = await executors["fetch_url_content"](url="https://example.com")

    assert "[URL 콘텐츠]" in result
    assert "테스트 콘텐츠" in result


@pytest.mark.asyncio
async def test_fetch_url_content_failure():
    """URL fetch 실패 시."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {}

    executors = create_research_executors(mock_store, mock_db, state)

    with patch("services.agent.nodes.research._fetch_url", return_value=None):
        result = await executors["fetch_url_content"](url="https://example.com")

    assert "가져오기 실패" in result


@pytest.mark.asyncio
async def test_analyze_trending_executor():
    """트렌딩 분석 실행 함수 (현재는 placeholder)."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {}

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["analyze_trending"](topic="AI", language="Korean")

    assert "[트렌딩 분석]" in result
    assert "AI" in result


@pytest.mark.asyncio
async def test_get_group_dna_from_store():
    """그룹 DNA를 Store에서 조회."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()
    state = {}

    mock_item = MagicMock()
    mock_item.value = {"tone": "친근함", "worldview": "일상"}
    mock_store.asearch.return_value = [mock_item]

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["get_group_dna"](group_id=1)

    assert "[그룹 DNA]" in result


@pytest.mark.asyncio
async def test_get_group_dna_from_db():
    """그룹 DNA를 DB에서 조회."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = Mock()
    state = {}

    # Store에 없음
    mock_store.asearch.return_value = []

    # DB에서 조회 (scalar_one_or_none은 동기 메서드)
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = {
        "tone": "진지함",
        "worldview": "판타지",
        "guidelines": "청소년 관람가",
    }

    # execute는 비동기 메서드
    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_db.execute = mock_execute

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["get_group_dna"](group_id=1)

    assert "[그룹 DNA]" in result
    assert "진지함" in result


@pytest.mark.asyncio
async def test_get_group_dna_not_found():
    """그룹 DNA가 없을 때."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = Mock()
    state = {}

    mock_store.asearch.return_value = []
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None

    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_db.execute = mock_execute

    executors = create_research_executors(mock_store, mock_db, state)
    result = await executors["get_group_dna"](group_id=999)

    assert "채널 DNA 없음" in result


# ── research_node 통합 테스트 ────────────────────────────


@pytest.mark.asyncio
async def test_research_node_tool_calling():
    """research_node가 Tool-Calling을 수행한다."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()

    state: ScriptState = {
        "topic": "외로움",
        "description": "혼자 있는 시간",
        "language": "Korean",
        "character_id": 1,
        "group_id": None,
        "references": [],
    }

    config = {"configurable": {"db": mock_db}}

    # call_with_tools 모킹 (research.py에서 import한 것을 패치)
    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        mock_call.return_value = (
            "[Research Brief] 외로움 주제는 공감 Hook이 중요합니다.",
            [{"tool_name": "search_topic_history", "arguments": {}, "result": "...", "error": None}],
        )

        result = await research_node(state, config, store=mock_store)

    assert "research_brief" in result
    assert result["research_brief"] is not None
    assert "research_tool_logs" in result
    assert len(result["research_tool_logs"]) == 1


@pytest.mark.asyncio
async def test_research_node_no_db_session():
    """DB 세션이 없으면 빈 brief 반환."""
    mock_store = AsyncMock(spec=BaseStore)

    state: ScriptState = {
        "topic": "테스트",
    }

    config = {}  # DB 없음

    result = await research_node(state, config, store=mock_store)

    assert result["research_brief"] is None
    assert result["research_tool_logs"] == []


@pytest.mark.asyncio
async def test_research_node_tool_calling_failure():
    """Tool-Calling 실패 시 fallback."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()

    state: ScriptState = {
        "topic": "테스트",
    }

    config = {"configurable": {"db": mock_db}}

    # call_with_tools 에러 발생
    with patch("services.agent.tools.base.call_with_tools", side_effect=RuntimeError("Max calls exceeded")):
        result = await research_node(state, config, store=mock_store)

    assert result["research_brief"] is None
    assert result["research_tool_logs"] == []


@pytest.mark.asyncio
async def test_research_node_with_references():
    """References가 있을 때 URL fetch 도구를 사용할 수 있어야 한다."""
    mock_store = AsyncMock(spec=BaseStore)
    mock_db = AsyncMock()

    state: ScriptState = {
        "topic": "AI 트렌드",
        "language": "Korean",
        "references": ["https://example.com/ai-news"],
    }

    config = {"configurable": {"db": mock_db}}

    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        mock_call.return_value = (
            "[Research Brief] URL 분석 결과...",
            [
                {
                    "tool_name": "fetch_url_content",
                    "arguments": {"url": "https://example.com/ai-news"},
                    "result": "AI 뉴스 콘텐츠",
                    "error": None,
                }
            ],
        )

        result = await research_node(state, config, store=mock_store)

    assert result["research_brief"] is not None
    assert len(result["research_tool_logs"]) == 1
    assert result["research_tool_logs"][0]["tool_name"] == "fetch_url_content"
