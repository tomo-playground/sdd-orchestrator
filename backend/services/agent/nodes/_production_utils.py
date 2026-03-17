"""Production 노드 공통 유틸리티 — LLM 호출 + JSON 파싱 + QC 검증 + 재시도."""

from __future__ import annotations

from collections.abc import Callable

from config import logger
from config_pipelines import CREATIVE_PIPELINE_MAX_RETRIES
from services.agent.langfuse_prompt import compile_prompt, get_prompt_template
from services.creative_utils import parse_json_response
from services.llm import LLMConfig, get_llm_provider

# Jinja2 → LangFuse 네이티브 전환 완료된 템플릿 목록
# compile_prompt() 경로를 사용한다 (Jinja2 렌더링 불필요).
_NATIVE_TEMPLATES: frozenset[str] = frozenset(
    {
        # C등급 (Sprint 0-1)
        "review_evaluate.j2",
        "creative/narrative_review.j2",
        "creative/devils_advocate.j2",
        "creative/edit_scenes.j2",
        "creative/material_analyst.j2",
        "validate_image_tags.j2",
        "creative/reference_analyst.j2",
        "creative/location_planner.j2",
        "creative/director_evaluate.j2",
        "creative/copyright_reviewer.j2",
        # B등급 (Sprint 2)
        "creative/explain.j2",
        "creative/tts_designer.j2",
        "creative/director.j2",
        "creative/director_checkpoint.j2",
        "creative/sound_designer.j2",
        "creative/director_plan.j2",
        "creative/scriptwriter.j2",
        "creative/writer_planning.j2",
        # A등급 (Sprint 3) — storyboard + tool + pipeline 잔여 10개
        "creative/analyze_topic.j2",
        "creative/concept_architect.j2",
        "creative/cinematographer.j2",
        "creative/review_reflection.j2",
        "creative/review_unified.j2",
        "creative/scene_expand.j2",
        "create_storyboard.j2",
        "create_storyboard_confession.j2",
        "create_storyboard_dialogue.j2",
        "create_storyboard_narrated.j2",
    }
)


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

    _NATIVE_TEMPLATES에 포함된 템플릿은 compile_prompt() 경로를 사용.
    그 외 템플릿은 기존 Jinja2 렌더링 경로 유지.

    Args:
        model: LLM 모델 ID. None이면 기본 모델(GEMINI_TEXT_MODEL) 사용.

    Returns: 전체 파싱된 JSON dict (예: {"scenes": [...], ...}).
    Raises: ValueError if max retries exceeded and QC still fails.
    """
    if template_name in _NATIVE_TEMPLATES:
        return await _run_native(
            template_name, template_vars, validate_fn,
            extract_key, step_name, model, system_instruction,
        )
    return await _run_jinja2(
        template_name, template_vars, validate_fn,
        extract_key, step_name, model, system_instruction,
    )


async def _run_native(
    template_name: str,
    template_vars: dict,
    validate_fn: Callable[[list | dict], dict],
    extract_key: str,
    step_name: str,
    model: str | None,
    system_instruction: str | None,
) -> dict:
    """네이티브 경로: compile_prompt() → LLM → QC → 재시도."""
    compiled = compile_prompt(template_name, **template_vars)
    resolved_sys = compiled.system or system_instruction or ""
    llm_config = LLMConfig(system_instruction=resolved_sys)
    _last_feedback = ""

    for retry in range(CREATIVE_PIPELINE_MAX_RETRIES + 1):
        if retry > 0:
            retry_vars = {**template_vars, "feedback": _last_feedback}
            compiled = compile_prompt(template_name, **retry_vars)
            resolved_sys = compiled.system or system_instruction or ""
            llm_config = LLMConfig(system_instruction=resolved_sys)

        try:
            llm_response = await get_llm_provider().generate(
                step_name=step_name,
                contents=compiled.user,
                config=llm_config,
                model=model,
                metadata={"template": template_name},
                langfuse_prompt=compiled.langfuse_prompt,
            )
            raw_text = llm_response.text
            if not raw_text:
                raise ValueError("Empty LLM response received")
            parsed = parse_json_response(raw_text)
        except Exception as e:
            logger.warning("[%s] 호출/파싱 실패 (retry %d): %s", step_name, retry, e)
            if retry < CREATIVE_PIPELINE_MAX_RETRIES:
                _last_feedback = f"JSON Error: {e}. Valid JSON only."
                continue
            raise

        extracted = parsed if extract_key == "" else parsed.get(extract_key, [])
        qc = validate_fn(extracted)
        if qc["ok"]:
            logger.info("[%s] QC 통과 (retry %d)", step_name, retry)
            return parsed

        if retry < CREATIVE_PIPELINE_MAX_RETRIES:
            _last_feedback = "\n".join(f"- {issue}" for issue in qc["issues"])
            logger.info("[%s] QC 실패, 재시도 %d: %s", step_name, retry, qc["issues"])
        else:
            logger.warning("[%s] 최대 재시도 도달, 마지막 결과 사용", step_name)
            return parsed

    return {}  # unreachable


async def _run_jinja2(
    template_name: str,
    template_vars: dict,
    validate_fn: Callable[[list | dict], dict],
    extract_key: str,
    step_name: str,
    model: str | None,
    system_instruction: str | None,
) -> dict:
    """기존 Jinja2 경로: get_prompt_template() → render → LLM → QC → 재시도."""
    bundle = get_prompt_template(template_name)
    retry_vars = dict(template_vars)
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
