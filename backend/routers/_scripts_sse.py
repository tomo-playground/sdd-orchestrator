"""Script SSE 스트리밍 헬퍼 — scripts.py에서 분리."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from config import logger
from services.agent.script_graph import get_compiled_graph

# -- 노드별 SSE 메타데이터 --
NODE_META: dict[str, dict] = {
    "director_plan": {"label": "디렉터 계획", "percent": 3},
    "director_plan_gate": {"label": "플랜 검토", "percent": 4},
    "inventory_resolve": {"label": "캐스팅", "percent": 5},
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

# AI Transparency: 노드별 reasoning 데이터 추출 매핑
_NODE_RESULT_KEYS: dict[str, str | list[str]] = {
    "director_plan": ["director_plan", "skip_stages"],
    "inventory_resolve": "casting_recommendation",
    "research": ["research_brief", "research_score"],
    "critic": ["critic_result", "debate_log"],
    "concept_gate": ["critic_result"],
    "review": "review_result",
    "revise": "draft_scenes",
    "cinematographer": ["cinematographer_result", "cinematographer_tool_logs"],
    "tts_designer": "tts_designer_result",
    "sound_designer": "sound_designer_result",
    "copyright_reviewer": "copyright_reviewer_result",
    "director": ["director_decision", "director_feedback", "agent_messages"],
    "explain": "explanation_result",
}


def _is_graph_interrupt(exc: Exception) -> bool:
    """GraphInterrupt 여부를 안전하게 확인한다."""
    return type(exc).__name__ == "GraphInterrupt"


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


def build_node_payload(
    node_name: str,
    thread_id: str,
    node_output: dict,
    char_ids: list[int | None],
) -> dict:
    """노드 이벤트를 SSE payload dict로 변환한다."""
    meta = NODE_META.get(node_name, {"label": node_name, "percent": 50})
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
        snapshot["cinematographer"] = {
            "result": cinema,
            "tool_logs": vals.get("cinematographer_tool_logs") or [],
        }
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


async def read_interrupt_state(graph, config: dict) -> tuple[str, dict]:  # noqa: ANN001
    """GraphInterrupt 후 checkpoint에서 interrupt 노드와 데이터를 읽는다."""
    try:
        snapshot = await graph.aget_state(config)
        vals = snapshot.values or {}
        pending = snapshot.next or ()
        interrupt_node = pending[0] if pending else "unknown"

        result: dict = {}
        if interrupt_node == "director_plan_gate":
            director_plan = vals.get("director_plan", {})
            skip_stages = vals.get("skip_stages", [])
            result = {
                "type": "plan_review",
                "director_plan": director_plan,
                "skip_stages": skip_stages,
                "casting_recommendation": vals.get("casting_recommendation"),
            }
        elif interrupt_node == "concept_gate":
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
                if vals.get(key) is not None:
                    result[out_key] = vals[key]
            ps = _build_production_snapshot(vals)
            if ps:
                result["production_snapshot"] = ps

        return interrupt_node, result
    except Exception:
        logger.debug("[SSE] Failed to read checkpoint for interrupt")
        return "unknown", {}


async def preflight_safety_check(topic: str, description: str) -> str | None:
    """주제의 안전성을 사전 검증한다. 차단 시 에러 메시지, 통과 시 None."""
    from google.genai import types  # noqa: PLC0415

    from config import GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client  # noqa: PLC0415

    if not gemini_client:
        return None

    prompt = f"이 주제를 한 문장으로 요약하세요: {topic}"
    if description:
        prompt += f"\n설명: {description[:200]}"

    cfg = types.GenerateContentConfig(safety_settings=GEMINI_SAFETY_SETTINGS, max_output_tokens=10)
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


async def stream_graph_events(
    graph_input: object,
    config: dict,
    thread_id: str,
    label: str,
) -> AsyncGenerator[str]:
    """Graph를 스트리밍하며 SSE 이벤트를 yield한다."""
    from services.agent.observability import (  # noqa: PLC0415, E501
        _patch_trace,
        end_root_span,
        update_root_span,
        update_trace_on_completion,
        update_trace_on_interrupt,
    )

    # Safety preflight — 초기 생성 요청(topic 포함 dict)일 때만 실행
    if isinstance(graph_input, dict) and graph_input.get("topic"):
        blocked = await preflight_safety_check(
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
            end_root_span()
            return

    if isinstance(graph_input, dict):
        update_root_span(input_data=graph_input)
    # Resume 케이스: trace input은 덮어쓰지 않는다.
    # 원본 storyboard 요청이 trace input으로 보존돼야 Langfuse에서 올바르게 표시된다.

    async with get_compiled_graph() as graph:
        char_ids: list[int | None] = [None, None]
        interrupted = False
        errored = False
        final_output: dict | None = None
        try:
            async for event in graph.astream(graph_input, config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue
                    payload = build_node_payload(node_name, thread_id, node_output, char_ids)
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    if node_name == "finalize" and node_output.get("final_scenes") is not None:
                        final_output = {
                            "scenes": node_output["final_scenes"],
                            "character_id": char_ids[0],
                            "character_b_id": char_ids[1],
                            "sound_recommendation": node_output.get("sound_recommendation"),
                        }

        except Exception as e:
            if _is_graph_interrupt(e):
                interrupted = True
            else:
                errored = True
                logger.exception("[SSE] %s error: %s", label, e)
                error_payload = {
                    "node": "error",
                    "label": "오류",
                    "percent": 0,
                    "status": "error",
                    "error": "스토리보드 생성 중 오류가 발생했습니다",
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

        # config의 요청별 handler에서 trace_id 추출 (v3: trace_context dict)
        handler_trace_id = None
        callbacks = config.get("callbacks", [])
        if callbacks:
            ctx = getattr(callbacks[0], "trace_context", None)
            handler_trace_id = ctx.get("trace_id") if ctx else None

        if interrupted:
            interrupt_node, result = await read_interrupt_state(graph, config)
            meta = NODE_META.get(interrupt_node, {"label": "대기", "percent": 50})
            payload_interrupt: dict = {
                "node": interrupt_node,
                "label": meta["label"],
                "percent": meta["percent"],
                "status": "waiting_for_input",
                "thread_id": thread_id,
            }
            if handler_trace_id:
                payload_interrupt["trace_id"] = handler_trace_id
            if result:
                payload_interrupt["result"] = result

            update_trace_on_interrupt(
                result or {"status": "waiting_for_input"},
                trace_id=handler_trace_id,
                interrupt_node=interrupt_node,
            )

            yield f"data: {json.dumps(payload_interrupt, ensure_ascii=False)}\n\n"
        elif errored:
            # 에러 시 trace에 error 상태를 명시적으로 기록 (LangFuse 대시보드 필터링용)
            _patch_trace(
                trace_id=handler_trace_id,
                body={"metadata": {"interrupted": False, "completed": False, "errored": True}},
                label="error",
            )
        else:
            # 정상 완료 시 interrupted: True stale 메타데이터를 리셋하고 최종 결과를 output에 기록
            update_trace_on_completion(trace_id=handler_trace_id, output_data=final_output)

        # 스트리밍 완료 시 root span 종료 (LangFuse 트레이스 그룹핑)
        end_root_span()
