"""Duration 부족 검증 및 보정 테스트.

Review 노드 총 duration 검증, Revise Tier 1.5, Finalize 보정을 커버한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import DURATION_DEFICIT_THRESHOLD
from services.agent.nodes._revise_expand import redistribute_durations
from services.agent.nodes.review import _validate_scenes

# ── Review: 총 duration 검증 ─────────────────────────────────


def test_review_duration_deficit_error():
    """총 duration < 85% target → 에러 발생."""
    scenes = [
        {"script": "짧은 대사", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"},
        {"script": "두번째 대사", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"},
    ]
    result = _validate_scenes(scenes, duration=45, language="Korean", structure="Monologue")
    duration_errors = [e for e in result["errors"] if "총 duration 부족" in e]
    assert len(duration_errors) == 1
    assert "38.2" in duration_errors[0] or "6.0" in duration_errors[0]


def test_review_duration_sufficient_no_error():
    """총 duration >= 85% target → duration 에러 없음."""
    scenes = [
        {"script": "대사 하나", "speaker": "A", "duration": 5.0, "image_prompt": "1girl"},
        {"script": "대사 둘", "speaker": "A", "duration": 5.0, "image_prompt": "1girl"},
    ]
    result = _validate_scenes(scenes, duration=10, language="Korean", structure="Monologue")
    duration_errors = [e for e in result["errors"] if "총 duration 부족" in e]
    assert len(duration_errors) == 0


def test_review_duration_exact_target_no_error():
    """총 duration == target → 에러 없음."""
    scenes = [
        {"script": "대사 하나", "speaker": "A", "duration": 5.0, "image_prompt": "1girl"},
        {"script": "대사 둘", "speaker": "A", "duration": 5.0, "image_prompt": "1girl"},
        {"script": "대사 셋", "speaker": "A", "duration": 5.0, "image_prompt": "1girl"},
    ]
    result = _validate_scenes(scenes, duration=15, language="Korean", structure="Monologue")
    duration_errors = [e for e in result["errors"] if "총 duration 부족" in e]
    assert len(duration_errors) == 0


# ── Redistribute: 스케일업 ────────────────────────────────────


def test_redistribute_scale_up_33_to_45():
    """33.5s → 45s 비례 확대 검증 (실제 케이스 재현)."""
    scenes = [
        {"duration": 4.0, "script": "첫 번째 대사"},
        {"duration": 5.0, "script": "두 번째 대사입니다"},
        {"duration": 4.5, "script": "세 번째"},
        {"duration": 5.0, "script": "네 번째 대사"},
        {"duration": 5.0, "script": "다섯 번째"},
        {"duration": 5.0, "script": "여섯 번째"},
        {"duration": 5.0, "script": "일곱 번째"},
    ]
    redistribute_durations(scenes, 45)
    total = sum(s["duration"] for s in scenes)
    assert total >= 45 * DURATION_DEFICIT_THRESHOLD


def test_redistribute_gap_correction():
    """gap > 0.5 시 균등 분배 검증."""
    scenes = [
        {"duration": 2.0, "script": "A"},
        {"duration": 2.0, "script": "B"},
        {"duration": 2.0, "script": "C"},
    ]
    redistribute_durations(scenes, 15)
    total = sum(s["duration"] for s in scenes)
    assert total >= 14.0


# ── Finalize: duration 보정 ───────────────────────────────────


def test_finalize_ensure_minimum_duration_triggers():
    """total < 85% target → redistribute 호출."""
    from services.agent.nodes.finalize import _ensure_minimum_duration

    scenes = [
        {"duration": 3.0, "script": "A"},
        {"duration": 3.0, "script": "B"},
        {"duration": 3.0, "script": "C"},
    ]
    _ensure_minimum_duration(scenes, target_duration=45, language="Korean")
    total = sum(s["duration"] for s in scenes)
    # redistribute가 호출되어 duration이 증가해야 함
    assert total > 9.0


def test_finalize_ensure_minimum_duration_skips():
    """total >= 85% target → 스킵."""
    from services.agent.nodes.finalize import _ensure_minimum_duration

    scenes = [
        {"duration": 5.0, "script": "A"},
        {"duration": 5.0, "script": "B"},
    ]
    _ensure_minimum_duration(scenes, target_duration=10, language="Korean")
    # 변경 없음
    assert scenes[0]["duration"] == 5.0
    assert scenes[1]["duration"] == 5.0


# ── Revise Tier 1.5: duration 재분배 ─────────────────────────


@pytest.mark.asyncio
async def test_revise_tier15_duration_redistribute():
    """duration 부족 에러 → redistribute → 해결 시 Tier 1.5 반환."""
    from services.agent.nodes.revise import revise_node

    scenes = [
        {"scene_id": 1, "script": "첫 대사입니다", "speaker": "A", "duration": 4.0, "image_prompt": "1girl"},
        {"scene_id": 2, "script": "두번째 대사", "speaker": "A", "duration": 3.5, "image_prompt": "1girl"},
        {"scene_id": 3, "script": "세번째 대사입니다", "speaker": "A", "duration": 4.0, "image_prompt": "1girl"},
        {"scene_id": 4, "script": "네번째 대사", "speaker": "A", "duration": 3.5, "image_prompt": "1girl"},
        {"scene_id": 5, "script": "다섯번째 대사입니다", "speaker": "A", "duration": 4.0, "image_prompt": "1girl"},
        {"scene_id": 6, "script": "여섯번째 대사", "speaker": "A", "duration": 3.5, "image_prompt": "1girl"},
        {"scene_id": 7, "script": "일곱번째 대사입니다", "speaker": "A", "duration": 4.0, "image_prompt": "1girl"},
    ]
    state = {
        "draft_scenes": scenes,
        "review_result": {
            "passed": False,
            "errors": ["총 duration 부족: 26.5s (목표 45s의 85% = 38.2s 미달)"],
        },
        "revision_count": 0,
        "duration": 45,
        "language": "Korean",
        "topic": "테스트",
    }

    result = await revise_node(state)

    assert result["revision_count"] == 1
    assert result.get("draft_scenes") is not None
    history = result.get("revision_history", [])
    assert any(h.get("tier") == "duration_redistribute" for h in history)


@pytest.mark.asyncio
@patch("services.agent.nodes.revise.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.revise.get_db_session")
async def test_revise_tier15_fails_to_tier3(mock_db, mock_gen):
    """redistribute로 해결 불가 → Tier 3 진행."""
    from services.agent.nodes.revise import revise_node

    mock_gen.return_value = {"scenes": [{"script": "재생성"}], "character_id": None, "character_b_id": None}
    mock_db.return_value.__enter__ = MagicMock()
    mock_db.return_value.__exit__ = MagicMock(return_value=False)

    # duration이 매우 부족한 상태 (2씬만 있고 target=60)
    state = {
        "draft_scenes": [
            {"scene_id": 1, "script": "A", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"},
            {"scene_id": 2, "script": "B", "speaker": "A", "duration": 3.0, "image_prompt": "1girl"},
        ],
        "review_result": {
            "passed": False,
            "errors": [
                "총 duration 부족: 6.0s (목표 60s의 85% = 51.0s 미달)",
                "씬 개수 부족: 2개 (최소 8개 필요, duration=60s)",
            ],
        },
        "revision_count": 0,
        "duration": 60,
        "language": "Korean",
        "topic": "테스트",
    }

    result = await revise_node(state)

    assert result["revision_count"] == 1
    # Tier 3 (재생성)이 호출되었어야 함
    assert mock_gen.called
