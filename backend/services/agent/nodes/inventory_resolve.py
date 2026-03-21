"""Phase 20-A: Inventory Resolve 노드.

Director의 캐스팅 추천을 유효성 검증 후 state에 확정한다.
캐스팅 SSOT: Director 추천 → plan_review 사용자 승인 → 이 노드에서 확정.
Pure Python 노드 (LLM 호출 없음).
"""

from __future__ import annotations

from config import MULTI_CHAR_STRUCTURES, coerce_structure_id
from config import pipeline_logger as logger
from services.agent.nodes._skip_guard import should_skip
from services.agent.state import ScriptState


def _validate_casting(casting: dict, state: ScriptState) -> dict | None:
    """캐스팅 추천의 유효성을 검증한다. 실패 시 None."""
    valid_chars = state.get("valid_character_ids") or []

    # 1. character_a_id 유효성
    char_a_id = casting.get("character_a_id")
    if char_a_id and char_a_id not in valid_chars:
        logger.info("[LangGraph] inventory_resolve: character_a_id=%s 유효하지 않음, 무시", char_a_id)
        casting["character_a_id"] = None
        casting["character_a_name"] = ""

    # 2. character_b_id 유효성
    char_b_id = casting.get("character_b_id")
    if char_b_id and char_b_id not in valid_chars:
        logger.info("[LangGraph] inventory_resolve: character_b_id=%s 유효하지 않음, 무시", char_b_id)
        casting["character_b_id"] = None
        casting["character_b_name"] = ""

    # 3. 중복 검증
    if casting.get("character_a_id") and casting["character_a_id"] == casting.get("character_b_id"):
        logger.info("[LangGraph] inventory_resolve: character_a_id == character_b_id, B를 제거")
        casting["character_b_id"] = None
        casting["character_b_name"] = ""

    # 4. 구조 적합성: 2인 구조 → character_b_id 자동 할당 시도
    structure = casting.get("structure")
    if structure in MULTI_CHAR_STRUCTURES and casting.get("character_a_id") and not casting.get("character_b_id"):
        char_a_id = casting["character_a_id"]
        others = [cid for cid in valid_chars if cid != char_a_id]
        if others:
            casting["character_b_id"] = others[0]
            logger.info(
                "[LangGraph] inventory_resolve: 2인 구조(%s)에 character_b 자동 할당 → %s", structure, others[0]
            )
        else:
            logger.info("[LangGraph] inventory_resolve: 2인 구조(%s)에 다른 캐릭터 없음, monologue로 변경", structure)
            casting["structure"] = "monologue"

    # 유효한 추천이 하나도 없으면 None
    if not casting.get("character_a_id") and not casting.get("structure"):
        return None

    return casting


async def inventory_resolve_node(state: ScriptState, config=None) -> dict:  # noqa: ARG001
    """Director 캐스팅 추천을 검증하고 state에 확정한다.

    캐스팅 SSOT = Director 추천 (plan_review에서 사용자가 승인/수정 피드백).
    Frontend는 structure/character를 전달하지 않으므로 user override 로직 불필요.
    """
    if should_skip(state, "inventory_resolve"):
        return {"casting_recommendation": None}

    casting = state.get("casting_recommendation")
    if not casting or not isinstance(casting, dict):
        # Director가 캐스팅을 생성하지 않았어도, Frontend가 structure를 지정했으면 보존
        raw_structure = state.get("structure")
        if raw_structure:
            coerced = coerce_structure_id(raw_structure)
            logger.info(
                "[LangGraph] inventory_resolve: 캐스팅 추천 없음, user structure='%s' 보존",
                coerced,
            )
            return {"structure": coerced}
        logger.info("[LangGraph] inventory_resolve: 캐스팅 추천 없음, 패스스루")
        return {"casting_recommendation": None}

    # 깊은 복사하여 원본 수정 방지
    casting = dict(casting)
    validated = _validate_casting(casting, state)

    if not validated:
        logger.info("[LangGraph] inventory_resolve: 유효한 추천 없음")
        return {"casting_recommendation": None}

    # Director 캐스팅을 state에 확정 (SSOT)
    result: dict = {"casting_recommendation": validated}

    if validated.get("character_a_id"):
        result["character_id"] = validated["character_a_id"]
    if validated.get("character_b_id"):
        result["character_b_id"] = validated["character_b_id"]
    if validated.get("structure"):
        result["structure"] = validated["structure"]

    logger.info(
        "[LangGraph] inventory_resolve 완료: char=%s, char_b=%s, structure=%s",
        result.get("character_id", "-"),
        result.get("character_b_id", "-"),
        result.get("structure", "-"),
    )
    return result
