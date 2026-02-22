"""Script generation endpoints."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import logger
from config_pipelines import (
    LANGGRAPH_DEFAULT_SKIP_STAGES,
    LANGGRAPH_PRESETS,
    VALID_SKIP_STAGES,
)
from database import get_db
from schemas import (
    FeedbackPresetOption,
    FeedbackPresetsResponse,
    ScriptFeedbackRequest,
    ScriptFeedbackResponse,
    ScriptGenerateResponse,
    ScriptPresetItem,
    ScriptPresetsResponse,
    ScriptResumeRequest,
    StoryboardRequest,
)
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
    "critic": {"label": "컨셉 토론", "percent": 15},
    "concept_gate": {"label": "컨셉 선택", "percent": 20},
    "writer": {"label": "대본 생성", "percent": 40},
    "review": {"label": "구조 검증", "percent": 55},
    "revise": {"label": "수정 중", "percent": 58},
    "cinematographer": {"label": "비주얼 디자인", "percent": 60},
    "tts_designer": {"label": "음성 디자인", "percent": 75},
    "sound_designer": {"label": "BGM 설계", "percent": 75},
    "copyright_reviewer": {"label": "저작권 검토", "percent": 75},
    "director": {"label": "통합 검증", "percent": 90},
    "human_gate": {"label": "승인 대기", "percent": 93},
    "finalize": {"label": "최종화", "percent": 95},
    "explain": {"label": "결정 설명", "percent": 98},
    "learn": {"label": "완료", "percent": 100},
}


def _resolve_skip_stages(request: StoryboardRequest, preset_data: dict) -> list[str]:
    """skip_stages 해석 우선순위: (1) 명시적 request.skip_stages > (2) preset > (3) 기본값."""
    # 1) 명시적 skip_stages
    if request.skip_stages is not None:
        return [s for s in request.skip_stages if s in VALID_SKIP_STAGES]

    # 2) preset의 skip_stages
    if preset_data and "skip_stages" in preset_data:
        return list(preset_data["skip_stages"])

    # 3) 기본값 (Express 동작)
    return list(LANGGRAPH_DEFAULT_SKIP_STAGES)


def _request_to_state(request: StoryboardRequest) -> ScriptState:
    """StoryboardRequest → ScriptState 변환."""
    preset_data = LANGGRAPH_PRESETS.get(request.preset or "") or {}
    skip_stages = _resolve_skip_stages(request, preset_data)

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
        references=request.references,
        preset=request.preset,
        auto_approve=preset_data.get("auto_approve", True),
        skip_stages=skip_stages,
        revision_count=0,
    )


def _resolve_thread_id() -> str:
    """매 요청마다 새 UUID 기반 thread_id를 생성한다."""
    return f"script-{uuid.uuid4().hex[:12]}"


def _build_config(thread_id: str, *, trace_id: str | None = None) -> dict:
    """LangGraph config를 구성한다. 요청별 LangFuse 핸들러를 생성하여 주입.

    trace_id가 주어지면 (resume) 기존 trace에 이어서 기록한다.
    """
    from services.agent.observability import create_langfuse_handler  # noqa: PLC0415

    cfg: dict = {"configurable": {"thread_id": thread_id}}
    handler = create_langfuse_handler(trace_id=trace_id, session_id=thread_id)
    if handler is not None:
        cfg["callbacks"] = [handler]
        cfg["metadata"] = {"langfuse_session_id": thread_id}
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


# AI Transparency: 노드별 reasoning 데이터 추출 매핑
_NODE_RESULT_KEYS: dict[str, str | list[str]] = {
    "critic": ["critic_result", "debate_log"],  # Phase 10-C-3: 토론 로그 추가
    "concept_gate": ["critic_result"],  # 사용자 선택 반영된 critic_result
    "review": "review_result",
    "cinematographer": ["cinematographer_result", "cinematographer_tool_logs"],
    "tts_designer": "tts_designer_result",
    "sound_designer": "sound_designer_result",
    "copyright_reviewer": "copyright_reviewer_result",
    "director": ["director_decision", "director_feedback", "agent_messages"],  # Phase 10-C-2: 양방향 메시지
    "explain": "explanation_result",
}


def _extract_node_result(node_name: str, node_output: dict) -> dict | None:
    """노드 출력에서 reasoning 데이터를 추출한다."""
    keys = _NODE_RESULT_KEYS.get(node_name)
    if keys is None:
        return None
    if isinstance(keys, list):
        prefix = f"{node_name}_"
        result = {k.removeprefix(prefix): node_output.get(k) for k in keys}
        return result if any(result.values()) else None
    return node_output.get(keys) or None


def _build_node_payload(
    node_name: str,
    thread_id: str,
    node_output: dict,
    char_ids: list[int | None],
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

    if node_name == "writer":
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
                "sound_recommendation": node_output.get("sound_recommendation"),
            }

    # AI Transparency: 특정 노드의 reasoning 데이터를 node_result로 전달
    nr = _extract_node_result(node_name, node_output)
    if nr is not None:
        payload["node_result"] = nr

    if node_output.get("error"):
        payload["status"] = "error"
        payload["error"] = node_output["error"]

    return payload


def _extract_quality_gate(vals: dict) -> dict | None:
    """review_result + director_checkpoint에서 품질 게이트 메트릭을 추출한다."""
    review = vals.get("review_result")
    has_checkpoint = vals.get("director_checkpoint_decision") is not None
    if not review and not has_checkpoint:
        return None
    gate: dict = {}
    if review:
        gate["review_passed"] = review.get("passed")
        gate["review_summary"] = review.get("user_summary", "")
        if ns := review.get("narrative_score"):
            gate["narrative_score"] = ns
    if has_checkpoint:
        gate["checkpoint_score"] = vals.get("director_checkpoint_score")
        gate["checkpoint_decision"] = vals.get("director_checkpoint_decision")
    if rs := vals.get("research_score"):
        gate["research_score"] = rs
    return gate


def _build_production_snapshot(vals: dict) -> dict:
    """Graph state에서 Production 스냅샷을 추출한다."""
    snapshot: dict = {}
    if plan := vals.get("director_plan"):
        snapshot["director_plan"] = plan
    if cinema := vals.get("cinematographer_result"):
        snapshot["cinematographer"] = cinema
    if tts := vals.get("tts_designer_result"):
        snapshot["tts_designer"] = tts
    if sound := vals.get("sound_designer_result"):
        snapshot["sound_designer"] = sound
    if cr := vals.get("copyright_reviewer_result"):
        snapshot["copyright_reviewer"] = cr
    if vals.get("director_decision"):
        snapshot["director"] = {
            "decision": vals.get("director_decision"),
            "feedback": vals.get("director_feedback"),
            "reasoning_steps": vals.get("director_reasoning_steps"),
        }
    if msgs := vals.get("agent_messages"):
        snapshot["agent_messages"] = msgs
    if qg := _extract_quality_gate(vals):
        snapshot["quality_gate"] = qg
    if rh := vals.get("revision_history"):
        snapshot["revision_history"] = rh
    if dl := vals.get("debate_log"):
        snapshot["debate_log"] = dl
    return snapshot


async def _read_interrupt_state(graph, config: dict) -> tuple[str, dict]:  # noqa: ANN001
    """GraphInterrupt 후 checkpoint에서 interrupt 노드와 데이터를 읽는다."""
    try:
        snapshot = await graph.aget_state(config)
        vals = snapshot.values or {}
        pending = snapshot.next or ()
        interrupt_node = pending[0] if pending else "unknown"

        result: dict = {}
        if interrupt_node == "concept_gate":
            critic_result = vals.get("critic_result", {})
            result = {
                "type": "concept_selection",
                "candidates": critic_result.get("candidates", []),
                "selected_concept": critic_result.get("selected_concept"),
                "evaluation": critic_result.get("evaluation"),
            }
        else:  # human_gate or others
            for key, out_key in [
                ("draft_scenes", "scenes"),
                ("review_result", "review_result"),
                ("scene_reasoning", "scene_reasoning"),
            ]:
                if vals.get(key):
                    result[out_key] = vals[key]
            ps = _build_production_snapshot(vals)
            if ps:
                result["production_snapshot"] = ps

        return interrupt_node, result
    except Exception:
        logger.warning("[SSE] Failed to read checkpoint for interrupt")
        return "unknown", {}


async def _preflight_safety_check(topic: str, description: str) -> str | None:
    """주제의 안전성을 사전 검증한다. 차단 시 에러 메시지, 통과 시 None."""
    from google.genai import types  # noqa: PLC0415

    from config import GEMINI_TEXT_MODEL, gemini_client  # noqa: PLC0415

    if not gemini_client:
        return None

    prompt = f"이 주제를 한 문장으로 요약하세요: {topic}"
    if description:
        prompt += f"\n설명: {description[:200]}"

    safety = [
        types.SafetySetting(category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE)
        for c in [
            types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
        ]
    ]
    cfg = types.GenerateContentConfig(safety_settings=safety, max_output_tokens=10)
    try:
        res = await gemini_client.aio.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=cfg,
        )
        if res.prompt_feedback and res.prompt_feedback.block_reason:
            return str(res.prompt_feedback.block_reason)
        if not res.text and res.candidates and res.candidates[0].finish_reason:
            reason = str(res.candidates[0].finish_reason)
            if "SAFETY" in reason.upper() or "PROHIBITED" in reason.upper():
                return reason
    except Exception:
        pass  # preflight 실패는 무시 — 본 파이프라인에서 재감지
    return None


async def _stream_graph_events(
    graph_input: object,
    config: dict,
    thread_id: str,
    label: str,
) -> AsyncGenerator[str]:
    """Graph를 스트리밍하며 SSE 이벤트를 yield한다."""
    from services.agent.observability import update_trace_on_interrupt  # noqa: PLC0415

    graph = await get_compiled_graph()
    char_ids: list[int | None] = [None, None]

    # Safety preflight — 초기 생성 요청(topic 포함 dict)일 때만 실행
    if isinstance(graph_input, dict) and graph_input.get("topic"):
        blocked = await _preflight_safety_check(
            graph_input["topic"],
            graph_input.get("description", ""),
        )
        if blocked:
            payload = {
                "node": "preflight",
                "label": "안전 검사",
                "percent": 0,
                "status": "error",
                "error": "이 주제는 Gemini 안전 정책에 의해 차단되었습니다 — 다른 주제로 시도해주세요",
                "thread_id": thread_id,
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            return

    interrupted = False
    try:
        async for event in graph.astream(graph_input, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                if not isinstance(node_output, dict):
                    continue
                payload = _build_node_payload(node_name, thread_id, node_output, char_ids)
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    except Exception as e:
        if _is_graph_interrupt(e):
            interrupted = True
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

    # astream은 interrupt 시 예외 없이 스트림만 종료할 수 있음 — 상태로 감지
    if not interrupted:
        try:
            snapshot = await graph.aget_state(config)
            if snapshot.next:
                interrupted = True
        except Exception:
            pass

    if interrupted:
        interrupt_node, result = await _read_interrupt_state(graph, config)
        meta = _NODE_META.get(interrupt_node, {"label": "대기", "percent": 50})
        payload_interrupt: dict = {
            "node": interrupt_node,
            "label": meta["label"],
            "percent": meta["percent"],
            "status": "waiting_for_input",
            "thread_id": thread_id,
        }
        # config의 요청별 handler에서 trace_id 추출 (v3: trace_context dict)
        handler_trace_id = None
        callbacks = config.get("callbacks", [])
        if callbacks:
            ctx = getattr(callbacks[0], "trace_context", None)
            handler_trace_id = ctx.get("trace_id") if ctx else None
            if handler_trace_id:
                payload_interrupt["trace_id"] = handler_trace_id
        if result:
            payload_interrupt["result"] = result

        update_trace_on_interrupt(
            result or {"status": "waiting_for_input"},
            trace_id=handler_trace_id,
        )

        yield f"data: {json.dumps(payload_interrupt, ensure_ascii=False)}\n\n"


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


@router.post("/resume")
async def resume_script(request: ScriptResumeRequest):
    """Human Gate / Concept Gate 재개 — thread_id로 interrupt된 그래프를 재개한다."""
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
    """사용 가능한 Preset 목록을 반환한다 (레거시 프리셋 제외)."""
    items = [
        ScriptPresetItem(
            id=p["id"],
            name=p["name"],
            name_ko=p["name_ko"],
            description=p["description"],
            auto_approve=p.get("auto_approve", False),
            skip_stages=p.get("skip_stages", []),
        )
        for p in LANGGRAPH_PRESETS.values()
    ]
    return ScriptPresetsResponse(presets=items)


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
