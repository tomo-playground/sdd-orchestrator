"""Cinematographer 노드 — Tool-Calling Agent로 씬에 비주얼 디자인을 추가한다."""

from __future__ import annotations

import json
import re

from langchain_core.runnables import RunnableConfig

from config import logger, template_env
from database import get_db_session
from services.agent.state import ScriptState
from services.creative_qc import validate_visuals
from services.creative_utils import parse_json_response

_EMPTY_RESULT: dict = {"cinematographer_result": None, "cinematographer_tool_logs": []}


def _load_characters_tags(state: ScriptState, db) -> dict[str, list[str]] | None:
    """캐릭터 ID → Speaker별 태그 목록 로드. LoRA 트리거 워드 포함."""
    character_id = state.get("character_id")
    if not character_id:
        return None

    speakers = {"A": character_id}
    char_b_id = state.get("character_b_id")
    if char_b_id:
        speakers["B"] = char_b_id

    result: dict[str, list[str]] = {}
    for speaker, cid in speakers.items():
        tags = _load_single_character_tags(cid, db)
        if tags:
            result[speaker] = tags

    return result if result else None


def _load_single_character_tags(cid: int, db) -> list[str]:
    """단일 캐릭터의 태그 + LoRA 트리거 워드를 로드한다."""
    from sqlalchemy import select  # noqa: PLC0415

    from models.character import Character  # noqa: PLC0415

    try:
        stmt = select(Character).where(Character.id == cid)
        char = db.execute(stmt).scalar_one_or_none()
        if not char:
            return []

        tags = [ct.tag.name for ct in char.tags if ct.tag]

        # LoRA 트리거 워드 추가
        if char.loras:
            from models.lora import LoRA  # noqa: PLC0415

            for lora_entry in char.loras:
                lora_id = lora_entry.get("lora_id")
                if not lora_id:
                    continue
                lora_stmt = select(LoRA).where(LoRA.id == lora_id)
                lora_obj = db.execute(lora_stmt).scalar_one_or_none()
                if lora_obj and lora_obj.trigger_words:
                    tags.extend(lora_obj.trigger_words)

        return tags
    except Exception as e:
        logger.warning("[Cinematographer] 캐릭터 태그 로드 실패 (cid=%d): %s", cid, e)
        return []


async def cinematographer_node(state: ScriptState, config: RunnableConfig) -> dict:
    """Tool-Calling Agent로 draft_scenes에 비주얼 디자인을 추가한다.

    실패 시 error를 설정하지 않고 cinematographer_result=None을 반환하여
    하위 병렬 노드(tts_designer, sound_designer, copyright_reviewer)가 skip되지 않도록 한다.
    """
    db_session = config.get("configurable", {}).get("db") if config else None
    if db_session:
        return await _run(state, db_session)

    with get_db_session() as db:
        return await _run(state, db)


async def _try_competition(
    state: ScriptState, db_session: object, base_prompt: str, director_feedback: str | None
) -> dict | None:
    """Full 모드 경쟁을 시도한다. 성공 시 결과 dict, 실패 시 None."""
    from config_pipelines import CINEMATOGRAPHER_COMPETITION_ENABLED  # noqa: PLC0415

    if not CINEMATOGRAPHER_COMPETITION_ENABLED:
        return None

    from ..cinematographer_competition import run_cinematographer_competition  # noqa: PLC0415

    logger.info("[Cinematographer] Full 모드 경쟁 실행 (3 Lens)")
    comp = await run_cinematographer_competition(state, db_session, base_prompt, director_feedback)

    if not comp.get("scenes"):
        logger.warning("[Cinematographer] Competition 실패, 단일 에이전트 fallback")
        return None

    qc = comp.get("qc") or validate_visuals(comp["scenes"])
    if not qc["ok"]:
        logger.warning("[Cinematographer] Competition QC WARN/FAIL: %s", qc.get("issues"))

    logger.info("[Cinematographer] Competition 완료: winner=%s, scores=%s", comp["winner"], comp["scores"])
    return {
        "cinematographer_result": {"scenes": comp["scenes"]},
        "cinematographer_tool_logs": comp["tool_logs"],
        "visual_qc_result": qc,
        "cinematographer_competition_scores": comp["scores"],
        "cinematographer_winner": comp["winner"],
    }


async def _run(state: ScriptState, db_session: object) -> dict:
    """Cinematographer 핵심 로직. DB 세션이 보장된 상태에서 실행."""
    from ..tools.base import call_with_tools  # noqa: PLC0415
    from ..tools.cinematographer_tools import (  # noqa: PLC0415
        create_cinematographer_executors,
        get_cinematographer_tools,
    )

    tools = get_cinematographer_tools()
    executors = create_cinematographer_executors(db_session, state)

    scenes = state.get("draft_scenes") or []
    character_id = state.get("character_id")
    director_feedback = state.get("director_feedback")

    characters_tags = _load_characters_tags(state, db_session)

    style = state.get("style", "Anime")
    writer_plan = state.get("writer_plan")

    tmpl = template_env.get_template("creative/cinematographer.j2")
    base_prompt = tmpl.render(
        scenes=scenes,
        character_id=character_id,
        style=style,
        characters_tags=characters_tags,
        writer_plan=writer_plan,
        feedback=director_feedback,
    )

    # Full 모드 경쟁 시도 (성공 시 즉시 반환)
    if state.get("mode", "quick") == "full":
        comp_result = await _try_competition(state, db_session, base_prompt, director_feedback)
        if comp_result:
            return comp_result

    prompt_parts = [
        "당신은 쇼츠 영상의 Cinematographer Agent입니다.",
        "각 씬에 Danbooru 태그, 카메라 앵글, 환경 설정을 추가하여 비주얼 디자인을 완성하세요.",
        "",
        "사용 가능한 도구:",
        "- validate_danbooru_tag: 태그가 유효한지 검증",
        "- get_character_visual_tags: 캐릭터의 비주얼 태그 조회 (일관성 유지)",
        "- check_tag_compatibility: 두 태그의 충돌 여부 확인",
        "- search_similar_compositions: 유사한 분위기의 레퍼런스 태그 조합 검색",
        "",
        "도구 사용 가이드:",
        "- 캐릭터 ID가 있으면 먼저 get_character_visual_tags를 호출하세요",
        "- 새로운 태그를 추가하기 전에 validate_danbooru_tag로 검증하세요",
        "- 중요한 태그 조합은 check_tag_compatibility로 충돌 여부를 확인하세요",
        "",
        f"대본 정보:\n{base_prompt}",
    ]

    if director_feedback:
        prompt_parts.append(f"\n[Director 피드백]\n{director_feedback}")

    prompt_parts.append(
        """
최종 출력은 반드시 다음 JSON 형식으로 작성하세요:
{
  "scenes": [
    {
      "order": 1,
      "text": "씬 대본",
      "visual_tags": ["tag1", "tag2", ...],
      "camera": "close-up",
      "environment": "indoors"
    },
    ...
  ]
}
"""
    )

    prompt = "\n".join(prompt_parts)

    # Tool-Calling 실행 (빈 응답 시 1회 재시도)
    max_attempts = 2
    tool_logs: list = []
    scenes_output: list[dict] | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("[Cinematographer] Tool-Calling Agent 시작 (attempt %d/%d)", attempt, max_attempts)
            response, attempt_logs = await call_with_tools(
                prompt=prompt,
                tools=tools,
                tool_executors=executors,
                max_calls=10,
                trace_name="cinematographer_tool_calling",
            )
            tool_logs = attempt_logs
        except Exception as e:
            logger.warning("[Cinematographer] Tool-Calling 실패 (graceful): %s", e)
            return _EMPTY_RESULT

        scenes_output = _parse_scenes(response)
        if scenes_output is not None:
            break

        if attempt < max_attempts:
            logger.warning("[Cinematographer] JSON 파싱 실패 (attempt %d), 재시도", attempt)
        else:
            logger.warning(
                "[Cinematographer] JSON 파싱 실패 (%d회 시도), cinematographer_result=None으로 진행", max_attempts
            )
            return {"cinematographer_result": None, "cinematographer_tool_logs": tool_logs}

    # 타입 가드: for 루프는 break(성공) 또는 return(실패)으로 종료되므로 여기에 도달하면 반드시 not None
    assert scenes_output is not None  # noqa: S101

    # QC 검증 (WARN은 통과, FAIL만 로깅 후 결과 그대로 반환)
    qc = validate_visuals(scenes_output)
    if not qc["ok"]:
        logger.warning("[Cinematographer] QC WARN/FAIL: %s (결과는 유지)", qc.get("issues"))

    logger.info("[Cinematographer] Tool-Calling 완료 (%d 씬, %d 도구 호출)", len(scenes_output), len(tool_logs))
    return {
        "cinematographer_result": {"scenes": scenes_output},
        "cinematographer_tool_logs": tool_logs,
        "visual_qc_result": qc,
    }


def _parse_scenes(response: str) -> list[dict] | None:
    """LLM 응답에서 scenes 배열을 추출한다.

    코드블록 추출 후 parse_json_response()로 이스케이프 복구를 시도한다.
    실패 시 None.
    """
    try:
        # 코드블록이 응답 중간에 있을 수 있으므로 먼저 추출
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        json_text = match.group(1) if match else response

        result_data = parse_json_response(json_text)
        if not isinstance(result_data, dict):
            logger.warning("[Cinematographer] Expected dict, got %s", type(result_data).__name__)
            return None
        return result_data.get("scenes", [])
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("[Cinematographer] JSON 파싱 실패: %s", e)
        return None
