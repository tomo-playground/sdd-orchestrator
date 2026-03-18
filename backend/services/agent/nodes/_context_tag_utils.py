"""Context-tag 유틸리티 — emotion→expression 매핑, 카테고리 검증, 카메라 다양성."""

from __future__ import annotations

from config import logger


def _coerce_str(val: object) -> str:
    """Gemini가 리스트로 반환한 context_tags 값을 문자열로 정규화한다."""
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val) if val is not None else ""


# ── Phase A: Emotion Vocabulary (SSOT) ────────────────────────────────
# 유효한 emotion → (expression, mood) 매핑. Gemini 템플릿에서 이 목록만 허용.
# 새 emotion 추가 시 이 테이블 하나만 수정하면 expression/mood 모두 자동 파생.
EMOTION_VOCAB: dict[str, tuple[str, str]] = {
    # (emotion)         (expression,        mood)
    "happy": ("smile", "cheerful"),
    "excited": ("excited", "bright"),
    "proud": ("grin", "warm"),
    "confident": ("smirk", "dramatic"),
    "sad": ("sad", "melancholic"),
    "lonely": ("sad", "lonely"),
    "grieving": ("crying", "melancholic"),
    "anxious": ("nervous", "tense"),
    "nervous": ("nervous", "tense"),
    "scared": ("scared", "dark"),
    "angry": ("angry", "intense"),
    "frustrated": ("frustrated", "intense"),
    "surprised": ("surprised", "dramatic"),
    "shocked": ("shocked", "dramatic"),
    "calm": ("expressionless", "serene"),
    "peaceful": ("smile", "peaceful"),
    "nostalgic": ("sad", "nostalgic"),
    "reflective": ("expressionless", "serene"),
    "thoughtful": ("serious", "mysterious"),
    "tense": ("serious", "tense"),
    "determined": ("serious", "dramatic"),
    "embarrassed": ("embarrassed", "warm"),
    "shy": ("shy", "warm"),
    "hopeful": ("smile", "warm"),
    "bittersweet": ("sad", "bittersweet"),
    "tired": ("half-closed_eyes", "gloomy"),
    "confused": ("confused", "mysterious"),
    "guilty": ("sad", "melancholic"),
    "resigned": ("expressionless", "somber"),
    "contempt": ("smirk", "dark"),
}

# 파생 딕셔너리 (EMOTION_VOCAB에서 자동 생성)
EMOTION_TO_EXPRESSION: dict[str, str] = {k: v[0] for k, v in EMOTION_VOCAB.items()}
EMOTION_TO_MOOD: dict[str, str] = {k: v[1] for k, v in EMOTION_VOCAB.items()}

# 한국어 emotion → 영어 emotion 별칭 (Writer가 한국어 emotion을 생성하는 경우)
_KOREAN_EMOTION_ALIASES: dict[str, str] = {
    "기쁨": "happy",
    "행복": "happy",
    "즐거움": "happy",
    "기대감": "excited",
    "기대": "excited",
    "흥분": "excited",
    "자신감": "confident",
    "자부심": "proud",
    "슬픔": "sad",
    "우울": "sad",
    "우울함": "sad",
    "외로움": "lonely",
    "고독": "lonely",
    "소외감": "lonely",
    "비참함": "grieving",
    "비통": "grieving",
    "불안": "anxious",
    "불안감": "anxious",
    "초조": "anxious",
    "긴장": "anxious",
    "걱정": "anxious",
    "두려움": "scared",
    "공포": "scared",
    "분노": "angry",
    "화남": "angry",
    "짜증": "frustrated",
    "답답함": "frustrated",
    "답답": "frustrated",
    "놀라움": "surprised",
    "충격": "shocked",
    "경악": "shocked",
    "평온": "calm",
    "차분": "calm",
    "그리움": "nostalgic",
    "향수": "nostalgic",
    "생각": "thoughtful",
    "고민": "thoughtful",
    "결심": "determined",
    "결의": "determined",
    "당황": "embarrassed",
    "부끄러움": "embarrassed",
    "수줍음": "shy",
    "피곤": "tired",
    "졸림": "tired",
    "씁쓸함": "bittersweet",
    "씁쓸": "bittersweet",
    "허탈": "resigned",
    "공허": "resigned",
    "체념": "resigned",
    "자책": "guilty",
    "후회": "guilty",
    "의아함": "confused",
    "혼란": "confused",
    "호기심": "excited",
    "희망": "hopeful",
    "감동": "happy",
    "감사": "happy",
    "내적 갈등": "tense",
    "갈등": "tense",
}

# 별칭을 EMOTION_TO_EXPRESSION / EMOTION_TO_MOOD에 병합
for _ko, _en in _KOREAN_EMOTION_ALIASES.items():
    if _en in EMOTION_VOCAB:
        EMOTION_TO_EXPRESSION[_ko] = EMOTION_VOCAB[_en][0]
        EMOTION_TO_MOOD[_ko] = EMOTION_VOCAB[_en][1]

# 유효 emotion 셋 (템플릿 검증용)
VALID_EMOTIONS: frozenset[str] = frozenset(EMOTION_VOCAB.keys())


def _normalize_emotion(raw: str) -> str:
    """비표준 emotion을 EMOTION_VOCAB의 유효 값으로 정규화한다."""
    key = raw.lower().strip()
    # 1) 정확히 존재
    if key in EMOTION_VOCAB:
        return key
    # 2) 한국어 별칭
    alias = _KOREAN_EMOTION_ALIASES.get(key)
    if alias:
        return alias
    # 3) 부분 매칭 (예: "lonely_expression" → "lonely")
    for valid in EMOTION_VOCAB:
        if valid in key:
            return valid
    return key  # 매핑 불가 — 원본 반환 (fallback to default)


def derive_expression_from_emotion(emotion: str | list | None) -> str | None:
    """emotion 문자열로부터 적절한 expression 태그를 파생한다."""
    s = _coerce_str(emotion)
    if not s:
        return None
    normalized = _normalize_emotion(s)
    return EMOTION_TO_EXPRESSION.get(normalized)


def derive_mood_from_emotion(emotion: str | list | None) -> str | None:
    """emotion 문자열로부터 적절한 mood 태그를 파생한다."""
    s = _coerce_str(emotion)
    if not s:
        return None
    normalized = _normalize_emotion(s)
    return EMOTION_TO_MOOD.get(normalized)


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


# ── Phase B-2: Expression 단조로움 보정 ──────────────────────────────
# 한국어 스크립트 키워드 → emotion 추론 (Writer가 emotion 미생성 시 fallback)
_SCRIPT_EMOTION_HINTS: list[tuple[list[str], str]] = [
    (["어려워", "힘들", "고민", "걱정", "불안"], "anxious"),
    (["슬퍼", "슬프", "울", "눈물"], "sad"),
    (["화나", "짜증", "싫어", "미워"], "angry"),
    (["놀라", "충격", "헐"], "surprised"),
    (["감사", "고마워", "고맙"], "happy"),
    (["편하", "낫", "안심", "다행"], "calm"),
    (["긴장", "떨려", "초조"], "nervous"),
    (["부끄러", "창피", "민망"], "embarrassed"),
    (["피곤", "졸려", "지쳐"], "tired"),
    (["결심", "해보", "각오", "파이팅"], "determined"),
    (["그리워", "보고싶", "옛날"], "nostalgic"),
    (["무서워", "겁나", "두려"], "scared"),
]


def _infer_emotion_from_script(script: str) -> str | None:
    """한국어 스크립트에서 emotion을 추론한다 (keyword matching)."""
    if not script:
        return None
    for keywords, emotion in _SCRIPT_EMOTION_HINTS:
        if any(kw in script for kw in keywords):
            return emotion
    return None


def diversify_expressions(scenes: list[dict]) -> None:
    """캐릭터 씬의 expression 단조로움을 감지하고 스크립트 기반으로 보정한다.

    >60% 씬이 동일 expression이면:
    1. emotion이 없는 씬에 스크립트 키워드 기반 emotion 추론
    2. 추론된 emotion → expression 파생으로 교체
    """
    from collections import Counter

    char_scenes = [(i, s) for i, s in enumerate(scenes) if s.get("speaker") != "Narrator"]
    if len(char_scenes) < 3:
        return

    # 현재 expression 분포 확인
    expressions = []
    for _, s in char_scenes:
        ctx = s.get("context_tags") or {}
        expr = _coerce_str(ctx.get("expression"))
        expressions.append(expr)

    counts = Counter(expressions)
    dominant_expr, dominant_count = counts.most_common(1)[0]
    if dominant_count <= len(char_scenes) * 0.6:
        return  # 충분히 다양함

    logger.info(
        "[Finalize] Expression 단조로움 감지: '%s'가 %d/%d 씬 — 스크립트 기반 보정 시작",
        dominant_expr,
        dominant_count,
        len(char_scenes),
    )

    corrected = 0
    for _, scene in char_scenes:
        ctx = scene.get("context_tags")
        if not ctx:
            continue
        # emotion이 이미 있으면 건너뜀 (이미 _inject_default_context_tags에서 처리됨)
        if ctx.get("emotion"):
            continue
        current_expr = _coerce_str(ctx.get("expression"))
        if current_expr != dominant_expr:
            continue  # 이미 다른 expression이면 유지

        # 스크립트에서 emotion 추론
        script = scene.get("script", "")
        inferred = _infer_emotion_from_script(script)
        if not inferred:
            continue
        derived_expr = EMOTION_TO_EXPRESSION.get(inferred)
        if derived_expr and derived_expr != dominant_expr:
            ctx["emotion"] = inferred
            ctx["expression"] = derived_expr
            corrected += 1
            logger.info(
                "[Finalize] Scene '%s' → emotion=%s, expression=%s (was %s)",
                script[:20],
                inferred,
                derived_expr,
                dominant_expr,
            )

    if corrected:
        logger.info("[Finalize] Expression 보정 완료: %d씬 교체", corrected)
