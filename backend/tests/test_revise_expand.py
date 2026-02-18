"""Revise Tier 2: 씬 확장 로직 테스트.

parse_scene_deficit, can_use_expansion, merge_expanded_scenes,
redistribute_durations, try_scene_expand 테스트.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.nodes._revise_expand import (
    can_use_expansion,
    merge_expanded_scenes,
    parse_scene_deficit,
    redistribute_durations,
)

# ── parse_scene_deficit ──────────────────────────────────────


def test_parse_scene_deficit_standard():
    """표준 에러 메시지에서 (current, target_min)을 추출한다."""
    errors = ["씬 개수 부족: 2개 (최소 3개 필요, duration=10s)"]
    result = parse_scene_deficit(errors)
    assert result == (2, 3)


def test_parse_scene_deficit_no_match():
    """매칭되지 않는 에러 → None."""
    errors = ["씬 1: duration이 0 이하 (0)"]
    result = parse_scene_deficit(errors)
    assert result is None


def test_parse_scene_deficit_empty():
    """빈 리스트 → None."""
    assert parse_scene_deficit([]) is None


# ── can_use_expansion ────────────────────────────────────────


def test_can_use_expansion_deficit_only():
    """씬 부족만 있으면 True."""
    errors = ["씬 개수 부족: 2개 (최소 5개 필요, duration=15s)"]
    assert can_use_expansion(errors) is True


def test_can_use_expansion_deficit_plus_rule_fixable():
    """씬 부족 + 규칙 수정 가능한 에러 → True."""
    errors = [
        "씬 개수 부족: 2개 (최소 5개 필요, duration=15s)",
        "씬 1: duration이 0 이하 (0)",
    ]
    assert can_use_expansion(errors) is True


def test_can_use_expansion_complex_errors():
    """씬 부족 + 해결 불가 에러 → False."""
    errors = [
        "씬 개수 부족: 2개 (최소 5개 필요, duration=15s)",
        "Dialogue 구조에서 speaker 'B'가 등장하지 않음",
    ]
    assert can_use_expansion(errors) is False


def test_can_use_expansion_no_deficit():
    """씬 부족 없음 → False."""
    errors = ["씬 1: duration이 0 이하 (0)"]
    assert can_use_expansion(errors) is False


# ── merge_expanded_scenes ────────────────────────────────────


def test_merge_insert_middle():
    """중간 삽입: insert_after=0 → 씬 0 뒤에 삽입."""
    existing = [
        {"scene_id": 1, "script": "A"},
        {"scene_id": 2, "script": "B"},
    ]
    new = [{"insert_after": 0, "script": "NEW"}]
    result = merge_expanded_scenes(existing, new)
    assert len(result) == 3
    assert result[0]["script"] == "A"
    assert result[1]["script"] == "NEW"
    assert result[2]["script"] == "B"
    # scene_id 재번호화
    assert [s["scene_id"] for s in result] == [1, 2, 3]


def test_merge_insert_beginning():
    """맨 앞 삽입: insert_after=-1."""
    existing = [{"scene_id": 1, "script": "A"}]
    new = [{"insert_after": -1, "script": "FIRST"}]
    result = merge_expanded_scenes(existing, new)
    assert len(result) == 2
    assert result[0]["script"] == "FIRST"
    assert result[1]["script"] == "A"


def test_merge_insert_end():
    """맨 뒤 삽입: insert_after=마지막 인덱스."""
    existing = [
        {"scene_id": 1, "script": "A"},
        {"scene_id": 2, "script": "B"},
    ]
    new = [{"insert_after": 1, "script": "LAST"}]
    result = merge_expanded_scenes(existing, new)
    assert len(result) == 3
    assert result[2]["script"] == "LAST"


def test_merge_multiple_inserts():
    """다중 삽입: 여러 위치에 동시 삽입."""
    existing = [
        {"scene_id": 1, "script": "A"},
        {"scene_id": 2, "script": "B"},
        {"scene_id": 3, "script": "C"},
    ]
    new = [
        {"insert_after": 0, "script": "NEW1"},
        {"insert_after": 2, "script": "NEW2"},
    ]
    result = merge_expanded_scenes(existing, new)
    assert len(result) == 5
    scripts = [s["script"] for s in result]
    assert scripts == ["A", "NEW1", "B", "C", "NEW2"]


def test_merge_renumbers_scene_ids():
    """병합 후 scene_id가 1부터 연속 번호로 재할당된다."""
    existing = [{"scene_id": 10, "script": "A"}]
    new = [{"insert_after": 0, "script": "B"}]
    result = merge_expanded_scenes(existing, new)
    assert [s["scene_id"] for s in result] == [1, 2]
    assert [s["order"] for s in result] == [0, 1]
    # insert_after 키가 제거된다
    assert "insert_after" not in result[0]
    assert "insert_after" not in result[1]


# ── redistribute_durations ───────────────────────────────────


def test_redistribute_scale_down():
    """총 duration > target → 비례 축소."""
    scenes = [{"duration": 4.0}, {"duration": 6.0}]
    redistribute_durations(scenes, 5)
    total = sum(s["duration"] for s in scenes)
    assert 4.9 <= total <= 5.1  # 근사적 일치


def test_redistribute_no_change_needed():
    """총 duration == target → 변경 없음."""
    scenes = [{"duration": 3.0}, {"duration": 2.0}]
    redistribute_durations(scenes, 5)
    assert scenes[0]["duration"] == 3.0
    assert scenes[1]["duration"] == 2.0


def test_redistribute_clamps_to_range():
    """재분배 결과가 SCENE_DURATION_RANGE 범위로 클램핑된다."""
    scenes = [{"duration": 1.0}, {"duration": 9.0}]
    redistribute_durations(scenes, 7)
    for s in scenes:
        assert 2.0 <= s["duration"] <= 3.5


def test_redistribute_empty_scenes():
    """빈 씬 리스트 → 에러 없이 종료."""
    redistribute_durations([], 10)


# ── try_scene_expand (통합 테스트) ─────────────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes._revise_expand.gemini_client")
@patch("services.agent.nodes._revise_expand.template_env")
@patch("services.agent.nodes._revise_expand.postprocess_new_scenes")
async def test_try_scene_expand_success(mock_postprocess, mock_tenv, mock_gemini):
    """Gemini가 새 씬을 반환하면 기존 씬에 병합한다."""
    from services.agent.nodes._revise_expand import try_scene_expand

    mock_tenv.get_template.return_value.render.return_value = "prompt"

    mock_response = MagicMock()
    mock_response.text = (
        '[{"insert_after": 0, "script": "NEW", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"}]'
    )
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    existing = [
        {"scene_id": 1, "script": "기존 씬 1", "speaker": "A", "duration": 3.0},
        {"scene_id": 2, "script": "기존 씬 2", "speaker": "A", "duration": 3.0},
    ]
    state = {
        "topic": "AI의 미래",
        "duration": 10,
        "language": "Korean",
        "structure": "Monologue",
        "style": "Anime",
    }

    result = await try_scene_expand(existing, state, deficit=1, target_min=3)

    assert result is not None
    assert len(result) == 3
    assert result[1]["script"] == "NEW"  # 중간에 삽입됨


@pytest.mark.asyncio
@patch("services.agent.nodes._revise_expand.gemini_client")
@patch("services.agent.nodes._revise_expand.template_env")
async def test_try_scene_expand_gemini_error(mock_tenv, mock_gemini):
    """Gemini API 에러 → None 반환 (Tier 3 fallback)."""
    from services.agent.nodes._revise_expand import try_scene_expand

    mock_tenv.get_template.return_value.render.return_value = "prompt"
    mock_gemini.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("API error"))

    existing = [{"scene_id": 1, "script": "기존", "speaker": "A", "duration": 3.0}]
    state = {"topic": "테스트", "duration": 10}

    result = await try_scene_expand(existing, state, deficit=2, target_min=3)
    assert result is None


@pytest.mark.asyncio
@patch("services.agent.nodes._revise_expand.gemini_client")
@patch("services.agent.nodes._revise_expand.template_env")
async def test_try_scene_expand_invalid_json(mock_tenv, mock_gemini):
    """잘못된 JSON → None 반환 (Tier 3 fallback)."""
    from services.agent.nodes._revise_expand import try_scene_expand

    mock_tenv.get_template.return_value.render.return_value = "prompt"

    mock_response = MagicMock()
    mock_response.text = "이것은 JSON이 아닙니다"
    mock_gemini.aio.models.generate_content = AsyncMock(return_value=mock_response)

    existing = [{"scene_id": 1, "script": "기존", "speaker": "A", "duration": 3.0}]
    state = {"topic": "테스트", "duration": 10}

    result = await try_scene_expand(existing, state, deficit=2, target_min=3)
    assert result is None


@pytest.mark.asyncio
async def test_try_scene_expand_no_gemini_client():
    """Gemini 클라이언트 없음 → None."""
    from services.agent.nodes._revise_expand import try_scene_expand

    with patch("services.agent.nodes._revise_expand.gemini_client", None):
        result = await try_scene_expand([], {}, deficit=1, target_min=2)
        assert result is None


# ── revise_node 통합: Tier 2 경로 ────────────────────────────


@pytest.mark.asyncio
@patch("services.agent.nodes.revise.try_scene_expand", new_callable=AsyncMock)
async def test_revise_node_tier2_path(mock_expand):
    """씬 부족 에러만 있을 때 Tier 2 확장을 시도한다."""
    from services.agent.nodes.revise import revise_node

    mock_expand.return_value = [
        {"scene_id": 1, "script": "A", "duration": 2.5},
        {"scene_id": 2, "script": "B", "duration": 2.5},
        {"scene_id": 3, "script": "C", "duration": 2.5},
    ]

    state = {
        "draft_scenes": [
            {"scene_id": 1, "script": "A", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"},
            {"scene_id": 2, "script": "B", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"},
        ],
        "review_result": {
            "passed": False,
            "errors": ["씬 개수 부족: 2개 (최소 3개 필요, duration=10s)"],
        },
        "revision_count": 0,
        "duration": 10,
        "topic": "테스트",
    }

    result = await revise_node(state)

    assert mock_expand.called
    assert result["revision_count"] == 1
    assert result["draft_scenes"] is not None


@pytest.mark.asyncio
@patch("services.agent.nodes.revise.try_scene_expand", new_callable=AsyncMock)
@patch("services.agent.nodes.revise.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.revise.get_db_session")
async def test_revise_node_tier2_fail_falls_to_tier3(mock_db, mock_gen, mock_expand):
    """Tier 2 실패 시 Tier 3(전체 재생성)으로 fallback."""
    from services.agent.nodes.revise import revise_node

    mock_expand.return_value = None  # Tier 2 실패
    mock_gen.return_value = {"scenes": [{"script": "재생성"}], "character_id": None, "character_b_id": None}
    mock_db.return_value.__enter__ = MagicMock()
    mock_db.return_value.__exit__ = MagicMock(return_value=False)

    state = {
        "draft_scenes": [{"scene_id": 1, "script": "A", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"}],
        "review_result": {
            "passed": False,
            "errors": ["씬 개수 부족: 1개 (최소 3개 필요, duration=10s)"],
        },
        "revision_count": 0,
        "duration": 10,
        "topic": "테스트",
    }

    result = await revise_node(state)

    assert mock_expand.called
    assert mock_gen.called  # Tier 3 호출됨
    assert result["revision_count"] == 1
