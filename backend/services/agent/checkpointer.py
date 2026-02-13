"""AsyncPostgresSaver 싱글턴 — LangGraph checkpoint 저장소.

서버 기동 시 한 번 초기화하고, 종료 시 정리한다.
from_conn_string()는 async context manager이므로,
psycopg.AsyncConnection을 직접 관리하여 수명을 분리한다.
"""

from __future__ import annotations

import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection

from config import DATABASE_URL, logger

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
