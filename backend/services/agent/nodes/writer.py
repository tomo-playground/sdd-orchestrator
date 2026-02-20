"""Writer 노드 — 기존 generate_script를 래핑하여 초안을 생성한다.

Phase 10-A: Planning Step 추가 (Full 모드)
  1. Planning: Hook 전략, 감정 곡선, 씬 배분 계획 수립
  2. Generation: 계획 기반으로 대본 생성
"""

from __future__ import annotations

import json

from config import GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from config_pipelines import LANGGRAPH_PLANNING_ENABLED
from database import get_db_session
from schemas import StoryboardRequest
from services.agent.llm_models import WriterPlanOutput
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState, WriterPlan, extract_selected_concept
from services.script.gemini_generator import generate_script

_SAFETY_KEYWORDS = ("안전 필터", "SAFETY", "safety", "차단", "block")

_SAFETY_HINT = (
    "\n\n[안전 가이드] 이전 시도가 콘텐츠 정책으로 차단되었습니다. "
    "다음 규칙을 반드시 준수하세요: "
    "폭력·선정·혐오 표현 금지, 긍정적이고 건전한 톤 유지, "
    "민감한 주제(정치, 종교, 건강 정보) 회피. "
    "안전하고 밝은 내용으로 대본을 작성하세요."
)


def _is_safety_error(exc: Exception) -> bool:
    """에러 메시지에 safety 관련 키워드가 포함되어 있는지 확인."""
    msg = str(exc)
    return any(kw in msg for kw in _SAFETY_KEYWORDS)


def _append_safety_hint(description: str) -> str:
    """description 끝에 safety 가이드를 추가한다."""
    return f"{description}{_SAFETY_HINT}".strip()


def _extract_reasoning(scenes: list[dict]) -> list[dict]:
    """각 씬에서 reasoning 필드를 추출한다. 없으면 빈 리스트."""
    reasoning = []
    for scene in scenes:
        r = scene.pop("reasoning", None)
        if isinstance(r, dict):
            reasoning.append(r)
        else:
            reasoning.append({})
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
        )

        async with trace_llm_call(name="writer_planning", input_text=prompt[:2000]) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
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
    is_full = state.get("mode") == "full"
    plan: WriterPlan | None = None

    # critic에서 선정된 컨셉 추출 (별도 변수로 템플릿에 전달)
    selected_concept = extract_selected_concept(state)

    # Phase 10-A: Planning Step (Full 모드 + PLANNING_ENABLED)
    if is_full and LANGGRAPH_PLANNING_ENABLED:
        plan = await _create_plan(state, selected_concept=selected_concept)

    # 파이프라인 컨텍스트를 별도 dict로 분리 (description 과적 방지)
    pipeline_ctx: dict[str, str] = {}
    research_brief = state.get("research_brief")
    if research_brief:
        pipeline_ctx["research_brief"] = research_brief

    if plan:
        plan_text = (
            f"Hook 전략: {plan['hook_strategy']}\n"
            f"감정 곡선: {', '.join(plan['emotional_arc'])}\n"
            f"씬 배분: intro={plan['scene_distribution'].get('intro', 0)}, "
            f"rising={plan['scene_distribution'].get('rising', 0)}, "
            f"climax={plan['scene_distribution'].get('climax', 0)}, "
            f"resolution={plan['scene_distribution'].get('resolution', 0)}\n\n"
            f"이 계획을 기반으로 대본을 작성하세요."
        )
        pipeline_ctx["writer_plan"] = plan_text

    feedback = state.get("revision_feedback")
    if feedback:
        pipeline_ctx["revision_feedback"] = feedback

    request = StoryboardRequest(
        topic=state["topic"],
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
        scene_reasoning = _extract_reasoning(scenes)
        logger.info(
            "[LangGraph] Writer 노드 완료: %d scenes, plan=%s",
            len(scenes),
            "생성" if plan else "건너뜀",
        )
        return {
            "draft_scenes": scenes,
            "draft_character_id": result.get("character_id"),
            "draft_character_b_id": result.get("character_b_id"),
            "scene_reasoning": scene_reasoning or None,
            "writer_plan": plan,
        }
