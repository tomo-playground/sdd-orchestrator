"""Script generation endpoints."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import LANGGRAPH_DEFAULT_MODE, LANGGRAPH_PRESETS, logger
from database import get_db
from schemas import (
    ScriptFeedbackRequest,
    ScriptFeedbackResponse,
    ScriptGenerateResponse,
    ScriptPresetItem,
    ScriptPresetsResponse,
    ScriptResumeRequest,
    StoryboardRequest,
)
from langgraph.store.base import BaseStore
from services.agent.script_graph import get_compiled_graph
from services.agent.state import ScriptState

# LangGraph Command (런타임에서만 사용)
try:
    from langgraph.types import Command
except ImportError:
    Command = None  # type: ignore[assignment, misc]

router = APIRouter(prefix="/scripts", tags=["scripts"])

# -- 노드별 SSE 메타데이터 --
_NODE_META: dict[str, dict] = {
    "research": {"label": "리서치", "percent": 5},
    "debate": {"label": "컨셉 토론", "percent": 15},
    "draft": {"label": "대본 생성", "percent": 40},
    "review": {"label": "구조 검증", "percent": 70},
    "revise": {"label": "수정 중", "percent": 75},
    "human_gate": {"label": "승인 대기", "percent": 85},
    "finalize": {"label": "최종화", "percent": 95},
    "learn": {"label": "완료", "percent": 100},
}


def _request_to_state(request: StoryboardRequest) -> ScriptState:
    """StoryboardRequest → ScriptState 변환."""
    mode = request.mode or LANGGRAPH_DEFAULT_MODE
    preset_data = LANGGRAPH_PRESETS.get(request.preset or "") or {}
    if preset_data:
        mode = preset_data.get("mode", mode)

    return ScriptState(
        topic=request.topic,
        description=request.description or "",
        duration=request.duration,
        style=request.style,
        language=request.language,
        structure=request.structure,
        actor_a_gender=request.actor_a_gender,
        character_id=request.character_id,
        character_b_id=request.character_b_id,
        group_id=request.group_id,
        mode=mode,
        preset=request.preset,
        auto_approve=preset_data.get("auto_approve", False),
        revision_count=0,
    )


def _resolve_thread_id() -> str:
    """매 요청마다 새 UUID 기반 thread_id를 생성한다."""
    return f"script-{uuid.uuid4().hex[:12]}"


def _build_config(thread_id: str) -> dict:
    """LangGraph config를 구성한다. LangFuse 콜백이 있으면 주입."""
    from services.agent.observability import get_langfuse_handler

    cfg: dict = {"configurable": {"thread_id": thread_id}}
    handler = get_langfuse_handler()
    if handler is not None:
        cfg["callbacks"] = [handler]
    return cfg


def _state_to_response(result: dict) -> dict:
    """Graph 결과 → API 응답 dict 변환."""
    return {
        "scenes": result.get("final_scenes") or [],
        "character_id": result.get("draft_character_id"),
        "character_b_id": result.get("draft_character_b_id"),
    }


@router.post("/generate", response_model=ScriptGenerateResponse)
async def generate_script_endpoint(
    request: StoryboardRequest,
    db: Session = Depends(get_db),  # noqa: ARG001
):
    """동기 엔드포인트 — 내부적으로 Graph를 경유한다."""
    logger.info("📝 [Script Generate] %s", request.model_dump())
    graph = await get_compiled_graph()
    state = _request_to_state(request)
    config = _build_config(_resolve_thread_id())
    result = await graph.ainvoke(state, config)
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return _state_to_response(result)


def _is_graph_interrupt(exc: Exception) -> bool:
    """GraphInterrupt 여부를 안전하게 확인한다."""
    return type(exc).__name__ == "GraphInterrupt"


def _build_node_payload(
    node_name: str, thread_id: str, node_output: dict, char_ids: list[int | None],
) -> dict:
    """노드 이벤트를 SSE payload dict로 변환한다 (공통 로직)."""
    meta = _NODE_META.get(node_name, {"label": node_name, "percent": 50})
    payload: dict = {
        "node": node_name,
        "label": meta["label"],
        "percent": meta["percent"],
        "status": "running",
        "thread_id": thread_id,
    }

    if node_name == "draft":
        char_ids[0] = node_output.get("draft_character_id")
        char_ids[1] = node_output.get("draft_character_b_id")

    if node_name == "finalize":
        final_scenes = node_output.get("final_scenes")
        if final_scenes is not None:
            payload["status"] = "completed"
            payload["result"] = {
                "scenes": final_scenes,
                "character_id": char_ids[0],
                "character_b_id": char_ids[1],
            }

    if node_output.get("error"):
        payload["status"] = "error"
        payload["error"] = node_output["error"]

    return payload


async def _stream_graph_events(
    graph_input: object, config: dict, thread_id: str, label: str,
) -> AsyncGenerator[str]:
    """Graph를 스트리밍하며 SSE 이벤트를 yield한다."""
    graph = await get_compiled_graph()
    char_ids: list[int | None] = [None, None]

    try:
        async for event in graph.astream(graph_input, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                payload = _build_node_payload(node_name, thread_id, node_output, char_ids)
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    except Exception as e:
        if _is_graph_interrupt(e):
            payload = {
                "node": "human_gate",
                "label": "승인 대기",
                "percent": 85,
                "status": "waiting_for_input",
                "thread_id": thread_id,
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        else:
            logger.error("[SSE] %s error: %s", label, e)
            error_payload = {
                "node": "error",
                "label": "오류",
                "percent": 0,
                "status": "error",
                "error": str(e),
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"


@router.post("/generate-stream")
async def generate_script_stream(
    request: StoryboardRequest,
    db: Session = Depends(get_db),  # noqa: ARG001
):
    """SSE 스트리밍 엔드포인트 — 노드별 진행률을 실시간 전송한다."""
    logger.info("📝 [Script Generate Stream] %s", request.model_dump())
    state = _request_to_state(request)
    thread_id = _resolve_thread_id()
    config = _build_config(thread_id)
    return StreamingResponse(
        _stream_graph_events(state, config, thread_id, "Stream"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/resume")
async def resume_script(request: ScriptResumeRequest):
    """Human Gate 재개 — thread_id로 interrupt된 그래프를 재개한다."""
    logger.info("📝 [Script Resume] thread=%s, action=%s", request.thread_id, request.action)
    config = _build_config(request.thread_id)
    resume_value = {"action": request.action, "feedback": request.feedback}
    return StreamingResponse(
        _stream_graph_events(Command(resume=resume_value), config, request.thread_id, "Resume"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/presets", response_model=ScriptPresetsResponse)
async def get_script_presets():
    """사용 가능한 Preset 목록을 반환한다."""
    items = [
        ScriptPresetItem(
            id=p["id"],
            name=p["name"],
            name_ko=p["name_ko"],
            description=p["description"],
            mode=p["mode"],
            auto_approve=p.get("auto_approve", False),
        )
        for p in LANGGRAPH_PRESETS.values()
    ]
    return ScriptPresetsResponse(presets=items)


@router.post("/feedback", response_model=ScriptFeedbackResponse)
async def submit_script_feedback(request: ScriptFeedbackRequest):
    """스크립트 생성 피드백을 수집하여 Memory Store에 저장한다."""
    from datetime import UTC, datetime

    from services.agent.store import get_store

    store = await get_store()

    # 1) 피드백 저장
    fb_ns = ("feedback", request.thread_id)
    fb_key = str(uuid.uuid4())
    await store.aput(
        fb_ns,
        fb_key,
        {
            "rating": request.rating,
            "feedback_text": request.feedback_text,
            "storyboard_id": request.storyboard_id,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )

    # 2) user preferences 업데이트 (긍정 비율 재계산)
    await _update_user_preferences(store, request.rating)

    logger.info("[Feedback] %s 피드백 저장: thread=%s", request.rating, request.thread_id)
    return ScriptFeedbackResponse(success=True, message="피드백이 저장되었습니다")


async def _update_user_preferences(store: BaseStore, rating: str) -> None:
    """user preferences의 피드백 카운트를 갱신한다."""
    user_ns = ("user", "preferences")
    existing = await store.asearch(user_ns)
    is_positive = 1 if rating == "positive" else 0

    if existing:
        prefs = existing[0].value
        total = prefs.get("total_feedback", 0) + 1
        positive = prefs.get("positive_count", 0) + is_positive
        prefs["total_feedback"] = total
        prefs["positive_count"] = positive
        prefs["positive_ratio"] = round(positive / total, 2) if total > 0 else 0
        await store.aput(user_ns, existing[0].key, prefs)
    else:
        await store.aput(
            user_ns,
            str(uuid.uuid4()),
            {
                "total_generations": 0,
                "total_feedback": 1,
                "positive_count": is_positive,
                "positive_ratio": float(is_positive),
                "feedback_themes": [],
            },
        )
