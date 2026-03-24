"""_validate_scene_modes() 직접 테스트 — SP-059."""

from __future__ import annotations

from services.agent.nodes.finalize import _validate_scene_modes


def _make_scenes(*modes: str) -> list[dict]:
    return [{"order": i, "scene_mode": m, "speaker": "speaker_1"} for i, m in enumerate(modes)]


# --- O-2c: 구조 기반 차단 ---


def test_monologue_forces_all_single():
    scenes = _make_scenes("multi", "single", "multi")
    _validate_scene_modes(scenes, "monologue", {"character_b_id": 5})
    assert all(s["scene_mode"] == "single" for s in scenes)


def test_dialogue_allows_multi():
    scenes = _make_scenes("single", "multi")
    _validate_scene_modes(scenes, "dialogue", {"character_b_id": 5})
    assert scenes[1]["scene_mode"] == "multi"


def test_narrated_dialogue_allows_multi():
    scenes = _make_scenes("single", "multi")
    _validate_scene_modes(scenes, "narrated_dialogue", {"character_b_id": 5})
    assert scenes[1]["scene_mode"] == "multi"


def test_narrated_dialogue_underscore_matching():
    """coerce_structure_id()로 'narrated_dialogue' → MULTI_CHAR_STRUCTURES 매칭 확인."""
    scenes = _make_scenes("multi")
    _validate_scene_modes(scenes, "narrated_dialogue", {"character_b_id": 5})
    assert scenes[0]["scene_mode"] == "multi"


# --- O-2b: character_b_id 없으면 single ---


def test_no_char_b_forces_single():
    scenes = _make_scenes("multi", "multi")
    _validate_scene_modes(scenes, "dialogue", {})
    assert all(s["scene_mode"] == "single" for s in scenes)


# --- O-2e: Narrator + multi 모순 ---


def test_narrator_speaker_forces_single():
    scenes = [{"order": 0, "scene_mode": "multi", "speaker": "narrator"}]
    _validate_scene_modes(scenes, "dialogue", {"character_b_id": 5})
    assert scenes[0]["scene_mode"] == "single"


# --- O-2d: 상한 캡 ---


def test_cap_multi_at_2():
    scenes = _make_scenes("multi", "single", "multi", "multi")
    _validate_scene_modes(scenes, "dialogue", {"character_b_id": 5})
    modes = [s["scene_mode"] for s in scenes]
    assert modes == ["multi", "single", "multi", "single"]


def test_cap_preserves_first_two():
    scenes = _make_scenes("multi", "multi", "multi", "multi")
    _validate_scene_modes(scenes, "dialogue", {"character_b_id": 5})
    modes = [s["scene_mode"] for s in scenes]
    assert modes == ["multi", "multi", "single", "single"]


# --- 정상 케이스 ---


def test_zero_multi_no_change():
    scenes = _make_scenes("single", "single", "single")
    _validate_scene_modes(scenes, "dialogue", {"character_b_id": 5})
    assert all(s["scene_mode"] == "single" for s in scenes)
