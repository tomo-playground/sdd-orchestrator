"""Location Planner 노드 — review 통과 후 실제 대본을 분석하여 장소를 배정한다.

대본(draft_scenes)의 script 내용을 LLM에 전달하여 각 씬에 적절한 위치를 배정.
Writer가 자유롭게 대본을 쓴 뒤, Location Planner가 대본을 분석하므로
대본-배경 불일치 문제를 근본적으로 해결한다.

실행 순서: writer → review → location_planner → director_checkpoint
실패 시 graceful degradation (finalize에서 기존 환경 태그 유지).
"""

from __future__ import annotations

import json

from config import coerce_language_id, coerce_structure_id
from config import pipeline_logger as logger
from services.agent.langfuse_prompt import compile_prompt
from services.agent.llm_models import LocationPlan
from services.agent.prompt_builders import build_optional_section
from services.agent.state import ScriptState, WriterPlan
from services.llm import LLMConfig, get_llm_provider


def _build_scenes_block(draft_scenes: list[dict]) -> str:
    """draft_scenes에서 LLM에 전달할 씬 요약 블록을 구성한다."""
    lines: list[str] = []
    for i, scene in enumerate(draft_scenes):
        script = scene.get("script", "")
        if script:
            lines.append(f"Scene {i}: {script}")
    return "\n".join(lines)


_TEMPLATE_NAME = "creative/location_planner"
_FALLBACK_SYS = (
    "You are a Location Planner for short-form video scripts. Analyze scene scripts and assign appropriate locations."
)


def _compile_location_prompt(state: ScriptState, scenes_block: str):
    """LangFuse 템플릿 컴파일 + scenes_block fallback 삽입."""
    draft_scenes = state.get("draft_scenes") or []
    compiled = compile_prompt(
        _TEMPLATE_NAME,
        topic=state.get("topic", ""),
        duration=str(state.get("duration", 30)),
        language=coerce_language_id(state.get("language")),
        structure=coerce_structure_id(state.get("structure")),
        expected_scenes_min=str(len(draft_scenes)),
        expected_scenes_max=str(len(draft_scenes)),
        description_block="",
        director_plan_block="",
        selected_concept_block="",
        scenes_block=build_optional_section("## Actual Scene Scripts (analyze these)", scenes_block),
    )
    # 정적 지시문은 LangFuse `creative/location_planner` 템플릿 user 파트에서 관리
    user_content = compiled.user or ""
    if scenes_block and scenes_block not in user_content:
        user_content += f"\n\n## Actual Scene Scripts (analyze these)\n{scenes_block}"
    return compiled, user_content


async def _plan_locations_from_scripts(state: ScriptState) -> list[dict] | None:
    """실제 대본(draft_scenes)을 분석하여 Location Map을 생성한다."""
    draft_scenes = state.get("draft_scenes") or []
    if not draft_scenes:
        logger.warning("[LocationPlanner] draft_scenes 없음, 스킵")
        return None

    scenes_block = _build_scenes_block(draft_scenes)
    if not scenes_block:
        return None

    try:
        compiled, user_content = _compile_location_prompt(state, scenes_block)

        llm_response = await get_llm_provider().generate(
            step_name="generate_content location_planner",
            contents=user_content,
            config=LLMConfig(system_instruction=compiled.system or _FALLBACK_SYS),
            metadata={"template": _TEMPLATE_NAME},
            langfuse_prompt=compiled.langfuse_prompt,
        )
        text = llm_response.text.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        data = json.loads(text)
        raw_locs = data.get("locations", [])
        locations = [LocationPlan.model_validate(loc).model_dump() for loc in raw_locs]

        logger.info(
            "[LocationPlanner] 대본 분석 완료: %d locations (%s)",
            len(locations),
            ", ".join(loc.get("name", "?") for loc in locations),
        )
        return locations if locations else None

    except Exception as e:
        logger.warning("[LocationPlanner] 실패 (graceful degradation): %s", e)
        return None


async def location_planner_node(state: ScriptState) -> dict:
    """대본(draft_scenes) 분석 후 writer_plan.locations를 설정한다.

    review 통과 후 실행. 모든 모드(Full/FastTrack)에서 동작.
    실패 시 빈 dict 반환 → finalize에서 기존 환경 태그 유지.
    """
    draft_scenes = state.get("draft_scenes")
    if not draft_scenes:
        logger.warning("[LocationPlanner] draft_scenes 없음, 스킵")
        return {}

    locations = await _plan_locations_from_scripts(state)
    if not locations:
        return {}

    existing: WriterPlan | None = state.get("writer_plan")
    updated: WriterPlan = dict(existing) if existing else {}  # type: ignore[assignment]
    updated["locations"] = locations

    return {"writer_plan": updated}
