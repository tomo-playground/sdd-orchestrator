"""LangFuse 콜백 핸들러 — 선택적 활성화.

LANGFUSE_ENABLED=false(기본)이면 None을 반환하여
LangGraph 파이프라인에 영향을 주지 않는다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from config import logger
from config_pipelines import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENABLED,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
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

    human_gate interrupt는 정상 동작이므로 trace output/metadata를 채워
    output=null(undefined) 상태를 방지한다.
    Langfuse v3 SDK는 OTel 기반이라 trace 직접 업데이트가 불가하여
    REST ingestion API를 사용한다.
    """
    if _handler is None:
        return

    trace_id = getattr(_handler, "last_trace_id", None)
    if not trace_id:
        logger.debug("[LangFuse] trace_id 없음, interrupt 기록 건너뜀")
        return

    try:
        import httpx

        now = datetime.now(UTC).isoformat()
        resp = httpx.post(
            f"{LANGFUSE_BASE_URL}/api/public/ingestion",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            json={
                "batch": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "trace-create",
                        "timestamp": now,
                        "body": {
                            "id": trace_id,
                            "timestamp": now,
                            "output": interrupt_data,
                            "metadata": {
                                "interrupted": True,
                                "interrupt_node": "human_gate",
                            },
                        },
                    },
                ],
            },
            timeout=5.0,
        )
        errors = resp.json().get("errors", [])
        if errors:
            logger.warning("[LangFuse] ingestion 오류: %s", errors)
        else:
            logger.info(
                "[LangFuse] interrupt 중간 결과 기록 (trace=%s)", trace_id[:16]
            )
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
