"""LangFuse 콜백 핸들러 — 선택적 활성화.

LANGFUSE_ENABLED=false(기본)이면 None을 반환하여
LangGraph 파이프라인에 영향을 주지 않는다.
"""

from __future__ import annotations

from config import logger
from config_pipelines import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENABLED,
    LANGFUSE_PUBLIC_KEY,
)

_handler = None
_langfuse_client = None
_initialized = False


def get_langfuse_handler():
    """LangFuse CallbackHandler 싱글턴. 비활성 시 None 반환."""
    global _handler, _langfuse_client, _initialized
    if _initialized:
        return _handler

    _initialized = True

    if not LANGFUSE_ENABLED:
        logger.info("[LangFuse] 비활성 (LANGFUSE_ENABLED=false)")
        return None

    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        _langfuse_client = Langfuse()
        _handler = CallbackHandler(public_key=LANGFUSE_PUBLIC_KEY)
        logger.info("[LangFuse] 콜백 핸들러 초기화 완료 (host=%s)", LANGFUSE_BASE_URL)
    except Exception as e:
        logger.warning("[LangFuse] 초기화 실패 (서비스는 정상 동작): %s", e)
        _handler = None

    return _handler


def update_trace_on_interrupt(interrupt_data: dict) -> None:
    """GraphInterrupt 시 Langfuse 트레이스에 중간 결과를 기록한다.

    human_gate interrupt는 정상 동작이므로 output을 채워
    ERROR(output=null) 상태를 방지한다.
    """
    if _handler is None or _langfuse_client is None:
        return

    try:
        trace_id = _handler.get_trace_id()
        if not trace_id:
            return

        _langfuse_client.trace(
            id=trace_id,
            output=interrupt_data,
            metadata={"interrupted": True, "interrupt_node": "human_gate"},
        )
        _langfuse_client.flush()
        logger.info("[LangFuse] interrupt 중간 결과 기록 (trace=%s)", trace_id[:16])
    except Exception as e:
        logger.warning("[LangFuse] interrupt 트레이스 업데이트 실패: %s", e)


def flush_langfuse() -> None:
    """shutdown 시 LangFuse 버퍼를 플러시한다."""
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            logger.info("[LangFuse] 버퍼 플러시 완료")
        except Exception as e:
            logger.warning("[LangFuse] 플러시 실패: %s", e)
