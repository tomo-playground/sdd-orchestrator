"""Location Planner 노드 — concept_gate와 writer 사이에서 장소 맵을 선행 계획한다.

Phase 30-P-6: 배경-대본 불일치 근본 수정 (독립 노드화)
  - Writer가 대본 생성과 동시에 locations를 만들던 방식 → 선행 분리
  - concept_gate → location_planner → writer 순서로 삽입
  - writer._create_plan()은 기존 locations가 있으면 재사용 (생성 스킵)
  - 실패 시 graceful degradation (writer가 자체 생성으로 fallback)
"""

from __future__ import annotations

import json

from config import GEMINI_FALLBACK_MODEL, GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from config_pipelines import LANGGRAPH_PLANNING_ENABLED
from services.agent.llm_models import LocationPlan
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState, WriterPlan, build_director_context, extract_selected_concept


def _estimate_scene_range(duration: int, structure: str = "Monologue") -> tuple[int, int]:
    """영상 길이(초)로 예상 씬 개수 범위를 계산한다 (구조 인식)."""
    from services.storyboard.helpers import calculate_max_scenes, calculate_min_scenes

    return calculate_min_scenes(duration, structure), calculate_max_scenes(duration, structure)


async def _plan_locations(state: ScriptState) -> list[dict] | None:
    """Gemini로 Location Map을 생성한다. 실패 시 None 반환."""
    if not gemini_client:
        logger.warning("[LocationPlanner] Gemini 클라이언트 없음, 건너뜀")
        return None

    duration = state.get("duration", 10)
    structure = state.get("structure", "Monologue")
    min_s, max_s = _estimate_scene_range(duration, structure)
    selected_concept = extract_selected_concept(state)

    try:
        tmpl = template_env.get_template("creative/location_planner.j2")
        prompt = tmpl.render(
            topic=state.get("topic", ""),
            description=state.get("description", ""),
            duration=duration,
            language=state.get("language", "Korean"),
            structure=state.get("structure", "Monologue"),
            selected_concept=selected_concept,
            director_plan_context=build_director_context(state),
            expected_scenes_min=min_s,
            expected_scenes_max=max_s,
        )

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=(
                "You are a Location Planner for short-form video scripts. "
                "Output only valid JSON with the locations array. No explanations."
            ),
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )
        async with trace_llm_call(name="location_planner", input_text=prompt) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
                config=config,
            )
            llm.record(response)

        text = (response.text or "").strip()
        if not text:
            feedback = getattr(response, "prompt_feedback", None)
            block_reason = getattr(feedback, "block_reason", None) if feedback else None
            if block_reason and "PROHIBITED" in getattr(block_reason, "name", str(block_reason)).upper():
                logger.warning("[LocationPlanner][Fallback] PROHIBITED_CONTENT → %s", GEMINI_FALLBACK_MODEL)
                async with trace_llm_call(
                    name="location_planner_fallback", input_text=prompt, model=GEMINI_FALLBACK_MODEL
                ) as llm_fb:
                    response = await gemini_client.aio.models.generate_content(
                        model=GEMINI_FALLBACK_MODEL,
                        contents=prompt,
                        config=config,
                    )
                    llm_fb.record(response)
                text = (response.text or "").strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        data = json.loads(text)
        raw_locs = data.get("locations", [])
        locations = [LocationPlan.model_validate(loc).model_dump() for loc in raw_locs]

        logger.info(
            "[LocationPlanner] 완료: %d locations (%s)",
            len(locations),
            ", ".join(loc.get("name", "?") for loc in locations),
        )
        return locations if locations else None

    except Exception as e:
        logger.warning("[LocationPlanner] 실패 (graceful degradation): %s", e)
        return None


async def location_planner_node(state: ScriptState) -> dict:
    """Location Map을 선행 계획하고 writer_plan.locations를 설정한다.

    Full 모드(+ PLANNING_ENABLED)에서만 동작.
    실패 시 빈 dict 반환 → writer가 자체 생성으로 fallback.
    """
    is_full = "concept" not in (state.get("skip_stages") or [])
    if not is_full or not LANGGRAPH_PLANNING_ENABLED:
        return {}

    locations = await _plan_locations(state)
    if not locations:
        return {}

    existing: WriterPlan | None = state.get("writer_plan")
    updated: WriterPlan = dict(existing) if existing else {}  # type: ignore[assignment]
    updated["locations"] = locations

    return {"writer_plan": updated}
