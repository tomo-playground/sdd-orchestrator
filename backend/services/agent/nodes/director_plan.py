"""Director Plan 노드 — 초기 목표 수립 + 캐스팅 추천 + 실행 계획 결정.

START 직후 실행되어 creative_goal, target_emotion,
quality_criteria 등을 설정한다. Phase 20-A: 인벤토리 인지 + 캐스팅 추천.
Phase 25: execution_plan으로 skip_stages를 자율 결정.
"""

from __future__ import annotations

from config import logger
from config_pipelines import DIRECTOR_MODEL, INVENTORY_CASTING_ENABLED
from services.agent.llm_models import CastingRecommendation, DirectorPlanOutput, validate_with_model
from services.agent.nodes._production_utils import run_production_step
from services.agent.prompt_builders import (
    build_casting_guide,
    build_casting_json_section,
    build_chat_context_block,
    build_feedback_section,
    build_inventory_characters_block,
    build_inventory_structures_block,
    build_inventory_styles_block,
    build_optional_section,
    build_references_block,
)
from services.agent.state import ScriptState
from services.script.gemini_generator import sanitize_chat_context as _sanitize_chat_context


def _load_inventory(group_id: int | None, max_count: int | None = None) -> dict:
    """DB에서 인벤토리를 로드하고 세션을 닫는다. 실패 시 빈 dict 반환."""
    from services.agent.inventory import load_full_inventory  # noqa: PLC0415

    return load_full_inventory(group_id, max_count=max_count)


def _extract_casting(result: dict) -> dict | None:
    """LLM 결과에서 casting 블록을 추출·검증한다."""
    raw = result.get("casting")
    if not raw or not isinstance(raw, dict):
        return None
    # 구 키 → 신 키 폴백 (LLM이 이전 포맷으로 응답할 경우 대비)
    if "character_id" in raw and "character_a_id" not in raw:
        raw["character_a_id"] = raw.pop("character_id")
    if "character_name" in raw and "character_a_name" not in raw:
        raw["character_a_name"] = raw.pop("character_name")
    try:
        validated = CastingRecommendation.model_validate(raw)
        return validated.model_dump()
    except Exception as e:
        logger.warning("[LangGraph] 캐스팅 추천 검증 실패: %s", e)
        return None


def _derive_skip_stages(result: dict) -> list[str]:
    """execution_plan에서 skip_stages를 결정. explain은 항상 실행."""
    ep = result.get("execution_plan") or {}
    stages: list[str] = []
    if not ep.get("run_research", True):
        stages.append("research")
    if not ep.get("run_concept", True):
        stages.append("concept")
    return stages


async def director_plan_node(state: ScriptState, config=None) -> dict:
    """Creative Director의 초기 목표 수립 + 캐스팅 추천 + 실행 계획 노드."""
    # Phase 20-A: 인벤토리 로드 (DB 세션은 LLM 호출 전에 닫음)
    inventory: dict = {}
    valid_char_ids: list[int] | None = None
    has_characters = False
    characters_block = ""
    structures_block = ""
    styles_block = ""
    casting_guide = ""

    if INVENTORY_CASTING_ENABLED:
        inventory = _load_inventory(state.get("group_id"))
        if inventory.get("characters"):
            has_characters = True
            characters_block = build_inventory_characters_block(inventory["characters"])
            structures_block = build_inventory_structures_block(inventory.get("structures", []))
            styles_block = build_inventory_styles_block(inventory.get("styles", []))
            casting_guide = build_casting_guide()
            valid_char_ids = [c.id for c in inventory["characters"]]

    description = state.get("description", "")
    style = state.get("style", "")
    structure = state.get("structure", "")
    references = state.get("references") or []
    chat_ctx = _sanitize_chat_context(state.get("chat_context") or [])

    template_vars = {
        "topic": state.get("topic", ""),
        "description_section": build_optional_section("- **상세 설명**:", description) if description else "",
        "duration": str(state.get("duration", 30)),
        "style_section": f"- **스타일**: {style}" if style else "",
        "language": state.get("language", "Korean"),
        "structure_section": f"- **구조**: {structure}" if structure else "",
        "chat_context_block": build_chat_context_block(chat_ctx) if chat_ctx else "",
        "references_block": ("\n## Reference Materials\n" + build_references_block(references) if references else ""),
        "characters_block": characters_block,
        "structures_block": structures_block,
        "styles_block": styles_block,
        "casting_guide": casting_guide,
        "casting_json_section": build_casting_json_section(has_characters),
        "feedback_section": build_feedback_section(state.get("director_plan_feedback"), header="## Retry Feedback"),
    }

    try:
        result = await run_production_step(
            template_name="creative/director_plan",
            template_vars=template_vars,
            validate_fn=lambda data: validate_with_model(DirectorPlanOutput, data).model_dump(),
            extract_key="",
            step_name="director_plan",
            model=DIRECTOR_MODEL,
        )

        plan = {
            "creative_goal": result.get("creative_goal", ""),
            "target_emotion": result.get("target_emotion", ""),
            "quality_criteria": result.get("quality_criteria", []),
            "risk_areas": result.get("risk_areas", []),
            "style_direction": result.get("style_direction", ""),
        }

        # Phase 20-A: 캐스팅 추천 추출
        casting = _extract_casting(result) if INVENTORY_CASTING_ENABLED else None

        # Phase 25: execution_plan → skip_stages 자율 결정
        derived_skip_stages = _derive_skip_stages(result)

        logger.info("[LangGraph] Director Plan 수립 완료: goal=%s", plan["creative_goal"][:50])
        return {
            "director_plan": plan,
            "casting_recommendation": casting,
            "valid_character_ids": valid_char_ids,
            "skip_stages": derived_skip_stages,
        }

    except Exception as e:
        logger.warning("[LangGraph] Director Plan 실패, graceful degradation: %s", e)
        return {"director_plan": None, "casting_recommendation": None, "skip_stages": []}
