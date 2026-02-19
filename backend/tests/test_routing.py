"""라우팅 함수 단위 테스트.

routing.py의 조건 분기 함수들을 검증한다.
"""

from __future__ import annotations

from services.agent.routing import (
    route_after_cinematographer,
    route_after_director,
    route_after_director_checkpoint,
    route_after_finalize,
    route_after_review,
    route_after_start,
    route_after_writer,
)

# -- 기본 라우팅 테스트 --


def test_routing_fanout_after_cinematographer():
    """cinematographer 이후 → 3개 병렬 fan-out, 에러 시 finalize."""
    result = route_after_cinematographer({"mode": "full"})
    assert isinstance(result, list)
    assert set(result) == {"tts_designer", "sound_designer", "copyright_reviewer"}

    assert route_after_cinematographer({"mode": "full", "error": "실패"}) == "finalize"


def test_routing_error_short_circuit_writer():
    """writer 에러 → route_after_writer가 finalize 반환."""
    assert route_after_writer({"mode": "quick"}) == "review"
    assert route_after_writer({"mode": "quick", "error": "Gemini API 실패"}) == "finalize"


def test_routing_error_short_circuit_review():
    """review 진입 시 에러 → finalize로 short-circuit."""
    assert route_after_review({"error": "이전 노드 에러", "mode": "quick"}) == "finalize"
    assert route_after_review({"error": "이전 노드 에러", "mode": "full"}) == "finalize"


# -- Director 라우팅 테스트 --


def test_route_after_director_approve_auto():
    """Director approve + auto_approve → finalize."""
    state = {"director_decision": "approve", "auto_approve": True}
    assert route_after_director(state) == "finalize"


def test_route_after_director_approve_manual():
    """Director approve + auto_approve=False → human_gate."""
    state = {"director_decision": "approve", "auto_approve": False}
    assert route_after_director(state) == "human_gate"


def test_route_after_director_revise_cinematographer():
    """Director가 cinematographer 수정을 요청한다."""
    state = {"director_decision": "revise_cinematographer", "director_revision_count": 0}
    assert route_after_director(state) == "cinematographer"


def test_route_after_director_revise_tts():
    """Director가 tts_designer 수정을 요청한다."""
    state = {"director_decision": "revise_tts", "director_revision_count": 0}
    assert route_after_director(state) == "tts_designer"


def test_route_after_director_revise_sound():
    """Director가 sound_designer 수정을 요청한다."""
    state = {"director_decision": "revise_sound", "director_revision_count": 0}
    assert route_after_director(state) == "sound_designer"


def test_route_after_director_revise_script():
    """Director가 스크립트 수정을 요청한다 → revise."""
    state = {"director_decision": "revise_script", "director_revision_count": 0}
    assert route_after_director(state) == "revise"


def test_route_after_director_max_revisions():
    """Director revision 최대 횟수 도달 시 human_gate로 강제 통과."""
    state = {"director_decision": "revise_cinematographer", "director_revision_count": 3}
    assert route_after_director(state) == "human_gate"


def test_route_after_director_error():
    """에러 상태에서는 finalize로 short-circuit."""
    state = {"error": "이전 노드 에러", "director_decision": "approve"}
    assert route_after_director(state) == "finalize"


# -- Explain / Finalize 라우팅 테스트 --


def test_route_after_finalize_full():
    """Full 모드: finalize → explain."""
    assert route_after_finalize({"mode": "full"}) == "explain"


def test_route_after_finalize_quick():
    """Quick 모드: finalize → learn (explain 스킵)."""
    assert route_after_finalize({"mode": "quick"}) == "learn"
    assert route_after_finalize({}) == "learn"  # 기본값 quick


# -- Director Checkpoint → Writer 라우팅 테스트 --


def test_route_review_pass_full_mode_goes_to_checkpoint():
    """Full 모드 review 통과 → director_checkpoint."""
    state = {"mode": "full", "review_result": {"passed": True, "errors": []}}
    assert route_after_review(state) == "director_checkpoint"


def test_route_checkpoint_revise_goes_to_writer():
    """Checkpoint revise → writer (revise 노드 아님)."""
    state = {"director_checkpoint_decision": "revise", "director_checkpoint_revision_count": 0}
    assert route_after_director_checkpoint(state) == "writer"


def test_route_start_full_mode_goes_to_director_plan():
    """Full 모드 START → director_plan."""
    assert route_after_start({"mode": "full"}) == "director_plan"
    assert route_after_start({"mode": "quick"}) == "writer"
    assert route_after_start({}) == "writer"  # 기본값 quick


# -- Score-Based Checkpoint Routing 테스트 --


def test_route_checkpoint_low_score_logs():
    """Low score (< 0.4) revise 시 writer로 라우팅 (강한 피드백)."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_score": 0.3,
        "director_checkpoint_revision_count": 0,
    }
    assert route_after_director_checkpoint(state) == "writer"


def test_route_checkpoint_mid_score():
    """Mid score (0.4-0.7) revise 시 writer로 라우팅 (기본 피드백)."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_score": 0.55,
        "director_checkpoint_revision_count": 0,
    }
    assert route_after_director_checkpoint(state) == "writer"


def test_route_checkpoint_high_score_proceed():
    """High score (>= 0.7) proceed 시 cinematographer."""
    state = {"director_checkpoint_decision": "proceed", "director_checkpoint_score": 0.8}
    assert route_after_director_checkpoint(state) == "cinematographer"
