"""AsyncPostgresStore 싱글턴 — LangGraph Memory Store.

서버 기동 시 한 번 초기화하고, 종료 시 정리한다.
from_conn_string()는 async context manager이므로,
psycopg.AsyncConnection을 직접 관리하여 수명을 분리한다.
(checkpointer.py와 동일한 싱글턴 패턴)
"""

from __future__ import annotations

import asyncio

from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from config import DATABASE_URL, logger

_store: AsyncPostgresStore | None = None
_conn: AsyncConnection | None = None
_lock = asyncio.Lock()


async def get_store() -> AsyncPostgresStore:
    """싱글턴 store를 반환한다. 최초 호출 시 초기화."""
    global _store, _conn
    if _store is not None:
        return _store

    async with _lock:
        if _store is not None:
            return _store

        _conn = await AsyncConnection.connect(
            DATABASE_URL, autocommit=True, prepare_threshold=0, row_factory=dict_row,
        )
        _store = AsyncPostgresStore(conn=_conn)
        await _store.setup()
        logger.info("[LangGraph] AsyncPostgresStore 초기화 완료")
        return _store


async def close_store() -> None:
    """store 커넥션을 정리한다."""
    global _store, _conn
    async with _lock:
        if _conn is not None:
            await _conn.close()
        _store = None
        _conn = None
    logger.info("[LangGraph] AsyncPostgresStore 종료 완료")
