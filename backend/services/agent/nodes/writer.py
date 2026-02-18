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
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState, WriterPlan
from services.script.gemini_generator import generate_script


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


async def _create_plan(state: ScriptState) -> WriterPlan | None:
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
        )

        async with trace_llm_call(name="writer_planning", input_text=prompt[:2000]) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
            )
            llm.record(response)

        # JSON 파싱
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        data = json.loads(text)

        plan: WriterPlan = {
            "hook_strategy": data.get("hook_strategy", ""),
            "emotional_arc": data.get("emotional_arc", []),
            "scene_distribution": data.get("scene_distribution", {}),
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

    # Phase 10-A: Planning Step (Full 모드 + PLANNING_ENABLED)
    if is_full and LANGGRAPH_PLANNING_ENABLED:
        plan = await _create_plan(state)

    # research_brief가 있으면 description에 컨텍스트 추가
    desc = state.get("description", "")
    research_brief = state.get("research_brief")
    if research_brief:
        desc = f"{desc}\n\n[참고 정보]\n{research_brief}".strip()

    # critic에서 선정된 컨셉이 있으면 description에 주입
    critic_result = state.get("critic_result")
    if critic_result:
        selected = critic_result.get("selected_concept", {})
        if selected:
            title = selected.get("title", "")
            concept = selected.get("concept", "")
            desc = f"{desc}\n\n[선정 컨셉]\n제목: {title}\n{concept}".strip()

    # Phase 10-A: Planning 결과를 description에 주입
    if plan:
        plan_text = f"""[Writer Plan]
Hook 전략: {plan['hook_strategy']}
감정 곡선: {', '.join(plan['emotional_arc'])}
씬 배분: intro={plan['scene_distribution'].get('intro', 0)}, rising={plan['scene_distribution'].get('rising', 0)}, climax={plan['scene_distribution'].get('climax', 0)}, resolution={plan['scene_distribution'].get('resolution', 0)}

이 계획을 기반으로 대본을 작성하세요."""
        desc = f"{desc}\n\n{plan_text}".strip()

    # revision_feedback가 있으면 description에 주입
    feedback = state.get("revision_feedback")
    if feedback:
        desc = f"{desc}\n\n[수정 요청] {feedback}".strip()

    request = StoryboardRequest(
        topic=state["topic"],
        description=desc,
        duration=state.get("duration", 10),
        style=state.get("style", "Anime"),
        language=state.get("language", "Korean"),
        structure=state.get("structure", "Monologue"),
        actor_a_gender=state.get("actor_a_gender", "female"),
        character_id=state.get("character_id"),
        character_b_id=state.get("character_b_id"),
        group_id=state.get("group_id"),
    )

    with get_db_session() as db:
        try:
            result = await generate_script(request, db)
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
        except Exception as e:
            logger.error("[LangGraph] Writer 노드 실패: %s", e)
            return {"error": str(e)}
