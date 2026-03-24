"""Intake 노드 — Guided 모드에서 사용자 의도를 파악한다.

Director Plan 앞에 위치하여, 소크라테스식 질문으로
structure/tone/캐릭터를 확정한다.
단일 interrupt 패턴: LLM이 토픽을 분석하여 제안 → 모든 질문을 한 번에 전달.
"""

from __future__ import annotations

from langgraph.types import interrupt

from config import (
    MULTI_CHAR_STRUCTURES,
    STRUCTURE_HINTS,
    STRUCTURE_METADATA,
    TONE_HINTS,
    TONE_METADATA,
    coerce_structure_id,
    coerce_tone_id,
)
from config import pipeline_logger as logger
from services.agent.state import ScriptState

_FALLBACK_SYSTEM = (
    "You are a topic classifier for short-form video scripts. "
    "Analyze the user's topic and suggest the best structure and tone."
)
_FALLBACK_USER = (
    "Topic: {topic}\n"
    "Description: {description}\n\n"
    "Respond in JSON: "
    '{{"suggested_structure": "monologue|dialogue|narrated_dialogue", '
    '"suggested_tone": "intimate|emotional|dynamic|humorous|suspense", '
    '"reasoning": "한국어로 이유 설명"}}'
)


def _load_inventory(group_id: int | None) -> dict:
    """DB에서 인벤토리를 로드한다. 실패 시 빈 dict."""
    from services.agent.inventory import load_full_inventory  # noqa: PLC0415

    return load_full_inventory(group_id)


async def _analyze_topic(topic: str, description: str) -> dict:
    """LLM으로 토픽을 분석하여 structure/tone을 제안한다."""
    from config_pipelines import INTAKE_MODEL  # noqa: PLC0415, E501
    from services.agent.langfuse_prompt import compile_prompt  # noqa: PLC0415
    from services.llm.registry import get_llm_provider  # noqa: PLC0415
    from services.llm.types import LLMConfig  # noqa: PLC0415

    template_vars = {"topic": topic, "description": description or ""}

    try:
        compiled = compile_prompt("creative/intake", **template_vars)
        system = compiled.system
        user = compiled.user

        use_fallback = not system and not user
        if use_fallback:
            logger.warning("[Intake] LangFuse 프롬프트 미존재, fallback 사용")
            system = _FALLBACK_SYSTEM
            user = _FALLBACK_USER.format(**template_vars)

        llm_config = LLMConfig(
            system_instruction=system,
            temperature=0.0,
            thinking_budget=0,
            response_mime_type="application/json",
        )
        response = await get_llm_provider().generate(
            step_name="intake_analyze_topic",
            contents=user,
            config=llm_config,
            model=INTAKE_MODEL,
            langfuse_prompt=None if use_fallback else compiled.langfuse_prompt,
        )
        if not response.text:
            return {}
        from services.creative_utils import parse_json_response  # noqa: PLC0415

        return parse_json_response(response.text)
    except Exception as e:
        logger.warning("[Intake] 토픽 분석 실패: %s", e)
        return {}


def _build_intake_summary(
    topic: str,
    structure: str,
    tone: str,
    characters: list,
    char_a: int | None,
    char_b: int | None,
) -> str:
    """Intake 결정 요약 문자열을 생성한다."""
    parts = [topic[:30]]

    # structure label
    struct_meta = next((s for s in STRUCTURE_METADATA if s.id == structure), None)
    parts.append(struct_meta.label_ko if struct_meta else structure)

    # tone label
    tone_meta = next((t for t in TONE_METADATA if t.id == tone), None)
    parts.append(tone_meta.label_ko if tone_meta else tone)

    # character names
    char_map = {c.id: c.name for c in characters}
    names = []
    if char_a and char_a in char_map:
        names.append(char_map[char_a])
    if char_b and char_b in char_map:
        names.append(char_map[char_b])
    if names:
        parts.append("↔".join(names) if len(names) == 2 else names[0])

    return ", ".join(parts)


def _build_interrupt_payload(analysis: dict, characters: list) -> dict:
    """interrupt에 전달할 질문 payload를 구성한다."""
    return {
        "type": "intake",
        "analysis": {
            "suggested_structure": analysis.get("suggested_structure"),
            "suggested_tone": analysis.get("suggested_tone"),
            "reasoning": analysis.get("reasoning", ""),
        },
        "questions": [
            {
                "key": "structure",
                "message": "어떤 형태의 영상을 상상하고 계세요?",
                "options": [
                    {"id": s.id, "label": s.label_ko, "description": STRUCTURE_HINTS.get(s.id, "")}
                    for s in STRUCTURE_METADATA
                ],
            },
            {
                "key": "tone",
                "message": "어떤 분위기를 원하세요?",
                "options": [
                    {"id": t.id, "label": t.label_ko, "description": TONE_HINTS.get(t.id, "")} for t in TONE_METADATA
                ],
            },
            {
                "key": "characters",
                "message": "캐릭터를 골라볼까요?",
                "applicable": True,
                # AI 제안 기반 초기 힌트. Frontend는 이 값을 절대 기준으로 쓰지 말고,
                # structure 선택이 바뀌면 MULTI_CHAR_STRUCTURES 기준으로 동적 갱신해야 함.
                "needs_two": analysis.get("suggested_structure", "monologue") in MULTI_CHAR_STRUCTURES,
                "characters": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "gender": getattr(c, "gender", None),
                        "summary": getattr(c, "appearance_summary", ""),
                    }
                    for c in characters
                ],
            },
        ],
    }


def _parse_resume(user_input: dict, analysis: dict, state: ScriptState) -> dict:
    """resume 값을 파싱하여 structure/tone/character를 결정한다."""
    structure = coerce_structure_id(user_input.get("structure") or analysis.get("suggested_structure") or "monologue")
    tone = coerce_tone_id(user_input.get("tone") or analysis.get("suggested_tone") or "intimate")

    char_a = user_input.get("character_id") or state.get("character_id")
    char_b = user_input.get("character_b_id") or state.get("character_b_id")

    if structure not in MULTI_CHAR_STRUCTURES:
        char_b = None

    return {"structure": structure, "tone": tone, "character_id": char_a, "character_b_id": char_b}


async def intake_node(state: ScriptState, config=None) -> dict:  # noqa: ARG001
    """사용자 의도 파악 노드. LLM 분석 → 단일 interrupt → 결과 반환."""
    topic = state.get("topic", "")
    description = state.get("description", "")
    group_id = state.get("group_id")

    logger.info("[LangGraph:Intake] 시작 — topic=%s", topic[:50])

    inventory = _load_inventory(group_id)
    characters = inventory.get("characters", [])

    analysis = await _analyze_topic(topic, description)
    user_input = interrupt(_build_interrupt_payload(analysis, characters))

    result = _parse_resume(user_input, analysis, state)
    summary = _build_intake_summary(
        topic, result["structure"], result["tone"], characters, result["character_id"], result["character_b_id"]
    )
    logger.info("[LangGraph:Intake] 완료 — %s", summary)

    return {**result, "intake_summary": summary}


__all__ = ["intake_node"]
