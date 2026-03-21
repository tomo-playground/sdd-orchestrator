"""Cinematographer Agent Tool-Calling 테스트 (Phase 10-B-3)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.agent.nodes.cinematographer import cinematographer_node
from services.agent.state import ScriptState
from services.agent.tools.cinematographer_tools import (
    create_cinematographer_executors,
    get_cinematographer_tools,
)

# ── 도구 정의 테스트 ──────────────────────────────────────


def test_get_cinematographer_tools_returns_4_tools():
    """4개 도구가 정의되어야 한다."""
    tools = get_cinematographer_tools()
    assert len(tools) == 4

    tool_names = []
    for tool in tools:
        if tool.function_declarations:
            for decl in tool.function_declarations:
                tool_names.append(decl.name)

    expected = [
        "validate_danbooru_tag",
        "search_similar_compositions",
        "get_character_visual_tags",
        "check_tag_compatibility",
    ]
    assert set(tool_names) == set(expected)


def test_validate_danbooru_tag_tool_definition():
    """validate_danbooru_tag 도구 정의가 올바른지 확인."""
    tools = get_cinematographer_tools()
    tag_tool = tools[0]
    decl = tag_tool.function_declarations[0]

    assert decl.name == "validate_danbooru_tag"
    assert "Danbooru" in decl.description
    assert "tag" in decl.parameters.properties
    assert "tag" in decl.parameters.required


# ── 도구 실행 함수 테스트 ─────────────────────────────────


@pytest.mark.asyncio
async def test_validate_danbooru_tag_valid():
    """유효한 태그 검증."""
    mock_db = AsyncMock(spec=AsyncSession)
    state = {}

    # 태그가 존재함
    mock_tag = Mock()
    mock_tag.category = "character"
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_tag

    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_db.execute = mock_execute

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["validate_danbooru_tag"](tag="brown_hair")

    assert "✓" in result
    assert "유효한" in result or "valid" in result.lower()


@pytest.mark.asyncio
async def test_validate_danbooru_tag_invalid():
    """유효하지 않은 태그 검증."""
    mock_db = AsyncMock(spec=AsyncSession)
    state = {}

    # 태그가 없음
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None

    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_db.execute = mock_execute

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["validate_danbooru_tag"](tag="invalid_tag_xyz")

    assert "✗" in result
    assert "존재하지 않는" in result


@pytest.mark.asyncio
async def test_search_similar_compositions():
    """유사 구도 검색 (placeholder)."""
    mock_db = AsyncMock()
    state = {}

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["search_similar_compositions"](mood="cheerful", scene_type="portrait")

    assert "[레퍼런스 태그 조합]" in result or "smile" in result


@pytest.mark.asyncio
async def test_get_character_visual_tags():
    """캐릭터 비주얼 태그 조회."""
    mock_db = AsyncMock(spec=AsyncSession)
    state = {}

    # 캐릭터와 태그 존재
    mock_char = Mock()
    mock_char.name = "Test Character"
    mock_char_tag = Mock()
    mock_char_tag.tag = Mock()
    mock_char_tag.tag.name = "brown_hair"
    mock_char.tags = [mock_char_tag]

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = mock_char

    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_db.execute = mock_execute

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["get_character_visual_tags"](character_id=1)

    assert "Test Character" in result
    assert "brown_hair" in result


@pytest.mark.asyncio
async def test_get_character_visual_tags_not_found():
    """캐릭터가 없을 때."""
    mock_db = AsyncMock(spec=AsyncSession)
    state = {}

    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None

    async def mock_execute(*args, **kwargs):
        return mock_result

    mock_db.execute = mock_execute

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["get_character_visual_tags"](character_id=999)

    assert "✗" in result
    assert "찾을 수 없습니다" in result


@pytest.mark.asyncio
async def test_check_tag_compatibility_compatible():
    """호환되는 태그."""
    mock_db = AsyncMock(spec=AsyncSession)
    state = {}

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_result = Mock()
        if call_count <= 2:
            # 태그 ID 조회
            mock_result.scalar_one_or_none.return_value = call_count
        else:
            # 충돌 규칙 조회 — 없음
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute = mock_execute

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["check_tag_compatibility"](tag_a="smile", tag_b="happy")

    assert "✓" in result
    assert "호환" in result


@pytest.mark.asyncio
async def test_check_tag_compatibility_conflict():
    """충돌하는 태그."""
    mock_db = AsyncMock(spec=AsyncSession)
    state = {}

    call_count = 0

    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_result = Mock()
        if call_count <= 2:
            # 태그 ID 조회
            mock_result.scalar_one_or_none.return_value = call_count
        else:
            # 충돌 규칙 조회 — 있음
            mock_rule = Mock()
            mock_rule.message = "표정이 충돌함"
            mock_result.scalar_one_or_none.return_value = mock_rule
        return mock_result

    mock_db.execute = mock_execute

    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["check_tag_compatibility"](tag_a="smile", tag_b="crying")

    assert "✗" in result
    assert "충돌" in result


# ── cinematographer_node 통합 테스트 ────────────────────────


@pytest.mark.asyncio
@patch("config_pipelines.CINEMATOGRAPHER_COMPETITION_ENABLED", False)
async def test_cinematographer_node_tool_calling():
    """cinematographer_node가 Tool-Calling을 수행한다."""
    mock_db = AsyncMock()

    state: ScriptState = {
        "draft_scenes": [
            {"order": 1, "text": "테스트 씬"},
        ],
        "character_id": 1,
    }

    config = {"configurable": {"db": mock_db}}

    # call_with_tools 모킹
    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        mock_call.return_value = (
            """```json
{
  "scenes": [
    {
      "order": 1,
      "text": "테스트 씬",
      "visual_tags": ["brown_hair", "smile"],
      "camera": "close-up",
      "environment": "indoors"
    }
  ]
}
```""",
            [{"tool_name": "get_character_visual_tags", "arguments": {}, "result": "...", "error": None}],
            None,
        )

        # validate_visuals 모킹
        with patch("services.agent.nodes.cinematographer.validate_visuals") as mock_validate:
            mock_validate.return_value = {"ok": True, "issues": [], "checks": {}}

            result = await cinematographer_node(state, config)

    assert "cinematographer_result" in result
    assert "cinematographer_tool_logs" in result
    assert len(result["cinematographer_tool_logs"]) == 1


@pytest.mark.asyncio
@patch("config_pipelines.CINEMATOGRAPHER_COMPETITION_ENABLED", False)
async def test_cinematographer_node_no_db_in_config():
    """config에 DB 세션이 없어도 get_db_session() fallback으로 정상 동작."""
    state: ScriptState = {
        "draft_scenes": [{"order": 1, "text": "테스트"}],
    }

    config = {}  # DB 없음 → get_db_session() fallback

    mock_db = MagicMock()

    with (
        patch("services.agent.nodes.cinematographer.get_db_session") as mock_get_db,
        patch("services.agent.tools.base.call_with_tools") as mock_call,
        patch("services.agent.nodes.cinematographer.validate_visuals") as mock_validate,
    ):
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_validate.return_value = {"ok": True, "issues": [], "checks": {}}
        mock_call.return_value = (
            '{"scenes": [{"order": 1, "text": "테스트", "visual_tags": ["1girl"], "camera": "close-up", "environment": "indoors"}]}',
            [],
            None,
        )

        result = await cinematographer_node(state, config)

    mock_get_db.assert_called_once()
    assert "cinematographer_result" in result


@pytest.mark.asyncio
@patch("config_pipelines.CINEMATOGRAPHER_COMPETITION_ENABLED", False)
@patch("services.agent.nodes.cinematographer._run_team", new_callable=AsyncMock, return_value=None)
async def test_cinematographer_node_json_parsing_graceful(mock_team):
    """JSON 파싱 2회 실패 → error 미설정, cinematographer_result=None (graceful)."""
    mock_db = AsyncMock()

    state: ScriptState = {
        "draft_scenes": [{"order": 1, "text": "테스트"}],
    }

    config = {"configurable": {"db": mock_db}}

    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        # 첫 시도: call_with_tools 파싱 불가
        mock_call.return_value = (
            "This is not valid JSON",
            [],
            None,
        )

        with patch("services.agent.tools.base.call_direct", new_callable=AsyncMock) as mock_direct:
            # 두 번째 시도: call_direct도 파싱 불가
            mock_direct.return_value = "Still not valid JSON"
            result = await cinematographer_node(state, config)

    assert "error" not in result
    assert result["cinematographer_result"] is None
    # attempt 1: call_with_tools 1회, attempt 2: call_direct 1회 (team은 mock으로 skip)
    assert mock_call.call_count == 1
    assert mock_direct.call_count == 1


@pytest.mark.asyncio
@patch("config_pipelines.CINEMATOGRAPHER_COMPETITION_ENABLED", False)
@patch("services.agent.nodes.cinematographer._run_team", new_callable=AsyncMock, return_value=None)
async def test_cinematographer_node_retry_succeeds_on_second_attempt(mock_team):
    """첫 번째 파싱 실패 → 두 번째 성공 (retry via call_direct). Competition+Team 비활성화 상태."""
    mock_db = AsyncMock()

    state: ScriptState = {
        "draft_scenes": [{"order": 1, "text": "테스트"}],
    }

    config = {"configurable": {"db": mock_db}}

    valid_json = '{"scenes": [{"order": 1, "text": "테스트", "visual_tags": ["1girl"], "camera": "close-up", "environment": "indoors"}]}'

    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        mock_call.return_value = ("", [], None)  # 첫 시도: 빈 응답

        with patch("services.agent.tools.base.call_direct", new_callable=AsyncMock) as mock_direct:
            mock_direct.return_value = valid_json  # 두 번째: call_direct 성공

            with patch("services.agent.nodes.cinematographer.validate_visuals") as mock_validate:
                mock_validate.return_value = {"ok": True, "issues": [], "checks": {}}
                result = await cinematographer_node(state, config)

    assert result["cinematographer_result"] is not None
    assert len(result["cinematographer_result"]["scenes"]) == 1
    assert mock_call.call_count == 1
    assert mock_direct.call_count == 1


@pytest.mark.asyncio
@patch("config_pipelines.CINEMATOGRAPHER_COMPETITION_ENABLED", False)
async def test_cinematographer_node_qc_failure_still_returns():
    """QC 검증 실패 → error 미설정, 결과는 그대로 반환 (graceful)."""
    mock_db = AsyncMock()

    state: ScriptState = {
        "draft_scenes": [{"order": 1, "text": "테스트"}],
    }

    config = {"configurable": {"db": mock_db}}

    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        mock_call.return_value = (
            """```json
{
  "scenes": [
    {
      "order": 1,
      "text": "테스트"
    }
  ]
}
```""",
            [],
            None,
        )

        with patch("services.agent.nodes.cinematographer.validate_visuals") as mock_validate:
            mock_validate.return_value = {"ok": False, "issues": ["Missing visual_tags"], "checks": {}}

            result = await cinematographer_node(state, config)

    assert "error" not in result
    assert result["cinematographer_result"] is not None
    assert result["cinematographer_result"]["scenes"] == [{"order": 1, "text": "테스트"}]


# ── search_similar_compositions DB 연동 테스트 ────────────────


@pytest.mark.asyncio
async def test_search_similar_compositions_with_db_data():
    """tag_effectiveness에 데이터가 있으면 DB 기반 결과를 반환한다."""
    mock_db = MagicMock()

    # DB에 effectiveness 높은 태그 데이터 존재
    mock_row = Mock()
    mock_row.tag = Mock()
    mock_row.tag.name = "smile"
    mock_row.effectiveness = 0.85
    mock_row.use_count = 50
    mock_row.match_count = 42

    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    state = {}
    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["search_similar_compositions"](mood="cheerful", scene_type="portrait")

    assert "smile" in result
    assert "85" in result or "0.85" in result  # effectiveness 수치 포함


@pytest.mark.asyncio
async def test_search_similar_compositions_fallback():
    """DB에 데이터가 없으면 기존 정적 데이터로 fallback한다."""
    mock_db = MagicMock()

    # DB 빈 결과
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    state = {}
    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["search_similar_compositions"](mood="cheerful", scene_type="portrait")

    # 기존 정적 데이터 포함
    assert "smile" in result or "레퍼런스" in result


@pytest.mark.asyncio
async def test_search_similar_compositions_db_error():
    """DB 에러 시 기존 정적 데이터로 fallback한다."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("DB connection error")

    state = {}
    executors = create_cinematographer_executors(mock_db, state)
    result = await executors["search_similar_compositions"](mood="dramatic", scene_type="action")

    # fallback 정적 데이터
    assert "레퍼런스" in result or "dynamic" in result
