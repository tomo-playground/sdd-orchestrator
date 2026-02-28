"""Express 경량 캐스팅 노드 — 토픽만으로 캐릭터 자동 선택.

Phase 20-C: Express 모드에서 캐릭터 미선택 시 Flash 모델로
인벤토리 기반 캐스팅만 수행한다 (creative_goal/quality_criteria 생략).
"""

from __future__ import annotations

from config import logger
from config_pipelines import (
    DIRECTOR_LITE_MODEL,
    INVENTORY_CASTING_ENABLED,
    INVENTORY_LITE_MAX_CHARACTERS,
)
from services.agent.llm_models import CastingRecommendation, validate_with_model
from services.agent.nodes._production_utils import run_production_step
from services.agent.nodes.director_plan import _extract_casting, _load_inventory
from services.agent.state import ScriptState  # LangGraph node signature


class _CastingOnlyOutput(CastingRecommendation):
    """경량 캐스팅 전용 LLM 응답 — casting 필드만 최상위."""


async def director_plan_lite_node(state: ScriptState, config=None) -> dict:
    """Express 경량 캐스팅 노드 — Flash 모델로 캐스팅만 추천."""
    if not INVENTORY_CASTING_ENABLED:
        return {"casting_recommendation": None}

    inventory = _load_inventory(state.get("group_id"), max_count=INVENTORY_LITE_MAX_CHARACTERS)
    if not inventory.get("characters"):
        logger.info("[LangGraph] director_plan_lite: 인벤토리 캐릭터 없음, fallback 시도")
        return _fallback()

    template_vars = {
        "topic": state.get("topic", ""),
        "description": state.get("description", ""),
        "duration": state.get("duration", 30),
        "language": state.get("language", "ko"),
        "characters": inventory["characters"],
        "structures": inventory.get("structures", []),
        "styles": inventory.get("styles", []),
    }

    valid_char_ids = [c.id for c in inventory["characters"]]
    valid_style_ids = [s.id for s in inventory.get("styles", [])]

    try:
        result = await run_production_step(
            template_name="creative/director_plan_lite.j2",
            template_vars=template_vars,
            validate_fn=lambda data: validate_with_model(_CastingOnlyOutput, data).model_dump(),
            extract_key="",
            step_name="director_plan_lite",
            model=DIRECTOR_LITE_MODEL,
        )

        # lite 템플릿은 casting 필드를 최상위로 반환 → _extract_casting 인터페이스에 맞춰 래핑
        casting = _extract_casting({"casting": result})
        if not casting:
            logger.info("[LangGraph] director_plan_lite: LLM 캐스팅 추출 실패, fallback")
            return _fallback(valid_char_ids, valid_style_ids)

        logger.info("[LangGraph] director_plan_lite 완료: char=%s", casting.get("character_name"))
        return {
            "casting_recommendation": casting,
            "valid_character_ids": valid_char_ids,
            "valid_style_profile_ids": valid_style_ids,
        }

    except Exception as e:
        logger.warning("[LangGraph] director_plan_lite LLM 실패, fallback: %s", e)
        return _fallback(valid_char_ids, valid_style_ids)


def _fallback(
    valid_char_ids: list[int] | None = None,
    valid_style_ids: list[int] | None = None,
) -> dict:
    """LLM 실패 시 최근 사용 캐릭터로 fallback."""
    from database import get_db_session  # noqa: PLC0415
    from services.agent.inventory import load_fallback_character  # noqa: PLC0415

    try:
        with get_db_session() as db:
            fb = load_fallback_character(db)
    except Exception:
        fb = None

    if not fb:
        return {"casting_recommendation": None}

    casting = {
        "character_id": fb["character_id"],
        "character_name": fb["character_name"],
        "character_b_id": None,
        "character_b_name": "",
        "structure": "monologue",
        "style_profile_id": None,
        "reasoning": "자동 선택 (최근 사용 캐릭터)",
    }
    return {
        "casting_recommendation": casting,
        "valid_character_ids": valid_char_ids,
        "valid_style_profile_ids": valid_style_ids,
    }
