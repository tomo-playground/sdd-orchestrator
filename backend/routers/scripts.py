"""Script generation endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import logger
from config_pipelines import VALID_SKIP_STAGES
from database import get_db
from routers._scripts_sse import stream_graph_events
from schemas import (
    FeedbackPresetOption,
    FeedbackPresetsResponse,
    ScriptEditRequest,
    ScriptEditResponse,
    ScriptFeedbackRequest,
    ScriptFeedbackResponse,
    ScriptGenerateResponse,
    ScriptPresetsResponse,
    ScriptResumeRequest,
    StoryboardRequest,
    TopicAnalyzeRequest,
    TopicAnalyzeResponse,
)
from services.agent.script_graph import get_compiled_graph
from services.agent.state import ScriptState

# LangGraph Command (런타임에서만 사용)
try:
    from langgraph.types import Command
except ImportError:
    Command = None  # type: ignore[assignment, misc]

router = APIRouter(prefix="/scripts", tags=["scripts"])


def _resolve_skip_stages(request: StoryboardRequest) -> list[str]:
    """skip_stages 해석: 명시적 지정만 허용, 미지정 시 빈 리스트 (Director가 채움)."""
    if request.skip_stages is not None:
        return [s for s in request.skip_stages if s in VALID_SKIP_STAGES]
    return []


def _request_to_state(request: StoryboardRequest) -> ScriptState:
    """StoryboardRequest → ScriptState 변환."""
    mode = request.interaction_mode or "guided"
    return ScriptState(
        topic=request.topic,
        description=request.description or "",
        duration=request.duration,
        style=request.style,
        language=request.language,
        structure="",  # Director 캐스팅 SSOT
        actor_a_gender=request.actor_a_gender,
        character_id=None,
        character_b_id=None,
        group_id=request.group_id,
        references=request.references,
        chat_context=request.chat_context,
        preset=request.preset,
        auto_approve=(mode == "auto"),
        interaction_mode=mode,
        skip_stages=_resolve_skip_stages(request),
        revision_count=0,
    )


def _resolve_thread_id() -> str:
    """매 요청마다 새 UUID 기반 thread_id를 생성한다."""
    return f"script-{uuid.uuid4().hex[:12]}"


def _build_config(thread_id: str, *, trace_id: str | None = None) -> dict:
    """LangGraph config를 구성한다. 요청별 LangFuse 핸들러를 생성하여 주입.

    trace_id가 주어지면 (resume) 기존 trace에 이어서 기록한다.
    """
    from config_pipelines import LANGGRAPH_RECURSION_LIMIT  # noqa: PLC0415
    from services.agent.observability import create_langfuse_handler, end_root_span  # noqa: PLC0415

    # Phase 25: review-revise + checkpoint 루프 중첩으로 기본 limit(25) 초과 가능
    cfg: dict = {"configurable": {"thread_id": thread_id}, "recursion_limit": LANGGRAPH_RECURSION_LIMIT}
    handler = create_langfuse_handler(trace_id=trace_id, session_id=thread_id)
    if handler is not None:
        cfg["callbacks"] = [handler]
        cfg["metadata"] = {"langfuse_session_id": thread_id}
        # 파이프라인 완료 후 root span 종료를 위한 cleanup 함수 참조
        cfg["_langfuse_cleanup"] = end_root_span
    return cfg


def _state_to_response(result: dict) -> dict:
    """Graph 결과 → API 응답 dict 변환."""
    resp = {
        "scenes": result.get("final_scenes") or [],
        "character_id": result.get("draft_character_id"),
        "character_b_id": result.get("draft_character_b_id"),
        "sound_recommendation": result.get("sound_recommendation"),
    }
    if result.get("explanation_result"):
        resp["explanation"] = result["explanation_result"]
    return resp


@router.post("/analyze-topic", response_model=TopicAnalyzeResponse)
async def analyze_topic_endpoint(request: TopicAnalyzeRequest):
    """토픽을 분석하여 최적의 영상 설정(duration, language, structure, character)을 추천한다."""
    from services.scripts.topic_analysis import analyze_topic  # noqa: PLC0415

    messages = [m.model_dump() for m in request.messages] if request.messages else None
    return await analyze_topic(request.topic, request.description, request.group_id, messages)


@router.post("/generate", response_model=ScriptGenerateResponse)
async def generate_script_endpoint(
    request: StoryboardRequest,
    db: Session = Depends(get_db),  # noqa: ARG001
):
    """동기 엔드포인트 — 내부적으로 Graph를 경유한다."""
    logger.info("📝 [Script Generate] %s", request.model_dump())
    async with get_compiled_graph() as graph:
        state = _request_to_state(request)
        config = _build_config(_resolve_thread_id())
        try:
            result = await graph.ainvoke(state, config)
            if result.get("error"):
                raise HTTPException(status_code=500, detail=result["error"])
            return _state_to_response(result)
        finally:
            cleanup = config.get("_langfuse_cleanup")
            if cleanup:
                cleanup()


def _resolve_feedback_preset(preset_id: str, params: dict[str, str] | None) -> str:
    """피드백 프리셋 ID → 피드백 텍스트로 변환. 파라미터가 있으면 치환."""
    from config_pipelines import FEEDBACK_PRESETS  # noqa: PLC0415

    preset = FEEDBACK_PRESETS.get(preset_id)
    if not preset:
        return ""
    feedback = preset["feedback"]
    if params:
        for key, value in params.items():
            feedback = feedback.replace(f"{{{key}}}", value)
    return feedback


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post(
    "/generate-stream",
    responses={
        200: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "SSE stream of ScriptProgressEvent JSON objects",
        },
    },
)
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
        stream_graph_events(state, config, thread_id, "Stream"),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post(
    "/resume",
    responses={
        200: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "SSE stream of ScriptProgressEvent JSON objects",
        },
    },
)
async def resume_script(request: ScriptResumeRequest):
    """Human Gate / Concept Gate 재개 — thread_id로 interrupt된 그래프를 SSE로 재개한다."""
    logger.info("📝 [Script Resume] thread=%s, action=%s", request.thread_id, request.action)
    config = _build_config(request.thread_id, trace_id=request.trace_id)

    # 피드백 프리셋 해석
    feedback = request.feedback
    if request.feedback_preset:
        feedback = _resolve_feedback_preset(request.feedback_preset, request.feedback_preset_params)

    resume_value: dict = {"action": request.action, "feedback": feedback}
    if request.concept_id is not None:
        resume_value["concept_id"] = request.concept_id
    if request.custom_concept is not None:
        resume_value["custom_concept"] = request.custom_concept
    return StreamingResponse(
        stream_graph_events(Command(resume=resume_value), config, request.thread_id, "Resume"),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get("/presets", response_model=ScriptPresetsResponse)
async def get_script_presets():
    """Preset 목록 — deprecated (Director 자율 실행으로 대체). 빈 리스트 반환."""
    return ScriptPresetsResponse(presets=[])


@router.get("/feedback-presets", response_model=FeedbackPresetsResponse)
async def get_feedback_presets():
    """사용 가능한 피드백 프리셋 목록을 반환한다."""
    from config_pipelines import FEEDBACK_PRESETS  # noqa: PLC0415

    items = [FeedbackPresetOption(**p) for p in FEEDBACK_PRESETS.values()]
    return FeedbackPresetsResponse(presets=items)


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
    from services.agent.feedback import update_user_preferences  # noqa: PLC0415

    await update_user_preferences(store, request.rating)

    logger.info("[Feedback] %s 피드백 저장: thread=%s", request.rating, request.thread_id)
    return ScriptFeedbackResponse(success=True, message="피드백이 저장되었습니다")


@router.post("/edit-scenes", response_model=ScriptEditResponse)
async def edit_scenes_endpoint(request: ScriptEditRequest):
    """Gemini를 사용하여 씬들을 자연어 지시에 따라 일괄 편집한다."""
    from services.scripts.scene_editor import edit_scenes  # noqa: PLC0415

    scenes_data = [s.model_dump() for s in request.scenes]
    context_data = request.context.model_dump()
    return await edit_scenes(request.instruction, scenes_data, context_data)
