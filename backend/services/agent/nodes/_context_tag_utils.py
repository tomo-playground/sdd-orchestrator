"""Context-tag 유틸리티 — emotion→expression 매핑, 카테고리 검증, 카메라 다양성."""

from __future__ import annotations

from config import logger


def _coerce_str(val: object) -> str:
    """Gemini가 리스트로 반환한 context_tags 값을 문자열로 정규화한다."""
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val) if val is not None else ""


# ── Phase A: emotion → expression 매핑 ────────────────────────────────
EMOTION_TO_EXPRESSION: dict[str, str] = {
    "happy": "smile",
    "joy": "smile",
    "cheerful": "smile",
    "excited": "excited",
    "proud": "grin",
    "confident": "smirk",
    "sad": "sad",
    "melancholy": "sad",
    "lonely": "sad",
    "grieving": "crying",
    "depressed": "sad",
    "fearful": "scared",
    "anxious": "nervous",
    "nervous": "nervous",
    "scared": "frightened",
    "terrified": "scared",
    "angry": "angry",
    "frustrated": "frustrated",
    "furious": "angry",
    "surprised": "surprised",
    "shocked": "shocked",
    "calm": "expressionless",
    "peaceful": "smile",
    "nostalgic": "sad",
    "reflective": "expressionless",
    "thoughtful": "serious",
    "tense": "serious",
    "determined": "serious",
    "embarrassed": "embarrassed",
    "shy": "shy",
    "sleepy": "sleepy",
    "tired": "tired",
    "bittersweet": "sad",
    "wistful": "sad",
    "hopeful": "smile",
}


def derive_expression_from_emotion(emotion: str | list | None) -> str | None:
    """emotion 문자열로부터 적절한 expression 태그를 파생한다."""
    s = _coerce_str(emotion)
    return EMOTION_TO_EXPRESSION.get(s.lower().strip()) if s else None


# ── Phase B: 카테고리 검증 ────────────────────────────────────────────
_CATEGORY_FIELDS = ("expression", "gaze", "pose")


def _get_valid_tags_for(field: str) -> frozenset[str]:
    """patterns.py CATEGORY_PATTERNS에서 해당 필드의 유효 태그셋을 가져온다."""
    from services.keywords.patterns import CATEGORY_PATTERNS

    return frozenset(CATEGORY_PATTERNS.get(field, []))


def validate_context_tag_categories(scenes: list[dict]) -> None:
    """expression/gaze/pose 값이 올바른 카테고리에 있는지 검증하고, 잘못 분류된 값을 재분류한다.

    mood 필드는 CATEGORY_PATTERNS["mood"]에 없으면 drop + 로그 경고.
    """
    from services.keywords.patterns import CATEGORY_PATTERNS

    valid_mood_tags = frozenset(CATEGORY_PATTERNS.get("mood", []))
    valid_by_field = {f: _get_valid_tags_for(f) for f in _CATEGORY_FIELDS}

    for i, scene in enumerate(scenes):
        ctx = scene.get("context_tags")
        if not ctx:
            continue

        # expression/gaze/pose 재분류
        misplaced: list[tuple[str, str]] = []  # (source_field, value)
        for field in _CATEGORY_FIELDS:
            raw = ctx.get(field)
            if not raw:
                continue
            val = _coerce_str(raw)
            ctx[field] = val  # list → str 정규화 반영
            norm = val.lower().strip()
            if norm not in valid_by_field[field]:
                misplaced.append((field, norm))
                ctx[field] = ""

        for source_field, val in misplaced:
            for target_field in _CATEGORY_FIELDS:
                if target_field == source_field:
                    continue
                if val in valid_by_field[target_field] and not ctx.get(target_field):
                    ctx[target_field] = val
                    logger.info(
                        "[Finalize] Scene %d: '%s' 재분류 %s → %s",
                        i,
                        val,
                        source_field,
                        target_field,
                    )
                    break
            else:
                logger.warning(
                    "[Finalize] Scene %d: '%s' (%s) 유효 카테고리 없음 → drop",
                    i,
                    val,
                    source_field,
                )

        # mood 검증
        mood = _coerce_str(ctx.get("mood"))
        if mood and mood.lower().strip() not in valid_mood_tags:
            logger.warning(
                "[Finalize] Scene %d: 비표준 mood '%s' → drop",
                i,
                mood,
            )
            ctx["mood"] = ""


# ── Phase C: 카메라 다양성 소프트 경고 ────────────────────────────────
def check_camera_diversity(scenes: list[dict]) -> None:
    """전체 씬의 >50%가 동일 카메라 앵글이면 logger.warning 출력."""
    if len(scenes) < 3:
        return

    from collections import Counter

    angles = []
    for scene in scenes:
        ctx = scene.get("context_tags") or {}
        cam = _coerce_str(ctx.get("camera") or ctx.get("camera_angle"))
        if cam:
            angles.append(cam.lower().strip())

    if not angles:
        return

    counts = Counter(angles)
    most_common_angle, most_common_count = counts.most_common(1)[0]
    if most_common_count > len(scenes) / 2:
        logger.warning(
            "[Finalize] 카메라 다양성 부족: '%s'가 %d/%d 씬 (%d%%)에서 반복",
            most_common_angle,
            most_common_count,
            len(scenes),
            int(most_common_count / len(scenes) * 100),
        )
