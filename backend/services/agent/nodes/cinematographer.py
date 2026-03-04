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

# 캐릭터 태그 계층 분류용 group_name 셋
_IDENTITY_GROUPS = frozenset(
    {
        "identity",
        "hair_color",
        "hair_length",
        "hair_style",
        "eye_color",
        "eye_detail",
    }
)
_APPEARANCE_GROUPS = frozenset(
    {
        "skin_color",
        "body_feature",
        "body_type",
        "appearance",
        "clothing_top",
        "clothing_bottom",
        "clothing_outfit",
        "clothing",
        "clothing_detail",
        "legwear",
        "footwear",
        "accessory",
        "hair_accessory",
    }
)
# Layer 8 (ACTION): 캐릭터 기본/선호 동작 힌트 (씬별 override 가능)
_ACTION_HINT_GROUPS = frozenset(
    {
        "pose",
        "action_body",
        "action_hand",
        "action_daily",
        "action",
        "gesture",
    }
)


def _load_characters_tags(state: ScriptState, db) -> dict[str, dict[str, list[str]]] | None:
    """캐릭터 ID → Speaker별 계층화된 태그 목록 로드."""
    character_id = state.get("character_id")
    if not character_id:
        return None

    speakers = {"A": character_id}
    char_b_id = state.get("character_b_id")
    if char_b_id:
        speakers["B"] = char_b_id

    result: dict[str, dict[str, list[str]]] = {}
    for speaker, cid in speakers.items():
        tags = _load_single_character_tags(cid, db)
        if any(tags.values()):
            result[speaker] = tags

    return result if result else None


def _load_single_character_tags(cid: int, db) -> dict[str, list[str]]:
    """단일 캐릭터의 계층화된 태그 + LoRA 트리거 워드를 로드한다."""
    from sqlalchemy import select  # noqa: PLC0415

    from models.character import Character  # noqa: PLC0415

    empty: dict[str, list[str]] = {"identity": [], "appearance": [], "lora_triggers": [], "action_hints": []}

    try:
        stmt = select(Character).where(Character.id == cid)
        char = db.execute(stmt).scalar_one_or_none()
        if not char:
            return empty

        result: dict[str, list[str]] = {"identity": [], "appearance": [], "lora_triggers": [], "action_hints": []}

        for ct in char.tags:
            if not ct.tag:
                continue
            group = ct.tag.group_name or ""
            if group in _IDENTITY_GROUPS:
                result["identity"].append(ct.tag.name)
            elif group in _APPEARANCE_GROUPS:
                result["appearance"].append(ct.tag.name)
            elif group in _ACTION_HINT_GROUPS:
                result["action_hints"].append(ct.tag.name)
            # else: expression, gaze 등 → 생략 (Cinematographer가 씬별로 자유 생성)

        # LoRA 트리거 워드 추가 (배치 조회로 N+1 방지)
        if char.loras:
            from models.lora import LoRA  # noqa: PLC0415

            lora_ids = [e.get("lora_id") for e in char.loras if e.get("lora_id")]
            if lora_ids:
                lora_objs = db.execute(select(LoRA).where(LoRA.id.in_(lora_ids))).scalars().all()
                for lora_obj in lora_objs:
                    if lora_obj.trigger_words:
                        result["lora_triggers"].extend(lora_obj.trigger_words)

        return result
    except Exception as e:
        logger.warning("[Cinematographer] 캐릭터 태그 로드 실패 (cid=%d): %s", cid, e)
        return empty


async def cinematographer_node(state: ScriptState, config: RunnableConfig) -> dict:
    """Tool-Calling Agent로 draft_scenes에 비주얼 디자인을 추가한다.

    실패 시 error를 설정하지 않고 cinematographer_result=None을 반환하여
    하위 병렬 노드(tts_designer, sound_designer, copyright_reviewer)가 skip되지 않도록 한다.
    """
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "cinematographer"):
        return {"cinematographer_result": None, "cinematographer_tool_logs": []}

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
    from ..tools.base import call_direct, call_with_tools  # noqa: PLC0415
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
    director_plan = state.get("director_plan")

    from services.script.gemini_generator import sanitize_chat_context  # noqa: PLC0415

    chat_context = sanitize_chat_context(state.get("chat_context") or [])

    tmpl = template_env.get_template("creative/cinematographer.j2")
    base_prompt = tmpl.render(
        scenes=scenes,
        character_id=character_id,
        style=style,
        characters_tags=characters_tags,
        writer_plan=writer_plan,
        director_plan=director_plan,
        feedback=director_feedback,
        chat_context=chat_context,
    )

    # Full 모드 경쟁 시도 (성공 시 즉시 반환)
    if "production" not in (state.get("skip_stages") or []):
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
[중요] 최종 출력 규칙:
- 반드시 아래 JSON 형식으로만 응답하세요
- 자연어 설명, 인사말, 확인 메시지를 절대 포함하지 마세요
- "네, 알겠습니다" 같은 대화체 응답 금지
- 순수 JSON만 출력하세요

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

    # Tool-Calling 실행 (빈 응답 시 도구 없이 직접 재시도)
    max_attempts = 2
    tool_logs: list = []
    scenes_output: list[dict] | None = None

    _JSON_RETRY_SUFFIX = (
        "\n\n[CRITICAL] 이전 응답에서 유효한 JSON을 받지 못했습니다. "
        "자연어 텍스트나 대화체 응답은 절대 금지입니다. "
        '반드시 {"scenes": [...]} JSON 형식으로만 응답하세요. '
        "markdown 코드블록이나 설명 텍스트를 포함하지 마세요."
    )

    for attempt in range(1, max_attempts + 1):
        current_prompt = prompt if attempt == 1 else prompt + _JSON_RETRY_SUFFIX
        try:
            logger.info("[Cinematographer] Agent 시작 (attempt %d/%d)", attempt, max_attempts)
            if attempt == 1:
                response, attempt_logs = await call_with_tools(
                    prompt=current_prompt,
                    tools=tools,
                    tool_executors=executors,
                    max_calls=10,
                    trace_name="cinematographer_tool_calling",
                )
                tool_logs = attempt_logs
            else:
                # 재시도: 도구 없이 직접 JSON 생성 (자연어 응답 방지)
                logger.info("[Cinematographer] 재시도: 도구 없이 직접 JSON 생성")
                response = await call_direct(
                    prompt=current_prompt,
                    trace_name="cinematographer_direct_retry",
                    temperature=0.0,
                )
        except Exception as e:
            logger.warning("[Cinematographer] Agent 실패 (graceful): %s", e)
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

    추출 전략 (우선순위):
    1. ```json 코드블록 내부
    2. 응답 전체를 parse_json_response()로 시도
    3. {"scenes" 패턴 위치부터 끝까지 추출
    빈 응답 시 즉시 None 반환.
    """
    if not response or not response.strip():
        logger.warning("[Cinematographer] 빈 응답 수신, 파싱 스킵")
        return None

    # 전략 1: ```json 코드블록 추출
    match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if match:
        parsed = _try_parse_json_dict(match.group(1))
        if parsed is not None:
            return parsed

    # 전략 2: 응답 전체를 직접 파싱
    parsed = _try_parse_json_dict(response)
    if parsed is not None:
        return parsed

    # 전략 3: {"scenes" 패턴부터 매칭 중괄호까지 추출 (앞뒤에 텍스트가 붙는 경우)
    scenes_idx = response.find('{"scenes"')
    if scenes_idx == -1:
        scenes_idx = response.find("{'scenes")  # single-quote fallback
    if scenes_idx >= 0:
        json_candidate = _extract_balanced_braces(response, scenes_idx)
        if json_candidate:
            parsed = _try_parse_json_dict(json_candidate)
            if parsed is not None:
                return parsed
        # 균형 추출 실패 시 끝까지 시도
        parsed = _try_parse_json_dict(response[scenes_idx:])
        if parsed is not None:
            return parsed

    logger.warning(
        "[Cinematographer] JSON 파싱 실패: 유효한 scenes JSON을 찾을 수 없음 (응답 길이=%d, 앞 100자=%r)",
        len(response),
        response[:100],
    )
    return None


def _extract_balanced_braces(text: str, start: int) -> str | None:
    """start 위치의 '{'부터 대응하는 '}'까지 추출한다. 실패 시 None."""
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _try_parse_json_dict(text: str) -> list[dict] | None:
    """텍스트에서 scenes 배열을 가진 dict를 파싱. 실패 시 None."""
    if not text or not text.strip():
        return None
    try:
        result_data = parse_json_response(text)
        if not isinstance(result_data, dict):
            return None
        scenes = result_data.get("scenes")
        return scenes if isinstance(scenes, list) else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
