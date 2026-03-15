"""_build_production_snapshot() + _extract_quality_gate() + _preflight_safety_check() 단위 테스트."""

from __future__ import annotations

from routers._scripts_sse import _build_production_snapshot, _extract_quality_gate


def test_empty_state_returns_empty():
    """빈 state는 빈 dict를 반환한다."""
    assert _build_production_snapshot({}) == {}


def test_director_plan_only():
    """director_plan만 있을 때 해당 키만 포함."""
    vals = {"director_plan": {"creative_goal": "감동", "target_emotion": "슬픔"}}
    result = _build_production_snapshot(vals)
    assert result == {"director_plan": vals["director_plan"]}


def test_all_production_keys():
    """모든 Production 키가 존재하면 전부 포함."""
    vals = {
        "director_plan": {"creative_goal": "웃음"},
        "cinematographer_result": {"scenes": [{"camera": "close_up"}]},
        "tts_designer_result": {"tts_designs": [{"scene_id": 1}]},
        "sound_designer_result": {"recommendation": {"mood": "epic"}},
        "copyright_reviewer_result": {"overall": "PASS", "checks": []},
        "director_decision": "APPROVED",
        "director_feedback": "Good",
        "director_reasoning_steps": [{"agent": "writer", "message": "ok"}],
        "agent_messages": [{"from": "writer", "to": "director"}],
    }
    result = _build_production_snapshot(vals)
    assert "director_plan" in result
    assert "cinematographer" in result
    assert "tts_designer" in result
    assert "sound_designer" in result
    assert "copyright_reviewer" in result
    assert result["director"]["decision"] == "APPROVED"
    assert result["director"]["feedback"] == "Good"
    assert len(result["director"]["reasoning_steps"]) == 1
    assert "agent_messages" in result


def test_director_decision_without_feedback():
    """director_decision만 있고 feedback/reasoning 없는 경우."""
    vals = {"director_decision": "REVISE"}
    result = _build_production_snapshot(vals)
    assert result["director"]["decision"] == "REVISE"
    assert result["director"]["feedback"] is None
    assert result["director"]["reasoning_steps"] is None


def test_partial_keys():
    """일부 키만 있으면 해당 키만 포함, 나머지는 누락."""
    vals = {
        "cinematographer_result": {"scenes": []},
        "copyright_reviewer_result": {"overall": "WARN"},
    }
    result = _build_production_snapshot(vals)
    assert set(result.keys()) == {"cinematographer", "copyright_reviewer"}
    assert "director_plan" not in result
    assert "tts_designer" not in result
    assert "director" not in result


def test_falsy_values_excluded():
    """None/빈 dict/빈 리스트 등 falsy 값은 제외된다."""
    vals = {
        "director_plan": None,
        "cinematographer_result": {},
        "tts_designer_result": [],
        "agent_messages": [],
    }
    result = _build_production_snapshot(vals)
    assert result == {}


# --- _extract_quality_gate() 단위 테스트 ---


def test_quality_gate_empty_returns_none():
    """review_result도 checkpoint도 없으면 None."""
    assert _extract_quality_gate({}) is None


def test_quality_gate_review_only():
    """review_result만 있을 때 해당 필드만 포함."""
    vals = {
        "review_result": {
            "passed": True,
            "user_summary": "구조 검증 통과",
            "narrative_score": {"overall": 0.73, "hook": 0.8},
        },
    }
    gate = _extract_quality_gate(vals)
    assert gate is not None
    assert gate["review_passed"] is True
    assert gate["review_summary"] == "구조 검증 통과"
    assert gate["narrative_score"]["overall"] == 0.73
    assert "checkpoint_score" not in gate


def test_quality_gate_checkpoint_only():
    """checkpoint만 있을 때 해당 필드만 포함."""
    vals = {
        "director_checkpoint_decision": "proceed",
        "director_checkpoint_score": 0.82,
    }
    gate = _extract_quality_gate(vals)
    assert gate is not None
    assert gate["checkpoint_decision"] == "proceed"
    assert gate["checkpoint_score"] == 0.82
    assert "review_passed" not in gate


def test_quality_gate_both():
    """review + checkpoint 모두 있을 때 합산."""
    vals = {
        "review_result": {"passed": False, "user_summary": "에러 2건"},
        "director_checkpoint_decision": "revise",
        "director_checkpoint_score": 0.45,
    }
    gate = _extract_quality_gate(vals)
    assert gate is not None
    assert gate["review_passed"] is False
    assert gate["checkpoint_decision"] == "revise"


# --- snapshot에 새 필드 포함 테스트 ---


def test_snapshot_includes_quality_gate():
    """quality_gate가 snapshot에 포함된다."""
    vals = {
        "review_result": {"passed": True, "user_summary": "OK"},
        "director_checkpoint_decision": "proceed",
        "director_checkpoint_score": 0.9,
    }
    snap = _build_production_snapshot(vals)
    assert "quality_gate" in snap
    assert snap["quality_gate"]["checkpoint_score"] == 0.9


def test_snapshot_includes_revision_history():
    """revision_history가 그대로 전달된다."""
    history = [
        {"attempt": 1, "errors": ["err1"], "tier": "rule_fix"},
        {"attempt": 2, "reflection": "fixed", "score": 0.8, "tier": "expansion"},
    ]
    snap = _build_production_snapshot({"revision_history": history})
    assert snap["revision_history"] == history


def test_snapshot_includes_debate_log():
    """debate_log가 그대로 전달된다."""
    log = [{"round": 1, "action": "propose", "concepts": []}]
    snap = _build_production_snapshot({"debate_log": log})
    assert snap["debate_log"] == log


def test_snapshot_backward_compat_no_new_fields():
    """새 필드가 없는 state에서 기존 동작이 변경되지 않음."""
    vals = {"director_plan": {"creative_goal": "x"}}
    snap = _build_production_snapshot(vals)
    assert "quality_gate" not in snap
    assert "revision_history" not in snap
    assert "debate_log" not in snap

