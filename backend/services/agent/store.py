"""AsyncPostgresStore 싱글턴 — LangGraph Memory Store.

서버 기동 시 한 번 초기화하고, 종료 시 정리한다.
AsyncConnectionPool을 사용하여 동시 접근을 지원한다.
(checkpointer.py와 동일한 풀 패턴)
"""

from __future__ import annotations

import asyncio

from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import DATABASE_URL
from config import pipeline_logger as logger

_store: AsyncPostgresStore | None = None
_pool: AsyncConnectionPool | None = None
_lock = asyncio.Lock()


async def get_store() -> AsyncPostgresStore:
    """싱글턴 store를 반환한다. 최초 호출 시 초기화."""
    global _store, _pool
    if _store is not None:
        return _store

    async with _lock:
        if _store is not None:
            return _store

        _pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=2,
            max_size=5,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )
        await _pool.open()
        _store = AsyncPostgresStore(conn=_pool)
        await _store.setup()
        logger.info("[LangGraph] AsyncPostgresStore 초기화 완료 (pool: 2-5)")
        return _store


async def close_store() -> None:
    """store 커넥션 풀을 정리한다."""
    global _store, _pool
    async with _lock:
        if _pool is not None:
            await _pool.close()
        _store = None
        _pool = None
    logger.info("[LangGraph] AsyncPostgresStore 종료 완료")
