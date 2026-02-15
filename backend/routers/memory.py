"""Memory Store 관리 API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import logger
from schemas import MemoryDeleteResponse, MemoryItem, MemoryListResponse, MemoryStatsResponse

router = APIRouter(prefix="/memory", tags=["memory"])

VALID_NS_TYPES = {"character", "topic", "user", "group", "feedback"}


def _to_iso(val) -> str | None:
    """datetime 또는 문자열을 ISO 문자열로 변환한다."""
    if val is None:
        return None
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


async def _get_store():
    from services.agent.store import get_store

    return await get_store()


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """네임스페이스별 카운트 통계."""
    store = await _get_store()
    stats = {}
    total = 0
    for ns_type in VALID_NS_TYPES:
        items = await store.asearch((ns_type,), limit=1000)
        stats[ns_type] = len(items)
        total += len(items)
    return MemoryStatsResponse(total=total, by_namespace=stats)


@router.get("/{ns_type}", response_model=MemoryListResponse)
async def list_memory_items(ns_type: str):
    """타입별 항목 목록."""
    if ns_type not in VALID_NS_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid namespace type: {ns_type}")
    store = await _get_store()
    items = await store.asearch((ns_type,), limit=100)
    return MemoryListResponse(
        namespace=ns_type,
        items=[
            MemoryItem(
                namespace=list(item.namespace),
                key=item.key,
                value=item.value,
                created_at=_to_iso(getattr(item, "created_at", None)),
                updated_at=_to_iso(getattr(item, "updated_at", None)),
            )
            for item in items
        ],
    )


@router.get("/{ns_type}/{ns_id}", response_model=MemoryListResponse)
async def get_memory_namespace(ns_type: str, ns_id: str):
    """특정 네임스페이스 조회."""
    if ns_type not in VALID_NS_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid namespace type: {ns_type}")
    store = await _get_store()
    items = await store.asearch((ns_type, ns_id), limit=100)
    return MemoryListResponse(
        namespace=f"{ns_type}/{ns_id}",
        items=[
            MemoryItem(
                namespace=list(item.namespace),
                key=item.key,
                value=item.value,
                created_at=_to_iso(getattr(item, "created_at", None)),
                updated_at=_to_iso(getattr(item, "updated_at", None)),
            )
            for item in items
        ],
    )


@router.delete("/{ns_type}/{ns_id}/{key}", response_model=MemoryDeleteResponse)
async def delete_memory_item(ns_type: str, ns_id: str, key: str):
    """단일 항목 삭제."""
    if ns_type not in VALID_NS_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid namespace type: {ns_type}")
    store = await _get_store()
    await store.adelete((ns_type, ns_id), key)
    logger.info("[Memory] 항목 삭제: (%s, %s) key=%s", ns_type, ns_id, key)
    return MemoryDeleteResponse(success=True, message="항목이 삭제되었습니다")


@router.delete("/{ns_type}/{ns_id}", response_model=MemoryDeleteResponse)
async def delete_memory_namespace(ns_type: str, ns_id: str):
    """네임스페이스 전체 삭제."""
    if ns_type not in VALID_NS_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid namespace type: {ns_type}")
    store = await _get_store()
    items = await store.asearch((ns_type, ns_id), limit=1000)
    for item in items:
        await store.adelete((ns_type, ns_id), item.key)
    logger.info("[Memory] 네임스페이스 삭제: (%s, %s) — %d items", ns_type, ns_id, len(items))
    return MemoryDeleteResponse(success=True, message=f"{len(items)}개 항목이 삭제되었습니다")
