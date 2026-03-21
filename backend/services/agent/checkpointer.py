"""AsyncPostgresSaver — LangGraph checkpoint 저장소.

Pool은 싱글턴, checkpointer는 **요청별** 생성한다.
AsyncPostgresSaver 내부의 asyncio.Lock이 싱글턴 인스턴스에서 동시 요청을
직렬화하여 "another command is already in progress" 에러를 유발하므로,
요청별 인스턴스를 만들어 lock 경합을 제거한다.
(ref: https://github.com/langchain-ai/langgraph/issues/3193)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection, sql
from psycopg_pool import AsyncConnectionPool

from config import CHECKPOINT_GC_RETENTION_DAYS, DATABASE_URL
from config import pipeline_logger as logger

_pool: AsyncConnectionPool | None = None
_lock = asyncio.Lock()


async def _ensure_pool() -> AsyncConnectionPool:
    """싱글턴 connection pool을 반환한다. 최초 호출 시 생성."""
    global _pool
    if _pool is not None:
        return _pool

    async with _lock:
        if _pool is not None:
            return _pool

        _pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=2,
            max_size=5,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await _pool.open()
        logger.info("[LangGraph] Checkpointer pool 초기화 완료 (2-5)")
        return _pool


async def init_checkpointer() -> None:
    """서버 startup 시 pool 생성 + 테이블 마이그레이션을 실행한다."""
    pool = await _ensure_pool()
    async with pool.connection() as conn:
        saver = AsyncPostgresSaver(conn)
        await saver.setup()
    logger.info("[LangGraph] Checkpointer 테이블 준비 완료")


@asynccontextmanager
async def get_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """요청별 checkpointer를 생성한다. async with 로 사용."""
    pool = await _ensure_pool()
    async with pool.connection() as conn:
        yield AsyncPostgresSaver(conn)


async def close_checkpointer() -> None:
    """checkpointer 커넥션 풀을 정리한다."""
    global _pool
    async with _lock:
        if _pool is not None:
            await _pool.close()
        _pool = None
    logger.info("[LangGraph] Checkpointer pool 종료 완료")


async def gc_checkpoints(retention_days: int | None = None) -> dict:
    """Delete checkpoint data for threads older than retention period.

    Uses checkpoint_id (UUID v6, time-sortable) to determine age.
    Returns summary dict with counts.
    """
    days = retention_days or CHECKPOINT_GC_RETENTION_DAYS
    cutoff = datetime.now(UTC) - timedelta(days=days)
    # UUID v6 timestamp: encode cutoff as hex prefix for comparison
    # UUID v6 embeds 60-bit timestamp (100ns ticks since 1582-10-15)
    _UUID_EPOCH = datetime(1582, 10, 15, tzinfo=UTC)
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
