"""AsyncPostgresStore 싱글턴 — LangGraph Memory Store.

서버 기동 시 한 번 초기화하고, 종료 시 정리한다.
checkpointer.py와 동일한 싱글턴 패턴 사용.
"""

from __future__ import annotations

import asyncio

from langgraph.store.postgres.aio import AsyncPostgresStore

from config import DATABASE_URL, logger

_store: AsyncPostgresStore | None = None
_lock = asyncio.Lock()


async def get_store() -> AsyncPostgresStore:
    """싱글턴 store를 반환한다. 최초 호출 시 초기화."""
    global _store
    if _store is not None:
        return _store

    async with _lock:
        if _store is not None:
            return _store

        _store = await AsyncPostgresStore.from_conn_string(DATABASE_URL)
        await _store.setup()
        logger.info("[LangGraph] AsyncPostgresStore 초기화 완료")
        return _store


async def close_store() -> None:
    """store 커넥션을 정리한다."""
    global _store
    async with _lock:
        if _store is not None:
            # AsyncPostgresStore manages its own connection pool
            _store = None
    logger.info("[LangGraph] AsyncPostgresStore 종료 완료")
