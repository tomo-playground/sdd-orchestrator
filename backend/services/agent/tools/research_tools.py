"""Research Agent용 도구 (Phase 10-B-2).

LLM이 필요한 정보원을 선택적으로 호출하여 research brief를 구성한다.
"""

from __future__ import annotations

import hashlib
from typing import Any

from google.genai import types
from langgraph.store.base import BaseStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import logger

from .base import define_tool


def _topic_key(topic: str) -> str:
    """토픽 문자열을 12자리 MD5 해시로 변환한다."""
    return hashlib.md5(topic.encode()).hexdigest()[:12]


# ── 도구 정의 ──────────────────────────────────────────────


def get_research_tools() -> list[types.Tool]:
    """Research Agent가 사용할 수 있는 도구 목록을 반환한다."""
    return [
        define_tool(
            name="search_topic_history",
            description="과거 동일/유사 주제로 생성된 스토리보드 이력을 검색합니다. 주제의 성공 패턴 분석에 활용합니다.",
            parameters={
                "topic": {
                    "type": "string",
                    "description": "검색할 주제 (예: '오늘 하루', '외로움')",
                },
                "limit": {
                    "type": "integer",
                    "description": "검색 결과 개수 (기본값: 5)",
                },
            },
            required=["topic"],
        ),
        define_tool(
            name="search_character_history",
            description="특정 캐릭터로 생성된 과거 스토리보드 이력을 검색합니다. 캐릭터의 톤, 어미, 선호 주제 분석에 활용합니다.",
            parameters={
                "character_id": {
                    "type": "integer",
                    "description": "캐릭터 ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "검색 결과 개수 (기본값: 5)",
                },
            },
            required=["character_id"],
        ),
        define_tool(
            name="fetch_url_content",
            description="URL에서 콘텐츠를 가져와 요약합니다. 사용자가 제공한 레퍼런스 URL 분석에 활용합니다.",
            parameters={
                "url": {
                    "type": "string",
                    "description": "가져올 URL (http:// 또는 https://)",
                },
            },
            required=["url"],
        ),
        define_tool(
            name="analyze_trending",
            description="해당 주제의 트렌딩 키워드 및 인기 패턴을 분석합니다. 최신 트렌드 반영이 필요한 주제에 활용합니다.",
            parameters={
                "topic": {
                    "type": "string",
                    "description": "분석할 주제",
                },
                "language": {
                    "type": "string",
                    "description": "언어 코드 (Korean, Japanese, English)",
                },
            },
            required=["topic", "language"],
        ),
        define_tool(
            name="get_group_dna",
            description="채널/시리즈의 톤, 세계관, 가이드라인을 조회합니다. 그룹별 일관성 유지에 활용합니다.",
            parameters={
                "group_id": {
                    "type": "integer",
                    "description": "그룹 ID",
                },
            },
            required=["group_id"],
        ),
    ]


# ── 도구 실행 함수 ─────────────────────────────────────────


async def _search_namespace(store: BaseStore, namespace: tuple, limit: int = 5) -> str | None:
    """네임스페이스를 검색하여 요약 문자열을 반환한다."""
    try:
        items = await store.asearch(namespace, limit=limit)
        if not items:
            return None
        summaries = []
        for item in items:
            val = item.value
            if isinstance(val, dict):
                summaries.append(str(val))
        if summaries:
            return " | ".join(summaries[:3])
    except Exception as e:
        logger.warning("[ResearchTool] 네임스페이스 검색 실패 (%s): %s", namespace, e)
    return None


def create_research_executors(
    store: BaseStore,
    db: AsyncSession,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Research Agent용 도구 실행 함수 맵을 생성한다.

    Args:
        store: LangGraph Store (Memory)
        db: DB 세션
        state: 현재 ScriptState

    Returns:
        도구 이름 → 실행 함수 매핑
    """

    async def search_topic_history(topic: str, limit: int = 5) -> str:
        """토픽 히스토리 검색."""
        topic_key = _topic_key(topic)
        result = await _search_namespace(store, ("topic", topic_key), limit=limit)
        if result:
            logger.info("[ResearchTool] 토픽 히스토리 검색 완료: %s", topic_key)
            return f"[토픽 히스토리] {result}"
        return f"[토픽 히스토리] '{topic}'에 대한 과거 이력 없음"

    async def search_character_history(character_id: int, limit: int = 5) -> str:
        """캐릭터 히스토리 검색."""
        result = await _search_namespace(store, ("character", str(character_id)), limit=limit)
        if result:
            logger.info("[ResearchTool] 캐릭터 히스토리 검색 완료: character_id=%d", character_id)
            return f"[캐릭터 히스토리] {result}"
        return f"[캐릭터 히스토리] character_id={character_id}의 과거 이력 없음"

    async def fetch_url_content(url: str) -> str:
        """URL 콘텐츠 fetch."""
        # research.py의 _fetch_url 재사용
        from services.agent.nodes.research import _fetch_url

        content = await _fetch_url(url)
        if content:
            logger.info("[ResearchTool] URL fetch 성공: %s", url)
            return f"[URL 콘텐츠]\n{content[:1000]}"
        return f"[URL 콘텐츠] {url} 가져오기 실패 (안전하지 않은 URL 또는 네트워크 에러)"

    async def analyze_trending(topic: str, language: str) -> str:
        """트렌딩 분석 (현재는 placeholder — 향후 외부 API 통합 예정)."""
        # TODO: 향후 트렌딩 API (Google Trends, YouTube API 등) 통합
        logger.info("[ResearchTool] 트렌딩 분석 요청: topic=%s, language=%s", topic, language)
        # Placeholder: 현재는 간단한 휴리스틱 반환
        return f"[트렌딩 분석] '{topic}'는 {language} 콘텐츠에서 꾸준한 관심 주제입니다. Hook에 질문형 구조를 사용하면 효과적입니다."

    async def get_group_dna(group_id: int) -> str:
        """그룹 DNA 조회."""
        # group 네임스페이스에서 채널 DNA 조회
        result = await _search_namespace(store, ("group", str(group_id)), limit=3)
        if result:
            logger.info("[ResearchTool] 그룹 DNA 조회 완료: group_id=%d", group_id)
            return f"[그룹 DNA] {result}"

        # 없으면 DB에서 group_config.channel_dna 조회
        try:
            from models import GroupConfig

            stmt = select(GroupConfig.channel_dna).where(GroupConfig.id == group_id)
            if isinstance(db, AsyncSession):
                result_proxy = await db.execute(stmt)
            else:
                result_proxy = db.execute(stmt)
            row = result_proxy.scalar_one_or_none()
            if row:
                dna = row
                tone = dna.get("tone", "")
                worldview = dna.get("worldview", "")
                guidelines = dna.get("guidelines", "")
                parts = []
                if tone:
                    parts.append(f"톤: {tone}")
                if worldview:
                    parts.append(f"세계관: {worldview}")
                if guidelines:
                    parts.append(f"가이드라인: {guidelines}")
                if parts:
                    logger.info("[ResearchTool] DB에서 그룹 DNA 조회 완료: group_id=%d", group_id)
                    return f"[그룹 DNA] {' | '.join(parts)}"
        except Exception as e:
            logger.warning("[ResearchTool] 그룹 DNA 조회 실패: %s", e)

        return f"[그룹 DNA] group_id={group_id}의 채널 DNA 없음"

    return {
        "search_topic_history": search_topic_history,
        "search_character_history": search_character_history,
        "fetch_url_content": fetch_url_content,
        "analyze_trending": analyze_trending,
        "get_group_dna": get_group_dna,
    }
