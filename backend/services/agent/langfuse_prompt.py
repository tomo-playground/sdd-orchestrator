"""LangFuse Prompt Management — chat 타입 fetch + Jinja2 렌더 + 파일 fallback.

include 없는 템플릿을 LangFuse chat 프롬프트로 관리한다.
- system 메시지: 역할/규칙 (LangFuse UI에서 편집 가능)
- user 메시지: Jinja2 템플릿 (데이터 조립)

LangFuse 비활성·오류 시 로컬 .j2 파일로 graceful degradation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jinja2 import BaseLoader, Environment

from config import logger, template_env

# LangFuse에서 fetch한 텍스트를 Jinja2로 렌더링하기 위한 환경
# FileSystemLoader 없이 from_string() 전용 (include 미지원)
_lf_jinja_env = Environment(loader=BaseLoader())

# LangFuse에서 runtime fetch하는 템플릿 ({% include %} 미사용)
# A등급(단순) + B등급(include 없는 복잡 로직) 통합
LANGFUSE_MANAGED_TEMPLATES: frozenset[str] = frozenset(
    {
        # --- A등급: 단순 변수 치환 + 경량 로직 ---
        "creative/analyze_topic.j2",
        "creative/concept_architect.j2",
        "creative/location_planner.j2",
        "creative/sound_designer.j2",
        "creative/material_analyst.j2",
        "creative/copyright_reviewer.j2",
        "creative/devils_advocate.j2",
        "creative/narrative_review.j2",
        "creative/reference_analyst.j2",
        "creative/scene_expand.j2",
        "creative/edit_scenes.j2",
        "creative/review_reflection.j2",
        "validate_image_tags.j2",
        "review_evaluate.j2",
        # --- B등급: include 없는 복잡 로직 (Phase 2) ---
        "creative/director.j2",
        "creative/scriptwriter.j2",
        "creative/director_plan.j2",
        "creative/writer_planning.j2",
        "creative/tts_designer.j2",
        "creative/director_checkpoint.j2",
        "creative/explain.j2",
        "creative/director_evaluate.j2",
        "creative/review_unified.j2",
        # --- include 제거 완료 (Phase 2 파셜→변수 전환) ---
        "creative/cinematographer.j2",
        "create_storyboard.j2",
        "create_storyboard_confession.j2",
        "create_storyboard_dialogue.j2",
        "create_storyboard_narrated.j2",
    }
)

# 하위 호환 별칭
A_GRADE_TEMPLATES = LANGFUSE_MANAGED_TEMPLATES


@dataclass
class PromptBundle:
    """LangFuse prompt fetch 결과.

    Attributes:
        template: render(**vars) 가능한 Jinja2 Template (user 메시지)
        system_instruction: LangFuse chat의 system 메시지. None이면 노드 하드코딩 사용.
        langfuse_prompt: LangFuse Prompt 객체 (trace 연결용). None이면 파일 fallback.
    """

    template: Any
    system_instruction: str | None = None
    langfuse_prompt: Any = None
    _source: str = field(default="file", repr=False)


def _to_langfuse_name(template_name: str) -> str:
    """템플릿 경로 → LangFuse 프롬프트 이름 변환.

    Examples:
        "creative/analyze_topic.j2" → "analyze-topic"
        "review_evaluate.j2" → "review-evaluate"
        "create_storyboard.j2" → "create-storyboard"
    """
    name = template_name
    if name.startswith("creative/"):
        name = name[len("creative/") :]
    name = name.removesuffix(".j2")
    return name.replace("_", "-")


def _parse_chat_prompt(prompt: Any) -> tuple[str | None, Any]:
    """LangFuse chat prompt에서 (system_instruction, user_template)를 추출한다.

    chat 타입: prompt.prompt = [{"role": "system", ...}, {"role": "user", ...}]
    text 타입: prompt.prompt = "template string" (하위 호환)
    """
    raw = prompt.prompt

    # chat 타입: list of messages
    if isinstance(raw, list):
        system_text = None
        user_text = ""
        for msg in raw:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and content:
                system_text = content
            elif role == "user":
                user_text = content
        tmpl = _lf_jinja_env.from_string(user_text)
        return system_text, tmpl

    # text 타입 (하위 호환): 전체가 user template
    tmpl = _lf_jinja_env.from_string(raw)
    return None, tmpl


def get_prompt_template(template_name: str) -> PromptBundle:
    """LangFuse 우선 fetch → PromptBundle 반환. 실패 시 로컬 파일 fallback.

    LANGFUSE_MANAGED_TEMPLATES에 포함된 템플릿만 LangFuse fetch를 시도.
    include 사용 템플릿(cinematographer, create_storyboard 등)은 항상 로컬 파일.

    Returns:
        PromptBundle(template, system_instruction, langfuse_prompt)
    """
    if template_name in LANGFUSE_MANAGED_TEMPLATES:
        from services.agent.observability import get_langfuse_client

        lf = get_langfuse_client()
        if lf is not None:
            lf_name = _to_langfuse_name(template_name)
            try:
                prompt = lf.get_prompt(lf_name, label="production")
                system_text, tmpl = _parse_chat_prompt(prompt)
                logger.debug(
                    "[LangFuse] Prompt '%s' fetched (v%s, type=%s)",
                    lf_name,
                    getattr(prompt, "version", "?"),
                    "chat" if isinstance(prompt.prompt, list) else "text",
                )
                return PromptBundle(
                    template=tmpl,
                    system_instruction=system_text,
                    langfuse_prompt=prompt,
                    _source="langfuse",
                )
            except Exception as e:
                logger.warning("[LangFuse] Prompt '%s' fetch 실패, Jinja2 fallback: %s", lf_name, e)

    # Fallback: 로컬 .j2 파일
    tmpl = template_env.get_template(template_name)
    return PromptBundle(template=tmpl)
