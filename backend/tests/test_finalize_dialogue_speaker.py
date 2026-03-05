"""Finalize 노드 — Dialogue speaker 방어 통합 테스트.

Cinematographer가 speaker를 모두 "A"로 리셋하더라도
Finalize에서 ensure_dialogue_speakers()가 A/B 교대 배정하는지 검증.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

import pytest


def _mock_get_db_session(db_session):
    @contextmanager
    def _ctx():
        yield db_session

    return _ctx


def _make_scene(order: int, speaker: str = "A", script: str = "대사") -> dict:
    return {
        "order": order,
        "script": script,
        "speaker": speaker,
        "image_prompt": "1girl, standing" if speaker != "Narrator" else "no_humans, scenery",
        "context_tags": {},
    }


def _base_state(scenes: list[dict], structure: str = "Dialogue") -> dict:
    return {
        "structure": structure,
        "skip_stages": [],
        "character_id": 100,
        "character_b_id": 200,
        "cinematographer_result": {"scenes": scenes},
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }


@pytest.mark.asyncio
async def test_finalize_fixes_all_a_speakers(db_session):
    """Cinematographer가 모든 speaker를 "A"로 리셋 → Finalize가 A/B 교대 배정."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "A") for i in range(6)]
    state = _base_state(scenes)

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert "A" in speakers
    assert "B" in speakers
    # 교대 배정 확인
    assert speakers[0] == "A"
    assert speakers[1] == "B"
    assert speakers[2] == "A"


@pytest.mark.asyncio
async def test_finalize_preserves_correct_ab_speakers(db_session):
    """이미 A/B 올바르게 배정된 경우 → 변경 없음 (멱등성)."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [
        _make_scene(0, "A"),
        _make_scene(1, "B"),
        _make_scene(2, "A"),
        _make_scene(3, "B"),
    ]
    state = _base_state(scenes)

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    assert [s["speaker"] for s in final] == ["A", "B", "A", "B"]


@pytest.mark.asyncio
async def test_finalize_narrator_preserved_in_dialogue(db_session):
    """Narrator 씬은 교대 배정에서 제외."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [
        _make_scene(0, "A"),
        _make_scene(1, "Narrator", "배경 묘사"),
        _make_scene(2, "A"),
        _make_scene(3, "A"),
    ]
    state = _base_state(scenes)

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    assert final[1]["speaker"] == "Narrator"
    non_narrator = [s["speaker"] for s in final if s["speaker"] != "Narrator"]
    assert "A" in non_narrator
    assert "B" in non_narrator


@pytest.mark.asyncio
async def test_finalize_narrated_dialogue_also_defended(db_session):
    """Narrated Dialogue 구조도 동일하게 방어."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "A") for i in range(4)]
    state = _base_state(scenes, structure="Narrated Dialogue")

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert "B" in speakers


@pytest.mark.asyncio
async def test_finalize_monologue_no_speaker_fix(db_session):
    """Monologue 구조 → speaker 교대 배정 미적용."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "A") for i in range(4)]
    state = _base_state(scenes, structure="Monologue")

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert all(s == "A" for s in speakers)


@pytest.mark.asyncio
async def test_finalize_draft_scenes_path_also_defended(db_session):
    """Cinematographer 미사용(draft_scenes 경로)도 speaker 방어 적용."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "A") for i in range(4)]
    state = {
        "structure": "Dialogue",
        "skip_stages": ["production"],
        "character_id": 100,
        "character_b_id": 200,
        "draft_scenes": scenes,
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert "B" in speakers
