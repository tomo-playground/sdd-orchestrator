"""Production 노드 공통 유틸리티 — LLM 호출 + JSON 파싱 + QC 검증 + 재시도."""

from __future__ import annotations

from collections.abc import Callable

from config import logger
from config_pipelines import CREATIVE_PIPELINE_MAX_RETRIES
from services.agent.langfuse_prompt import get_prompt_template
from services.creative_utils import parse_json_response
from services.llm import LLMConfig, get_llm_provider


async def run_production_step(
    template_name: str,
    template_vars: dict,
    validate_fn: Callable[[list | dict], dict],
    extract_key: str,
    step_name: str,
    model: str | None = None,
    system_instruction: str | None = None,
) -> dict:
    """Production step: 템플릿 렌더 → LLM → JSON 파싱 → QC → 재시도.

    LangFuse Prompt Management가 활성화되면 LangFuse에서 프롬프트를 fetch하고,
    실패 시 로컬 Jinja2 파일로 fallback한다.

    Args:
        model: LLM 모델 ID. None이면 기본 모델(GEMINI_TEXT_MODEL) 사용.

    Returns: 전체 파싱된 JSON dict (예: {"scenes": [...], ...}).
    Raises: ValueError if max retries exceeded and QC still fails.
    """
    bundle = get_prompt_template(template_name)
    retry_vars = dict(template_vars)
    # LangFuse chat system 메시지 우선, 없으면 노드 하드코딩 사용
    resolved_sys = bundle.system_instruction if bundle.system_instruction is not None else system_instruction
    llm_config = LLMConfig(system_instruction=resolved_sys)

    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        prompt = bundle.template.render(**retry_vars)
        try:
            llm_response = await get_llm_provider().generate(
                step_name=step_name,
                contents=prompt,
                config=llm_config,
                model=model,
                metadata={"template": template_name},
                langfuse_prompt=bundle.langfuse_prompt,
            )
            raw_text = llm_response.text
            if not raw_text:
                raise ValueError("Empty LLM response received")
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
