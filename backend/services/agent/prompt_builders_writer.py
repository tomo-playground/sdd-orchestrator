"""Writer/Script Prompt Builders -- scriptwriter, tts_designer, sound_designer, writer_planning.

prompt_builders_b.py에서 분리된 Writer/Script 관련 빌더 함수.
prompt_builders.py에서 re-export되어 기존 import를 유지한다.
"""

from __future__ import annotations

from config import TONE_HINTS

# -- tts_designer 빌더 --


def build_tts_characters_block(characters: list[dict] | None) -> str:
    """tts_designer -- ``{% for char in characters %}``."""
    if not characters:
        return ""
    parts = []
    for char in characters:
        line = (
            f"- **Speaker {char.get('speaker', '?')}** ({char.get('name', '')}): Gender={char.get('gender', 'female')}"
        )
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
    """tts_designer -- ``{% if director_plan and director_plan.target_emotion %}``."""
    if not director_plan:
        return ""
    emotion = director_plan.get("target_emotion", "")
    if not emotion:
        return ""
    return f"\n\n## Target Emotion (from Director)\n**{emotion}**\nAll voice designs should align with this overall emotional direction."


def build_emotional_arc_section(writer_plan: dict | None) -> str:
    """tts_designer / sound_designer -- ``{% if writer_plan.emotional_arc %}``."""
    if not writer_plan:
        return ""
    arc = writer_plan.get("emotional_arc")
    if not arc:
        return ""
    arc_str = " \u2192 ".join(str(e) for e in arc)
    return f"\n\n## Emotional Arc (from Writer Plan)\n{arc_str}"


# -- sound_designer 빌더 --


def build_sound_emotional_arc_section(writer_plan: dict | None) -> str:
    """sound_designer -- 감정 곡선 + BGM 안내."""
    if not writer_plan:
        return ""
    arc = writer_plan.get("emotional_arc")
    if not arc:
        return ""
    arc_str = " \u2192 ".join(str(e) for e in arc)
    return f"\n\n## Emotional Arc (from Writer Plan)\n{arc_str}\nThe BGM mood should complement this emotional progression."


def build_language_hint(language: str) -> str:
    """sound_designer -- ``{% if language == 'Korean' %}``."""
    if language == "korean":
        return "\nreasoning\uc740 \ubc18\ub4dc\uc2dc \ud55c\uad6d\uc5b4\ub85c \uc791\uc131\ud558\uc138\uc694."
    return ""


# -- director_plan 빌더 --


def build_chat_context_block(chat_context: list[dict] | None) -> str:
    """director_plan -- ``{% for msg in chat_context %}``."""
    if not chat_context:
        return ""
    parts = [
        "## User Intent Context (\uc0ac\uc804 \ub300\ud654 \uc774\ub825)",
        "",
        "\uc544\ub798\ub294 \uc0ac\uc6a9\uc790\uc640 \uc2dc\uc2a4\ud15c \uac04\uc758 \uc0ac\uc804 \ub300\ud654\uc785\ub2c8\ub2e4.",
        "\uc774 \ub9e5\ub77d\uc5d0\uc11c \uc0ac\uc6a9\uc790\uc758 **\uc758\ub3c4\uc640 \uc694\uad6c\uc0ac\ud56d**\uc744 \ud30c\uc545\ud558\uc5ec execution_plan\uc5d0 \ubc18\uc601\ud558\uc138\uc694.",
        "",
    ]
    for msg in chat_context:
        role_label = "\uc0ac\uc6a9\uc790" if msg.get("role") == "user" else "\uc2dc\uc2a4\ud15c"
        parts.append(f"- **{role_label}**: {msg.get('text', '')}")
    return "\n".join(parts)


# -- scriptwriter 빌더 --


def build_scriptwriter_characters_block(characters: dict | None, character_name: str | None) -> str:
    """scriptwriter -- ``{% for speaker, char in characters.items() %}``."""
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
    """scriptwriter -- structure별 규칙."""
    base = f"- Structure: {structure}"
    if structure == "monologue":
        return f'{base}\n- Speaker: Always "A" (single narrator)'
    if structure == "dialogue":
        return (
            f"{base}\n"
            '- Speakers: "A" and "B" (two characters in conversation)\n'
            "- Distribution: A and B must appear roughly equally. Both MUST have at least 1 scene.\n"
            "- Alternation pattern: A \u2192 B \u2192 A \u2192 B (avoid consecutive same-speaker scenes)"
        )
    if structure == "narrated_dialogue":
        return (
            f"{base}\n"
            '- Speakers: "Narrator" for narration, "A"/"B" for dialogue\n'
            "- Distribution: ~\u2153 Narrator, ~\u2153 A, ~\u2153 B. ALL THREE must appear at least once.\n"
            "- Alternation pattern: Narrator \u2192 A \u2192 B \u2192 Narrator \u2192 A \u2192 B\n"
            '- IMPORTANT: "Narrator" scenes are background/environment description scenes.\n'
            "- Narrator typically opens (scene 0) to set the stage, and may close the story."
        )
    return base


def build_tone_hint_block(tone: str) -> str:
    """scriptwriter -- tone별 힌트."""
    hint = TONE_HINTS.get(tone, "")
    if not hint:
        return f"- Tone: {tone}"
    return f"- Tone: {tone}\n- {hint}"


def build_korean_rules_block(language: str) -> str:
    """scriptwriter -- 한국어 전용 규칙."""
    if language != "korean":
        return ""
    return (
        "  6. **\ud55c\uad6d\uc5b4 \ub9de\ucda4\ubc95 \ud544\uc218 \uac80\uc99d**:\n"
        "     - \ud3f0\ud2b8 \ub80c\ub354\ub9c1 \uc624\ub958 \ubc29\uc9c0\ub97c \uc704\ud574 **\ud45c\uc900\uc5b4**\ub9cc \uc0ac\uc6a9\n"
        "     - \ube44\ud45c\uc900\uc5b4, \uc778\ud130\ub137 \uc2e0\uc870\uc5b4 \uc808\ub300 \uc0ac\uc6a9 \uae08\uc9c0\n"
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
        "     - \ud544\uc218 \ud1a4: \uce5c\uad6c\ud55c\ud14c \uc598\uae30\ud558\ub4ef \ub0a0\uac83\uc758 \uad6c\uc5b4\uccb4\n"
        "  10. **TTS \ub0ad\ub3c5 \uc790\uc5f0\uc2a4\ub7ec\uc6c0 (CRITICAL)**:\n"
        "     - \ubaa8\ub4e0 \ubb38\uc7a5\uc744 **\uc18c\ub9ac \ub0b4\uc5b4 \uc77d\uc5c8\uc744 \ub54c** \uc785\uc5d0 \uc798 \ubd99\uc5b4\uc57c \ud55c\ub2e4\n"
        "     - \uc870\uc0ac/\uc5b4\ubbf8\uac00 \uc2e4\uc81c \ub300\ud654\uc5d0\uc11c \uc4f0\uc774\ub294 \ud615\ud0dc\uc5ec\uc57c \ud55c\ub2e4\n"
        '     - \u274c \uc5b4\uc0c9\ud55c \uc870\uc0ac: "\ubfcc\ub85c" \u2192 \u2705 "\ubfcc\ub77c\uace0"\n'
        '     - \u274c \ucd95\uc57d \ub204\ub77d: "\uadf8\uac83\uc740" \u2192 \u2705 "\uadf8\uac74"\n'
        '     - \u274c \uacfc\ub3c4\ud55c \uc874\ub313\ub9d0: "\ud558\uc168\uc2b5\ub2c8\ub2e4" \u2192 \u2705 "\ud588\uc5b4" / "\ud588\uac70\ub4e0"\n'
        '     - \u274c \ubd80\uc790\uc5f0 \uc5f0\uacb0: "\uadf8\ub9ac\uace0 \ub098\uc11c" \u2192 \u2705 "\uadf8\ub7ec\ub2e4\uac00" / "\uadfc\ub370"\n'
        "     - \ud55c \ud638\ud761\uc5d0 \uc77d\uae30 \uc5b4\ub824\uc6b4 \uae34 \ubb38\uc7a5(40\uc790 \ucd08\uacfc) \uae08\uc9c0\n"
        "  11. **\uc494 \uac04 \ub9e5\ub77d \uc5f0\uacb0 (CRITICAL)**:\n"
        "     - \uac01 \uc494\uc758 **\ub9c8\uc9c0\ub9c9 \uac10\uc815**\uc774 \ub2e4\uc74c \uc494\uc758 **\uccab \uac10\uc815**\uacfc \uc790\uc5f0\uc2a4\ub7fd\uac8c \uc774\uc5b4\uc838\uc57c \ud55c\ub2e4\n"
        "     - \uae09\uaca9\ud55c \uac10\uc815 \uc804\ud658 \uae08\uc9c0 (\uc2ac\ud514 \u2192 \uac11\uc790\uae30 \uae30\uc068 \u2717)\n"
        '     - \ud654\uc81c \uc804\ud658 \uc2dc \uc811\uc18d \ud45c\ud604 \uc0ac\uc6a9: "\uadfc\ub370", "\uadf8\ub7ec\ub2e4\uac00", "\ud55c\ud3b8", "\uadf8\ub54c"\n'
        "     - \uc5f0\uc18d \uc494\uc5d0\uc11c **\uac19\uc740 \uc885\uacb0\uc5b4\ubbf8 3\ud68c \uc774\uc0c1 \ubc18\ubcf5** \uae08\uc9c0 (~\uac70\ub4e0, ~\uac70\ub4e0, ~\uac70\ub4e0 \u2717)\n"
        "     - \uc5f0\uc18d \uc494\uc5d0\uc11c **\uac19\uc740 \uc811\uc18d\uc0ac \uc5f0\uc18d \uc0ac\uc6a9** \uae08\uc9c0 (\uadf8\ub798\uc11c, \uadf8\ub798\uc11c \u2717)"
    )


def build_korean_critical_hint(language: str) -> str:
    """scriptwriter -- 한국어 CRITICAL 힌트."""
    if language != "korean":
        return ""
    return "\n\ubc18\ub4dc\uc2dc \ubaa8\ub4e0 \ub300\uc0ac\uc640 \uc124\uba85\uc744 \ud55c\uad6d\uc5b4\ub85c \uc791\uc131\ud558\uc138\uc694. \uc601\uc5b4 \uc0ac\uc6a9 \uae08\uc9c0."


def build_output_format_block(structure: str) -> str:
    """scriptwriter -- structure별 JSON 예시."""
    if structure == "narrated_dialogue":
        return (
            '    {"order": 0, "script": "\ub098\ub808\uc774\uc158 \ud14d\uc2a4\ud2b8", "speaker": "Narrator", "duration": 2.5, "speakable": true},\n'
            '    {"order": 1, "script": "A \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "A", "duration": 3.0, "speakable": true},\n'
            '    {"order": 2, "script": "B \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "B", "duration": 3.0, "speakable": true}'
        )
    if structure == "dialogue":
        return (
            '    {"order": 0, "script": "A \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "A", "duration": 3.0, "speakable": true},\n'
            '    {"order": 1, "script": "B \ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "B", "duration": 3.0, "speakable": true}'
        )
    return '    {"order": 0, "script": "\ub300\uc0ac \ud14d\uc2a4\ud2b8", "speaker": "A", "duration": 2.5, "speakable": true}'


# -- writer_planning 빌더 --


def build_scene_range_text(duration: int, structure: str) -> str:
    """writer_planning -- 씬 개수 범위 계산 (Jinja2 수식 대체)."""
    try:
        from services.storyboard.helpers import calculate_max_scenes, calculate_min_scenes

        min_s = calculate_min_scenes(duration, structure)
        max_s = calculate_max_scenes(duration, structure)
    except Exception:
        if structure in ("dialogue", "narrated_dialogue"):
            min_s = max(3, round(duration / 6))
            max_s = round(duration / 4)
        else:
            min_s = round(duration / 3)
            max_s = round(duration / 2)
    return f"{min_s}-{max_s}"
