"""Research 노드 — Memory Store에서 과거 생성 히스토리를 조회한다.

character, topic, user, group 네임스페이스를 검색하여
draft/debate 노드에 전달할 research_brief를 구성한다.
"""

from __future__ import annotations

import hashlib

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from config import logger
from services.agent.state import ScriptState


def _topic_key(topic: str) -> str:
    """토픽 문자열을 12자리 MD5 해시로 변환한다."""
    return hashlib.md5(topic.encode()).hexdigest()[:12]


async def _search_namespace(store: BaseStore, namespace: tuple, label: str) -> str | None:
    """네임스페이스를 검색하여 요약 문자열을 반환한다."""
    try:
        items = await store.asearch(namespace, limit=5)
        if not items:
            return None
        summaries = []
        for item in items:
            val = item.value
            if isinstance(val, dict):
                summaries.append(str(val))
        if summaries:
            return f"[{label}] " + " | ".join(summaries[:3])
    except Exception as e:
        logger.warning("[Research] %s 검색 실패: %s", label, e)
    return None


async def research_node(state: ScriptState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """Memory Store에서 관련 히스토리를 수집하여 research_brief를 구성한다."""
    brief_parts: list[str] = []

    # 1) Character history
    char_id = state.get("character_id")
    if char_id:
        result = await _search_namespace(store, ("character", str(char_id)), "캐릭터")
        if result:
            brief_parts.append(result)

    # 2) Topic history
    topic = state.get("topic", "")
    if topic:
        topic_key = _topic_key(topic)
        result = await _search_namespace(store, ("topic", topic_key), "토픽")
        if result:
            brief_parts.append(result)

    # 3) User preferences
    result = await _search_namespace(store, ("user", "preferences"), "사용자 선호")
    if result:
        brief_parts.append(result)

    # 4) Group history
    group_id = state.get("group_id")
    if group_id:
        result = await _search_namespace(store, ("group", str(group_id)), "그룹")
        if result:
            brief_parts.append(result)

    brief = "\n".join(brief_parts) if brief_parts else None
    if brief:
        logger.info("[Research] brief 구성 완료 (%d 섹션)", len(brief_parts))
    else:
        logger.info("[Research] 저장된 히스토리 없음 — 빈 brief")

    return {"research_brief": brief}
