"""LangFuse 콜백 핸들러 — 선택적 활성화.

LANGFUSE_ENABLED=false(기본)이면 None을 반환하여
LangGraph 파이프라인에 영향을 주지 않는다.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from config import GEMINI_TEXT_MODEL, logger
from config_pipelines import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENABLED,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
)

_handler = None
_langfuse_client = None
_initialized = False


def _ensure_initialized() -> bool:
    """Langfuse 클라이언트를 초기화한다. 성공 시 True 반환."""
    global _handler, _langfuse_client, _initialized
    if _initialized:
        return _handler is not None

    _initialized = True

    if not LANGFUSE_ENABLED:
        logger.info("[LangFuse] 비활성 (LANGFUSE_ENABLED=false)")
        return False

    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        _langfuse_client = Langfuse()
        _handler = CallbackHandler(public_key=LANGFUSE_PUBLIC_KEY)
        logger.info("[LangFuse] 콜백 핸들러 초기화 완료 (host=%s)", LANGFUSE_BASE_URL)
        return True
    except Exception as e:
        logger.warning("[LangFuse] 초기화 실패 (서비스는 정상 동작): %s", e)
        _handler = None
        return False


def get_langfuse_handler():
    """LangFuse CallbackHandler 싱글턴. 비활성 시 None 반환."""
    _ensure_initialized()
    return _handler


def create_langfuse_handler(*, trace_id: str | None = None, session_id: str | None = None):
    """요청별 CallbackHandler를 생성한다.

    trace_id가 주어지면 기존 trace에 이어서 기록한다 (resume용).
    """
    if not _ensure_initialized():
        return None

    try:
        from langfuse.langchain import CallbackHandler

        kwargs: dict[str, Any] = {"public_key": LANGFUSE_PUBLIC_KEY}
        if trace_id:
            kwargs["trace_id"] = trace_id
        if session_id:
            kwargs["session_id"] = session_id
        return CallbackHandler(**kwargs)
    except Exception as e:
        logger.warning("[LangFuse] 요청별 핸들러 생성 실패: %s", e)
        return None


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


# ── Gemini GENERATION 추적 ────────────────────────────────────


@dataclass
class LLMCallResult:
    """trace_llm_call()이 yield하는 결과 객체."""

    generation: Any = None
    output: str = ""
    usage: dict[str, int] | None = None

    def record(self, response: Any) -> None:
        """Gemini 응답에서 output 텍스트와 토큰 사용량을 추출한다."""
        self.output = getattr(response, "text", "") or ""
        meta = getattr(response, "usage_metadata", None)
        if meta:
            self.usage = {
                "input": int(getattr(meta, "prompt_token_count", 0) or 0),
                "output": int(getattr(meta, "candidates_token_count", 0) or 0),
                "total": int(getattr(meta, "total_token_count", 0) or 0),
            }


@asynccontextmanager
async def trace_llm_call(
    name: str,
    model: str = "",
    input_text: str = "",
):
    """Gemini 호출을 LangFuse GENERATION으로 추적한다.

    LangFuse 비활성 시 no-op으로 동작한다 (graceful degradation).
    """
    if _langfuse_client is None:
        yield LLMCallResult()
        return

    trace_id = getattr(_handler, "last_trace_id", None)
    trace_ctx = {"trace_id": trace_id} if trace_id else None
    generation = _langfuse_client.start_generation(
        trace_context=trace_ctx,
        name=name,
        model=model or GEMINI_TEXT_MODEL,
        input=input_text[:2000],
    )
    result = LLMCallResult(generation=generation)
    try:
        yield result
        generation.update(
            output=result.output[:2000] if result.output else "",
            usage_details=result.usage,
        )
        generation.end()
    except Exception as e:
        generation.update(
            level="ERROR",
            status_message=str(e)[:500],
        )
        generation.end()
        raise
