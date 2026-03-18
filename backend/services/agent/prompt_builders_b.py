"""B등급 Prompt Builders -- Director/QC 빌더 함수.

Director, Checkpoint, Explain, QC 관련 빌더 함수.
prompt_builders.py에서 re-export되어 기존 import를 유지한다.

Writer/Script 함수는 prompt_builders_writer.py로,
Inventory 함수는 prompt_builders_inventory.py로 분리됨.
"""

from __future__ import annotations

import json


def to_json(obj: object) -> str:
    """Jinja2 ``| tojson(indent=2)`` 대체."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


# -- director 빌더 --


def build_quality_criteria_block(criteria: list[str]) -> str:
    """director -- ``{% for c in quality_criteria %}`` 대체."""
    if not criteria:
        return ""
    items = "\n".join(f"{i}. {c}" for i, c in enumerate(criteria, 1))
    return f"\n\n## Creative Direction Quality Criteria\n{items}\n이 기준도 Production 결과 평가에 반영하세요."


def build_visual_qc_section(visual_qc_result: dict | None) -> str:
    """director -- Visual QC 결과를 포맷팅한다.

    정적 규칙(Environment-Script Consistency 등)은 LangFuse
    ``creative/director`` system prompt에서 관리한다.
    이 빌더는 동적 QC 결과(issues 목록)만 조립한다.
    """
    if not visual_qc_result or visual_qc_result.get("ok"):
        return ""
    issues = visual_qc_result.get("issues", [])
    items = "\n".join(f"- {issue}" for issue in issues)
    return f"\n\n### Visual QC Warnings\n{items}\n위 다양성/일관성 문제가 감지되었습니다. revise_cinematographer를 고려하세요."


def _format_qc_issues(label: str, qc_result: dict | None, revise_hint: str) -> str:
    """단일 QC 결과를 이슈 문자열로 변환한다. ok이거나 없으면 빈 문자열."""
    if not qc_result or qc_result.get("ok"):
        return ""
    issues = qc_result.get("issues", [])
    items = "\n".join(f"- {issue}" for issue in issues)
    return f"\n### {label} QC Warnings\n{items}\n{revise_hint}"


def build_production_qc_section(state: dict) -> str:
    """Director -- TTS/Sound/Copyright QC 결과를 포맷팅한다."""
    parts = [
        _format_qc_issues(
            "TTS Design",
            state.get("tts_qc_result"),
            "revise_tts_designer를 고려하세요.",
        ),
        _format_qc_issues(
            "Sound Design",
            state.get("sound_qc_result"),
            "revise_sound_designer를 고려하세요.",
        ),
        _format_qc_issues(
            "Copyright",
            state.get("copyright_qc_result"),
            "revise_copyright_reviewer를 고려하세요.",
        ),
    ]
    combined = "".join(p for p in parts if p)
    return f"\n{combined}" if combined else ""


def build_previous_steps_block(steps: list[dict]) -> str:
    """director -- ``{% for prev in previous_steps %}``."""
    if not steps:
        return ""
    parts = []
    for prev in steps:
        lines = [
            f"### Step {prev.get('step', '?')}",
            f"- **Observe**: {prev.get('observe', '')}",
            f"- **Think**: {prev.get('think', '')}",
            f"- **Act**: {prev.get('act', '')}",
        ]
        if prev.get("feedback"):
            lines.append(f"- **Feedback sent**: {prev['feedback']}")
        parts.append("\n".join(lines))
    return "\n\n## Previous ReAct Steps\n" + "\n\n".join(parts)


# -- 공통 빌더 --


def build_feedback_section(feedback: str | None, header: str = "## Previous Attempt Feedback") -> str:
    """공통 -- ``{% if feedback %}``."""
    if not feedback:
        return ""
    return f"\n\n{header}\n{feedback}\nFix the issues above in your new output."


def build_feedback_response_json_hint(feedback: str | None) -> str:
    """tts_designer / sound_designer -- JSON 예시 내 response_message 힌트."""
    if not feedback:
        return ""
    return ',\n  "response_message": "Director 피드백에 대한 응답을 여기에 작성하세요. 수정한 내용, 이유, 대안을 포함하세요."'


# -- explain 빌더 --


def build_director_decision_section(decision: str | None, feedback: str | None) -> str:
    """explain -- ``{% if director_decision %}``."""
    if not decision:
        return ""
    result = f"\n\n## Director Decision: {decision}"
    if feedback:
        result += f"\nFeedback: {feedback}"
    return result


def build_scene_reasoning_section(reasoning: list | None) -> str:
    """explain -- ``{% if scene_reasoning %}``."""
    if not reasoning:
        return ""
    return f"\n\n## Scene Reasoning\n{to_json(reasoning)}"


# -- director_checkpoint 빌더 --


def build_checkpoint_director_plan_section(director_plan: dict | None) -> str:
    """director_checkpoint -- director_plan 블록."""
    if not director_plan:
        return "\n(Director Plan 없음 \u2014 일반 기준으로 평가)"
    parts = [
        f"- **Creative Goal**: {director_plan.get('creative_goal', 'N/A')}",
        f"- **Target Emotion**: {director_plan.get('target_emotion', 'N/A')}",
        "- **Quality Criteria**:",
    ]
    for i, c in enumerate(director_plan.get("quality_criteria", []), 1):
        parts.append(f"  {i}. {c}")
    style_dir = director_plan.get("style_direction")
    if style_dir:
        parts.append(f"- **Style Direction**: {style_dir}")
    return "\n".join(parts)


def build_checkpoint_draft_scenes_block(scenes: list[dict]) -> str:
    """director_checkpoint -- ``{% for scene in draft_scenes %}``."""
    parts = []
    for i, scene in enumerate(scenes, 1):
        parts.append(
            f"### Scene {i}\n"
            f"- **\ub300\uc0ac**: {scene.get('script', '')}\n"
            f"- **\ud654\uc790**: {scene.get('speaker', 'A')}\n"
            f"- **\uae38\uc774**: {scene.get('duration', 0)}\ucd08"
        )
    return "\n\n".join(parts)


def build_checkpoint_locations_section(writer_plan: dict | None) -> str:
    """director_checkpoint -- ``{% if writer_plan.get('locations') %}``."""
    if not writer_plan:
        return ""
    locations = writer_plan.get("locations")
    if not locations:
        return ""
    parts = []
    for loc in locations:
        name = loc.get("name", "?")
        scenes = loc.get("scenes", [])
        tags = loc.get("tags", [])
        scenes_str = ", ".join(str(s) for s in scenes)
        tags_str = ", ".join(tags)
        parts.append(f"- **{name}** (\uc54c \uc778\ub371\uc2a4: {scenes_str}): \ud0dc\uadf8 = {tags_str}")
    return "\n\n## Writer's Location Map (\uac80\uc99d \ud544\uc218)\n\n" + "\n".join(parts)


# ---------------------------------------------------------------------------
# 후방 호환 re-export -- 기존 ``from prompt_builders_b import X`` 유지
# ---------------------------------------------------------------------------
from services.agent.prompt_builders_inventory import (  # noqa: E402, F401
    build_casting_guide,
    build_casting_json_section,
    build_inventory_characters_block,
    build_inventory_structures_block,
    build_inventory_styles_block,
)
from services.agent.prompt_builders_writer import (  # noqa: E402, F401
    build_chat_context_block,
    build_director_plan_section_for_tts,
    build_emotional_arc_section,
    build_korean_critical_hint,
    build_korean_rules_block,
    build_language_hint,
    build_output_format_block,
    build_scene_range_text,
    build_scriptwriter_characters_block,
    build_sound_emotional_arc_section,
    build_structure_rules_block,
    build_tts_characters_block,
)
