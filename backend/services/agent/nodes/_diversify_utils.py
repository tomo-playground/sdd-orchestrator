"""다양성 보정 유틸리티 — gaze, action, camera, pose 반복 감지 및 emotion 기반 교정.

_context_tag_utils.py에서 분리. 4개 diversify 함수가 공통 패턴(_diversify_context_field)을 공유.
"""

from __future__ import annotations

from collections import Counter

from config import DEFAULT_SPEAKER
from config import pipeline_logger as logger
from services.agent.nodes._context_tag_utils import (
    _KOREAN_EMOTION_ALIASES,
    _coerce_str,
    _normalize_emotion,
)


def _apply_korean_aliases(emotion_map: dict[str, str]) -> dict[str, str]:
    """Add Korean emotion aliases to an emotion map."""
    for ko, en in _KOREAN_EMOTION_ALIASES.items():
        if en in emotion_map and ko not in emotion_map:
            emotion_map[ko] = emotion_map[en]
    return emotion_map


# ── Emotion → Gaze 매핑 ──────────────────────────────────────────
EMOTION_TO_GAZE: dict[str, str] = {
    "sad": "looking_down",
    "lonely": "looking_down",
    "grieving": "looking_down",
    "hopeful": "looking_up",
    "determined": "looking_up",
    "proud": "looking_up",
    "nostalgic": "looking_afar",
    "reflective": "looking_afar",
    "bittersweet": "looking_afar",
    "nervous": "looking_to_the_side",
    "shy": "looking_to_the_side",
    "embarrassed": "looking_to_the_side",
    "calm": "closed_eyes",
    "peaceful": "closed_eyes",
    "guilty": "looking_away",
    "resigned": "looking_away",
    "tired": "looking_down",
    "confused": "looking_to_the_side",
    "scared": "looking_away",
    "anxious": "looking_to_the_side",
    "angry": "looking_to_the_side",
    "frustrated": "looking_to_the_side",
    "tense": "looking_to_the_side",
}

_apply_korean_aliases(EMOTION_TO_GAZE)

_GAZE_ALTERNATIVES = ["looking_down", "looking_up", "looking_afar", "looking_to_the_side", "closed_eyes"]


# ── Emotion → Action 매핑 ──────────────────────────────────────────
_EMOTION_TO_ACTION: dict[str, str] = {
    "happy": "waving",
    "excited": "arms_up",
    "proud": "hands_on_hips",
    "confident": "arms_crossed",
    "sad": "hugging",
    "lonely": "hugging",
    "nervous": "reaching",
    "anxious": "pointing",
    "angry": "pointing",
    "frustrated": "arms_crossed",
    "calm": "sitting",
    "nostalgic": "sitting",
    "determined": "arms_up",
    "embarrassed": "hand_on_face",
    "scared": "hugging",
    "tired": "sitting",
}

_ACTION_ALTERNATIVES = list(dict.fromkeys(_EMOTION_TO_ACTION.values()))


# ── Emotion → Camera 매핑 ──────────────────────────────────────────
EMOTION_TO_CAMERA: dict[str, str] = {
    "sad": "close-up",
    "lonely": "close-up",
    "grieving": "close-up",
    "guilty": "close-up",
    "anxious": "upper_body",
    "nervous": "upper_body",
    "tense": "upper_body",
    "angry": "dutch_angle",
    "frustrated": "dutch_angle",
    "excited": "cowboy_shot",
    "happy": "cowboy_shot",
    "proud": "cowboy_shot",
    "determined": "full_body",
    "nostalgic": "from_above",
    "reflective": "from_above",
    "hopeful": "from_below",
    "surprised": "from_below",
    "shocked": "from_below",
    "calm": "upper_body",
    "peaceful": "upper_body",
}

_apply_korean_aliases(EMOTION_TO_CAMERA)

_CAMERA_ALTERNATIVES = ["close-up", "upper_body", "cowboy_shot", "full_body", "from_above", "dutch_angle"]


# ── Emotion → Pose 매핑 ──────────────────────────────────────────
EMOTION_TO_POSE: dict[str, str] = {
    "calm": "sitting",
    "tired": "sitting",
    "sad": "sitting",
    "nostalgic": "sitting",
    "reflective": "sitting",
    "anxious": "leaning_forward",
    "nervous": "leaning_forward",
    "tense": "leaning_forward",
    "confused": "leaning_forward",
    "excited": "arms_up",
    "determined": "arms_up",
    "proud": "hands_on_hips",
    "confident": "hands_on_hips",
    "happy": "hands_on_hips",
    "embarrassed": "hand_on_face",
    "shy": "arms_behind_back",
    "scared": "arms_crossed",
    "angry": "arms_crossed",
    "frustrated": "arms_crossed",
}

_apply_korean_aliases(EMOTION_TO_POSE)

_POSE_ALTERNATIVES = ["sitting", "standing", "arms_crossed", "hands_on_hips", "leaning_forward", "arms_up"]


# ── Generic diversify function ──────────────────────────────────


def _diversify_context_field(
    scenes: list[dict],
    *,
    field: str,
    emotion_map: dict[str, str],
    alternatives: list[str],
    threshold: float = 0.5,
    include_narrator: bool = False,
    field_alias: str | None = None,
    label: str,
) -> None:
    """context_tags의 지정 필드에 대해 반복을 감지하고 emotion 기반으로 교정한다.

    Parameters
    ----------
    field : context_tags 키 (e.g. "gaze", "camera", "pose")
    emotion_map : emotion → 권장 태그 매핑
    alternatives : 연속 동일 방지용 대안 리스트
    threshold : 단조로움 판정 비율 (0.0~1.0)
    include_narrator : True이면 Narrator 씬도 대상에 포함
    field_alias : 보조 필드명 (e.g. "camera_angle")
    label : 로그 레이블 (e.g. "Camera", "Gaze")
    """
    target = scenes if include_narrator else [s for s in scenes if s.get("speaker") != DEFAULT_SPEAKER]
    if len(target) < 3:
        return

    def _read_val(ctx: dict) -> str:
        raw = ctx.get(field)
        if not raw and field_alias:
            raw = ctx.get(field_alias)
        return _coerce_str(raw)

    values = [_read_val(s.get("context_tags") or {}) for s in target]

    counts = Counter(v for v in values if v)
    if not counts:
        return

    dominant, dominant_count = counts.most_common(1)[0]
    if dominant_count <= len(target) * threshold:
        return

    logger.info(
        "[Finalize] %s 단조로움 감지: '%s'가 %d/%d 씬 — emotion 기반 교정 시작",
        label,
        dominant,
        dominant_count,
        len(target),
    )

    corrected = 0
    prev = ""
    for scene in target:
        ctx = scene.get("context_tags")
        if not ctx:
            continue

        current = _read_val(ctx)
        if current != dominant:
            prev = current
            continue

        emotion = _coerce_str(ctx.get("emotion"))
        if not emotion:
            prev = current
            continue

        normalized = _normalize_emotion(emotion)
        suggested = emotion_map.get(normalized) or emotion_map.get(emotion)
        if not suggested or suggested == dominant:
            prev = current
            continue

        if suggested == prev:
            for alt in alternatives:
                if alt != prev and alt != dominant:
                    suggested = alt
                    break
            else:
                continue

        ctx[field] = suggested
        prev = suggested
        corrected += 1

    if corrected:
        logger.info("[Finalize] %s 보정 완료: %d씬 교체", label, corrected)


# ── Thin wrappers ──────────────────────────────────────────────────


def diversify_gazes(scenes: list[dict]) -> None:
    """캐릭터 씬의 >50%가 동일 gaze이면 emotion 기반 교정."""
    _diversify_context_field(
        scenes,
        field="gaze",
        emotion_map=EMOTION_TO_GAZE,
        alternatives=_GAZE_ALTERNATIVES,
        threshold=0.5,
        label="Gaze",
    )


def diversify_actions(scenes: list[dict]) -> None:
    """캐릭터 씬의 >40%가 동일 action이면 emotion 기반 교정."""
    _diversify_context_field(
        scenes,
        field="action",
        emotion_map=_EMOTION_TO_ACTION,
        alternatives=_ACTION_ALTERNATIVES,
        threshold=0.4,
        label="Action",
    )


def diversify_cameras(scenes: list[dict]) -> None:
    """전체 씬의 >50%가 동일 카메라 앵글이면 emotion 기반 교정."""
    # NOTE: Narrator scenes included — camera diversity benefits narration visually
    _diversify_context_field(
        scenes,
        field="camera",
        emotion_map=EMOTION_TO_CAMERA,
        alternatives=_CAMERA_ALTERNATIVES,
        threshold=0.5,
        include_narrator=True,
        field_alias="camera_angle",
        label="Camera",
    )


def diversify_poses(scenes: list[dict]) -> None:
    """캐릭터 씬의 >50%가 동일 pose이면 emotion 기반 교정."""
    _diversify_context_field(
        scenes,
        field="pose",
        emotion_map=EMOTION_TO_POSE,
        alternatives=_POSE_ALTERNATIVES,
        threshold=0.5,
        label="Pose",
    )
