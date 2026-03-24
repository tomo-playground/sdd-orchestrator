"""Finalize 노드 — Dialogue speaker 방어 통합 테스트.

Cinematographer가 speaker를 모두 "speaker_1"로 리셋하더라도
Finalize에서 ensure_dialogue_speakers()가 speaker_1/speaker_2 교대 배정하는지 검증.
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


def _make_scene(order: int, speaker: str = "speaker_1", script: str = "대사") -> dict:
    return {
        "order": order,
        "script": script,
        "speaker": speaker,
        "image_prompt": "1girl, standing" if speaker != "narrator" else "no_humans, scenery",
        "context_tags": {},
    }


def _base_state(scenes: list[dict], structure: str = "dialogue") -> dict:
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
    """Cinematographer가 모든 speaker를 "speaker_1"로 리셋 → Finalize가 speaker_1/speaker_2 교대 배정."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "speaker_1") for i in range(6)]
    state = _base_state(scenes)

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert "speaker_1" in speakers
    assert "speaker_2" in speakers
    # 교대 배정 확인
    assert speakers[0] == "speaker_1"
    assert speakers[1] == "speaker_2"
    assert speakers[2] == "speaker_1"


@pytest.mark.asyncio
async def test_finalize_preserves_correct_ab_speakers(db_session):
    """이미 speaker_1/speaker_2 올바르게 배정된 경우 → 변경 없음 (멱등성)."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [
        _make_scene(0, "speaker_1"),
        _make_scene(1, "speaker_2"),
        _make_scene(2, "speaker_1"),
        _make_scene(3, "speaker_2"),
    ]
    state = _base_state(scenes)

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    assert [s["speaker"] for s in final] == ["speaker_1", "speaker_2", "speaker_1", "speaker_2"]


@pytest.mark.asyncio
async def test_finalize_narrator_preserved_in_dialogue(db_session):
    """Narrator 씬은 교대 배정에서 제외."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [
        _make_scene(0, "speaker_1"),
        _make_scene(1, "narrator", "배경 묘사"),
        _make_scene(2, "speaker_1"),
        _make_scene(3, "speaker_1"),
    ]
    state = _base_state(scenes)

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    assert final[1]["speaker"] == "narrator"
    non_narrator = [s["speaker"] for s in final if s["speaker"] != "narrator"]
    assert "speaker_1" in non_narrator
    assert "speaker_2" in non_narrator


@pytest.mark.asyncio
async def test_finalize_narrated_dialogue_also_defended(db_session):
    """Narrated Dialogue 구조도 동일하게 방어."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "speaker_1") for i in range(4)]
    state = _base_state(scenes, structure="narrated_dialogue")

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert "speaker_2" in speakers


@pytest.mark.asyncio
async def test_finalize_monologue_no_speaker_fix(db_session):
    """Monologue 구조 → speaker 교대 배정 미적용."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "speaker_1") for i in range(4)]
    state = _base_state(scenes, structure="monologue")

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    final = result["final_scenes"]
    speakers = [s["speaker"] for s in final]
    assert all(s == "speaker_1" for s in speakers)


@pytest.mark.asyncio
async def test_finalize_draft_scenes_path_also_defended(db_session):
    """Cinematographer 미사용(draft_scenes 경로)도 speaker 방어 적용."""
    from services.agent.nodes.finalize import finalize_node

    scenes = [_make_scene(i, "speaker_1") for i in range(4)]
    state = {
        "structure": "dialogue",
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
    assert "speaker_2" in speakers
