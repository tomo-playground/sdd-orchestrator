"""LangFuse 콜백 핸들러 — 선택적 활성화.

LANGFUSE_ENABLED=false(기본)이면 None을 반환하여
LangGraph 파이프라인에 영향을 주지 않는다.

요청별 trace_id는 contextvars로 전파하여 동시성을 보장한다.
"""

from __future__ import annotations

import contextvars
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from config import logger
from config_pipelines import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENABLED,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
)

_langfuse_client = None
_initialized = False

# GENERATION input/output 최대 기록 길이 (디버깅용)
_MAX_IO_LEN = 8000

# 요청별 trace_id를 전파하는 contextvar (asyncio 태스크별 자동 분리)
_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("langfuse_trace_id", default=None)
# 요청별 root span을 전파하는 contextvar (generation의 부모로 사용)
_current_root_span: contextvars.ContextVar[Any] = contextvars.ContextVar("langfuse_root_span", default=None)


def _to_hex32(trace_id: str) -> str:
    """UUID 형식 trace_id를 Langfuse v3가 요구하는 32자 hex로 변환한다."""
    return trace_id.replace("-", "")


def _ensure_initialized() -> bool:
    """Langfuse 클라이언트를 초기화한다. 성공 시 True 반환."""
    global _langfuse_client, _initialized
    if _initialized:
        return _langfuse_client is not None

    _initialized = True

    if not LANGFUSE_ENABLED:
        logger.info("[LangFuse] 비활성 (LANGFUSE_ENABLED=false)")
        return False

    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse()
        logger.info("[LangFuse] 클라이언트 초기화 완료 (host=%s)", LANGFUSE_BASE_URL)
        return True
    except Exception as e:
        logger.warning("[LangFuse] 초기화 실패 (서비스는 정상 동작): %s", e)
        return False


def get_langfuse_client():
    """초기화된 LangFuse 클라이언트를 반환한다. 비활성 시 None."""
    _ensure_initialized()
    return _langfuse_client


@asynccontextmanager
async def trace_context(
    name: str,
    *,
    session_id: str | None = None,
    input_data: Any = None,
):
    """LangGraph 비의존 trace context. 내부 trace_llm_call()이 이 trace에 연결된다.

    analyze-topic 등 LangGraph 파이프라인 외부의 독립 Gemini 호출에 사용한다.
    """
    if not _ensure_initialized() or _langfuse_client is None:
        yield
        return

    trace_id = uuid.uuid4().hex
    prev_trace_id = _current_trace_id.get()
    _current_trace_id.set(trace_id)
    try:
        _langfuse_client.trace(
            id=trace_id,
            name=name,
            session_id=session_id,
            input=input_data,
        )
        yield
    finally:
        _current_trace_id.set(prev_trace_id)
        try:
            _langfuse_client.flush()
        except Exception:
            pass


def create_langfuse_handler(
    *,
    trace_id: str | None = None,
    session_id: str | None = None,
    action: str = "generate",
) -> Any:
    """요청별 CallbackHandler를 생성하고 trace_id를 contextvar에 설정한다.

    trace_id가 없으면 새로 생성한다 (fresh generate).
    생성된 trace_id는 동일 asyncio 태스크 내 trace_llm_call()에서 자동 참조된다.

    Args:
        action: 워크플로우 액션. "generate" 또는 "resume".
            Trace name = "storyboard.{action}", Root Span name = "pipeline.{action}".
    """
    if not _ensure_initialized():
        return None

    try:
        from langfuse.langchain import CallbackHandler

        if not trace_id:
            trace_id = uuid.uuid4().hex
        else:
            trace_id = _to_hex32(trace_id)
        _current_trace_id.set(trace_id)

        trace_ctx: dict[str, str] = {"trace_id": trace_id}

        # 명시적 Trace 생성 (SDK 기본 "LangGraph" 대신 의미 있는 이름 부여)
        _langfuse_client.trace(
            id=trace_id,
            name=f"storyboard.{action}",
            session_id=session_id,
        )

        # Root span을 만들어 이후 generation들의 부모로 사용
        root_span = _langfuse_client.start_span(
            trace_context=trace_ctx,
            name=f"pipeline.{action}",
            metadata={"session_id": session_id} if session_id else None,
        )
        _current_root_span.set(root_span)

        handler = CallbackHandler(trace_context=trace_ctx)
        logger.debug("[LangFuse] 핸들러 생성 (trace=%s, action=%s, session=%s)", trace_id[:16], action, session_id)
        return handler
    except Exception as e:
        logger.warning("[LangFuse] 요청별 핸들러 생성 실패: %s", e)
        return None


def update_trace_on_interrupt(
    interrupt_data: dict,
    *,
    trace_id: str | None = None,
    interrupt_node: str = "unknown",
) -> None:
    """GraphInterrupt 시 Langfuse 트레이스에 중간 결과를 기록한다.

    interrupt_data는 output이 아닌 metadata에 저장한다.
    output 필드를 오염시키면 resume 후 Langfuse 목록에서 input/output이
    뒤바뀌어 보이는 문제가 발생한다.
    """
    if _langfuse_client is None:
        return

    raw_id = trace_id or _current_trace_id.get()
    if not raw_id:
        logger.debug("[LangFuse] trace_id 없음, interrupt 기록 건너뜀")
        return
    resolved_trace_id = _to_hex32(raw_id)

    try:
        import httpx

        now = datetime.now(UTC).isoformat()
        resp = httpx.post(
            f"{LANGFUSE_BASE_URL}/api/public/ingestion",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            json={
                "batch": [
                    {
                        "id": uuid.uuid4().hex,
                        "type": "trace-create",
                        "timestamp": now,
                        "body": {
                            "id": resolved_trace_id,
                            "timestamp": now,
                            "metadata": {
                                "interrupted": True,
                                "interrupt_node": interrupt_node,
                                "interrupt_data": interrupt_data,
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
            logger.info("[LangFuse] interrupt 기록 (node=%s, trace=%s)", interrupt_node, resolved_trace_id[:16])
    except Exception as e:
        logger.warning("[LangFuse] interrupt 트레이스 업데이트 실패: %s", e)


def update_root_span(*, input_data: Any = None, output_data: Any = None) -> None:
    """root span에 input/output을 기록한다."""
    root_span = _current_root_span.get()
    if root_span is None:
        return
    try:
        kwargs: dict[str, Any] = {}
        if input_data is not None:
            kwargs["input"] = input_data
        if output_data is not None:
            kwargs["output"] = output_data
        if kwargs:
            root_span.update(**kwargs)
    except Exception:
        pass


def end_root_span() -> None:
    """요청 완료 시 root span을 종료한다."""
    root_span = _current_root_span.get()
    if root_span is not None:
        try:
            root_span.end()
        except Exception:
            pass
        _current_root_span.set(None)


def update_trace_on_completion(*, trace_id: str | None = None, output_data: dict | None = None) -> None:
    """Resume 완료 시 LangFuse 트레이스의 interrupted 메타데이터를 리셋한다."""
    if _langfuse_client is None:
        return

    raw_id = trace_id or _current_trace_id.get()
    if not raw_id:
        return
    resolved_trace_id = _to_hex32(raw_id)

    try:
        import httpx

        now = datetime.now(UTC).isoformat()
        body: dict = {
            "id": resolved_trace_id,
            "timestamp": now,
            "metadata": {
                "interrupted": False,
                "completed": True,
            },
        }
        if output_data is not None:
            body["output"] = output_data

        resp = httpx.post(
            f"{LANGFUSE_BASE_URL}/api/public/ingestion",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            json={
                "batch": [
                    {
                        "id": uuid.uuid4().hex,
                        "type": "trace-create",
                        "timestamp": now,
                        "body": body,
                    },
                ],
            },
            timeout=5.0,
        )
        errors = resp.json().get("errors", [])
        if errors:
            logger.warning("[LangFuse] completion 업데이트 오류: %s", errors)
        else:
            logger.info("[LangFuse] completion 메타데이터 업데이트 (trace=%s)", resolved_trace_id[:16])
    except Exception as e:
        logger.warning("[LangFuse] completion 트레이스 업데이트 실패: %s", e)


def flush_langfuse() -> None:
    """shutdown 시 LangFuse 버퍼를 플러시한다."""
    end_root_span()
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            logger.info("[LangFuse] 버퍼 플러시 완료")
        except Exception as e:
            logger.warning("[LangFuse] 플러시 실패: %s", e)


# ── Gemini GENERATION 추적 ────────────────────────────────────


def _safe_extract_text(response: Any) -> str:
    """response.text 대신 parts에서 text만 추출한다 (function_call 경고 방지)."""
    try:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return ""
        parts = getattr(candidates[0].content, "parts", None)
        if not parts:
            return ""
        return "".join(getattr(p, "text", "") or "" for p in parts if hasattr(p, "text"))
    except Exception:
        return getattr(response, "text", "") or ""


def _extract_usage(response: Any) -> dict[str, int] | None:
    """Gemini response에서 token usage를 추출한다."""
    meta = getattr(response, "usage_metadata", None)
    if not meta:
        return None
    return {
        "input": int(getattr(meta, "prompt_token_count", 0) or 0),
        "output": int(getattr(meta, "candidates_token_count", 0) or 0),
        "total": int(getattr(meta, "total_token_count", 0) or 0),
    }


@dataclass
class LLMCallResult:
    """trace_llm_call()이 yield하는 결과 객체."""

    generation: Any = None
    output: str = ""
    usage: dict[str, int] | None = None

    def record(self, response: Any) -> None:
        """기존 Gemini response 파싱 (하위 호환 유지)."""
        self.output = _safe_extract_text(response)
        self.usage = _extract_usage(response)

    def record_text(self, text: str, usage: dict[str, int] | None = None) -> None:
        """Provider-agnostic 기록. Ollama 등 non-Gemini provider에서 사용."""
        self.output = text
        self.usage = usage


@asynccontextmanager
async def trace_llm_call(
    name: str,
    model: str = "",
    input_text: str = "",
    *,
    metadata: dict[str, Any] | None = None,
    langfuse_prompt: Any = None,
):
    """Gemini 호출을 LangFuse GENERATION으로 추적한다.

    contextvar에서 요청별 trace_id를 읽어 동일 trace 트리에 연결한다.
    LangFuse 비활성 시 no-op으로 동작한다 (graceful degradation).

    Args:
        metadata: 추가 메타데이터 (template_name 등). generation.metadata에 기록.
        langfuse_prompt: LangFuse Prompt 객체. generation에 연결하여 버전 추적.
    """
    if _langfuse_client is None:
        yield LLMCallResult()
        return

    raw_trace_id = _current_trace_id.get()
    trace_ctx = {"trace_id": _to_hex32(raw_trace_id)} if raw_trace_id else None
    root_span = _current_root_span.get()

    gen_kwargs: dict[str, Any] = {
        "name": name,
        "model": model or "",
        "input": input_text[:_MAX_IO_LEN],
    }
    if metadata:
        gen_kwargs["metadata"] = metadata
    if langfuse_prompt is not None:
        gen_kwargs["prompt"] = langfuse_prompt

    # root span이 있으면 자식으로 생성 (계층 구조 — trace_context 불필요)
    # root span이 없으면 _langfuse_client에서 직접 연결 (trace_context 필요)
    if root_span:
        generation = root_span.start_generation(**gen_kwargs)
    else:
        generation = _langfuse_client.start_generation(trace_context=trace_ctx, **gen_kwargs)
    result = LLMCallResult(generation=generation)
    try:
        yield result
        generation.update(
            output=result.output[:_MAX_IO_LEN] if result.output else "",
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
