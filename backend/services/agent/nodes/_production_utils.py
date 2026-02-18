"""Production 노드 공통 유틸리티 — Gemini 호출 + JSON 파싱 + QC 검증 + 재시도."""

from __future__ import annotations

from collections.abc import Callable

from config import GEMINI_TEXT_MODEL, gemini_client, logger, template_env
from config_pipelines import CREATIVE_PIPELINE_MAX_RETRIES
from services.agent.observability import trace_llm_call
from services.creative_utils import parse_json_response


async def run_production_step(
    template_name: str,
    template_vars: dict,
    validate_fn: Callable[[list | dict], dict],
    extract_key: str,
    step_name: str,
) -> dict:
    """Production step: 템플릿 렌더 → Gemini → JSON 파싱 → QC → 재시도.

    Returns: 전체 파싱된 JSON dict (예: {"scenes": [...], ...}).
    Raises: ValueError if max retries exceeded and QC still fails.
    """
    if not gemini_client:
        raise RuntimeError(f"[{step_name}] Gemini 클라이언트가 설정되지 않음")

    tmpl = template_env.get_template(template_name)
    retry_vars = dict(template_vars)

    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        prompt = tmpl.render(**retry_vars)
        try:
            async with trace_llm_call(name=step_name, input_text=prompt[:2000]) as llm:
                response = await gemini_client.aio.models.generate_content(
                    model=GEMINI_TEXT_MODEL,
                    contents=prompt,
                )
                llm.record(response)
            raw_text = response.text or ""
            parsed = parse_json_response(raw_text)
        except Exception as e:
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
