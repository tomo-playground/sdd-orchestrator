"""AsyncPostgresSaver 싱글턴 — LangGraph checkpoint 저장소.

서버 기동 시 한 번 초기화하고, 종료 시 정리한다.
from_conn_string()는 async context manager이므로,
psycopg.AsyncConnection을 직접 관리하여 수명을 분리한다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection, sql

from config import CHECKPOINT_GC_RETENTION_DAYS, DATABASE_URL, logger

_checkpointer: AsyncPostgresSaver | None = None
_conn: AsyncConnection | None = None
_lock = asyncio.Lock()


async def get_checkpointer() -> AsyncPostgresSaver:
    """싱글턴 checkpointer를 반환한다. 최초 호출 시 초기화."""
    global _checkpointer, _conn
    if _checkpointer is not None:
        return _checkpointer

    async with _lock:
        # Double-check after acquiring lock
        if _checkpointer is not None:
            return _checkpointer

        _conn = await AsyncConnection.connect(DATABASE_URL, autocommit=True, prepare_threshold=0)
        _checkpointer = AsyncPostgresSaver(conn=_conn)
        await _checkpointer.setup()
        logger.info("[LangGraph] AsyncPostgresSaver 초기화 완료")
        return _checkpointer


async def close_checkpointer() -> None:
    """checkpointer 커넥션을 정리한다."""
    global _checkpointer, _conn
    async with _lock:
        if _conn is not None:
            await _conn.close()
        _checkpointer = None
        _conn = None
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
