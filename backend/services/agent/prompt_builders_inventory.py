"""Inventory Prompt Builders -- director_plan 인벤토리 + 캐스팅 가이드.

prompt_builders_b.py에서 분리된 Inventory 관련 빌더 함수.
prompt_builders.py에서 re-export되어 기존 import를 유지한다.
"""

from __future__ import annotations


def build_inventory_characters_block(characters: list | None) -> str:
    """director_plan -- characters 인벤토리."""
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
    """director_plan -- structures 블록."""
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
    """director_plan -- styles 블록."""
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
    """director_plan -- Casting Guide 섹션."""
    return (
        "\n\n## Casting Guide\n"
        "\uc544\ub798 4\ub2e8\uacc4\ub85c \ucd5c\uc801\uc758 \uce90\uc2a4\ud305\uc744 \ucd94\ucc9c\ud558\uc138\uc694:\n"
        "1. **\ud1a0\ud53d \ubd84\uc11d**: \uc8fc\uc81c\uc758 \ud575\uc2ec \uac10\uc815\uacfc \uc7a5\ub974\ub97c \ud30c\uc545\ud558\uc138\uc694\n"
        "2. **\uad6c\uc870 \uc120\ud0dd**: 1\uc778 \ub3c5\ubc31 vs \ub300\ud654/\uac08\ub4f1\uc5d0 \ub530\ub77c monologue, dialogue, narrated_dialogue\uc911 \uc120\ud0dd\n"
        "3. **\uce90\ub9ad\ud130 \uc120\ud0dd** (\uac00\uc7a5 \uc911\uc694):\n"
        "   - **1\uc21c\uc704: \uce90\ub9ad\ud130 \uc131\uaca9\xb7\ubd84\uc704\uae30 \uc801\ud569\uc131**\n"
        "   - **2\uc21c\uc704: \uc0ac\uc6a9 \ud69f\uc218** \u2014 \uc2dc\ub9ac\uc988\uc758 \uac04\ud310\uc774\ubbc0\ub85c \uc801\uadf9 \ud65c\uc6a9\n"
        "   - **3\uc21c\uc704: LoRA \ubcf4\uc720** \u2014 \ud544\uc218 \uc870\uac74\uc740 \uc544\ub2d8\n"
        "   - **\ub2e4\uc591\uc131 \uc6d0\uce59**: \ub9e4\ubc88 \uac19\uc740 \uce90\ub9ad\ud130\ub97c \ubf51\uc9c0 \ub9c8\uc138\uc694\n"
        "   - **dialogue/narrated_dialogue \uc120\ud0dd \uc2dc**: \ubc18\ub4dc\uc2dc \uc11c\ub85c \ub2e4\ub978 2\uba85\n"
        "4. **ID \uad50\ucc28\uac80\uc99d**: \uce90\ub9ad\ud130 ID\uc640 \uc774\ub984\uc744 \ubc18\ub4dc\uc2dc \ud568\uaed8 \uae30\uc7ac\ud558\uc138\uc694"
    )


def build_casting_json_section(has_characters: bool) -> str:
    """director_plan -- JSON 예시 내 casting 블록."""
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
