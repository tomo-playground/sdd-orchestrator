"""B등급 Prompt Builders — Sprint 2 Jinja2→네이티브 전환용 빌더 함수.

복잡한 Jinja2 제어문({% for %}, {% if %}, | tojson)을
Python 함수로 사전 렌더링하여 LangFuse {{변수}} 치환만으로 동작하도록 한다.

prompt_builders.py에서 re-export되어 기존 import를 유지한다.
"""

from __future__ import annotations

import json


def to_json(obj: object) -> str:
    """Jinja2 ``| tojson(indent=2)`` 대체."""
    return json.dumps(obj, ensure_ascii=False, indent=2)


# -- director.j2 빌더 --

def build_quality_criteria_block(criteria: list[str]) -> str:
    """director.j2 — ``{% for c in quality_criteria %}`` 대체."""
    if not criteria:
        return ""
    items = "\n".join(f"{i}. {c}" for i, c in enumerate(criteria, 1))
    return f"\n\n## Creative Direction Quality Criteria\n{items}\n이 기준도 Production 결과 평가에 반영하세요."


def build_visual_qc_section(visual_qc_result: dict | None) -> str:
    """director.j2 — ``{% if visual_qc_result and not visual_qc_result.ok %}``."""
    if not visual_qc_result or visual_qc_result.get("ok"):
        return ""
    issues = visual_qc_result.get("issues", [])
    items = "\n".join(f"- {issue}" for issue in issues)
    return f"\n\n### Visual QC Warnings\n{items}\n위 다양성 문제가 감지되었습니다. revise_cinematographer를 고려하세요."


def build_previous_steps_block(steps: list[dict]) -> str:
    """director.j2 — ``{% for prev in previous_steps %}``."""
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


# -- tts_designer.j2 빌더 --

def build_tts_characters_block(characters: list[dict] | None) -> str:
    """tts_designer.j2 — ``{% for char in characters %}``."""
    if not characters:
        return ""
    parts = []
    for char in characters:
        line = f"- **Speaker {char.get('speaker', '?')}** ({char.get('name', '')}): Gender={char.get('gender', 'female')}"
        if char.get("reference_voice"):
            line += f', Reference voice: "{char["reference_voice"]}"'
        if char.get("has_preset"):
            line += " [PRESET CONFIGURED]"
        parts.append(line)
    header = "## Character Profiles\n" + "\n".join(parts)
    rules = (
        "\nIMPORTANT:\n"
        "- Match each character's voice to their gender.\n"
        "- If a reference voice is provided, use it as the baseline and adjust for emotion.\n"
        "- **[PRESET CONFIGURED] speakers**: Do NOT generate `voice_design_prompt`. Only design `pacing`.\n"
        "- **Speakers without preset**: Generate both `voice_design_prompt` and `pacing`."
    )
    return f"\n\n{header}\n{rules}"


def build_director_plan_section_for_tts(director_plan: dict | None) -> str:
    """tts_designer.j2 — ``{% if director_plan and director_plan.target_emotion %}``."""
    if not director_plan:
        return ""
    emotion = director_plan.get("target_emotion", "")
    if not emotion:
        return ""
    return f"\n\n## Target Emotion (from Director)\n**{emotion}**\nAll voice designs should align with this overall emotional direction."


def build_emotional_arc_section(writer_plan: dict | None) -> str:
    """tts_designer / sound_designer — ``{% if writer_plan.emotional_arc %}``."""
    if not writer_plan:
        return ""
    arc = writer_plan.get("emotional_arc")
    if not arc:
        return ""
    arc_str = " \u2192 ".join(str(e) for e in arc)
    return f"\n\n## Emotional Arc (from Writer Plan)\n{arc_str}"


# -- 공통 빌더 --

def build_feedback_section(feedback: str | None, header: str = "## Previous Attempt Feedback") -> str:
    """공통 — ``{% if feedback %}``."""
    if not feedback:
        return ""
    return f"\n\n{header}\n{feedback}\nFix the issues above in your new output."


def build_feedback_response_json_hint(feedback: str | None) -> str:
    """tts_designer / sound_designer — JSON 예시 내 response_message 힌트."""
    if not feedback:
        return ""
    return ',\n  "response_message": "Director 피드백에 대한 응답을 여기에 작성하세요. 수정한 내용, 이유, 대안을 포함하세요."'


# -- explain.j2 빌더 --

def build_director_decision_section(decision: str | None, feedback: str | None) -> str:
    """explain.j2 — ``{% if director_decision %}``."""
    if not decision:
        return ""
    result = f"\n\n## Director Decision: {decision}"
    if feedback:
        result += f"\nFeedback: {feedback}"
    return result


def build_scene_reasoning_section(reasoning: list | None) -> str:
    """explain.j2 — ``{% if scene_reasoning %}``."""
    if not reasoning:
        return ""
    return f"\n\n## Scene Reasoning\n{to_json(reasoning)}"


# -- director_checkpoint.j2 빌더 --

def build_checkpoint_director_plan_section(director_plan: dict | None) -> str:
    """director_checkpoint.j2 — director_plan 블록."""
    if not director_plan:
        return "\n(Director Plan 없음 \u2014 일반 기준으로 평가)"
    parts = [
        f'- **Creative Goal**: {director_plan.get("creative_goal", "N/A")}',
        f'- **Target Emotion**: {director_plan.get("target_emotion", "N/A")}',
        "- **Quality Criteria**:",
    ]
    for i, c in enumerate(director_plan.get("quality_criteria", []), 1):
        parts.append(f"  {i}. {c}")
    style_dir = director_plan.get("style_direction")
    if style_dir:
        parts.append(f"- **Style Direction**: {style_dir}")
    return "\n".join(parts)


def build_checkpoint_draft_scenes_block(scenes: list[dict]) -> str:
    """director_checkpoint.j2 — ``{% for scene in draft_scenes %}``."""
    parts = []
    for i, scene in enumerate(scenes, 1):
        parts.append(
            f"### Scene {i}\n"
            f'- **\ub300\uc0ac**: {scene.get("script", "")}\n'
            f'- **\ud654\uc790**: {scene.get("speaker", "A")}\n'
            f'- **\uae38\uc774**: {scene.get("duration", 0)}\ucd08'
        )
    return "\n\n".join(parts)


def build_checkpoint_locations_section(writer_plan: dict | None) -> str:
    """director_checkpoint.j2 — ``{% if writer_plan.get('locations') %}``."""
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


# -- sound_designer.j2 빌더 --

def build_sound_emotional_arc_section(writer_plan: dict | None) -> str:
    """sound_designer.j2 — 감정 곡선 + BGM 안내."""
    if not writer_plan:
        return ""
    arc = writer_plan.get("emotional_arc")
    if not arc:
        return ""
    arc_str = " \u2192 ".join(str(e) for e in arc)
    return f"\n\n## Emotional Arc (from Writer Plan)\n{arc_str}\nThe BGM mood should complement this emotional progression."


def build_language_hint(language: str) -> str:
    """sound_designer.j2 — ``{% if language == 'Korean' %}``."""
    if language == "Korean":
        return "\nreasoning\uc740 \ubc18\ub4dc\uc2dc \ud55c\uad6d\uc5b4\ub85c \uc791\uc131\ud558\uc138\uc694."
    return ""


# -- director_plan.j2 빌더 --

def build_chat_context_block(chat_context: list[dict] | None) -> str:
    """director_plan.j2 — ``{% for msg in chat_context %}``."""
    if not chat_context:
        return ""
    parts = [
        "## User Intent Context (\uc0ac\uc804 \ub300\ud654 \uc774\ub825)", "",
        "\uc544\ub798\ub294 \uc0ac\uc6a9\uc790\uc640 \uc2dc\uc2a4\ud15c \uac04\uc758 \uc0ac\uc804 \ub300\ud654\uc785\ub2c8\ub2e4.",
        "\uc774 \ub9e5\ub77d\uc5d0\uc11c \uc0ac\uc6a9\uc790\uc758 **\uc758\ub3c4\uc640 \uc694\uad6c\uc0ac\ud56d**\uc744 \ud30c\uc545\ud558\uc5ec execution_plan\uc5d0 \ubc18\uc601\ud558\uc138\uc694.", "",
    ]
    for msg in chat_context:
        role_label = "\uc0ac\uc6a9\uc790" if msg.get("role") == "user" else "\uc2dc\uc2a4\ud15c"
        parts.append(f"- **{role_label}**: {msg.get('text', '')}")
    return "\n".join(parts)


def build_inventory_characters_block(characters: list | None) -> str:
    """director_plan.j2 — characters 인벤토리."""
    if not characters:
        return ""

    def _attr(obj: object, key: str, default: object = "") -> object:
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    parts = ["\n## Available Inventory", f"\n### Characters ({len(characters)}\uba85)"]
    for char in characters:
        cid = _attr(char, "id", "?")
        name = _attr(char, "name", "")
        gender = _attr(char, "gender", "")
        usage = _attr(char, "usage_count", 0)
        appearance = _attr(char, "appearance_summary", "")
        has_lora = _attr(char, "has_lora", False)
        has_ref = _attr(char, "has_reference", False)

        star = " \u2b50\uc2dc\ub9ac\uc988 \uc8fc\uc5f0" if usage >= 10 else ""
        line = f"- **ID {cid}**: {name} ({gender}) \u2014 \ucd9c\uc5f0 {usage}\ud68c{star}"
        line += f"\n  - \ud2b9\uc9d5: {appearance or '\ubbf8\uc124\uc815'}"
        lora_str = "\uc788\uc74c" if has_lora else "\uc5c6\uc74c"
        ref_str = "\uc788\uc74c" if has_ref else "\uc5c6\uc74c"
        line += f"\n  - LoRA: {lora_str} / \ub808\ud37c\ub7f0\uc2a4: {ref_str}"
        parts.append(line)
    return "\n".join(parts)


def build_inventory_structures_block(structures: list | None) -> str:
    """director_plan.j2 — structures 블록."""
    if not structures:
        return ""

    def _attr(obj: object, key: str, default: object = "") -> object:
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    parts = [f"\n### Structures ({len(structures)}\uc885)"]
    for struct in structures:
        sid = _attr(struct, "id", "")
        name = _attr(struct, "name", "")
        tone = _attr(struct, "tone", "")
        req2 = _attr(struct, "requires_two_characters", False)
        suffix = " (2\uc778 \ud544\uc218)" if req2 else ""
        parts.append(f"- **{sid}**: {name} \u2014 {tone}{suffix}")
    return "\n".join(parts)


def build_inventory_styles_block(styles: list | None) -> str:
    """director_plan.j2 — styles 블록."""
    if not styles:
        return ""

    def _attr(obj: object, key: str, default: object = "") -> object:
        return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)

    parts = [f"\n### Styles ({len(styles)}\uc885)"]
    for sty in styles:
        sid = _attr(sty, "id", "")
        name = _attr(sty, "name", "")
        desc = _attr(sty, "description", "")
        desc_short = desc[:80] if desc else ""
        suffix = f" \u2014 {desc_short}" if desc_short else ""
        parts.append(f"- **ID {sid}**: {name}{suffix}")
    return "\n".join(parts)


def build_casting_guide() -> str:
    """director_plan.j2 — Casting Guide 섹션."""
    return (
        "\n\n## Casting Guide\n"
        "\uc544\ub798 4\ub2e8\uacc4\ub85c \ucd5c\uc801\uc758 \uce90\uc2a4\ud305\uc744 \ucd94\ucc9c\ud558\uc138\uc694:\n"
        "1. **\ud1a0\ud53d \ubd84\uc11d**: \uc8fc\uc81c\uc758 \ud575\uc2ec \uac10\uc815\uacfc \uc7a5\ub974\ub97c \ud30c\uc545\ud558\uc138\uc694\n"
        "2. **\uad6c\uc870 \uc120\ud0dd**: 1\uc778 \ub3c5\ubc31 vs \ub300\ud654/\uac08\ub4f1\uc5d0 \ub530\ub77c monologue, dialogue, narrated_dialogue, confession \uc911 \uc120\ud0dd\n"
        "3. **\uce90\ub9ad\ud130 \uc120\ud0dd** (\uac00\uc7a5 \uc911\uc694):\n"
        "   - **1\uc21c\uc704: \uce90\ub9ad\ud130 \uc131\uaca9\xb7\ubd84\uc704\uae30 \uc801\ud569\uc131**\n"
        "   - **2\uc21c\uc704: \uc0ac\uc6a9 \ud69f\uc218** \u2014 \uc2dc\ub9ac\uc988\uc758 \uac04\ud310\uc774\ubbc0\ub85c \uc801\uadf9 \ud65c\uc6a9\n"
        "   - **3\uc21c\uc704: LoRA \ubcf4\uc720** \u2014 \ud544\uc218 \uc870\uac74\uc740 \uc544\ub2d8\n"
        "   - **\ub2e4\uc591\uc131 \uc6d0\uce59**: \ub9e4\ubc88 \uac19\uc740 \uce90\ub9ad\ud130\ub97c \ubf51\uc9c0 \ub9c8\uc138\uc694\n"
        "   - **dialogue/narrated_dialogue \uc120\ud0dd \uc2dc**: \ubc18\ub4dc\uc2dc \uc11c\ub85c \ub2e4\ub978 2\uba85\n"
        "4. **ID \uad50\ucc28\uac80\uc99d**: \uce90\ub9ad\ud130 ID\uc640 \uc774\ub984\uc744 \ubc18\ub4dc\uc2dc \ud568\uaed8 \uae30\uc7ac\ud558\uc138\uc694"
    )


def build_casting_json_section(has_characters: bool) -> str:
    """director_plan.j2 — JSON 예시 내 casting 블록."""
    if not has_characters:
        return ""
    return (
        ',\n    "casting": {\n'
        '        "character_a_id": 1,\n'
        '        "character_a_name": "\uce90\ub9ad\ud130A \uc774\ub984 (ID\uc640 \ubc18\ub4dc\uc2dc \uc77c\uce58)",\n'
        '        "character_b_id": 2,\n'
        '        "character_b_name": "\uce90\ub9ad\ud130B \uc774\ub984 (dialogue/narrated_dialogue \uad6c\uc870 \uc2dc \ud544\uc218, 1\uc778 \uad6c\uc870\uba74 null)",\n'
        '        "structure": "dialogue",\n'
        '        "style_profile_id": null,\n'
        '        "reasoning": "\uc774 \uce90\ub9ad\ud130/\uad6c\uc870/\uc2a4\ud0c0\uc77c\uc744 \ucd94\ucc9c\ud558\ub294 \uadfc\uac70 (\ud55c\uad6d\uc5b4)"\n'
        "    }"
    )


# -- scriptwriter.j2 빌더 --

def build_scriptwriter_characters_block(characters: dict | None, character_name: str | None) -> str:
    """scriptwriter.j2 — ``{% for speaker, char in characters.items() %}``."""
    if characters:
        parts = []
        for speaker, char in characters.items():
            name = char.get("name", "") if isinstance(char, dict) else getattr(char, "name", "")
            parts.append(f'- Speaker "{speaker}": {name}')
        return "\n".join(parts)
    if character_name:
        return f"Name: {character_name}"
    return ""


def build_structure_rules_block(structure: str) -> str:
    """scriptwriter.j2 — structure별 규칙."""
    base = f"- Structure: {structure}"
    if structure == "Monologue":
        return f'{base}\n- Speaker: Always "A" (single narrator)'
    if structure == "Dialogue":
        return (
            f"{base}\n"
            '- Speakers: "A" and "B" (two characters in conversation)\n'
            "- Distribution: A and B must appear roughly equally. Both MUST have at least 1 scene.\n"
            "- Alternation pattern: A \u2192 B \u2192 A \u2192 B (avoid consecutive same-speaker scenes)"
        )
    if structure == "Narrated Dialogue":
        return (
            f"{base}\n"
            '- Speakers: "Narrator" for narration, "A"/"B" for dialogue\n'
            "- Distribution: ~\u2153 Narrator, ~\u2153 A, ~\u2153 B. ALL THREE must appear at least once.\n"
            "- Alternation pattern: Narrator \u2192 A \u2192 B \u2192 Narrator \u2192 A \u2192 B\n"
            '- IMPORTANT: "Narrator" scenes are background/environment description scenes.\n'
            "- Narrator typically opens (scene 0) to set the stage, and may close the story."
        )
    return base


def build_korean_rules_block(language: str) -> str:
    """scriptwriter.j2 — 한국어 전용 규칙."""
    if language != "Korean":
        return ""
    return (
        "  6. **\ud55c\uad6d\uc5b4 \ub9de\ucda4\ubc95 \ud544\uc218 \uac80\uc99d**:\n"
        '     - \ud3f0\ud2b8 \ub80c\ub354\ub9c1 \uc624\ub958 \ubc29\uc9c0\ub97c \uc704\ud574 **\ud45c\uc900\uc5b4**\ub9cc \uc0ac\uc6a9\n'
        '     - \ube44\ud45c\uc900\uc5b4, \uc778\ud130\ub137 \uc2e0\uc870\uc5b4 \uc808\ub300 \uc0ac\uc6a9 \uae08\uc9c0\n'
        "     - \ubaa8\ub4e0 \ubb38\uc7a5\uc744 \uc18c\ub9ac \ub0b4\uc5b4 \uc77d\uc5c8\uc744 \ub54c \uc790\uc5f0\uc2a4\ub7ec\uc6b4\uc9c0 \ud655\uc778\n"
        "     - \ubc1b\uce68 \ud0c8\ub77d/\uc624\ud0c8\uc790 \uc5c6\ub294\uc9c0 \uae00\uc790 \ub2e8\uc704\ub85c \uc810\uac80\n"
        "  7. **\ud55c\uad6d\uc5b4 \ubb38\uc7a5 \ud488\uc9c8**:\n"
        "     - \uac19\uc740 \ubb38\uc7a5 \uad6c\uc870 \uc5f0\uc18d \ubc18\ubcf5 \uae08\uc9c0\n"
        "     - \uad6c\uc5b4\uccb4\uc640 \ubb38\uc5b4\uccb4 \ud63c\uc6a9 \uae08\uc9c0\n"
        "  8. **\uc21f\ud3fc \ub3c4\ud30c\ubbfc \ubb38\ubc95 (CRITICAL)**:\n"
        "     - 1\ubb38\uc7a5 \u2264 15\uc790 \uad8c\uc7a5\n"
        '     - \uac10\ud0c4\uc0ac/\uc758\uc131\uc5b4 \uc801\uadf9 \ud65c\uc6a9: "\ud5d0", "\ubbf8\ucce4\ub2e4", "\uc18c\ub984"\n'
        "     - \uc9c1\uc811 \ud654\ubc95 > \uac04\uc811 \ud654\ubc95\n"
        "  9. **AI \ub9d0\ud22c \uc808\ub300 \uae08\uc9c0 (CRITICAL)**:\n"
        '     - \uae08\uc9c0 \uc5b4\ubbf8: "~\uc785\ub2c8\ub2e4", "~\ud558\uc8e0", "~\uc778\ub370\uc694"\n'
        '     - \uae08\uc9c0 \ud45c\ud604: "\ub180\ub77c\uc6b4 \uc0ac\uc2e4", "\uc5ec\ub7ec\ubd84"\n'
        "     - \ud544\uc218 \ud1a4: \uce5c\uad6c\ud55c\ud14c \uc598\uae30\ud558\ub4ef \ub0a0\uac83\uc758 \uad6c\uc5b4\uccb4"
    )


def build_korean_critical_hint(language: str) -> str:
    """scriptwriter.j2 — 한국어 CRITICAL 힌트."""
    if language != "Korean":
        return ""
    return "\n\ubc18\ub4dc\uc2dc \ubaa8\ub4e0 \ub300\uc0ac\uc640 \uc124\uba85\uc744 \ud55c\uad6d\uc5b4\ub85c \uc791\uc131\ud558\uc138\uc694. \uc601\uc5b4 \uc0ac\uc6a9 \uae08\uc9c0."


def build_output_format_block(structure: str) -> str:
    """scriptwriter.j2 — structure별 JSON 예시."""
    if structure == "Narrated Dialogue":
        return (
            '    {"order": 0, "script": "\ub098\ub808\uc774\uc158 \ud14d\uc2a4\ud2b8", "speaker": "Narrator", "duration": 2.5, "speakable": true},\n'
            '    {"order": 1, "script": "A \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "A", "duration": 3.0, "speakable": true},\n'
            '    {"order": 2, "script": "B \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "B", "duration": 3.0, "speakable": true}'
        )
    if structure == "Dialogue":
        return (
            '    {"order": 0, "script": "A \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "A", "duration": 3.0, "speakable": true},\n'
            '    {"order": 1, "script": "B \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "B", "duration": 3.0, "speakable": true}'
        )
    return '    {"order": 0, "script": "\ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "A", "duration": 2.5, "speakable": true}'


# -- writer_planning.j2 빌더 --

def build_scene_range_text(duration: int, structure: str) -> str:
    """writer_planning.j2 — 씬 개수 범위 계산 (Jinja2 수식 대체)."""
    try:
        from services.storyboard.helpers import calculate_max_scenes, calculate_min_scenes
        min_s = calculate_min_scenes(duration, structure)
        max_s = calculate_max_scenes(duration, structure)
    except Exception:
        if structure in ("Dialogue", "Narrated Dialogue"):
            min_s = max(3, round(duration / 6))
            max_s = round(duration / 4)
        else:
            min_s = round(duration / 3)
            max_s = round(duration / 2)
    return f"{min_s}-{max_s}"
