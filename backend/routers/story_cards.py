"""소재 카드 API — 시리즈별 대본 소재 풀 관리."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    DeleteStatusResponse,
    StoryCardCreate,
    StoryCardGenerateRequest,
    StoryCardListResponse,
    StoryCardResponse,
    StoryCardUpdate,
)
from services.story_card import (
    create_story_card,
    delete_story_card,
    generate_story_cards,
    list_story_cards,
    update_story_card,
)

# group-scoped 라우터: /groups/{group_id}/story-cards
group_scoped_router = APIRouter(prefix="/groups", tags=["story-cards"])

# item 라우터: /story-cards/{id}
item_router = APIRouter(prefix="/story-cards", tags=["story-cards"])


@group_scoped_router.get(
    "/{group_id}/story-cards",
    response_model=StoryCardListResponse,
)
def api_list_story_cards(
    group_id: int,
    status: str | None = None,
    cluster: str | None = None,
    offset: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    items, total = list_story_cards(db, group_id, status=status, cluster=cluster, offset=offset, limit=limit)
    return StoryCardListResponse(items=items, total=total)


@group_scoped_router.post(
    "/{group_id}/story-cards",
    response_model=StoryCardResponse,
    status_code=201,
)
def api_create_story_card(
    group_id: int,
    body: StoryCardCreate,
    db: Session = Depends(get_db),
):
    from models.group import Group

    group = db.query(Group).filter(Group.id == group_id, Group.deleted_at.is_(None)).first()
    if not group:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    return create_story_card(db, group_id, body.model_dump(exclude_unset=True))


@group_scoped_router.post(
    "/{group_id}/story-cards/generate",
    response_model=list[StoryCardResponse],
)
async def api_generate_story_cards(
    group_id: int,
    body: StoryCardGenerateRequest,
    db: Session = Depends(get_db),
):
    try:
        return await generate_story_cards(db, group_id, body.cluster, body.count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@item_router.patch(
    "/{card_id}",
    response_model=StoryCardResponse,
)
def api_update_story_card(
    card_id: int,
    body: StoryCardUpdate,
    db: Session = Depends(get_db),
):
    card = update_story_card(db, card_id, body.model_dump(exclude_unset=True))
    if not card:
        raise HTTPException(status_code=404, detail=f"StoryCard {card_id} not found")
    return card


@item_router.delete(
    "/{card_id}",
    response_model=DeleteStatusResponse,
)
def api_delete_story_card(
    card_id: int,
    db: Session = Depends(get_db),
):
    card = delete_story_card(db, card_id)
    if not card:
        raise HTTPException(status_code=404, detail=f"StoryCard {card_id} not found")
    return DeleteStatusResponse(status="deleted", id=card_id)
