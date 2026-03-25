"""Research Agent용 도구 (Phase 10-B-2).

LLM이 필요한 정보원을 선택적으로 호출하여 research brief를 구성한다.
"""

from __future__ import annotations

from typing import Any

from google.genai import types
from langgraph.store.base import BaseStore
from sqlalchemy.orm import Session

from config import pipeline_logger as logger

from .base import define_tool

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
            name="get_story_cards",
            description="시리즈(그룹)에 등록된 미사용 소재 카드를 조회합니다. 대본 작성 시 검증된 소재를 활용할 수 있습니다.",
            parameters={
                "group_id": {
                    "type": "integer",
                    "description": "그룹(시리즈) ID",
                },
                "topic": {
                    "type": "string",
                    "description": "현재 주제 (시맨틱 매칭용, 선택)",
                },
                "limit": {
                    "type": "integer",
                    "description": "조회 개수 (기본값: 10)",
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
    db: Session,
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
        from services.agent.utils import topic_key

        t_key = topic_key(topic)
        result = await _search_namespace(store, ("topic", t_key), limit=limit)
        if result:
            logger.info("[ResearchTool] 토픽 히스토리 검색 완료: %s", t_key)
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

    async def get_story_cards(group_id: int, topic: str = "", limit: int = 10) -> str:
        """시리즈 소재 카드 조회. 선택된 카드 ID를 state에 기록한다."""
        from models.story_card import StoryCard

        try:
            cards = (
                db.query(StoryCard)
                .filter(
                    StoryCard.group_id == group_id,
                    StoryCard.status == "unused",
                    StoryCard.deleted_at.is_(None),
                )
                .order_by(StoryCard.hook_score.desc().nullslast(), StoryCard.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.warning("[ResearchTool] 소재 카드 조회 실패: %s", e)
            return "[소재 카드] 조회 실패"

        if not cards:
            return "[소재 카드] 미사용 소재 없음"

        # 소재를 포맷팅하여 반환
        card_ids = [c.id for c in cards]
        parts = [f"[소재 카드] {len(cards)}개 미사용 소재:"]
        for c in cards:
            parts.append(f"\n### {c.title} (score: {c.hook_score or 'N/A'})")
            if c.situation:
                parts.append(f"  상황: {c.situation}")
            if c.hook_angle:
                parts.append(f"  후크: {c.hook_angle}")
            if c.key_moments:
                parts.append(f"  핵심: {', '.join(str(k) for k in c.key_moments)}")

        # state에 카드 ID 기록 (Writer → Finalize → storyboard save 시 활용)
        existing_ids = state.get("used_story_card_ids") or []
        state["used_story_card_ids"] = existing_ids + card_ids

        # state에 카드 dict 기록 (Writer 프롬프트 빌더용)
        card_dicts = [
            {
                "title": c.title,
                "situation": c.situation,
                "hook_angle": c.hook_angle,
                "key_moments": c.key_moments,
                "emotional_arc": c.emotional_arc,
                "empathy_details": c.empathy_details,
            }
            for c in cards
        ]
        existing_cards = state.get("story_materials") or []
        state["story_materials"] = existing_cards + card_dicts

        logger.info("[ResearchTool] 소재 카드 %d개 조회 (group_id=%d)", len(cards), group_id)
        return "\n".join(parts)

    return {
        "search_topic_history": search_topic_history,
        "search_character_history": search_character_history,
        "fetch_url_content": fetch_url_content,
        "analyze_trending": analyze_trending,
        "get_story_cards": get_story_cards,
    }
