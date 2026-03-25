"""StoryCard 서비스 — CRUD + Gemini 대량 생성 + status 관리."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.story_card import StoryCard

logger = logging.getLogger(__name__)


def list_story_cards(
    db: Session,
    group_id: int,
    *,
    status: str | None = None,
    cluster: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[StoryCard], int]:
    """시리즈별 소재 카드 목록 조회 (status/cluster 필터, 페이지네이션)."""
    q = db.query(StoryCard).filter(
        StoryCard.group_id == group_id,
        StoryCard.deleted_at.is_(None),
    )
    if status:
        q = q.filter(StoryCard.status == status)
    if cluster:
        q = q.filter(StoryCard.cluster == cluster)
    total = q.count()
    items = (
        q.order_by(
            StoryCard.hook_score.desc().nullslast(),
            StoryCard.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def create_story_card(db: Session, group_id: int, data: dict) -> StoryCard:
    """소재 카드 단건 생성."""
    card = StoryCard(group_id=group_id, **data)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_story_card(db: Session, card_id: int) -> StoryCard | None:
    """소재 카드 단건 조회 (soft delete 필터)."""
    return db.query(StoryCard).filter(StoryCard.id == card_id, StoryCard.deleted_at.is_(None)).first()


def update_story_card(db: Session, card_id: int, data: dict) -> StoryCard | None:
    """소재 카드 부분 수정."""
    card = get_story_card(db, card_id)
    if not card:
        return None
    for key, value in data.items():
        setattr(card, key, value)
    # status → "used" 전환 시 used_at 자동 설정
    if data.get("status") == "used" and card.used_at is None:
        card.used_at = datetime.now(UTC)
    # status → "unused" 전환 시 used_at/used_in_storyboard_id 초기화
    if data.get("status") == "unused":
        card.used_at = None
        card.used_in_storyboard_id = None
    db.commit()
    db.refresh(card)
    return card


def delete_story_card(db: Session, card_id: int) -> StoryCard | None:
    """소재 카드 Soft Delete."""
    card = get_story_card(db, card_id)
    if not card:
        return None
    card.deleted_at = func.now()
    db.commit()
    return card


def mark_cards_as_used(
    db: Session,
    card_ids: list[int],
    storyboard_id: int | None = None,
) -> int:
    """소재 카드를 사용 완료 상태로 일괄 전환. 이미 used인 카드는 스킵."""
    now = datetime.now(UTC)
    updated = (
        db.query(StoryCard)
        .filter(
            StoryCard.id.in_(card_ids),
            StoryCard.status == "unused",
            StoryCard.deleted_at.is_(None),
        )
        .update(
            {
                StoryCard.status: "used",
                StoryCard.used_at: now,
                StoryCard.used_in_storyboard_id: storyboard_id,
            },
            synchronize_session="fetch",
        )
    )
    db.commit()
    return updated


def _build_generate_prompt(
    group_name: str, group_description: str, cluster: str, count: int, existing_titles: list[str]
) -> tuple[str, str]:
    """Gemini 소재 생성용 시스템/유저 프롬프트를 구성한다."""
    existing_text = "\n".join(f"- {t}" for t in existing_titles) if existing_titles else "(없음)"
    system_prompt = "당신은 쇼츠 콘텐츠 소재 전문가입니다. 시리즈 특성에 맞는 고품질 소재 카드를 생성합니다."
    user_prompt = f"""## 시리즈 정보
- 이름: {group_name}
- 설명: {group_description}
- 소재 분류: {cluster}
- 생성 개수: {count}

## 이미 사용된 소재 (중복 금지)
{existing_text}

## 출력 형식 (JSON 배열)
[{{
  "title": "소재 제목",
  "situation": "구체적 상황 설명",
  "hook_angle": "시청자를 끌어당기는 각도",
  "key_moments": ["핵심 장면1", "핵심 장면2", "핵심 장면3"],
  "emotional_arc": {{"start": "시작 감정", "peak": "절정 감정", "end": "마무리 감정"}},
  "empathy_details": ["공감 디테일1", "공감 디테일2"],
  "characters_hint": {{"speaker_a": "캐릭터 A 성격/역할", "speaker_b": "캐릭터 B 성격/역할"}},
  "hook_score": 0.85
}}]"""
    return system_prompt, user_prompt


def _parse_and_save_cards(db: Session, group_id: int, cluster: str, raw: str) -> list[StoryCard]:
    """Gemini JSON 응답을 파싱하여 StoryCard 인스턴스를 생성·저장한다."""
    try:
        cards_data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini JSON 파싱 실패: {e}") from e
    if not isinstance(cards_data, list):
        raise ValueError("Gemini 응답이 JSON 배열이 아닙니다.")

    created: list[StoryCard] = []
    for item in cards_data:
        card = StoryCard(
            group_id=group_id,
            cluster=cluster,
            title=item.get("title", "Untitled"),
            situation=item.get("situation"),
            hook_angle=item.get("hook_angle"),
            key_moments=item.get("key_moments"),
            emotional_arc=item.get("emotional_arc"),
            empathy_details=item.get("empathy_details"),
            characters_hint=item.get("characters_hint"),
            hook_score=item.get("hook_score"),
            status="unused",
        )
        db.add(card)
        created.append(card)
    db.commit()
    for c in created:
        db.refresh(c)
    return created


async def generate_story_cards(db: Session, group_id: int, cluster: str, count: int) -> list[StoryCard]:
    """Gemini Flash로 소재 카드를 배치 생성한다."""
    from models.group import Group
    from services.llm import LLMConfig, get_llm_provider

    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.is_(None)).first()
    if not group:
        raise ValueError(f"Group {group_id} not found")

    existing_titles = [
        t[0]
        for t in db.query(StoryCard.title).filter(StoryCard.group_id == group_id, StoryCard.deleted_at.is_(None)).all()
    ]

    system_prompt, user_prompt = _build_generate_prompt(
        group.name, group.description or "", cluster, count, existing_titles
    )
    config = LLMConfig(system_instruction=system_prompt, temperature=0.9, response_mime_type="application/json")
    resp = await get_llm_provider().generate(step_name="story_card.generate", contents=user_prompt, config=config)
    return _parse_and_save_cards(db, group_id, cluster, resp.text.strip())
