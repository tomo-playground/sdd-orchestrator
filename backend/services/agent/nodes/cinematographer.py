"""Cinematographer 노드 — Tool-Calling Agent로 씬에 비주얼 디자인을 추가한다."""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from config import pipeline_logger as logger
from database import get_db_session
from services.agent.observability import record_score
from services.agent.state import ScriptState
from services.creative_qc import validate_visuals

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
    # Score 기록 (Phase 38)
    record_score("visual_qc_issues", len(qc.get("issues", [])))
    return {
        "cinematographer_result": {"scenes": comp["scenes"]},
        "cinematographer_tool_logs": comp["tool_logs"],
        "visual_qc_result": qc,
        "cinematographer_competition_scores": comp["scores"],
        "cinematographer_winner": comp["winner"],
    }


async def _run(state: ScriptState, db_session: object) -> dict:
    """Cinematographer 오케스트레이터: Competition → Team → Single fallback."""
    from ..tools.cinematographer_tools import (  # noqa: PLC0415
        create_cinematographer_executors,
        get_cinematographer_tools,
    )

    tools = get_cinematographer_tools()
    executors = create_cinematographer_executors(db_session, state)

    scenes = state.get("draft_scenes") or []
    director_feedback = state.get("director_feedback")
    characters_tags = _load_characters_tags(state, db_session) or {}
    style = state.get("style", "Anime")
    writer_plan = state.get("writer_plan")

    from services.script.gemini_generator import sanitize_chat_context  # noqa: PLC0415

    chat_context = sanitize_chat_context(state.get("chat_context") or [])

    from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415
    from services.agent.prompt_builders_c import (  # noqa: PLC0415
        build_character_tags_fallback,
        build_characters_tags_block,
        build_chat_context_cinematographer,
        build_cine_feedback_json_hint,
        build_cine_feedback_section,
        build_creative_direction_section,
        build_style_section,
        build_writer_plan_section,
    )
    from services.agent.prompt_partials import EMOTION_CONSISTENCY_RULES, IMAGE_PROMPT_KO_RULES  # noqa: PLC0415

    characters_tags_block = build_characters_tags_block(characters_tags)
    style_section = build_style_section(style)
    writer_plan_section = build_writer_plan_section(writer_plan)

    _cine_template = "creative/cinematographer"
    compiled = compile_prompt(
        _cine_template,
        scenes_json=json.dumps(scenes, ensure_ascii=False, indent=2),
        characters_tags_block=characters_tags_block,
        character_tags_fallback=build_character_tags_fallback(None),
        style_section=style_section,
        writer_plan_section=writer_plan_section,
        chat_context_block=build_chat_context_cinematographer(chat_context),
        creative_direction_section=build_creative_direction_section(state.get("creative_direction")),
        cine_feedback_section=build_cine_feedback_section(director_feedback),
        cine_feedback_json_hint=build_cine_feedback_json_hint(director_feedback),
        partial_image_prompt_ko_rules=IMAGE_PROMPT_KO_RULES,
        partial_emotion_consistency_rules=EMOTION_CONSISTENCY_RULES,
    )
    base_prompt = compiled.user

    # 1) Competition 시도 (Full 모드)
    if "production" not in (state.get("skip_stages") or []):
        comp_result = await _try_competition(state, db_session, base_prompt, director_feedback)
        if comp_result:
            return comp_result

    # 2) Team 실행 시도 (4 서브 에이전트 순차)
    scenes_json = json.dumps(scenes, ensure_ascii=False, indent=2)
    visual_direction = (state.get("director_plan") or {}).get("visual_direction", "")

    team_result = await _run_team(
        scenes_json=scenes_json,
        visual_direction=visual_direction,
        writer_plan_section=writer_plan_section,
        characters_tags_block=characters_tags_block,
        style_section=style_section,
        image_prompt_ko_rules=IMAGE_PROMPT_KO_RULES,
        emotion_consistency_rules=EMOTION_CONSISTENCY_RULES,
        tools=tools,
        tool_executors=executors,
    )
    if team_result:
        return team_result

    # 3) Single-agent fallback
    logger.info("[Cinematographer] Team 실패, 단일 에이전트 fallback")
    return await _run_single(
        base_prompt=base_prompt,
        compiled=compiled,
        director_feedback=director_feedback,
        tools=tools,
        executors=executors,
        cine_template=_cine_template,
    )


async def _run_team(
    *,
    scenes_json: str,
    visual_direction: str,
    writer_plan_section: str,
    characters_tags_block: str,
    style_section: str,
    image_prompt_ko_rules: str,
    emotion_consistency_rules: str,
    tools: list,
    tool_executors: dict,
) -> dict | None:
    """4 서브 에이전트 순차 실행: Framing → Action → Atmosphere → Compositor."""
    from ._cine_action import run_action  # noqa: PLC0415
    from ._cine_atmosphere import run_atmosphere  # noqa: PLC0415
    from ._cine_compositor import run_compositor  # noqa: PLC0415
    from ._cine_framing import run_framing  # noqa: PLC0415

    # 1) Framing — 카메라, 시선, Ken Burns
    framing = await run_framing(scenes_json, visual_direction, writer_plan_section)
    if not framing:
        logger.warning("[CineTeam] Framing 실패, 팀 중단")
        return None

    # 2) Action — 감정, 포즈, 액션, 소품 (Framing 참조)
    action = await run_action(scenes_json, framing, characters_tags_block)
    if not action:
        logger.warning("[CineTeam] Action 실패, 팀 중단")
        return None

    # 3) Atmosphere — 환경, 시네마틱 (Framing + Action 참조)
    atmosphere = await run_atmosphere(scenes_json, framing, action, style_section, writer_plan_section)
    if not atmosphere:
        logger.warning("[CineTeam] Atmosphere 실패, 팀 중단")
        return None

    # 4) Compositor — 통합 + 정합성 추론 + 태그 검증
    scenes_output, tool_logs = await run_compositor(
        scenes_json,
        framing,
        action,
        atmosphere,
        characters_tags_block,
        style_section,
        image_prompt_ko_rules,
        emotion_consistency_rules,
        tools,
        tool_executors,
    )
    if not scenes_output:
        logger.warning("[CineTeam] Compositor 실패, 팀 중단")
        return None

    qc = validate_visuals(scenes_output)
    if not qc["ok"]:
        logger.warning("[CineTeam] QC WARN/FAIL: %s", qc.get("issues"))

    logger.info("[CineTeam] 완료: %d scenes, %d tool calls", len(scenes_output), len(tool_logs))
    record_score("visual_qc_issues", len(qc.get("issues", [])))
    return {
        "cinematographer_result": {"scenes": scenes_output},
        "cinematographer_tool_logs": tool_logs,
        "visual_qc_result": qc,
    }


async def _run_single(
    *,
    base_prompt: str,
    compiled: object,
    director_feedback: str | None,
    tools: list,
    executors: dict,
    cine_template: str,
) -> dict:
    """단일 에이전트 실행 (기존 Tool-Calling 방식)."""
    from ..tools.base import call_direct, call_with_tools  # noqa: PLC0415

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
        f"대본 정보:\n{base_prompt}",
    ]
    if director_feedback:
        prompt_parts.append(f"\n[Director 피드백]\n{director_feedback}")
    prompt_parts.append(_JSON_OUTPUT_INSTRUCTION)
    prompt = "\n".join(prompt_parts)

    max_attempts = 2
    tool_logs: list = []
    scenes_output: list[dict] | None = None
    cine_obs_id: str | None = None

    for attempt in range(1, max_attempts + 1):
        current_prompt = prompt if attempt == 1 else prompt + _JSON_RETRY_SUFFIX
        try:
            logger.info("[Cinematographer] Single agent (attempt %d/%d)", attempt, max_attempts)
            _meta = {"template": cine_template}
            if attempt == 1:
                response, attempt_logs, cine_obs_id = await call_with_tools(
                    prompt=current_prompt,
                    tools=tools,
                    tool_executors=executors,
                    max_calls=10,
                    trace_name="cinematographer",
                    system_instruction=compiled.system  # type: ignore[attr-defined]
                    or "당신은 쇼츠 영상의 Cinematographer Agent입니다.",
                    metadata=_meta,
                )
                tool_logs = attempt_logs
            else:
                logger.info("[Cinematographer] 재시도: 도구 없이 직접 JSON 생성")
                response = await call_direct(
                    prompt=current_prompt,
                    trace_name="cinematographer",
                    temperature=0.0,
                    system_instruction=compiled.system  # type: ignore[attr-defined]
                    or "당신은 쇼츠 영상의 Cinematographer Agent입니다.",
                    metadata=_meta,
                )
        except Exception as e:
            logger.warning("[Cinematographer] Agent 실패 (graceful): %s", e)
            record_score("visual_qc_issues", None)
            return _EMPTY_RESULT

        scenes_output = _parse_scenes(response)
        if scenes_output is not None:
            break
        if attempt < max_attempts:
            logger.warning("[Cinematographer] JSON 파싱 실패 (attempt %d), 재시도", attempt)
        else:
            logger.warning("[Cinematographer] JSON 파싱 실패 (%d회), None으로 진행", max_attempts)
            record_score("visual_qc_issues", None)
            return {"cinematographer_result": None, "cinematographer_tool_logs": tool_logs}

    assert scenes_output is not None  # noqa: S101

    qc = validate_visuals(scenes_output)
    if not qc["ok"]:
        logger.warning("[Cinematographer] QC WARN/FAIL: %s (결과는 유지)", qc.get("issues"))

    logger.info("[Cinematographer] Single agent 완료 (%d 씬, %d 도구)", len(scenes_output), len(tool_logs))
    record_score("visual_qc_issues", len(qc.get("issues", [])), observation_id=cine_obs_id)
    return {
        "cinematographer_result": {"scenes": scenes_output},
        "cinematographer_tool_logs": tool_logs,
        "visual_qc_result": qc,
    }


_JSON_OUTPUT_INSTRUCTION = """
[중요] 최종 출력 규칙:
- 반드시 아래 JSON 형식으로만 응답하세요
- 자연어 설명, 인사말, 확인 메시지를 절대 포함하지 마세요
- 순수 JSON만 출력하세요

{"scenes": [{"order": 1, "text": "씬 대본", "visual_tags": ["tag1"], "camera": "close-up", "environment": "indoors"}, ...]}
"""

_JSON_RETRY_SUFFIX = (
    '\n\n[CRITICAL] 이전 응답에서 유효한 JSON을 받지 못했습니다. 반드시 {"scenes": [...]} JSON 형식으로만 응답하세요.'
)


# 파싱 함수는 _cine_common에서 import (하위 호환용 re-export)
from services.agent.nodes._cine_common import parse_scenes as _parse_scenes  # noqa: E402
