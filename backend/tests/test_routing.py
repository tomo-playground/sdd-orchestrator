"""라우팅 함수 단위 테스트.

routing.py의 조건 분기 함수들을 검증한다.
"""

from __future__ import annotations

from services.agent.routing import (
    route_after_cinematographer,
    route_after_director,
    route_after_director_checkpoint,
    route_after_finalize,
    route_after_research,
    route_after_review,
    route_after_revise,
    route_after_start,
    route_after_writer,
)

# -- Research 되돌리기 분기 테스트 --


def test_route_after_research_good_score():
    """overall >= 0.3 → critic으로 진행."""
    state = {"research_score": {"overall": 0.5}, "research_retry_count": 0}
    assert route_after_research(state) == "critic"


def test_route_after_research_low_score_retry():
    """overall < 0.3 + retry_count=0 → research 재실행."""
    state = {"research_score": {"overall": 0.2}, "research_retry_count": 0}
    assert route_after_research(state) == "research"


def test_route_after_research_max_retries():
    """overall < 0.3 + retry_count > MAX → critic 강제 진행.

    MAX_RETRIES=1: 실행 2회(retry_count=2)면 한도 초과.
    """
    state = {"research_score": {"overall": 0.1}, "research_retry_count": 2}
    assert route_after_research(state) == "critic"
    # retry_count=1이면 아직 재시도 여유 있음
    state_one = {"research_score": {"overall": 0.1}, "research_retry_count": 1}
    assert route_after_research(state_one) == "research"


def test_route_after_research_none_score():
    """score=None → critic (graceful 진행)."""
    state = {"research_score": None, "research_retry_count": 0}
    assert route_after_research(state) == "critic"


def test_route_after_research_error():
    """에러 상태 → finalize."""
    state = {"error": "Research 실패", "research_score": {"overall": 0.5}}
    assert route_after_research(state) == "finalize"


def test_route_after_research_threshold_boundary():
    """overall=0.3 정확히 → critic (경계값, >= 이므로 진행)."""
    state = {"research_score": {"overall": 0.3}, "research_retry_count": 0}
    assert route_after_research(state) == "critic"


# -- 기본 라우팅 테스트 --


def test_routing_fanout_after_cinematographer():
    """cinematographer 이후 → 3개 병렬 fan-out, 에러 시 finalize."""
    result = route_after_cinematographer({})
    assert isinstance(result, list)
    assert set(result) == {"tts_designer", "sound_designer", "copyright_reviewer"}

    assert route_after_cinematographer({"error": "실패"}) == "finalize"


def test_routing_error_short_circuit_writer():
    """writer 에러 → route_after_writer가 finalize 반환."""
    assert route_after_writer({}) == "finalize"  # 빈 씬 → finalize short-circuit
    assert route_after_writer({"error": "Gemini API 실패"}) == "finalize"


def test_routing_error_short_circuit_review():
    """review 진입 시 에러 → finalize로 short-circuit."""
    assert (
        route_after_review({"error": "이전 노드 에러", "skip_stages": ["research", "concept", "production", "explain"]})
        == "finalize"
    )
    assert route_after_review({"error": "이전 노드 에러", "skip_stages": []}) == "finalize"


# -- Director 라우팅 테스트 --


def test_route_after_director_approve_auto():
    """Director approve + auto_approve → finalize."""
    state = {"director_decision": "approve", "auto_approve": True}
    assert route_after_director(state) == "finalize"


def test_route_after_director_approve_manual():
    """Phase 25: Director approve → finalize (human_gate 제거)."""
    state = {"director_decision": "approve", "auto_approve": False}
    assert route_after_director(state) == "finalize"


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
    """Director revision 최대 횟수 도달 시 finalize로 강제 통과 (Phase 25: human_gate 제거)."""
    state = {"director_decision": "revise_cinematographer", "director_revision_count": 3}
    assert route_after_director(state) == "finalize"


def test_route_after_director_error():
    """에러 상태에서는 finalize로 short-circuit."""
    state = {"error": "이전 노드 에러", "director_decision": "approve"}
    assert route_after_director(state) == "finalize"


# -- Revise 에러 short-circuit 테스트 --


def test_route_after_revise_normal():
    """revise 정상 → review."""
    assert route_after_revise({}) == "review"


def test_route_after_revise_error():
    """revise 에러 → finalize (short-circuit)."""
    assert route_after_revise({"error": "Safety filter blocked"}) == "finalize"


# -- Explain / Finalize 라우팅 테스트 --


def test_route_after_finalize_error():
    """finalize 에러 상태 → learn (explain 스킵)."""
    assert route_after_finalize({"error": "이전 에러", "skip_stages": []}) == "learn"


def test_route_after_finalize_full():
    """skip_stages에 explain 없음: finalize → explain."""
    assert route_after_finalize({"skip_stages": []}) == "explain"


def test_route_after_finalize_quick():
    """skip_stages에 explain 포함: finalize → learn."""
    assert route_after_finalize({"skip_stages": ["research", "concept", "production", "explain"]}) == "learn"
    assert route_after_finalize({}) == "explain"  # 기본값: skip_stages 없으면 explain 실행


# -- Director Checkpoint → Writer 라우팅 테스트 --


def test_route_review_pass_full_mode_goes_to_checkpoint():
    """production 미스킵 + review 통과 → director_checkpoint."""
    state = {"skip_stages": [], "review_result": {"passed": True, "errors": []}}
    assert route_after_review(state) == "director_checkpoint"


def test_route_checkpoint_revise_goes_to_writer():
    """Checkpoint revise → writer (revise 노드 아님)."""
    state = {"director_checkpoint_decision": "revise", "director_checkpoint_revision_count": 0}
    assert route_after_director_checkpoint(state) == "writer"


def test_route_start_full_mode_goes_to_director_plan():
    """skip_stages 비어있으면 START → director_plan."""
    assert route_after_start({"skip_stages": []}) == "director_plan"
    assert route_after_start({"skip_stages": ["research", "concept", "production", "explain"]}) == "writer"
    assert route_after_start({}) == "director_plan"  # 기본값: skip_stages 없으면 director_plan


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


# -- skip_stages 부분 스킵 테스트 --


def test_route_start_partial_skip_research_only():
    """Phase 25: skip_stages 있으면 writer 직행 (API override)."""
    assert route_after_start({"skip_stages": ["research"]}) == "writer"


def test_route_start_partial_skip_concept_only():
    """Phase 25: skip_stages 있으면 writer 직행 (API override)."""
    assert route_after_start({"skip_stages": ["concept"]}) == "writer"


def test_route_start_both_research_concept_skipped():
    """research + concept 둘 다 스킵 → writer."""
    assert route_after_start({"skip_stages": ["research", "concept"]}) == "writer"


def test_route_review_production_skipped():
    """production 스킵 + review 통과 → finalize."""
    state = {"skip_stages": ["production"], "review_result": {"passed": True, "errors": []}}
    assert route_after_review(state) == "finalize"


def test_route_review_production_not_skipped():
    """production 미스킵 + review 통과 → director_checkpoint."""
    state = {"skip_stages": ["research", "concept"], "review_result": {"passed": True, "errors": []}}
    assert route_after_review(state) == "director_checkpoint"


def test_route_finalize_explain_not_skipped():
    """explain 미스킵 → explain."""
    assert route_after_finalize({"skip_stages": ["research", "concept", "production"]}) == "explain"


def test_route_finalize_explain_skipped():
    """explain 스킵 → learn."""
    assert route_after_finalize({"skip_stages": ["explain"]}) == "learn"
