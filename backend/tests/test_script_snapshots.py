"""스냅샷 기반 회귀 테스트 — Phase 1 Graph 전환 시 동일 출력 구조 보장.

10건의 request/response fixture를 로드하여:
1. Graph에 request를 입력 (generate_script mock)
2. 출력 구조가 스냅샷 response와 일치하는지 검증
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services.agent.script_graph import build_script_graph
from services.agent.state import ScriptState

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"


def _load_snapshots() -> list[tuple[str, dict]]:
    """스냅샷 파일 전체를 로드한다."""
    snapshots = []
    for p in sorted(SNAPSHOTS_DIR.glob("snapshot_*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        snapshots.append((p.stem, data))
    return snapshots


def _build_state_from_request(req: dict) -> ScriptState:
    """스냅샷의 request를 ScriptState로 변환한다."""
    return ScriptState(
        topic=req["topic"],
        description=req.get("description", ""),
        duration=req.get("duration", 10),
        style=req.get("style", "Anime"),
        language=req.get("language", "Korean"),
        structure=req.get("structure", "Monologue"),
        actor_a_gender=req.get("actor_a_gender", "female"),
        character_id=req.get("character_id"),
        character_b_id=req.get("character_b_id"),
        group_id=req.get("group_id"),
    )


def _validate_scene_structure(actual_scene: dict, expected_scene: dict) -> list[str]:
    """씬의 구조적 일치를 검증한다. 값이 아닌 키/타입 수준."""
    errors = []
    required_keys = {"script", "speaker", "duration", "image_prompt"}
    for key in required_keys:
        if key not in actual_scene:
            errors.append(f"Missing key: {key}")

    if not isinstance(actual_scene.get("script"), str):
        errors.append(f"script should be str, got {type(actual_scene.get('script'))}")
    if not isinstance(actual_scene.get("duration"), (int, float)):
        errors.append(f"duration should be number, got {type(actual_scene.get('duration'))}")

    # speaker 유효값 검증
    valid_speakers = {"Narrator", "A", "B"}
    if actual_scene.get("speaker") not in valid_speakers:
        errors.append(f"Invalid speaker: {actual_scene.get('speaker')}")

    return errors


@pytest.fixture(params=_load_snapshots(), ids=lambda x: x[0])
def snapshot(request):
    """각 스냅샷 파일을 parametrize한다."""
    return request.param[1]


@pytest.mark.asyncio
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.SessionLocal")
async def test_graph_output_matches_snapshot_structure(
    mock_session_cls, mock_gen_script, snapshot
):
    """Graph 실행 결과가 스냅샷 response와 구조적으로 일치하는지 검증."""
    expected = snapshot["response"]
    mock_gen_script.return_value = expected

    graph = build_script_graph().compile()
    input_state = _build_state_from_request(snapshot["request"])
    result = await graph.ainvoke(input_state)

    # 1. final_scenes 존재
    assert result["final_scenes"] is not None, "final_scenes is None"

    # 2. 씬 개수 일치
    assert len(result["final_scenes"]) == len(expected["scenes"]), (
        f"Scene count mismatch: {len(result['final_scenes'])} vs {len(expected['scenes'])}"
    )

    # 3. 각 씬 구조 검증
    for i, (actual, exp) in enumerate(zip(result["final_scenes"], expected["scenes"], strict=True)):
        errors = _validate_scene_structure(actual, exp)
        assert not errors, f"Scene {i} structural errors: {errors}"

    # 4. character_id 전파
    if expected.get("character_id"):
        assert result.get("draft_character_id") == expected["character_id"]
    if expected.get("character_b_id"):
        assert result.get("draft_character_b_id") == expected["character_b_id"]


@pytest.mark.asyncio
@patch("services.agent.nodes.draft.generate_script", new_callable=AsyncMock)
@patch("services.agent.nodes.draft.SessionLocal")
async def test_graph_passthrough_preserves_scenes(mock_session_cls, mock_gen_script, snapshot):
    """Phase 0 패스스루: draft_scenes == final_scenes (데이터 손실 없음)."""
    mock_gen_script.return_value = snapshot["response"]

    graph = build_script_graph().compile()
    input_state = _build_state_from_request(snapshot["request"])
    result = await graph.ainvoke(input_state)

    assert result["draft_scenes"] == result["final_scenes"], "Passthrough violated: draft != final"


def test_all_snapshots_loaded():
    """스냅샷 10건이 모두 로드되는지 확인한다."""
    snapshots = _load_snapshots()
    assert len(snapshots) == 10, f"Expected 10 snapshots, found {len(snapshots)}"


def test_snapshot_request_schema():
    """모든 스냅샷 request가 필수 필드를 포함하는지 확인한다."""
    required_fields = {"topic", "duration", "language", "structure"}
    for name, data in _load_snapshots():
        req = data["request"]
        missing = required_fields - set(req.keys())
        assert not missing, f"{name} missing request fields: {missing}"


def test_snapshot_response_schema():
    """모든 스냅샷 response가 scenes 배열을 포함하는지 확인한다."""
    for name, data in _load_snapshots():
        resp = data["response"]
        assert "scenes" in resp, f"{name} missing 'scenes' in response"
        assert len(resp["scenes"]) > 0, f"{name} has empty scenes"
        for i, scene in enumerate(resp["scenes"]):
            assert "script" in scene, f"{name} scene {i} missing 'script'"
            assert "speaker" in scene, f"{name} scene {i} missing 'speaker'"
