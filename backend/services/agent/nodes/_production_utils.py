"""Production 노드 공통 유틸리티 — LLM 호출 + JSON 파싱 + QC 검증 + 재시도."""

from __future__ import annotations

from collections.abc import Callable

from config import pipeline_logger as logger
from config_pipelines import CREATIVE_PIPELINE_MAX_RETRIES, FLASH_THINKING_BUDGET
from services.agent.langfuse_prompt import compile_prompt
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
    thinking_budget: int | None = None,
) -> dict:
    """Production step: compile_prompt() → LLM → JSON 파싱 → QC → 재시도.

    Args:
        model: LLM 모델 ID. None이면 기본 모델(GEMINI_TEXT_MODEL) 사용.
        thinking_budget: Gemini thinking token 제한. None이면 FLASH_THINKING_BUDGET 사용.

    Returns: 전체 파싱된 JSON dict (예: {"scenes": [...], ...}).
        마지막 LLM 호출의 observation_id가 ``_observation_id`` 키에 포함된다.
    Raises: ValueError if max retries exceeded and QC still fails.
    """
    return await _run_native(
        template_name,
        template_vars,
        validate_fn,
        extract_key,
        step_name,
        model,
        system_instruction,
        thinking_budget,
    )


async def _run_native(
    template_name: str,
    template_vars: dict,
    validate_fn: Callable[[list | dict], dict],
    extract_key: str,
    step_name: str,
    model: str | None,
    system_instruction: str | None,
    thinking_budget: int | None = None,
) -> dict:
    """네이티브 경로: compile_prompt() → LLM → QC → 재시도."""
    # 로그용 짧은 이름: "generate_content sound_designer" → "sound_designer"
    log_name = step_name.split(" ", 1)[-1] if " " in step_name else step_name

    # thinking budget: 명시 지정 > FLASH_THINKING_BUDGET 기본값
    resolved_budget = thinking_budget if thinking_budget is not None else FLASH_THINKING_BUDGET

    compiled = compile_prompt(template_name, **template_vars)
    resolved_sys = compiled.system or system_instruction or ""
    llm_config = LLMConfig(system_instruction=resolved_sys, thinking_budget=resolved_budget)
    _last_feedback = ""
    _last_obs_id: str | None = None

    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        if retry > 0:
            retry_vars = {**template_vars, "feedback": _last_feedback}
            compiled = compile_prompt(template_name, **retry_vars)
            resolved_sys = compiled.system or system_instruction or ""
            llm_config = LLMConfig(system_instruction=resolved_sys, thinking_budget=resolved_budget)

        try:
            step_metadata: dict = {"template": template_name}
            if retry > 0:
                step_metadata["retry"] = True
                step_metadata["attempt"] = retry + 1
            llm_response = await get_llm_provider().generate(
                step_name=step_name,
                contents=compiled.user,
                config=llm_config,
                model=model,
                metadata=step_metadata,
                langfuse_prompt=compiled.langfuse_prompt,
            )
            raw_text = llm_response.text
            _last_obs_id = llm_response.observation_id
            if not raw_text:
                raise ValueError("Empty LLM response received")
            parsed = parse_json_response(raw_text)
        except Exception as e:
            logger.warning("[%s] 호출/파싱 실패 (retry %d): %s", log_name, retry, e)
            if retry < CREATIVE_PIPELINE_MAX_RETRIES:
                _last_feedback = f"JSON Error: {e}. Valid JSON only."
                continue
            raise

        extracted = parsed if extract_key == "" else parsed.get(extract_key, [])
        qc = validate_fn(extracted)
        if qc["ok"]:
            logger.info("[%s] QC 통과 (retry %d)", log_name, retry)
            parsed["_observation_id"] = _last_obs_id
            return parsed

        if retry < CREATIVE_PIPELINE_MAX_RETRIES:
            _last_feedback = "\n".join(f"- {issue}" for issue in qc["issues"])
            logger.info("[%s] QC 실패, 재시도 %d: %s", log_name, retry, qc["issues"])
        else:
            logger.warning("[%s] 최대 재시도 도달, 마지막 결과 사용", log_name)
            parsed["_observation_id"] = _last_obs_id
            return parsed

    return {}  # unreachable
