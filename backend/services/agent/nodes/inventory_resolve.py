"""Phase 20-A: Inventory Resolve 노드.

Director의 캐스팅 추천을 유효성 검증하고, user override와 병합한다.
Pure Python 노드 (LLM 호출 없음).
"""

from __future__ import annotations

from config import logger
from services.agent.nodes._skip_guard import should_skip
from services.agent.state import ScriptState

_TWO_CHAR_STRUCTURES = frozenset({"dialogue", "narrated_dialogue"})


def _validate_casting(casting: dict, state: ScriptState) -> dict | None:
    """캐스팅 추천의 유효성을 검증한다. 실패 시 None."""
    valid_chars = state.get("valid_character_ids") or []

    # 1. character_id 유효성
    char_id = casting.get("character_id")
    if char_id and char_id not in valid_chars:
        logger.info("[LangGraph] inventory_resolve: character_id=%s 유효하지 않음, 무시", char_id)
        casting["character_id"] = None
        casting["character_name"] = ""

    # 2. character_b_id 유효성
    char_b_id = casting.get("character_b_id")
    if char_b_id and char_b_id not in valid_chars:
        logger.info("[LangGraph] inventory_resolve: character_b_id=%s 유효하지 않음, 무시", char_b_id)
        casting["character_b_id"] = None
        casting["character_b_name"] = ""

    # 3. 중복 검증
    if casting.get("character_id") and casting["character_id"] == casting.get("character_b_id"):
        logger.info("[LangGraph] inventory_resolve: character_id == character_b_id, B를 제거")
        casting["character_b_id"] = None
        casting["character_b_name"] = ""

    # 4. 구조 적합성: 2인 구조 → character_b_id 필수
    structure = casting.get("structure")
    if structure in _TWO_CHAR_STRUCTURES and casting.get("character_id") and not casting.get("character_b_id"):
        logger.info(
            "[LangGraph] inventory_resolve: 2인 구조(%s)에 character_b 없음, 구조를 monologue로 변경", structure
        )
        casting["structure"] = "monologue"

    # 유효한 추천이 하나도 없으면 None
    if not casting.get("character_id") and not casting.get("structure"):
        return None

    return casting


async def inventory_resolve_node(state: ScriptState, config=None) -> dict:
    """인벤토리 유효성 검증 + user override 병합."""
    if should_skip(state, "inventory_resolve"):
        return {"casting_recommendation": None}

    casting = state.get("casting_recommendation")
    if not casting or not isinstance(casting, dict):
        logger.info("[LangGraph] inventory_resolve: 캐스팅 추천 없음, 패스스루")
        return {"casting_recommendation": None}

    # 깊은 복사하여 원본 수정 방지
    casting = dict(casting)
    validated = _validate_casting(casting, state)

    if not validated:
        logger.info("[LangGraph] inventory_resolve: 유효한 추천 없음")
        return {"casting_recommendation": None}

    # User override 병합: user가 이미 선택한 값은 유지
    result: dict = {"casting_recommendation": validated}

    # character_id: user 선택 우선
    user_char = state.get("character_id")
    if not user_char and validated.get("character_id"):
        result["character_id"] = validated["character_id"]

    # character_b_id: user 선택 우선
    user_char_b = state.get("character_b_id")
    if not user_char_b and validated.get("character_b_id"):
        result["character_b_id"] = validated["character_b_id"]

    # structure: user 선택 우선 (빈 문자열이 아닌 경우)
    user_structure = state.get("structure", "")
    if not user_structure and validated.get("structure"):
        result["structure"] = validated["structure"]

    logger.info(
        "[LangGraph] inventory_resolve 완료: char=%s, char_b=%s, structure=%s",
        result.get("character_id", "user"),
        result.get("character_b_id", "user"),
        result.get("structure", "user"),
    )
    return result
