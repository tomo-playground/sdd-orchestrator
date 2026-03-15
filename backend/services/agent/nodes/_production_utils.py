"""Production 노드 공통 유틸리티 — Gemini 호출 + JSON 파싱 + QC 검증 + 재시도."""

from __future__ import annotations

from collections.abc import Callable

from google.genai import types

from config import GEMINI_FALLBACK_MODEL, GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from config_pipelines import CREATIVE_PIPELINE_MAX_RETRIES
from services.agent.observability import trace_llm_call
from services.creative_utils import parse_json_response


async def run_production_step(
    template_name: str,
    template_vars: dict,
    validate_fn: Callable[[list | dict], dict],
    extract_key: str,
    step_name: str,
    model: str | None = None,
    system_instruction: str | None = None,
) -> dict:
    """Production step: 템플릿 렌더 → Gemini → JSON 파싱 → QC → 재시도.

    Args:
        model: Gemini 모델 ID. None이면 GEMINI_TEXT_MODEL(Flash) 사용.

    Returns: 전체 파싱된 JSON dict (예: {"scenes": [...], ...}).
    Raises: ValueError if max retries exceeded and QC still fails.
    """
    if not gemini_client:
        raise RuntimeError(f"[{step_name}] Gemini 클라이언트가 설정되지 않음")

    resolved_model = model or GEMINI_TEXT_MODEL
    tmpl = template_env.get_template(template_name)
    retry_vars = dict(template_vars)
    config = types.GenerateContentConfig(
        safety_settings=GEMINI_SAFETY_SETTINGS,
        system_instruction=system_instruction,
    )

    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        prompt = tmpl.render(**retry_vars)
        used_fallback = False
        try:
            async with trace_llm_call(name=step_name, input_text=prompt, model=resolved_model) as llm:
                response = await gemini_client.aio.models.generate_content(
                    model=resolved_model,
                    contents=prompt,
                    config=config,
                )
                llm.record(response)
            raw_text = response.text or ""
            if not raw_text:
                # 안전 필터 등으로 빈 응답 — prompt_feedback 확인
                feedback_info = getattr(response, "prompt_feedback", None)
                block_reason = getattr(feedback_info, "block_reason", None) if feedback_info else None
                if feedback_info:
                    logger.warning("[%s] Empty response, prompt_feedback: %s", step_name, feedback_info)
                if block_reason and "PROHIBITED" in getattr(block_reason, "name", str(block_reason)).upper():
                    # PROHIBITED_CONTENT → 폴백 모델로 1회 재시도
                    logger.warning("[%s][Fallback] PROHIBITED_CONTENT → %s", step_name, GEMINI_FALLBACK_MODEL)
                    async with trace_llm_call(
                        name=f"{step_name}_fallback", input_text=prompt, model=GEMINI_FALLBACK_MODEL
                    ) as llm_fb:
                        response = await gemini_client.aio.models.generate_content(
                            model=GEMINI_FALLBACK_MODEL,
                            contents=prompt,
                            config=config,
                        )
                        llm_fb.record(response)
                    raw_text = response.text or ""
                    used_fallback = True
                    if not raw_text:
                        raise ValueError(f"Safety filter blocked (fallback also failed): {block_reason}")
                elif block_reason:
                    raise ValueError(f"Safety filter blocked: {block_reason}")
                else:
                    raise ValueError("Empty LLM response received")
            parsed = parse_json_response(raw_text)
        except Exception as e:
            # 폴백 성공 후 파싱 실패 → 재시도 무의미, 즉시 raise
            if used_fallback:
                logger.error("[%s] Fallback 응답 파싱 실패 (재시도 불가): %s", step_name, e)
                raise
            logger.warning("[%s] 호출/파싱 실패 (retry %d): %s", step_name, retry, e)
            if retry < CREATIVE_PIPELINE_MAX_RETRIES:
                retry_vars = {**template_vars, "feedback": f"JSON Error: {e}. Valid JSON only."}
                continue
            raise

        # extract_key가 빈 문자열이면 전체 dict 검증 (Phase 10-A Director ReAct)
        extracted = parsed if extract_key == "" else parsed.get(extract_key, [])
        qc = validate_fn(extracted)
        if qc["ok"]:
            logger.info("[%s] QC 통과 (retry %d)", step_name, retry)
            return parsed

        if retry < CREATIVE_PIPELINE_MAX_RETRIES:
            feedback = "\n".join(f"- {issue}" for issue in qc["issues"])
            retry_vars = {**template_vars, "feedback": feedback}
            logger.info("[%s] QC 실패, 재시도 %d: %s", step_name, retry, qc["issues"])
        else:
            logger.warning("[%s] 최대 재시도 도달, 마지막 결과 사용", step_name)
            return parsed

    return {}  # unreachable
