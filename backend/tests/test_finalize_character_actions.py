"""Finalize 노드 — character_actions 변환 + context_tags fallback 통합 테스트."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from config import DEFAULT_SCENE_NEGATIVE_PROMPT

# ── P0-2: _inject_default_context_tags 단위 테스트 ────────────────────


class TestInjectDefaultContextTags:
    """_inject_default_context_tags가 pose/gaze 기본값을 올바르게 주입한다."""

    def test_missing_pose_and_gaze_injected(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"emotion": "happy"}}]
        _inject_default_context_tags(scenes)

        assert scenes[0]["context_tags"]["pose"] == "standing"
        assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"
        assert scenes[0]["context_tags"]["expression"] == "smile"
        assert scenes[0]["context_tags"]["emotion"] == "happy"  # preserved

    def test_existing_pose_preserved(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A", "context_tags": {"pose": "sitting"}}]
        _inject_default_context_tags(scenes)

        assert scenes[0]["context_tags"]["pose"] == "sitting"
        assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"
        assert scenes[0]["context_tags"]["expression"] == "smile"

    def test_narrator_skipped(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "Narrator", "context_tags": {"mood": "dark"}}]
        _inject_default_context_tags(scenes)

        assert "pose" not in scenes[0]["context_tags"]
        assert "gaze" not in scenes[0]["context_tags"]

    def test_none_context_tags_creates_new(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [{"speaker": "A"}]
        _inject_default_context_tags(scenes)

        assert scenes[0]["context_tags"] == {
            "pose": "standing",
            "gaze": "looking_at_viewer",
            "expression": "smile",
        }

    def test_mixed_speakers(self):
        from services.agent.nodes.finalize import _inject_default_context_tags

        scenes = [
            {"speaker": "A", "context_tags": {"pose": "walking"}},
            {"speaker": "Narrator"},
            {"speaker": "B", "context_tags": {}},
        ]
        _inject_default_context_tags(scenes)

        assert scenes[0]["context_tags"]["pose"] == "walking"  # preserved
        assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"  # injected
        assert "context_tags" not in scenes[1] or "pose" not in scenes[1].get("context_tags", {})
        assert scenes[2]["context_tags"]["pose"] == "standing"
        assert scenes[2]["context_tags"]["gaze"] == "looking_at_viewer"
        assert scenes[2]["context_tags"]["expression"] == "smile"


def _mock_get_db_session(db_session):
    """테스트용 get_db_session mock — 실제 db_session을 context manager로 래핑."""

    @contextmanager
    def _ctx():
        yield db_session

    return _ctx


@pytest.mark.asyncio
async def test_finalize_populates_character_actions(db_session):
    """Full 모드: context_tags 있는 scenes → finalize 후 character_actions 포함."""
    from models.tag import Tag
    from services.agent.nodes.finalize import finalize_node

    # Seed tags
    for name, cat, layer in [("smile", "expression", 7), ("standing", "pose", 8)]:
        db_session.add(Tag(name=name, category=cat, default_layer=layer))
    db_session.flush()

    state = {
        "skip_stages": [],
        "character_id": 100,
        "character_b_id": None,
        "cinematographer_result": {
            "scenes": [
                {
                    "order": 0,
                    "script": "씬1",
                    "speaker": "A",
                    "image_prompt": "1girl, smile, standing",
                    "context_tags": {"expression": ["smile"], "pose": ["standing"]},
                },
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    scenes = result["final_scenes"]
    assert len(scenes) == 1
    assert "character_actions" in scenes[0]
    assert len(scenes[0]["character_actions"]) == 2
    assert all(a["character_id"] == 100 for a in scenes[0]["character_actions"])


@pytest.mark.asyncio
async def test_finalize_narrator_no_character_actions(db_session):
    """Narrator 씬 → character_actions 미생성."""
    from models.tag import Tag
    from services.agent.nodes.finalize import finalize_node

    db_session.add(Tag(name="smile", category="expression", default_layer=7))
    db_session.flush()

    state = {
        "skip_stages": [],
        "character_id": 100,
        "character_b_id": None,
        "cinematographer_result": {
            "scenes": [
                {
                    "order": 0,
                    "script": "배경 묘사",
                    "speaker": "Narrator",
                    "image_prompt": "no_humans, scenery",
                    "context_tags": {"environment": ["night"]},
                },
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    scenes = result["final_scenes"]
    assert "character_actions" not in scenes[0]


@pytest.mark.asyncio
async def test_finalize_fallback_injects_default_pose_gaze(db_session):
    """context_tags에 pose/gaze/expression 없으면 기본값 주입 → DB 태그 있으면 character_actions 생성."""
    from models.tag import Tag
    from services.agent.nodes.finalize import finalize_node

    # Seed tags matching defaults (올바른 카테고리 필수 — compound-key 매칭)
    db_session.add(Tag(name="standing", category="pose", default_layer=8))
    db_session.add(Tag(name="looking_at_viewer", category="gaze", default_layer=7))
    db_session.add(Tag(name="smile", category="expression", default_layer=7))
    db_session.flush()

    state = {
        "skip_stages": [],
        "character_id": 100,
        "character_b_id": None,
        "cinematographer_result": {
            "scenes": [
                {
                    "order": 0,
                    "script": "씬1",
                    "speaker": "A",
                    "image_prompt": "1girl",
                    "context_tags": {"camera": ["close-up"], "environment": ["kitchen"]},
                },
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    scenes = result["final_scenes"]
    # Fallback injected pose/gaze/expression + DB tags exist → character_actions created
    assert "character_actions" in scenes[0]
    assert len(scenes[0]["character_actions"]) == 3


@pytest.mark.asyncio
async def test_finalize_no_context_tags_creates_defaults(db_session):
    """context_tags가 None이면 기본 context_tags 생성."""
    from models.tag import Tag
    from services.agent.nodes.finalize import finalize_node

    db_session.add(Tag(name="standing", category="pose", default_layer=8))
    db_session.add(Tag(name="looking_at_viewer", category="gaze", default_layer=7))
    db_session.add(Tag(name="smile", category="expression", default_layer=7))
    db_session.flush()

    state = {
        "skip_stages": [],
        "character_id": 100,
        "character_b_id": None,
        "cinematographer_result": {
            "scenes": [
                {
                    "order": 0,
                    "script": "씬1",
                    "speaker": "A",
                    "image_prompt": "1girl",
                    # context_tags 완전 누락
                },
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    scenes = result["final_scenes"]
    assert scenes[0]["context_tags"]["pose"] == "standing"
    assert scenes[0]["context_tags"]["gaze"] == "looking_at_viewer"
    assert scenes[0]["context_tags"]["expression"] == "smile"
    assert "character_actions" in scenes[0]


@pytest.mark.asyncio
async def test_finalize_preserves_existing_pose_gaze(db_session):
    """이미 pose/gaze가 있으면 기본값으로 덮어쓰지 않음."""
    from models.tag import Tag
    from services.agent.nodes.finalize import finalize_node

    db_session.add(Tag(name="sitting", category="pose", default_layer=8))
    db_session.add(Tag(name="looking_down", category="gaze", default_layer=7))
    db_session.add(Tag(name="crying", category="expression", default_layer=7))
    db_session.flush()

    state = {
        "skip_stages": [],
        "character_id": 100,
        "character_b_id": None,
        "cinematographer_result": {
            "scenes": [
                {
                    "order": 0,
                    "script": "씬1",
                    "speaker": "A",
                    "image_prompt": "1girl",
                    "context_tags": {"pose": "sitting", "gaze": "looking_down", "expression": "crying"},
                },
            ],
        },
        "tts_designer_result": {"tts_designs": []},
        "sound_designer_result": None,
        "copyright_reviewer_result": None,
    }

    with patch("services.agent.nodes.finalize.get_db_session", _mock_get_db_session(db_session)):
        result = await finalize_node(state, {})

    scenes = result["final_scenes"]
    assert scenes[0]["context_tags"]["pose"] == "sitting"  # preserved
    assert scenes[0]["context_tags"]["gaze"] == "looking_down"  # preserved
    assert scenes[0]["context_tags"]["expression"] == "crying"  # preserved


@pytest.mark.asyncio
async def test_finalize_without_character_id_still_works():
    """캐릭터 ID 없으면 character_actions 변환 건너뜀."""
    from services.agent.nodes.finalize import finalize_node

    state = {
        "skip_stages": ["research", "concept", "production", "explain"],
        "character_id": None,
        "character_b_id": None,
        "draft_scenes": [
            {"order": 0, "script": "퀵 씬", "speaker": "A"},
        ],
    }

    result = await finalize_node(state, {})

    scenes = result["final_scenes"]
    assert len(scenes) == 1
    assert scenes[0]["negative_prompt"] == DEFAULT_SCENE_NEGATIVE_PROMPT


@pytest.mark.asyncio
async def test_finalize_error_state_propagated():
    """에러 상태이면 character_actions 변환 없이 즉시 반환."""
    from services.agent.nodes.finalize import finalize_node

    state = {
        "error": "Writer 안전 필터 차단",
        "character_id": 100,
        "character_b_id": None,
    }

    result = await finalize_node(state, {})

    assert result["error"] == "Writer 안전 필터 차단"
    assert "final_scenes" not in result
