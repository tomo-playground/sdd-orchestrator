"""LangFuse Prompt Management — compile() 기반 네이티브 프롬프트 관리.

28개 프롬프트 모두 LangFuse 네이티브 compile() 경로로 전환 완료.
- system 메시지: 역할/규칙 (LangFuse UI에서 편집 가능)
- user 메시지: {{var}} 네이티브 변수 치환
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import pipeline_logger as logger

# LangFuse에서 runtime fetch하는 프롬프트 목록
# A등급(단순) + B등급(복잡 로직) 통합
LANGFUSE_MANAGED_TEMPLATES: frozenset[str] = frozenset(
    {
        # --- A등급: 단순 변수 치환 + 경량 로직 ---
        "creative/analyze_topic",
        "creative/concept_architect",
        "creative/location_planner",
        "creative/sound_designer",
        "creative/material_analyst",
        "creative/copyright_reviewer",
        "creative/devils_advocate",
        "creative/narrative_review",
        "creative/reference_analyst",
        "creative/scene_expand",
        "creative/edit_scenes",
        "creative/review_reflection",
        "validate_image_tags",
        "review_evaluate",
        # --- B등급: 복잡 로직 ---
        "creative/director",
        "creative/scriptwriter",
        "creative/director_plan",
        "creative/writer_planning",
        "creative/tts_designer",
        "creative/director_checkpoint",
        "creative/explain",
        "creative/director_evaluate",
        "creative/review_unified",
        # --- 파셜→변수 전환 완료 ---
        "creative/cinematographer",
        "create_storyboard",
        "create_storyboard_confession",
        "create_storyboard_dialogue",
        "create_storyboard_narrated",
    }
)

# 하위 호환 별칭
A_GRADE_TEMPLATES = LANGFUSE_MANAGED_TEMPLATES


# 프롬프트 이름 → LangFuse 폴더 기반 이름 매핑
_TEMPLATE_TO_LANGFUSE: dict[str, str] = {
    # pipeline/ — 파이프라인 메인 노드
    "creative/director": "pipeline/director",
    "creative/director_plan": "pipeline/director/plan",
    "creative/director_checkpoint": "pipeline/director/checkpoint",
    "creative/director_evaluate": "pipeline/director/evaluate",
    "creative/scriptwriter": "pipeline/writer/script",
    "creative/writer_planning": "pipeline/writer/planning",
    "creative/cinematographer": "pipeline/cinematographer",
    "creative/tts_designer": "pipeline/tts-designer",
    "creative/sound_designer": "pipeline/sound-designer",
    "creative/review_unified": "pipeline/review/unified",
    "review_evaluate": "pipeline/review/evaluate",
    "creative/review_reflection": "pipeline/review/reflection",
    "creative/narrative_review": "pipeline/review/narrative",
    # storyboard/ — 스토리보드 생성 (structure별)
    "create_storyboard": "storyboard/default",
    "create_storyboard_dialogue": "storyboard/dialogue",
    "create_storyboard_narrated": "storyboard/narrated",
    "create_storyboard_confession": "storyboard/confession",
    # tool/ — 보조 도구
    "creative/analyze_topic": "tool/analyze-topic",
    "creative/concept_architect": "tool/concept-architect",
    "creative/devils_advocate": "tool/devils-advocate",
    "creative/copyright_reviewer": "tool/copyright-reviewer",
    "creative/material_analyst": "tool/material-analyst",
    "creative/reference_analyst": "tool/reference-analyst",
    "creative/location_planner": "tool/location-planner",
    "creative/scene_expand": "tool/scene-expand",
    "creative/edit_scenes": "tool/edit-scenes",
    "creative/explain": "tool/explain",
    "validate_image_tags": "tool/validate-image-tags",
}


def _to_langfuse_name(template_name: str) -> str:
    """프롬프트 이름 → LangFuse 프롬프트 이름 변환.

    Examples:
        "creative/director" → "pipeline/director"
        "create_storyboard" → "storyboard/default"
        "creative/analyze_topic" → "tool/analyze-topic"
    """
    if template_name in _TEMPLATE_TO_LANGFUSE:
        return _TEMPLATE_TO_LANGFUSE[template_name]
    # fallback: 미매핑 프롬프트
    name = template_name
    if name.startswith("creative/"):
        name = name[len("creative/") :]
    return name.replace("_", "-")


@dataclass
class CompiledPrompt:
    """LangFuse compile() 결과 — system/user 완전 분리.

    Jinja2 없이 LangFuse 네이티브 변수({{var}})만 사용.
    """

    system: str
    user: str
    langfuse_prompt: Any = None


def compile_prompt(template_name: str, **vars: Any) -> CompiledPrompt:
    """LangFuse compile()로 system/user 분리된 프롬프트 반환.

    LangFuse 네이티브 변수({{var}})만 사용.
    제어문({% if %}, {% for %})은 vars에서 사전 처리 필요.

    Returns:
        CompiledPrompt(system, user, langfuse_prompt)
    """
    from services.agent.observability import get_langfuse_client

    lf = get_langfuse_client()
    lf_name = _to_langfuse_name(template_name)

    if lf is None:
        logger.error(
            "[LangFuse] 클라이언트 미연결 — '%s' 프롬프트를 가져올 수 없습니다. "
            "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST 환경변수를 확인하세요.",
            lf_name,
        )
        return CompiledPrompt(system="", user="")

    try:
        prompt = lf.get_prompt(lf_name, label="production")
        messages = prompt.compile(**vars)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = "\n".join(m["content"] for m in messages if m["role"] == "user")

        # 미치환 변수 방어
        for field_name, field_val in [("system", system), ("user", user)]:
            if "{{" in field_val:
                logger.warning("[LangFuse] 미치환 변수 감지 (%s/%s)", lf_name, field_name)

        return CompiledPrompt(system=system, user=user, langfuse_prompt=prompt)
    except Exception as e:
        logger.error("[LangFuse] compile '%s' 실패: %s", lf_name, e)
        return CompiledPrompt(system="", user="")
