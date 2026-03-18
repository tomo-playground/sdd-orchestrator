"""Prompt variable builders — Jinja2 제어문을 Python 사전 처리로 대체.

LangFuse compile()은 단순 {{변수}} 치환만 지원하므로,
{% for %}, {% if %} 등 제어문은 Python에서 문자열로 사전 렌더링한다.

prompt_partials.py의 함수(render_character_profile 등)를 내부 호출하여 재사용.
"""

from __future__ import annotations


def build_concepts_block(concepts: list[dict]) -> str:
    """{% for concept in concepts %} 대체."""
    parts = []
    for i, c in enumerate(concepts, 1):
        role = c.get("agent_role", f"concept_{i}")
        content = c.get("content", "")
        parts.append(f"### Concept {i}: {role}\n{content}")
    return "\n\n".join(parts)


def build_concepts_block_simple(concepts: list[dict]) -> str:
    """{% for concept in concepts %} — agent_role + content만."""
    parts = []
    for c in concepts:
        role = c.get("agent_role", "unknown")
        content = c.get("content", "")
        parts.append(f"### {role}\n{content}")
    return "\n\n".join(parts)


def build_scenes_block(scenes: list[dict]) -> str:
    """{% for scene in scenes %} 대체 (edit_scenes용)."""
    parts = []
    for s in scenes:
        idx = s.get("scene_index", 0)
        speaker = s.get("speaker", "A")
        duration = s.get("duration", 3)
        script = s.get("script") or "(empty)"
        image_prompt = s.get("image_prompt") or "(empty)"
        parts.append(
            f"### Scene {idx}\n"
            f"- **Speaker**: {speaker}\n"
            f"- **Duration**: {duration}s\n"
            f"- **Script**: {script}\n"
            f"- **Image Prompt**: {image_prompt}"
        )
    return "\n\n".join(parts)


def build_materials_block(materials: list[dict]) -> str:
    """{% for material in materials %} 대체."""
    parts = []
    for i, m in enumerate(materials, 1):
        url = m.get("url", "N/A")
        content = m.get("content", "")
        parts.append(f"### Material {i}\n**URL**: {url}\n**Content**:\n{content}")
    return "\n\n".join(parts)


def build_tags_block(tags: list[str]) -> str:
    """{% for tag in tags %} 대체."""
    return "\n".join(f"- {tag}" for tag in tags)


def build_references_block(references: list[str]) -> str:
    """{% for ref in references %} 대체."""
    return "\n".join(f"- {ref}" for ref in references)


def build_optional_section(header: str, content: str | None) -> str:
    """{% if content %}## Header\n{{ content }}{% endif %} 대체."""
    if not content:
        return ""
    return f"\n\n{header}\n{content}"


def build_copyright_scenes_block(scenes: list[dict]) -> str:
    """copyright_reviewer용 씬 블록."""
    parts = []
    for i, s in enumerate(scenes, 1):
        lines = [
            f"### Scene {i}",
            f'- **Script**: {s.get("script", "")}',
            f'- **Speaker**: {s.get("speaker", "A")}',
            f'- **Camera**: {s.get("camera", "N/A")}',
            f'- **Environment**: {s.get("environment", "N/A")}',
        ]
        if s.get("image_prompt"):
            lines.append(f'- **Visual Prompt**: {s["image_prompt"]}')
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_selected_concept_block(concept: dict | None) -> str:
    """{% if selected_concept %} 대체."""
    if not concept:
        return ""
    title = concept.get("title", "")
    body = concept.get("concept", "")
    return f"\n\n## Selected Concept\n**Title**: {title}\n**Concept**: {body}"


# ---------------------------------------------------------------------------
# Director/QC 빌더 re-export (prompt_builders_b.py)
# ---------------------------------------------------------------------------
from services.agent.prompt_builders_b import (  # noqa: E402, F401
    build_checkpoint_director_plan_section,
    build_checkpoint_draft_scenes_block,
    build_checkpoint_locations_section,
    build_director_decision_section,
    build_feedback_response_json_hint,
    build_feedback_section,
    build_previous_steps_block,
    build_production_qc_section,
    build_quality_criteria_block,
    build_scene_reasoning_section,
    build_visual_qc_section,
    to_json,
)

# Sprint 3 빌더 re-export
from services.agent.prompt_builders_c import (  # noqa: E402, F401
    build_character_context_section,
    build_character_name_section,
    build_character_tag_rules,
    build_character_tags_fallback,
    build_characters_tags_block,
    build_chat_context_cinematographer,
    build_cine_feedback_json_hint,
    build_cine_feedback_section,
    build_creative_direction_section,
    build_critic_feedback_section,
    build_description_section,
    build_dialogue_rules_section,
    build_dialogue_scene_max,
    build_dialogue_scene_range,
    build_director_feedback_section,
    build_director_plan_section,
    build_durations_list,
    build_errors_block,
    build_expand_feedback_section,
    build_gemini_feedback_section,
    build_korean_hint,
    build_korean_quality_rules,
    build_languages_list,
    build_messages_block,
    build_multi_character_rules,
    build_multi_scene_mode_field,
    build_narrative_score_section,
    build_optional_text_section,
    build_prev_concept_section,
    build_reference_guidelines_section,
    build_research_brief_section,
    build_rule_errors_section,
    build_rule_warnings_section,
    build_scene_count_max,
    build_scene_count_range,
    build_selected_concept_json,
    build_storyboard_chat_context,
    build_structure_speaker_rule,
    build_structures_list,
    build_style_section,
    build_warnings_block,
    build_writer_plan_section,
)

# ---------------------------------------------------------------------------
# Inventory 빌더 re-export (prompt_builders_inventory.py)
# ---------------------------------------------------------------------------
from services.agent.prompt_builders_inventory import (  # noqa: E402, F401
    build_casting_guide,
    build_casting_json_section,
    build_inventory_characters_block,
    build_inventory_structures_block,
    build_inventory_styles_block,
)

# ---------------------------------------------------------------------------
# Writer/Script 빌더 re-export (prompt_builders_writer.py)
# ---------------------------------------------------------------------------
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
