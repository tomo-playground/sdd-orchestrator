"""AsyncPostgresSaver 싱글턴 — LangGraph checkpoint 저장소.

서버 기동 시 한 번 초기화하고, 종료 시 정리한다.
AsyncConnectionPool을 사용하여 동시 checkpoint 접근을 지원한다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool

from config import CHECKPOINT_GC_RETENTION_DAYS, DATABASE_URL, logger

_checkpointer: AsyncPostgresSaver | None = None
_pool: AsyncConnectionPool | None = None
_lock = asyncio.Lock()


async def get_checkpointer() -> AsyncPostgresSaver:
    """싱글턴 checkpointer를 반환한다. 최초 호출 시 초기화."""
    global _checkpointer, _pool
    if _checkpointer is not None:
        return _checkpointer

    async with _lock:
        # Double-check after acquiring lock
        if _checkpointer is not None:
            return _checkpointer

        _pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=2,
            max_size=5,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await _pool.open()
        _checkpointer = AsyncPostgresSaver(conn=_pool)
        await _checkpointer.setup()
        logger.info("[LangGraph] AsyncPostgresSaver 초기화 완료 (pool: 2-5)")
        return _checkpointer


async def close_checkpointer() -> None:
    """checkpointer 커넥션 풀을 정리한다."""
    global _checkpointer, _pool
    async with _lock:
        if _pool is not None:
            await _pool.close()
        _checkpointer = None
        _pool = None
    logger.info("[LangGraph] AsyncPostgresSaver 종료 완료")


async def gc_checkpoints(retention_days: int | None = None) -> dict:
    """Delete checkpoint data for threads older than retention period.

    Uses checkpoint_id (UUID v6, time-sortable) to determine age.
    Returns summary dict with counts.
    """
    days = retention_days or CHECKPOINT_GC_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    # UUID v6 timestamp: encode cutoff as hex prefix for comparison
    # UUID v6 embeds 60-bit timestamp (100ns ticks since 1582-10-15)
    _UUID_EPOCH = datetime(1582, 10, 15, tzinfo=timezone.utc)
    ticks = int((cutoff - _UUID_EPOCH).total_seconds() * 1e7)
    # UUID v6 format: time_high (32b) - time_mid (16b) - version(4b)+time_low(12b)
    time_high = (ticks >> 28) & 0xFFFFFFFF
    time_mid = (ticks >> 12) & 0xFFFF
    time_low = ticks & 0xFFF
    cutoff_uuid = f"{time_high:08x}-{time_mid:04x}-6{time_low:03x}-8000-000000000000"

    conn = await AsyncConnection.connect(DATABASE_URL, autocommit=True, prepare_threshold=0)
    try:
        # Find old threads: all checkpoint_ids < cutoff_uuid
        q_select = sql.SQL(
            "SELECT DISTINCT thread_id FROM checkpoints "
            "WHERE thread_id NOT IN ("
            "  SELECT DISTINCT thread_id FROM checkpoints "
            "  WHERE checkpoint_id >= {cutoff}"
            ")"
        ).format(cutoff=sql.Literal(cutoff_uuid))
        cur = await conn.execute(q_select)
        old_threads = [row[0] for row in await cur.fetchall()]

        if not old_threads:
            logger.info("[Checkpoint GC] No old threads to clean (retention=%dd)", days)
            return {"deleted_threads": 0, "retention_days": days}

        # Delete from all 3 tables
        deleted = {}
        for table in ["checkpoint_writes", "checkpoint_blobs", "checkpoints"]:
            q_del = sql.SQL("DELETE FROM {tbl} WHERE thread_id = ANY({ids})").format(
                tbl=sql.Identifier(table),
                ids=sql.Literal(old_threads),
            )
            cur = await conn.execute(q_del)
            deleted[table] = cur.rowcount

        logger.info(
            "[Checkpoint GC] Cleaned %d threads (retention=%dd): %s",
            len(old_threads),
            days,
            deleted,
        )
        return {
            "deleted_threads": len(old_threads),
            "retention_days": days,
            "deleted_rows": deleted,
        }
    finally:
        await conn.close()
