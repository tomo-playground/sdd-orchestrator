"""Writer 노드 — 기존 generate_script를 래핑하여 초안을 생성한다.

Phase 10-A: Planning Step 추가 (Full 모드)
  1. Planning: Hook 전략, 감정 곡선, 씬 배분 계획 수립
  2. Generation: 계획 기반으로 대본 생성
"""

from __future__ import annotations

import json

from config import GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from config_pipelines import LANGGRAPH_PLANNING_ENABLED
from database import get_db_session
from schemas import StoryboardRequest
from services.agent.llm_models import WriterPlanOutput
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState, WriterPlan, build_director_context, extract_selected_concept
from services.script.gemini_generator import generate_script

_BRIEF_FIELD_LABELS = {
    "topic_summary": "주제 요약",
    "recommended_angle": "추천 각도",
    "key_elements": "핵심 요소",
    "emotional_arc_suggestion": "감정 곡선 제안",
    "audience_hook": "시청자 훅",
}


def _format_brief_text(brief: dict) -> str:
    """구조화 research_brief dict를 읽기 좋은 텍스트로 변환한다."""
    parts = []
    for key, label in _BRIEF_FIELD_LABELS.items():
        value = brief.get(key)
        if not value:
            continue
        if isinstance(value, list):
            parts.append(f"{label}: {', '.join(str(v) for v in value)}")
        else:
            parts.append(f"{label}: {value}")
    return "\n".join(parts) if parts else brief.get("topic_summary", "")


_SAFETY_KEYWORDS = ("안전 필터", "SAFETY", "safety", "차단", "block")

_SAFETY_HINT = (
    "\n\n[안전 가이드] 이전 시도가 콘텐츠 정책으로 차단되었습니다. "
    "다음만 제거하세요: 노골적 폭력·선정·혐오 표현. "
    "자극적이고 거친 톤, 감정적 표현, 숏폼 특유의 날것의 말투는 그대로 유지하세요. "
    "점잖게 만들지 마세요. 혐오만 빼고 나머지는 과감하게 쓰세요."
)


def _is_safety_error(exc: Exception) -> bool:
    """에러 메시지에 safety 관련 키워드가 포함되어 있는지 확인."""
    msg = str(exc)
    return any(kw in msg for kw in _SAFETY_KEYWORDS)


def _append_safety_hint(description: str) -> str:
    """description 끝에 safety 가이드를 추가한다."""
    return f"{description}{_SAFETY_HINT}".strip()


def _is_scenes_empty(scenes: list[dict]) -> bool:
    """씬 리스트가 비어있거나 모든 씬의 script가 빈 문자열인지 확인."""
    return not scenes or all(not s.get("script", "").strip() for s in scenes)


def _extract_reasoning(scenes: list[dict]) -> list[dict]:
    """각 씬에서 reasoning 필드를 분리 추출한다. 원본 씬 dict 보호, scenes 리스트는 in-place 교체."""
    reasoning = []
    cleaned = []
    for scene in scenes:
        r = scene.get("reasoning")
        reasoning.append(r if isinstance(r, dict) else {})
        cleaned.append({k: v for k, v in scene.items() if k != "reasoning"})
    scenes[:] = cleaned
    return reasoning


async def _create_plan(state: ScriptState, selected_concept: dict | None = None) -> WriterPlan | None:
    """Writer Planning Step을 수행한다 (Phase 10-A).

    Hook 전략, 감정 곡선, 씬 배분 계획을 Gemini로 생성한다.
    실패 시 None 반환 (graceful degradation).
    """
    if not gemini_client:
        logger.warning("[LangGraph] Writer Planning: Gemini 클라이언트 없음, 건너뜀")
        return None

    try:
        tmpl = template_env.get_template("creative/writer_planning.j2")
        prompt = tmpl.render(
            topic=state.get("topic", ""),
            description=state.get("description", ""),
            duration=state.get("duration", 10),
            language=state.get("language", "Korean"),
            structure=state.get("structure", "Monologue"),
            selected_concept=selected_concept,
            director_plan_context=build_director_context(state),
        )

        from google.genai import types

        plan_config = types.GenerateContentConfig(
            system_instruction=(
                "You are a writing planner for short-form video scripts. "
                "Create hook strategies, emotional arcs, and scene distributions."
            ),
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )
        async with trace_llm_call(name="writer_planning", input_text=prompt) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
                config=plan_config,
            )
            llm.record(response)

        # JSON 파싱 + Pydantic 검증
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(text)

        parsed = WriterPlanOutput.model_validate(data)
        plan: WriterPlan = {
            "hook_strategy": parsed.hook_strategy,
            "emotional_arc": parsed.emotional_arc,
            "scene_distribution": parsed.scene_distribution,
        }
        # location_planner 노드가 선행 실행한 경우 기존 locations 재사용 (생성 스킵)
        existing_locs = (state.get("writer_plan") or {}).get("locations")
        if existing_locs:
            plan["locations"] = existing_locs
        elif parsed.locations:
            plan["locations"] = [loc.model_dump() for loc in parsed.locations]

        logger.info(
            "[LangGraph] Writer Planning 완료: hook=%s, arc_len=%d, dist=%s",
            plan["hook_strategy"][:50],
            len(plan["emotional_arc"]),
            plan["scene_distribution"],
        )
        return plan

    except Exception as e:
        logger.warning("[LangGraph] Writer Planning 실패: %s", e)
        return None


async def writer_node(state: ScriptState) -> dict:
    """StoryboardRequest를 생성하고 기존 generate_script를 호출한다.

    Phase 10-A: Full 모드에서 Planning Step을 먼저 수행한다.
      1. Planning: Hook 전략 + 감정 곡선 + 씬 배분
      2. Generation: 계획을 description에 주입하여 생성
    """
    is_full = "concept" not in (state.get("skip_stages") or [])
    plan: WriterPlan | None = None

    # critic에서 선정된 컨셉 추출 (별도 변수로 템플릿에 전달)
    selected_concept = extract_selected_concept(state)

    # Phase 10-A: Planning Step (Full 모드 + PLANNING_ENABLED)
    if is_full and LANGGRAPH_PLANNING_ENABLED:
        plan = await _create_plan(state, selected_concept=selected_concept)

    # 파이프라인 컨텍스트를 별도 dict로 분리 (description 과적 방지)
    pipeline_ctx: dict[str, str | list] = {}
    research_brief = state.get("research_brief")
    if research_brief:
        # 12-B-2: dict인 경우 텍스트로 포맷팅
        if isinstance(research_brief, dict):
            pipeline_ctx["research_brief"] = _format_brief_text(research_brief)
        else:
            pipeline_ctx["research_brief"] = research_brief

    # 12-B-1: Director Plan 컨텍스트 주입
    director_ctx = build_director_context(state)
    if director_ctx:
        pipeline_ctx["director_plan_context"] = director_ctx

    if plan:
        plan_text = (
            f"Hook 전략: {plan['hook_strategy']}\n"
            f"감정 곡선: {', '.join(plan['emotional_arc'])}\n"
            f"씬 배분: intro={plan['scene_distribution'].get('intro', 0)}, "
            f"rising={plan['scene_distribution'].get('rising', 0)}, "
            f"climax={plan['scene_distribution'].get('climax', 0)}, "
            f"resolution={plan['scene_distribution'].get('resolution', 0)}"
        )
        locations = plan.get("locations", [])
        if locations:
            plan_text += "\n\n## Location Map (MUST use these environment tags)\n"
            from services.agent.state import get_loc_field

            for loc in locations:
                loc_scenes: list = get_loc_field(loc, "scenes", [])  # type: ignore[assignment]
                loc_tags: list = get_loc_field(loc, "tags", [])  # type: ignore[assignment]
                loc_name: str = get_loc_field(loc, "name", "")  # type: ignore[assignment]
                scenes_str = ", ".join(str(s) for s in loc_scenes)
                tags_str = ", ".join(loc_tags)
                plan_text += f"- **{loc_name}** (scenes {scenes_str}): {tags_str}\n"
        plan_text += "\n이 계획을 기반으로 대본을 작성하세요."
        pipeline_ctx["writer_plan"] = plan_text

    chat_context = state.get("chat_context")
    if chat_context:
        pipeline_ctx["chat_context"] = chat_context

    feedback = state.get("revision_feedback")
    if feedback:
        pipeline_ctx["revision_feedback"] = feedback

    request = StoryboardRequest(
        topic=state.get("topic", ""),
        description=state.get("description", ""),
        duration=state.get("duration", 10),
        style=state.get("style", "Anime"),
        language=state.get("language", "Korean"),
        structure=state.get("structure", "Monologue"),
        actor_a_gender=state.get("actor_a_gender", "female"),
        character_id=state.get("character_id"),
        character_b_id=state.get("character_b_id"),
        group_id=state.get("group_id"),
        selected_concept=selected_concept,
    )

    with get_db_session() as db:
        try:
            result = await generate_script(request, db, pipeline_context=pipeline_ctx)
        except Exception as e:
            if _is_safety_error(e):
                logger.warning("[LangGraph] Writer: 안전 필터 차단, 프롬프트 완화 후 재시도")
                request.description = _append_safety_hint(request.description or "")
                try:
                    result = await generate_script(request, db, pipeline_context=pipeline_ctx)
                except Exception as retry_err:
                    logger.error("[LangGraph] Writer 재시도도 실패: %s", retry_err)
                    return {"error": str(retry_err)}
            else:
                logger.error("[LangGraph] Writer 노드 실패: %s", e)
                return {"error": str(e)}

        scenes = result.get("scenes", [])

        # Phase 28-A: 빈 씬 자체 검증 + 1회 재시도
        if _is_scenes_empty(scenes):
            logger.warning("[LangGraph] Writer: 빈 씬 감지 (%d scenes), 힌트 추가 1회 재시도", len(scenes))
            retry_desc = (state.get("description") or "") + "\n\n[중요] 반드시 1개 이상의 씬을 생성하세요."
            request.description = retry_desc
            try:
                retry_result = await generate_script(request, db, pipeline_context=pipeline_ctx)
                scenes = retry_result.get("scenes", [])
                result = retry_result
            except Exception as retry_err:
                logger.error("[LangGraph] Writer 빈 씬 재시도 실패: %s", retry_err)
                return {"error": f"빈 스크립트 생성 (재시도 실패: {retry_err})"}
            if _is_scenes_empty(scenes):
                logger.error("[LangGraph] Writer 재시도 후에도 빈 씬")
                return {"error": "빈 스크립트 — Writer가 유효한 씬을 생성하지 못했습니다"}

        # Duration auto-calculation from reading time
        from services.storyboard.helpers import estimate_reading_duration

        language = state.get("language", "Korean")
        for scene in scenes:
            if scene.get("script", "").strip():
                scene["duration"] = estimate_reading_duration(scene["script"], language)

        # Annotate speakable flag (SSOT for TTS eligibility)
        from services.script.scene_postprocess import annotate_speakable

        annotate_speakable(scenes)

        scene_reasoning = _extract_reasoning(scenes)
        logger.info(
            "[LangGraph] Writer 노드 완료: %d scenes, plan=%s",
            len(scenes),
            "생성" if plan else "건너뜀",
        )
        # plan이 None이면 location_planner가 선행 설정한 writer_plan을 보존
        final_plan = plan if plan is not None else state.get("writer_plan")
        return {
            "draft_scenes": scenes,
            "draft_character_id": result.get("character_id"),
            "draft_character_b_id": result.get("character_b_id"),
            "scene_reasoning": scene_reasoning or None,
            "writer_plan": final_plan,
        }
