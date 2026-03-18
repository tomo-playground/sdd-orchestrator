"""C등급 Prompt Builders — Sprint 3 Jinja2→네이티브 전환용 빌더 함수.

analyze_topic, review_reflection, review_unified, scene_expand,
concept_architect, cinematographer, create_storyboard 4종의
Jinja2 제어문을 Python 사전 렌더링으로 대체한다.
"""

from __future__ import annotations

import json

# ── analyze_topic ──────────────────────────────────────────────


def build_description_section(description: str | None) -> str:
    """{% if description %} 대체."""
    if not description:
        return ""
    return f"- **상세 설명**: {description}"


def build_messages_block(messages: list[dict] | None) -> str:
    """{% if messages %}{% for msg in messages %} 대체."""
    if not messages:
        return ""
    parts = ["\n## Conversation History"]
    for msg in messages:
        role = msg.get("role", "?")
        text = msg.get("text", "")
        parts.append(f"- **{role}**: {text}")
    return "\n".join(parts)


def build_durations_list(durations: list[int]) -> str:
    """{% for d in durations %} 대체."""
    return "\n".join(f"- {d}초" for d in durations)


def build_languages_list(languages: list[dict]) -> str:
    """{% for lang in languages %} 대체."""
    return "\n".join(
        f"- {lang.get('value', '')} ({lang.get('label', '')})"
        for lang in languages
    )


def build_structures_list(structures: list) -> str:
    """{% for struct in structures %} 대체."""
    parts = []
    for struct in structures:
        sid = getattr(struct, "id", "") if not isinstance(struct, dict) else struct.get("id", "")
        name = getattr(struct, "name", "") if not isinstance(struct, dict) else struct.get("name", "")
        tone = getattr(struct, "tone", "") if not isinstance(struct, dict) else struct.get("tone", "")
        req2 = getattr(struct, "requires_two_characters", False) if not isinstance(struct, dict) else struct.get("requires_two_characters", False)
        suffix = " (2인 필수)" if req2 else ""
        parts.append(f"- **{sid}**: {name} — {tone}{suffix}")
    return "\n".join(parts)


# ── review_reflection ──────────────────────────────────────────


def build_errors_block(errors: list[str] | None) -> str:
    """{% if errors %}{% for error in errors %} 대체."""
    if not errors:
        return "(No rule errors)"
    return "\n".join(f"- {e}" for e in errors)


def build_warnings_block(warnings: list[str] | None) -> str:
    """{% if warnings %}{% for warning in warnings %} 대체."""
    if not warnings:
        return "(No warnings)"
    return "\n".join(f"- {w}" for w in warnings)


def build_gemini_feedback_section(feedback: str | None) -> str:
    """{% if gemini_feedback %} 대체."""
    if not feedback:
        return ""
    return f"\n### Gemini Feedback\n{feedback}"


def build_narrative_score_section(
    score: dict | None,
    threshold: float | str = 0.6,
) -> str:
    """{% if narrative_score %} 대체."""
    if not score:
        return ""
    lines = [
        f"\n### Narrative Quality Score (Failed Threshold: {threshold})",
        f"- Hook: {score.get('hook', 0)}",
        f"- Emotional Arc: {score.get('emotional_arc', 0)}",
        f"- Twist/Payoff: {score.get('twist_payoff', 0)}",
        f"- Speaker Tone: {score.get('speaker_tone', 0)}",
        f"- Script-Image Sync: {score.get('script_image_sync', 0)}",
        f"- **Overall: {score.get('overall', 0)}** (threshold: {threshold})",
        "",
        f"Narrative Feedback: {score.get('feedback', '')}",
    ]
    return "\n".join(lines)


# ── review_unified ──────────────────────────────────────────


def build_rule_errors_section(errors: list[str] | None) -> str:
    """{% if rule_errors %}{% for error in rule_errors %} 대체."""
    if not errors:
        return ""
    items = "\n".join(f"- {e}" for e in errors)
    return f"\n### Rule-Based Errors (already detected)\n{items}"


def build_rule_warnings_section(warnings: list[str] | None) -> str:
    """{% if rule_warnings %}{% for warning in rule_warnings %} 대체."""
    if not warnings:
        return ""
    items = "\n".join(f"- {w}" for w in warnings)
    return f"\n### Warnings\n{items}"


# ── scene_expand ──────────────────────────────────────────


def build_selected_concept_json(concept: dict | None) -> str:
    """{% if selected_concept %}{{ selected_concept | tojson }} 대체."""
    if not concept:
        return ""
    return f"\n## Selected Concept\n{json.dumps(concept, ensure_ascii=False, indent=2)}"


def build_character_context_section(ctx: str | None) -> str:
    """{% if character_context %} 대체."""
    if not ctx:
        return ""
    return f"\n## Character\n{ctx}"


def build_structure_speaker_rule(structure: str) -> str:
    """{% if structure == 'Monologue' %} 등 대체."""
    if structure == "Monologue":
        return '6. Speaker: Always "A" (single narrator).'
    if structure == "Dialogue":
        return (
            '6. Speakers: "A" and "B" (two characters in conversation). '
            "CRITICAL: Both A and B MUST each have at least 30% of dialogue scenes."
        )
    if structure == "Narrated Dialogue":
        return (
            '6. Speakers: "Narrator" for narration/description, "A" and "B" for character dialogue. '
            "CRITICAL: Both A and B MUST each have at least 30% of dialogue scenes. "
            "Include at least 1 Narrator scene for atmosphere/context."
        )
    return f"6. Structure: {structure}"


def build_expand_feedback_section(feedback: str | None) -> str:
    """{% if feedback %} 대체."""
    if not feedback:
        return ""
    return (
        f"\n## Feedback from Review\n{feedback}\n"
        "Consider this feedback when creating new scenes."
    )


def build_korean_hint(language: str) -> str:
    """{% if language == 'Korean' %} 대체."""
    if language != "Korean":
        return ""
    return "\n반드시 모든 대사를 한국어로 작성하세요."


# ── concept_architect ──────────────────────────────────────


def build_character_name_section(
    name: str | None, label: str = "Character A"
) -> str:
    """{% if character_name %} 대체."""
    if not name:
        return ""
    return f"\n## {label}\nName: {name}"


def build_dialogue_rules_section(
    char_b_name: str | None,
    structure: str,
    char_a_name: str | None = None,
) -> str:
    """{% if character_b_name or structure in ('Dialogue', ...) %} 대체."""
    if not char_b_name and structure not in ("Dialogue", "Narrated Dialogue"):
        return ""
    a = char_a_name or "Character A"
    b = char_b_name or "Character B"
    return (
        "\n## Dialogue Rules (MANDATORY)\n"
        "- This is a **two-character conversation**. Both Speaker A and Speaker B MUST appear.\n"
        "- Alternate speakers across scenes: A \u2192 B \u2192 A \u2192 B (with occasional Narrator allowed).\n"
        f"- Speaker A = {a}, Speaker B = {b}.\n"
        "- Do NOT make all scenes speaker=\"A\". At least 40% of non-Narrator scenes must be Speaker B."
    )


def build_director_plan_section(plan: dict | None) -> str:
    """{% if director_plan %} 대체."""
    if not plan:
        return ""
    goal = plan.get("creative_goal", "")
    emotion = plan.get("target_emotion", "")
    criteria = plan.get("quality_criteria", [])
    criteria_str = ", ".join(str(c) for c in criteria)
    return (
        "\n## Creative Direction (from Director)\n"
        f"- Goal: {goal}\n"
        f"- Target Emotion: {emotion}\n"
        f"- Quality Criteria: {criteria_str}\n"
        "Your concept MUST align with this creative direction."
    )


def build_reference_guidelines_section(guidelines: str | None) -> str:
    """{% if reference_guidelines %} 대체."""
    if not guidelines:
        return ""
    return f"\n## Reference Guidelines\n{guidelines}"


def build_research_brief_section(brief: dict | None) -> str:
    """{% if research_brief %} 대체."""
    if not brief:
        return ""
    return (
        "\n## Research Brief (from Source Materials)\n"
        f"Topic Summary: {brief.get('topic_summary', 'N/A')}\n"
        f"Recommended Angle: {brief.get('recommended_angle', 'N/A')}\n"
        f"Key Elements: {', '.join(str(e) for e in brief.get('key_elements', []))}\n"
        f"Emotional Arc: {brief.get('emotional_arc_suggestion', 'N/A')}\n"
        f"Audience Hook: {brief.get('audience_hook', 'N/A')}"
    )


def build_prev_concept_section(prev: str | None) -> str:
    """{% if prev_concept %} 대체."""
    if not prev:
        return ""
    return f"\n## Your Previous Concept (Improve This)\n{prev}"


def build_director_feedback_section(feedback: str | None) -> str:
    """{% if director_feedback %} 대체."""
    if not feedback:
        return ""
    return f"\n## Director Feedback\n{feedback}"


def build_critic_feedback_section(feedback: str | None) -> str:
    """{% if critic_feedback %} 대체."""
    if not feedback:
        return ""
    return f"\n## Critic Feedback (Address These Weaknesses)\n{feedback}"


def build_korean_quality_rules(language: str) -> str:
    """{% if language == 'Korean' %} 한국어 품질 규칙."""
    if language != "Korean":
        return ""
    return (
        "\n## 한국어 품질 규칙\n"
        "- title, hook, arc, key_moments의 description 모두 **자연스러운 한국어**로 작성\n"
        "- 맞춤법/오탈자 필수 점검: 받침 탈락, 의미 없는 글자 조합 금지\n"
        "- 문장을 소리 내어 읽었을 때 어색하지 않아야 함\n"
        "- 같은 표현 반복 금지 (key_moments 간 description이 서로 달라야 함)"
    )


# ── cinematographer ──────────────────────────────────────────


def build_characters_tags_block(characters_tags: dict | None) -> str:
    """{% if characters_tags %} + {% for speaker, tag_layers %} 대체."""
    if not characters_tags:
        return ""
    parts = ["## Character Visual Tags (per speaker)"]
    for speaker, tag_layers in characters_tags.items():
        parts.append(f'### Speaker "{speaker}"')
        hints = tag_layers.get("action_hints", [])
        if hints:
            parts.append(
                f"**Preferred actions (use as default, override per scene):** {json.dumps(hints, ensure_ascii=False)}"
            )
    parts.extend([
        "\u26a0\ufe0f CHARACTER TAG RULES (MANDATORY):",
        "- Do NOT write character identity tags (hair, eyes, body), clothing/accessory tags, or LoRA trigger words in `image_prompt`",
        "- These are ALL injected automatically by the system from the character database",
        "- In `image_prompt`, write ONLY: scene-specific tags (camera, environment, lighting, action, pose, expression, props)",
        "- Do NOT invent or add clothing tags (e.g. `blue_skirt`, `white_shirt`, `checkered_shirt`)",
        "Action hints are the character's typical poses/actions \u2014 use them as defaults but freely override with scene-appropriate actions.",
    ])
    return "\n".join(parts)


def build_character_tags_fallback(tags: dict | None) -> str:
    """{% elif character_tags %} 대체."""
    if not tags:
        return ""
    return f"## Character Visual Tags\n{json.dumps(tags, ensure_ascii=False, indent=2)}"


def build_style_section(style: str | None) -> str:
    """{% if style %} + {% if style == 'Anime' %} 등 대체."""
    if not style:
        return ""
    parts = [f"## Visual Style: {style}"]
    s = style.lower() if style else ""
    if s == "anime":
        parts.append(
            "- This is an **anime** style project. Do NOT add `realistic`, `photorealistic`, or `photo` tags.\n"
            "- Appropriate style tags: none needed (anime is default for SD)"
        )
    elif s == "chibi":
        parts.append(
            "- Add `chibi, super_deformed, small_body, big_head` to every scene.\n"
            "- Do NOT add `realistic`, `photorealistic` tags."
        )
    elif s in ("realistic", "photorealistic"):
        parts.append(
            "- Add `realistic` or `photorealistic` to every scene.\n"
            "- Do NOT add `chibi`, `super_deformed`, `water_color`, `sketch` tags."
        )
    return "\n".join(parts)


def build_writer_plan_section(plan: dict | None) -> str:
    """{% if writer_plan %} — cinematographer용 Writer Plan 블록."""
    if not plan:
        return ""
    hook = plan.get("hook_strategy", "")
    arc = plan.get("emotional_arc", [])
    arc_str = ", ".join(str(e) for e in arc)
    dist = plan.get("scene_distribution", {})
    intro = dist.get("intro", 0)
    rising = dist.get("rising", 0)
    climax = dist.get("climax", 0)
    resolution = dist.get("resolution", 0)

    parts = [
        "## Writer's Creative Plan (USE THIS to guide your visual decisions)",
        f"- **Hook Strategy**: {hook}",
        f"- **Emotional Arc**: {arc_str}",
        f"- **Scene Distribution**: intro={intro}, rising={rising}, climax={climax}, resolution={resolution}",
        "",
        "Match your visual design to this plan:",
        f"- Hook scenes (first {intro} scenes): Use attention-grabbing angles and lighting",
        "- Rising scenes: Build visual intensity gradually",
        "- Climax scene: Maximum visual impact (strongest camera + lighting combination)",
        "- Resolution scenes: Release tension with softer visuals",
    ]

    locations = plan.get("locations")
    if locations:
        parts.append("")
        parts.append("### Location Map (CRITICAL \u2014 environment consistency)")
        for loc in locations:
            name = loc.get("name", "?")
            scenes = loc.get("scenes", [])
            tags = loc.get("tags", [])
            parts.append(
                f"- **{name}** (scenes {', '.join(str(s) for s in scenes)}): {', '.join(tags)}"
            )
        parts.append(
            "**Rules**: Scenes sharing the same location MUST use the same `context_tags.environment` tags listed above. "
            "Do NOT invent new environment tags for scenes already mapped to a location."
        )

    return "\n".join(parts)


def build_chat_context_cinematographer(ctx: list[dict] | None) -> str:
    """{% if chat_context %}{% for msg in chat_context %} — cinematographer용."""
    if not ctx:
        return ""
    parts = [
        "## User Intent Context",
        "사용자의 사전 대화에서 파악된 의도입니다. 창작 방향에 참고하세요.",
    ]
    for msg in ctx:
        role_label = "사용자" if msg.get("role") == "user" else "시스템"
        parts.append(f"- **{role_label}**: {msg.get('text', '')}")
    return "\n".join(parts)


def build_creative_direction_section(direction: dict | None) -> str:
    """{% if creative_direction %} 대체."""
    if not direction:
        return ""
    name = direction.get("name", "")
    instruction = direction.get("instruction", "")
    techniques = direction.get("techniques", [])
    parts = [
        f"## Your Creative Direction: {name}",
        instruction,
        "",
        "### Signature Techniques (use at least 2 per scene):",
    ]
    for t in techniques:
        parts.append(f"- `{t}`")
    return "\n".join(parts)


def build_cine_feedback_section(feedback: str | None) -> str:
    """{% if feedback %} — cinematographer 하단 + JSON 예시 내 response_message."""
    if not feedback:
        return ""
    return (
        f"\n## Previous Attempt Feedback\n{feedback}\n"
        "Fix the issues above in your new output."
    )


def build_cine_feedback_json_hint(feedback: str | None) -> str:
    """JSON 예시 안의 response_message 힌트."""
    if not feedback:
        return ""
    return (
        ',\n  "response_message": "Director 피드백에 대한 응답을 여기에 작성하세요. '
        '수정한 내용, 이유, 대안이 있다면 포함하세요."'
    )


# ── create_storyboard 공통 ──────────────────────────────────


def build_optional_text_section(
    header: str, content: str | None
) -> str:
    """{% if var %}\\n## Header\\n{{ var }}{% endif %} 패턴."""
    if not content:
        return ""
    return f"\n## {header}\n{content}"


def build_storyboard_chat_context(ctx: list[dict] | None) -> str:
    """create_storyboard의 chat_context 블록."""
    if not ctx:
        return ""
    parts = [
        "\n## User Intent Context",
        "사용자의 사전 대화에서 파악된 의도입니다. 창작 방향에 참고하세요.",
    ]
    for msg in ctx:
        role_label = "사용자" if msg.get("role") == "user" else "시스템"
        parts.append(f"- **{role_label}**: {msg.get('text', '')}")
    return "\n".join(parts)


def build_character_tag_rules(has_character: bool) -> str:
    """{% if character_context %} 내 TAG RULES 블록."""
    if not has_character:
        return ""
    return (
        "\n\u26a0\ufe0f CHARACTER TAG RULES:\n"
        "- Do NOT include character identity tags (hair, eyes, body) or costume tags in image_prompt\n"
        "- These are injected automatically by the system for visual consistency\n"
        "- Do NOT invent clothing, hair colors, eye colors, or outfits \u2014 the system handles all character appearance\n"
        "- Focus image_prompt ONLY on: expression, gaze, pose, action, props, camera, environment, mood"
    )


def build_scene_count_range(duration: int, structure: str = "Monologue") -> str:
    """{{ ((duration / 3) | round | int) }}-{{ ((duration / 2) | round | int) }} 대체."""
    from services.storyboard.helpers import (  # noqa: PLC0415
        calculate_max_scenes,
        calculate_min_scenes,
    )

    try:
        min_s = calculate_min_scenes(duration, structure)
        max_s = calculate_max_scenes(duration, structure)
    except Exception:
        min_s = round(duration / 3)
        max_s = round(duration / 2)
    return f"{min_s}-{max_s}"


def build_scene_count_max(duration: int, structure: str = "Monologue") -> str:
    """{{ ((duration / 2) | round | int) }} 대체."""
    from services.storyboard.helpers import calculate_max_scenes  # noqa: PLC0415

    try:
        return str(calculate_max_scenes(duration, structure))
    except Exception:
        return str(round(duration / 2))


# ── dialogue / narrated 전용 ──────────────────────────────


def build_dialogue_scene_range(duration: int) -> str:
    """{{ [3, ((duration / 6) | round | int)] | max }}-{{ ((duration / 4) | round | int) }}."""
    min_s = max(3, round(duration / 6))
    max_s = round(duration / 4)
    return f"{min_s}-{max_s}"


def build_dialogue_scene_max(duration: int) -> str:
    """{{ ((duration / 4) | round | int) }}."""
    return str(round(duration / 4))


def build_multi_character_rules(
    is_multi: bool,
    char_a_ctx: dict | None = None,
    char_b_ctx: dict | None = None,
) -> str:
    """{% if is_multi_character_capable %} 대체."""
    if not is_multi:
        return ""
    parts = [
        "\n\u26a0\ufe0f MULTI-CHARACTER SCENE RULES (scene_mode: \"multi\"):",
        "- You MAY create 1-2 scenes where BOTH characters appear together",
        "- Use these ONLY for key emotional moments (reunion, confrontation, farewell, shared reaction)",
        "- Multi scenes: character tags are injected automatically \u2014 do NOT add them",
        '- Multi scenes: subject tag should reflect both characters (e.g., "1boy, 1girl" / "2girls" / "2boys")',
    ]
    if char_a_ctx and char_b_ctx:
        ga = (char_a_ctx.get("gender") or "female").lower()
        gb = (char_b_ctx.get("gender") or "female").lower()
        if ga == "male" and gb == "male":
            parts.append('- Multi scenes subject: "2boys"')
        elif ga == "female" and gb == "female":
            parts.append('- Multi scenes subject: "2girls"')
        else:
            parts.append('- Multi scenes subject: "1boy, 1girl"')
    parts.extend([
        '- Multi scenes: add interaction tags (e.g., "eye_contact", "facing_another", "hand_holding")',
        '- Multi scenes: speaker can be "A" or "B" (whoever is speaking in that moment)',
        '- Each multi scene MUST include "scene_mode": "multi" in JSON output',
        '- All other scenes MUST include "scene_mode": "single" in JSON output',
        "- LIMIT: Maximum 1-2 multi scenes per storyboard",
    ])
    return "\n".join(parts)


def build_multi_scene_mode_field(is_multi: bool) -> str:
    """JSON 예시 안의 scene_mode 필드."""
    if not is_multi:
        return ""
    return '\n    "scene_mode": "single",'
