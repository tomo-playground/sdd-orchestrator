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
