"""Location Planner 노드 — concept_gate와 writer 사이에서 장소 맵을 선행 계획한다.

Phase 30-P-6: 배경-대본 불일치 근본 수정 (독립 노드화)
  - Writer가 대본 생성과 동시에 locations를 만들던 방식 → 선행 분리
  - concept_gate → location_planner → writer 순서로 삽입
  - writer._create_plan()은 기존 locations가 있으면 재사용 (생성 스킵)
  - 실패 시 graceful degradation (writer가 자체 생성으로 fallback)
"""

from __future__ import annotations

import json

from config import logger
from config_pipelines import LANGGRAPH_PLANNING_ENABLED
from services.agent.langfuse_prompt import compile_prompt
from services.agent.llm_models import LocationPlan
from services.agent.prompt_builders import build_optional_section, build_selected_concept_block
from services.agent.state import ScriptState, WriterPlan, build_director_context, extract_selected_concept
from services.llm import LLMConfig, get_llm_provider


def _estimate_scene_range(duration: int, structure: str = "Monologue") -> tuple[int, int]:
    """영상 길이(초)로 예상 씬 개수 범위를 계산한다 (구조 인식)."""
    from services.storyboard.helpers import calculate_max_scenes, calculate_min_scenes

    return calculate_min_scenes(duration, structure), calculate_max_scenes(duration, structure)


async def _plan_locations(state: ScriptState) -> list[dict] | None:
    """Gemini로 Location Map을 생성한다. 실패 시 None 반환."""
    duration = state.get("duration", 10)
    structure = state.get("structure", "Monologue")
    min_s, max_s = _estimate_scene_range(duration, structure)
    selected_concept = extract_selected_concept(state)

    try:
        _template_name = "creative/location_planner.j2"
        _fallback_sys = (
            "You are a Location Planner for short-form video scripts. "
            "Output only valid JSON with the locations array. No explanations."
        )
        description = state.get("description", "")
        director_ctx = build_director_context(state)

        compiled = compile_prompt(
            _template_name,
            topic=state.get("topic", ""),
            description_section=build_optional_section("**Description**:", description) if description else "",
            duration=str(duration),
            language=state.get("language", "Korean"),
            structure=state.get("structure", "Monologue"),
            director_plan_section=build_optional_section("## Creative Direction (from Director)", director_ctx) if director_ctx else "",
            selected_concept_section=build_selected_concept_block(selected_concept) if selected_concept else "",
            expected_scenes_min=str(min_s),
            expected_scenes_max=str(max_s),
        )

        llm_response = await get_llm_provider().generate(
            step_name="location_planner",
            contents=compiled.user,
            config=LLMConfig(system_instruction=compiled.system or _fallback_sys),
            metadata={"template": _template_name},
            langfuse_prompt=compiled.langfuse_prompt,
        )
        text = llm_response.text.strip()

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
