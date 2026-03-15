"""Revise 노드 — Review 에러를 규칙 기반 또는 재생성으로 수정한다.

DD-4: 단순 오류(duration <= 0, 빈 필드)는 직접 수정, 복잡한 오류는 재생성.
"""

from __future__ import annotations

import re

from config import DURATION_DEFICIT_THRESHOLD, LANGGRAPH_MAX_REVISIONS, SCENE_DEFAULT_DURATION, logger
from config_pipelines import REVISE_EXPANSION_ENABLED, REVISE_MAX_EXPANSION_SCENES
from database import get_db_session
from schemas import StoryboardRequest
from services.agent.nodes._revise_expand import (
    can_use_expansion,
    parse_scene_deficit,
    redistribute_durations,
    try_scene_expand,
)
from services.agent.state import ScriptState, extract_selected_concept
from services.script.gemini_generator import generate_script

_DURATION_RE = re.compile(r"씬 (\d+): duration이 0 이하")
_FIELD_RE = re.compile(r"씬 (\d+): 필수 필드 '(script|image_prompt)' 누락")
_DURATION_DEFICIT_RE = re.compile(r"총 duration 부족")
_DURATION_OVERFLOW_RE = re.compile(r"총 duration 초과")
_INVALID_SPEAKER_RE = re.compile(r"speaker='A' 또는 'Narrator'만 허용")
_DIALOGUE_MISSING_SPEAKER_RE = re.compile(r"Dialogue 구조에서 speaker '([AB])'가 등장하지 않음")


def _has_duration_deficit(errors: list[str]) -> bool:
    """에러 목록에 총 duration 부족 에러가 있는지 확인한다."""
    return any(_DURATION_DEFICIT_RE.search(e) for e in errors)


def _has_duration_overflow(errors: list[str]) -> bool:
    """에러 목록에 총 duration 초과 에러가 있는지 확인한다."""
    return any(_DURATION_OVERFLOW_RE.search(e) for e in errors)


def _generate_placeholder_prompt(state: ScriptState) -> str:
    """state 기반 image_prompt placeholder를 생성한다."""
    gender = state.get("actor_a_gender", "female")
    style = (state.get("style") or "anime").lower()
    tag = "1girl" if gender == "female" else "1boy"
    return f"{tag}, solo, {style}"


def _try_rule_fix(scenes: list[dict], errors: list[str], *, fallback_prompt: str = "1girl, solo") -> bool:
    """규칙 기반 수정을 시도한다. 모든 에러를 처리하면 True."""
    unresolved = 0
    for err in errors:
        if m := _DURATION_RE.search(err):
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(scenes):
                scenes[idx]["duration"] = SCENE_DEFAULT_DURATION
        elif m := _FIELD_RE.search(err):
            idx, field = int(m.group(1)) - 1, m.group(2)
            if 0 <= idx < len(scenes) and not scenes[idx].get(field):
                scenes[idx][field] = "(placeholder)" if field == "script" else fallback_prompt
        elif _INVALID_SPEAKER_RE.search(err):
            # Monologue에 B 등 완전히 잘못된 speaker가 섞인 경우 → "A"로 교정 (Narrator는 보존)
            fixed = sum(1 for s in scenes if s.get("speaker") not in ("A", "Narrator"))
            for scene in scenes:
                if scene.get("speaker") not in ("A", "Narrator"):
                    scene["speaker"] = "A"
            logger.info("[Revise] invalid speaker 교정: %d개 씬 → 'A'로 변경 (Narrator 보존)", fixed)
        elif _DIALOGUE_MISSING_SPEAKER_RE.search(err):
            # Dialogue에서 A 또는 B가 빠진 경우 → non-Narrator 씬을 교대 배정
            non_narrator = [s for s in scenes if s.get("speaker") != "Narrator"]
            if non_narrator:
                for i, scene in enumerate(non_narrator):
                    scene["speaker"] = "A" if i % 2 == 0 else "B"
                logger.info("[Revise] Dialogue speaker 교대 배정: %d개 non-Narrator 씬", len(non_narrator))
            else:
                unresolved += 1
        else:
            unresolved += 1
    return unresolved == 0


def _summarize_history(history: list[dict]) -> str:
    """revision_history를 최대 3줄로 요약한다 (토큰 절약)."""
    lines: list[str] = ["[이전 수정 히스토리]"]
    for entry in history[-3:]:
        attempt = entry.get("attempt", "?")
        errs = entry.get("errors", [])
        tier = entry.get("tier", "unknown")
        err_summary = ", ".join(errs[:2]) if errs else "없음"
        lines.append(f"- 시도 {attempt}: errors=[{err_summary}], tier={tier}")
    lines.append("→ 이전과 다른 접근법을 사용하세요.")
    return "\n".join(lines)


def _build_feedback(state: ScriptState) -> str:
    """human_feedback, revision_feedback, review errors, reflection을 결합.

    Phase 10-A: review_reflection (Self-Reflection 근본 원인 분석 + 수정 전략) 추가.
    Revision History: 이전 시도 요약을 추가하여 동일 실패 반복 방지.
    """
    parts: list[str] = []

    # Revision History 요약 (이전 시도 정보)
    if history := state.get("revision_history"):
        parts.append(_summarize_history(history))

    if fb := state.get("human_feedback"):
        parts.append(f"[사용자 피드백] {fb}")
    if rf := state.get("revision_feedback"):
        parts.append(f"[수정 지시] {rf}")
    if df := state.get("director_feedback"):
        parts.append(f"[디렉터 피드백] {df}")

    # Phase 10-A: Self-Reflection 우선 배치 (근본 원인 분석 → 구체적 수정 전략)
    if reflection := state.get("review_reflection"):
        parts.append(f"[Review Self-Reflection]\n{reflection}")

    review = state.get("review_result") or {}
    if errs := review.get("errors"):
        parts.append(f"[검증 오류] {'; '.join(errs)}")
    if ns := review.get("narrative_score"):
        if ns_fb := ns.get("feedback"):
            parts.append(f"[서사 품질 피드백] {ns_fb}")

    return "\n".join(parts)


def _summarize_scenes(scenes: list[dict]) -> str:
    """현재 대본을 요약하여 Gemini에 컨텍스트로 전달한다."""
    if not scenes:
        return ""
    lines = ["--- 현재 대본 (수정 기준) ---"]
    for i, s in enumerate(scenes, 1):
        script = s.get("script", "")
        lines.append(f"씬 {i}: {script}")
    return "\n".join(lines)


def _make_request(state: ScriptState, desc: str) -> StoryboardRequest:
    """state에서 StoryboardRequest를 생성한다."""
    return StoryboardRequest(
        topic=state.get("topic", ""),
        description=desc,
        duration=state.get("duration", 10),
        style=state.get("style", "Anime"),
        language=state.get("language", "Korean"),
        structure=state.get("structure", "Monologue"),
        actor_a_gender=state.get("actor_a_gender", "female"),
        character_id=state.get("character_id"),
        character_b_id=state.get("character_b_id"),
        group_id=state.get("group_id"),
        selected_concept=extract_selected_concept(state),
    )


def _append_history(state: ScriptState) -> list[dict]:
    """현재 review_result + reflection을 revision_history에 추가."""
    history = list(state.get("revision_history") or [])
    review = state.get("review_result") or {}
    narrative = review.get("narrative_score") or {}
    entry: dict = {
        "attempt": len(history) + 1,
        "errors": review.get("errors", []),
        "warnings": review.get("warnings", []),
        "reflection": state.get("review_reflection"),
        "score": state.get("director_checkpoint_score"),
        "tier": "pending",  # 아래에서 실제 tier로 업데이트
    }
    # narrative_score: 재생성 이유가 서사 품질 미달인 경우에만 포함
    if narrative.get("overall") is not None:
        entry["narrative_score"] = {
            "overall": narrative["overall"],
            "feedback": narrative.get("feedback"),
        }
    history.append(entry)
    return history


async def revise_node(state: ScriptState) -> dict:
    """Review 에러를 수정한다. 단순 오류는 직접, 복잡 오류는 재생성."""
    count = state.get("revision_count", 0)
    if count >= LANGGRAPH_MAX_REVISIONS:
        logger.warning("[LangGraph] Revise 최대 횟수 도달 (%d)", count)
        return {"revision_count": count}

    # Revision History 누적
    history = _append_history(state)

    scenes = [s.copy() for s in (state.get("draft_scenes") or [])]
    errors = (state.get("review_result") or {}).get("errors", [])
    fallback_prompt = _generate_placeholder_prompt(state)

    # Tier 1: 규칙 기반 수정
    if errors and _try_rule_fix(scenes, errors, fallback_prompt=fallback_prompt):
        logger.info("[LangGraph] Revise Tier 1 규칙 수정 완료 (revision=%d)", count + 1)
        history[-1]["tier"] = "rule_fix"
        return {"draft_scenes": scenes, "revision_count": count + 1, "revision_history": history}

    # Tier 1.5: duration 부족 → redistribute로 해결 시도
    if _has_duration_deficit(errors):
        redistribute_durations(scenes, state.get("duration", 10), language=state.get("language", "Korean"))
        new_total = sum(s.get("duration", 0) for s in scenes)
        if new_total >= state.get("duration", 10) * DURATION_DEFICIT_THRESHOLD:
            logger.info("[LangGraph] Revise Tier 1.5 duration 재분배 완료 (revision=%d)", count + 1)
            history[-1]["tier"] = "duration_redistribute"
            return {"draft_scenes": scenes, "revision_count": count + 1, "revision_history": history}

    # Tier 1.6: duration 초과 → 씬 개수 trim (구조 인식)
    if _has_duration_overflow(errors):
        from services.storyboard.helpers import calculate_max_scenes, normalize_structure  # noqa: PLC0415

        structure = normalize_structure(state.get("structure"))
        duration = state.get("duration", 10)
        max_sc = calculate_max_scenes(duration, structure)
        if len(scenes) > max_sc:
            trimmed_count = len(scenes) - max_sc
            scenes = scenes[:max_sc]
            logger.info(
                "[LangGraph] Revise Tier 1.6 overflow trim: %d씬 제거 → %d씬 (max=%d, structure=%s)",
                trimmed_count,
                len(scenes),
                max_sc,
                structure,
            )
            history[-1]["tier"] = "overflow_trim"
            return {"draft_scenes": scenes, "revision_count": count + 1, "revision_history": history}

    # Tier 2: 씬 개수 부족 → 타겟 확장 (기존 씬 보존)
    if REVISE_EXPANSION_ENABLED:
        deficit_info = parse_scene_deficit(errors)
        if deficit_info and can_use_expansion(errors):
            _try_rule_fix(scenes, errors, fallback_prompt=fallback_prompt)  # 규칙 수정 가능한 에러 먼저 처리
            _current, target_min = deficit_info
            deficit = target_min - len(scenes)
            if 0 < deficit <= REVISE_MAX_EXPANSION_SCENES:
                expanded = await try_scene_expand(scenes, state, deficit, target_min)
                if expanded:
                    redistribute_durations(
                        expanded,
                        state.get("duration", 10),
                        language=state.get("language", "Korean"),
                    )
                    logger.info("[LangGraph] Revise Tier 2 확장 완료 (revision=%d)", count + 1)
                    history[-1]["tier"] = "expansion"
                    return {
                        "draft_scenes": expanded,
                        "revision_count": count + 1,
                        "revision_history": history,
                    }

    # Tier 3: 복잡 오류 — 피드백 + 현재 대본을 별도 컨텍스트로 전달 후 재생성
    feedback = _build_feedback(state)
    pipeline_ctx: dict[str, str] = {}
    current_script = _summarize_scenes(scenes)
    if current_script:
        pipeline_ctx["current_script_summary"] = current_script
    if feedback:
        pipeline_ctx["revision_feedback"] = feedback

    history[-1]["tier"] = "regeneration"
    desc = state.get("description", "")
    with get_db_session() as db:
        try:
            result = await generate_script(_make_request(state, desc), db, pipeline_context=pipeline_ctx)
            scenes = result.get("scenes") or []

            # writer_node와 동일한 후처리 적용
            from services.agent.nodes.writer import _extract_reasoning
            from services.script.scene_postprocess import annotate_speakable

            annotate_speakable(scenes)
            scene_reasoning = _extract_reasoning(scenes)

            logger.info("[LangGraph] Revise 재생성 완료 (revision=%d)", count + 1)
            return {
                "draft_scenes": scenes,
                "draft_character_id": result.get("character_id"),
                "draft_character_b_id": result.get("character_b_id"),
                "scene_reasoning": scene_reasoning or None,
                "revision_count": count + 1,
                "revision_history": history,
            }
        except Exception as e:
            logger.error("[LangGraph] Revise 재생성 실패: %s", e)
            return {"error": str(e), "revision_count": count + 1, "revision_history": history}
