"""Director Plan 노드 — 초기 목표 수립 + 캐스팅 추천.

Full 모드에서 START 직후 실행되어 creative_goal, target_emotion,
quality_criteria 등을 설정한다. Phase 20-A: 인벤토리 인지 + 캐스팅 추천.
"""

from __future__ import annotations

from config import logger
from config_pipelines import DIRECTOR_MODEL, INVENTORY_CASTING_ENABLED
from services.agent.llm_models import CastingRecommendation, DirectorPlanOutput, validate_with_model
from services.agent.nodes._production_utils import run_production_step
from services.agent.nodes._skip_guard import should_skip
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState


def _load_inventory(group_id: int | None, max_count: int | None = None) -> dict:
    """DB에서 인벤토리를 로드하고 세션을 닫는다. 실패 시 빈 dict 반환."""
    from database import get_db_session  # noqa: PLC0415
    from services.agent.inventory import load_characters, load_structures, load_styles  # noqa: PLC0415

    try:
        with get_db_session() as db:
            characters = load_characters(db, group_id=group_id, max_count=max_count)
            styles = load_styles(db)
            structures = load_structures()
        return {
            "characters": characters,
            "styles": styles,
            "structures": structures,
        }
    except Exception as e:
        logger.warning("[LangGraph] 인벤토리 로드 실패, 캐스팅 없이 진행: %s", e)
        return {}


def _extract_casting(result: dict) -> dict | None:
    """LLM 결과에서 casting 블록을 추출·검증한다."""
    raw = result.get("casting")
    if not raw or not isinstance(raw, dict):
        return None
    try:
        validated = CastingRecommendation.model_validate(raw)
        return validated.model_dump()
    except Exception as e:
        logger.warning("[LangGraph] 캐스팅 추천 검증 실패: %s", e)
        return None


async def director_plan_node(state: ScriptState, config=None) -> dict:
    """Creative Director의 초기 목표 수립 + 캐스팅 추천 노드."""
    if should_skip(state, "director_plan"):
        return {"director_plan": None, "casting_recommendation": None}

    template_vars = {
        "topic": state.get("topic", ""),
        "description": state.get("description", ""),
        "duration": state.get("duration", 30),
        "style": state.get("style", ""),
        "language": state.get("language", "ko"),
        "structure": state.get("structure", ""),
        "references": state.get("references") or [],
    }

    # Phase 20-A: 인벤토리 로드 (DB 세션은 LLM 호출 전에 닫음)
    inventory: dict = {}
    valid_char_ids: list[int] | None = None
    valid_style_ids: list[int] | None = None

    if INVENTORY_CASTING_ENABLED:
        inventory = _load_inventory(state.get("group_id"))
        if inventory.get("characters"):
            template_vars["characters"] = inventory["characters"]
            template_vars["structures"] = inventory.get("structures", [])
            template_vars["styles"] = inventory.get("styles", [])
            valid_char_ids = [c.id for c in inventory["characters"]]
            valid_style_ids = [s.id for s in inventory.get("styles", [])]

    try:
        async with trace_llm_call(name="director_plan", input_text=template_vars.get("topic", "")):
            result = await run_production_step(
                template_name="creative/director_plan.j2",
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

        logger.info("[LangGraph] Director Plan 수립 완료: goal=%s", plan["creative_goal"][:50])
        return {
            "director_plan": plan,
            "casting_recommendation": casting,
            "valid_character_ids": valid_char_ids,
            "valid_style_profile_ids": valid_style_ids,
        }

    except Exception as e:
        logger.warning("[LangGraph] Director Plan 실패, graceful degradation: %s", e)
        return {"director_plan": None, "casting_recommendation": None}
