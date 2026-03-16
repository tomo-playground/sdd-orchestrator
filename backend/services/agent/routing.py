"""조건 분기 함수 — Graph 엣지에서 사용하는 라우팅 로직.

script_graph.py의 파일 크기를 줄이기 위해 분리.
"""

from __future__ import annotations

from config import LANGGRAPH_MAX_REVISIONS, logger
from config_pipelines import (
    LANGGRAPH_CHECKPOINT_LOW_THRESHOLD,
    LANGGRAPH_MAX_CHECKPOINT_REVISIONS,
    LANGGRAPH_MAX_DIRECTOR_REVISIONS,
    LANGGRAPH_MAX_GLOBAL_REVISIONS,
    RESEARCH_MAX_RETRIES,
    RESEARCH_QUALITY_LOW,
)
from services.agent.state import ScriptState

_DIRECTOR_DECISION_MAP: dict[str, str] = {
    "revise_cinematographer": "cinematographer",
    "revise_tts": "tts_designer",
    "revise_sound": "sound_designer",
    "revise_script": "revise",
}


def _has_error(state: ScriptState) -> bool:
    """에러 상태인지 확인."""
    return bool(state.get("error"))


def _total_revisions(state: ScriptState) -> int:
    """전체 리비전 횟수를 파생 계산한다 (state 필드 추가 없이).

    review-revise + director checkpoint + director post-production 합산.
    """
    return (
        state.get("revision_count", 0)
        + state.get("director_checkpoint_revision_count", 0)
        + state.get("director_revision_count", 0)
    )


def route_after_start(state: ScriptState) -> str:
    """START 이후: Director가 항상 실행.

    외부 override(skip_stages 직접 지정) 시에만 writer 직행.
    """
    skip = state.get("skip_stages") or []
    if skip:  # API에서 skip_stages를 직접 지정한 경우 (테스트/디버깅용)
        return "writer"
    return "director_plan"


def route_after_inventory_resolve(state: ScriptState) -> str:
    """inventory_resolve 이후: Express → writer 직행, Full → research."""
    skip = state.get("skip_stages") or []
    if "research" in skip:
        return "writer"
    return "research"


def route_after_research(state: ScriptState) -> str:
    """Research 이후: 점수 기반 재실행 분기.

    - 에러 → finalize
    - score None 또는 >= RESEARCH_QUALITY_LOW → critic (진행)
    - score < RESEARCH_QUALITY_LOW + 재시도 여유 → research (재실행)
    - 재시도 한도 도달 → critic (강제 진행)
    """
    if _has_error(state):
        return "finalize"

    score = state.get("research_score")
    if score is None:
        return "critic"

    overall = score.get("overall", 0.0) if isinstance(score, dict) else 0.0
    if overall >= RESEARCH_QUALITY_LOW:
        return "critic"

    # retry_count = 실행 횟수 (노드 실행 후 증분). MAX_RETRIES=1이면 재시도 1회 허용 (총 2회)
    retry_count = state.get("research_retry_count", 0)
    if retry_count > RESEARCH_MAX_RETRIES:
        logger.warning(
            "[LangGraph] Research 재시도 한도(%d) 도달 (score=%.2f), critic으로 강제 진행",
            RESEARCH_MAX_RETRIES,
            overall,
        )
        return "critic"

    logger.info("[LangGraph] Research 점수 낮음 (%.2f < %.2f), 재실행", overall, RESEARCH_QUALITY_LOW)
    return "research"


def route_after_writer(state: ScriptState) -> str:
    """writer 이후: 에러/빈 씬 → finalize (short-circuit), 정상 → review."""
    if _has_error(state):
        logger.warning("[LangGraph] writer 에러, finalize로 short-circuit")
        return "finalize"
    if not state.get("draft_scenes"):
        logger.warning("[LangGraph] writer 빈 씬, finalize로 short-circuit")
        return "finalize"
    return "review"


def route_after_revise(state: ScriptState) -> str:
    """revise 이후: 에러 → finalize (short-circuit), 정상 → review."""
    if _has_error(state):
        logger.warning("[LangGraph] revise 에러, finalize로 short-circuit")
        return "finalize"
    return "review"


def route_after_review(state: ScriptState) -> str:
    """review 이후: passed → cinematographer(full)/finalize(quick), failed → revise.

    Quick → finalize 직행, Full → cinematographer (Production chain 시작).
    에러 상태이면 즉시 finalize로 short-circuit.
    """
    if _has_error(state):
        logger.warning("[LangGraph] review 진입 시 에러 발견, finalize로 short-circuit")
        return "finalize"

    result = state.get("review_result")
    passed = result.get("passed") if result else False

    # 실패했으나 revision 여유가 있으면 revise
    if not passed:
        count = state.get("revision_count", 0)
        total = _total_revisions(state)
        if total >= LANGGRAPH_MAX_GLOBAL_REVISIONS:
            logger.warning("[LangGraph] 글로벌 리비전 상한(%d) 도달, 강제 통과", LANGGRAPH_MAX_GLOBAL_REVISIONS)
        elif count < LANGGRAPH_MAX_REVISIONS:
            return "revise"
        else:
            logger.warning(
                "[LangGraph] 최대 revision 횟수(%d) 도달, 강제 통과",
                LANGGRAPH_MAX_REVISIONS,
            )

    # passed 또는 max_revision 도달 → production skip 여부에 따라 분기
    skip = set(state.get("skip_stages") or [])
    if "production" in skip:
        # FastTrack: cinematographer만 실행 (캐릭터 일관성 + 카메라 다양성)
        # director_checkpoint / tts_designer / sound_designer / copyright_reviewer는 skip
        return "cinematographer"
    return "director_checkpoint"


def route_after_cinematographer(state: ScriptState) -> list[str] | str:
    """cinematographer 이후: 에러 → finalize, 정상 → 3개 병렬 fan-out.

    FastTrack(production skip): fan-out 없이 finalize 직행.
    """
    if _has_error(state):
        return "finalize"
    skip = set(state.get("skip_stages") or [])
    if "production" in skip:
        return "finalize"
    return ["tts_designer", "sound_designer", "copyright_reviewer"]


def route_after_director(state: ScriptState) -> str:
    """Director 이후: approve → finalize, revise → 해당 노드."""
    if _has_error(state):
        return "finalize"

    decision = state.get("director_decision", "approve")

    if decision in ("error", "approve"):
        mode = state.get("interaction_mode", "guided")
        if mode == "hands_on":
            return "human_gate"
        return "finalize"

    # 글로벌 리비전 상한 체크 (Phase 28-B #10)
    total = _total_revisions(state)
    if total >= LANGGRAPH_MAX_GLOBAL_REVISIONS:
        logger.warning(
            "[LangGraph] 글로벌 리비전 상한(%d) 도달 (total=%d), 강제 finalize", LANGGRAPH_MAX_GLOBAL_REVISIONS, total
        )
        return "finalize"

    # revision 횟수 체크 (최대 LANGGRAPH_MAX_DIRECTOR_REVISIONS)
    count = state.get("director_revision_count", 0)
    if count >= LANGGRAPH_MAX_DIRECTOR_REVISIONS:
        logger.warning("[LangGraph] Director revision 최대 횟수(%d) 도달, 강제 통과", count)
        return "finalize"

    # Phase 28-B #9: 미등록 decision 경고 로깅
    target = _DIRECTOR_DECISION_MAP.get(decision)
    if target is None:
        logger.warning("[LangGraph] Director 미등록 decision '%s', finalize로 fallback", decision)
        return "finalize"
    return target


def route_after_director_checkpoint(state: ScriptState) -> str:
    """Director Checkpoint 이후: score 기반 분기.

    - error → cinematographer (graceful proceed)
    - score < LOW_THRESHOLD (0.4): revise → writer (강한 피드백)
    - score 0.4-0.7: revise → writer (기본 피드백)
    - score >= 0.7: proceed → cinematographer
    기존 revision_count 가드레일 유지.
    """
    if _has_error(state):
        return "finalize"

    decision = state.get("director_checkpoint_decision", "proceed")
    score = state.get("director_checkpoint_score") or 0.0

    if decision == "error":
        logger.warning("[LangGraph] Checkpoint error, graceful proceed → cinematographer")
        return "cinematographer"

    if decision == "proceed":
        return "cinematographer"

    # 글로벌 리비전 상한 체크 (Phase 28-B #10)
    total = _total_revisions(state)
    if total >= LANGGRAPH_MAX_GLOBAL_REVISIONS:
        logger.warning(
            "[LangGraph] 글로벌 리비전 상한(%d) 도달, cinematographer로 강제 진행", LANGGRAPH_MAX_GLOBAL_REVISIONS
        )
        return "cinematographer"

    # revise 횟수 체크
    count = state.get("director_checkpoint_revision_count", 0)
    if count >= LANGGRAPH_MAX_CHECKPOINT_REVISIONS:
        logger.warning(
            "[LangGraph] Checkpoint revision 최대 횟수(%d) 도달, 강제 통과",
            LANGGRAPH_MAX_CHECKPOINT_REVISIONS,
        )
        return "cinematographer"

    # Score 기반 피드백 강도 로깅
    if score < LANGGRAPH_CHECKPOINT_LOW_THRESHOLD:
        logger.info("[LangGraph] Checkpoint low score (%.2f): 강한 피드백으로 writer 호출", score)

    return "writer"


def route_after_director_plan_gate(state: ScriptState) -> str:
    """Director Plan Gate 이후: revise → director_plan (재수립), 그 외 → inventory_resolve."""
    if state.get("plan_action") == "revise":
        return "director_plan"
    return "inventory_resolve"


def route_after_concept_gate(state: ScriptState) -> str:
    """Concept Gate 이후: regenerate → critic (재생성), 그 외 → location_planner."""
    if state.get("concept_action") == "regenerate":
        return "critic"
    return "location_planner"


def route_after_location_planner(state: ScriptState) -> str:
    """Location Planner 이후: 에러 → finalize (short-circuit), 정상 → writer."""
    if _has_error(state):
        logger.warning("[LangGraph] location_planner 에러, finalize로 short-circuit")
        return "finalize"
    return "writer"


def route_after_human_gate(state: ScriptState) -> str:
    """Human Gate 이후: approve → finalize, revise → revise."""
    action = state.get("human_action", "approve")
    if action == "revise":
        return "revise"
    return "finalize"


def route_after_finalize(state: ScriptState) -> str:
    """finalize 이후: 에러 → learn (explain 스킵), explain skip → learn, else → explain."""
    if _has_error(state):
        return "learn"
    if "explain" in (state.get("skip_stages") or []):
        return "learn"
    return "explain"
