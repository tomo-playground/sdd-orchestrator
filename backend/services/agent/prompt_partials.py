"""프롬프트 파셜 — {% include %} 대체 Python 렌더러.

Jinja2 {% include %} 의존성을 제거하여 LangFuse from_string() 호환.
정적 텍스트는 상수, 동적 로직은 함수로 제공.
호출부에서 template_vars에 렌더 결과를 주입한다.
"""

# ── 정적 파셜 (변수 없음) ──────────────────────────────────

IMAGE_PROMPT_KO_RULES = """\
   - image_prompt_ko: ONE natural Korean sentence (subject + verb/descriptive phrase, NOT comma-separated tags)
     * Describe ONLY: action, emotion, situation, environment
     * EXCLUDE character appearance (hair, eyes, clothing, style) — already injected by Character Identity system
     * GOOD: "밤에 부엌에서 땀 흘리며 서 있는 모습"
     * GOOD: "어색하게 웃으며 상대를 바라보는 모습"
     * GOOD: "햇살이 들어오는 카페 창가" (environment-only scene)
     * BAD: "플랫 컬러 스타일의 갈색 머리 소녀가 흰 셔츠를 입고 미소 지으며 서 있다." (identity included)
     * BAD: "미소, 서있는, 부엌, 밤" (comma-separated tags)
     * BAD: "미래주의_도시, 실험실, 로봇, 전선" (Korean-translated Danbooru tags)
     * Pattern: "[장소/상황]에서 [감정/동작]하는 모습" or "[분위기] [장소 묘사]"
     * **한국어 품질**: 모든 글자가 실제 한국어 단어인지 반드시 확인. 의미 없는 글자 조합 금지 (예: "훈기심"→"호기심", "낮반한"→"낯선", "가리타리"→"가로등")\
"""

EMOTION_CONSISTENCY_RULES = """\
## EMOTION CONSISTENCY RULE (MANDATORY)

Expression tags and mood/atmosphere tags MUST have consistent emotional direction:
- POSITIVE expressions (smile, happy, grin, laughing) → pair with POSITIVE moods (romantic, cozy, cheerful, warm)
- NEGATIVE expressions (crying, angry, sad, frown) → pair with NEGATIVE moods (melancholic, horror, gloomy, tense)
- NEUTRAL expressions (serious, blank_stare) → can pair with ANY mood

FORBIDDEN combinations (will be auto-rejected):
- smile + melancholic
- crying + romantic
- angry + cozy
- happy + horror
- laughing + gloomy

If a scene requires emotional contrast, use NEUTRAL expressions instead of mixing opposites.\
"""


# ── 동적 파셜 (변수 필요) ──────────────────────────────────


def render_selected_concept(selected_concept: dict | None) -> str:
    """_partials/selected_concept 대체."""
    if not selected_concept:
        return ""
    title = selected_concept.get("title", "")
    concept = selected_concept.get("concept", "")
    strengths = selected_concept.get("strengths", [])

    lines = [
        "",
        "=== SELECTED CONCEPT (MANDATORY — DO NOT IGNORE) ===",
        f"Title: {title}",
        f"Concept: {concept}",
    ]
    if strengths:
        lines.append(f"Strengths: {', '.join(str(s) for s in strengths)}")
    lines.extend(
        [
            "",
            "YOU MUST follow this concept precisely:",
            '- The script MUST tell the story described in "Concept" above',
            "- The title sets the theme — every scene must serve this theme",
            "- Do NOT invent a different story, angle, or theme",
            "- Deviating from this concept is a CRITICAL ERROR",
            "=== END SELECTED CONCEPT ===",
        ]
    )
    return "\n".join(lines)


def render_character_profile(ctx: dict | None, speaker: str | None = None) -> str:
    """_partials/character_profile 대체.

    Args:
        ctx: character_context dict (name, gender, description, costume_tags)
        speaker: "speaker_1", "speaker_2", or None (monologue)
    """
    if not ctx:
        return ""

    name = ctx.get("name", "")
    gender = ctx.get("gender", "")
    description = ctx.get("description", "")
    costume_tags = ctx.get("costume_tags", [])

    header = f"SPEAKER {speaker} - " if speaker else ""
    lines = [
        f"{header}CHARACTER PROFILE:",
        f"Character Name: {name}",
        f"Gender: {gender}",
    ]
    if description:
        lines.append(f"Personality/Background: {description}")
    if costume_tags:
        lines.append("Costume Reference (for script context only — do NOT include in image_prompt):")
        lines.append(", ".join(str(t) for t in costume_tags))
    lines.extend(
        [
            "",
            f"⚠️ SCRIPT RULES for {name}:",
            f"- Write dialogue/narration that matches {gender} character's natural speech patterns",
        ]
    )
    if description:
        lines.append(f"- Reflect this character's personality: {description}")
    lines.append("- The character's gender and personality MUST be consistent across ALL scenes")
    return "\n".join(lines)


def render_allowed_tags(allowed_tags: dict[str, list[str]]) -> str:
    """_partials/allowed_tags_by_category 대체.

    Args:
        allowed_tags: {"camera": [...], "expression": [...], ...}
    """
    sections = []
    _CATEGORIES = [
        ("camera", "Allowed Camera Tags (use ONLY these for camera category)"),
        ("expression", "Allowed Expression Tags (use ONLY these for expression category)"),
        ("action", "Allowed Action Tags (use ONLY these for action/pose category)"),
        ("environment", "Allowed Environment Tags (use ONLY these for environment/location category)"),
        ("mood", "Allowed Mood Tags (use ONLY these for mood/atmosphere category)"),
    ]
    for key, label in _CATEGORIES:
        tags = allowed_tags.get(key, [])
        if tags:
            sections.append(f"\n{label}:\n{', '.join(str(t) for t in tags)}")
    return "\n".join(sections)
