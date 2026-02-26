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
    # English
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
    # Korean (한국어 스토리보드에서 Gemini가 한국어 emotion을 생성하는 경우)
    "기쁨": "smile",
    "행복": "smile",
    "즐거움": "smile",
    "기대감": "excited",
    "기대": "excited",
    "흥분": "excited",
    "자신감": "smirk",
    "자부심": "grin",
    "슬픔": "sad",
    "우울": "sad",
    "우울함": "sad",
    "외로움": "sad",
    "고독": "sad",
    "고독감": "sad",
    "소외감": "sad",
    "비참함": "crying",
    "비통": "crying",
    "불안": "nervous",
    "불안감": "nervous",
    "초조함": "nervous",
    "초조": "nervous",
    "긴장": "nervous",
    "긴장감": "nervous",
    "두려움": "scared",
    "공포": "scared",
    "무서움": "frightened",
    "분노": "angry",
    "화남": "angry",
    "짜증": "frustrated",
    "답답함": "frustrated",
    "답답": "frustrated",
    "놀라움": "surprised",
    "충격": "shocked",
    "경악": "shocked",
    "평온": "expressionless",
    "차분": "expressionless",
    "그리움": "sad",
    "향수": "sad",
    "회상": "expressionless",
    "생각": "serious",
    "고민": "serious",
    "걱정": "nervous",
    "결심": "serious",
    "결의": "serious",
    "당황": "embarrassed",
    "부끄러움": "embarrassed",
    "수줍음": "shy",
    "졸림": "sleepy",
    "피곤": "tired",
    "씁쓸함": "sad",
    "씁쓸": "sad",
    "허탈": "expressionless",
    "공허함": "expressionless",
    "공허": "expressionless",
    "허무": "expressionless",
    "자책": "sad",
    "후회": "sad",
    "의아함": "confused",
    "의아": "confused",
    "혼란": "confused",
    "호기심": "curious",
    "궁금": "curious",
    "감동": "crying",
    "감사": "smile",
    "희망": "smile",
    # 복합 감정 (Gemini가 생성하는 구문형 emotion)
    "공감 유도": "smile",
    "공감": "smile",
    "무반응": "expressionless",
    "자기 검열": "nervous",
    "자기검열": "nervous",
    "미묘한 관찰": "serious",
    "내적 갈등": "furrowed_brow",
    "내적갈등": "furrowed_brow",
    "체념": "expressionless",
    "냉소": "smirk",
    "무관심": "expressionless",
    "경계": "serious",
    "관찰": "serious",
    "동경": "smile",
    "감탄": "surprised",
}


# ── emotion → mood 매핑 (빈 mood 자동 생성) ──────────────────────────
EMOTION_TO_MOOD: dict[str, str] = {
    # English
    "happy": "cheerful",
    "joy": "cheerful",
    "excited": "bright",
    "sad": "melancholic",
    "melancholy": "melancholic",
    "lonely": "lonely",
    "anxious": "tense",
    "nervous": "tense",
    "scared": "dark",
    "angry": "intense",
    "nostalgic": "nostalgic",
    "peaceful": "peaceful",
    "calm": "serene",
    "hopeful": "warm",
    "bittersweet": "bittersweet",
    "tense": "tense",
    "determined": "dramatic",
    # Korean
    "기쁨": "cheerful",
    "행복": "warm",
    "기대감": "bright",
    "기대": "bright",
    "슬픔": "melancholic",
    "우울": "gloomy",
    "외로움": "lonely",
    "소외감": "lonely",
    "불안": "tense",
    "불안감": "tense",
    "긴장": "tense",
    "공포": "dark",
    "분노": "intense",
    "짜증": "intense",
    "놀라움": "dramatic",
    "충격": "dramatic",
    "평온": "serene",
    "그리움": "nostalgic",
    "향수": "nostalgic",
    "씁쓸함": "bittersweet",
    "씁쓸": "bittersweet",
    "허탈": "melancholic",
    "공허": "gloomy",
    "의아함": "mysterious",
    "호기심": "mysterious",
    "공감 유도": "warm",
    "무반응": "gloomy",
    "자기 검열": "tense",
    "미묘한 관찰": "mysterious",
    "내적 갈등": "tense",
    "체념": "somber",
}


def derive_expression_from_emotion(emotion: str | list | None) -> str | None:
    """emotion 문자열로부터 적절한 expression 태그를 파생한다."""
    s = _coerce_str(emotion)
    return EMOTION_TO_EXPRESSION.get(s.lower().strip()) if s else None


def derive_mood_from_emotion(emotion: str | list | None) -> str | None:
    """emotion 문자열로부터 적절한 mood 태그를 파생한다."""
    s = _coerce_str(emotion)
    return EMOTION_TO_MOOD.get(s.lower().strip()) if s else None


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
                del ctx[field]  # None이 아닌 키 삭제 → _inject_default에서 is None 체크 통과

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
            del ctx["mood"]


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
