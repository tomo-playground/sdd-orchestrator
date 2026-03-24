"""Review 규칙 기반 검증 — 씬 유효성 검사 (순수 함수).

review.py에서 분리. Revise 노드가 에러 패턴을 파싱하여 자동 수정에 사용한다.
"""

from __future__ import annotations

import re
from collections import defaultdict

from config import (
    DEFAULT_SPEAKER,
    DIALOGUE_CLICHE_PATTERNS,
    DURATION_DEFICIT_THRESHOLD,
    DURATION_OVERFLOW_THRESHOLD,
    REVIEW_SCRIPT_MAX_CHARS_OTHER,
    SCRIPT_LENGTH_KOREAN,
    SPEAKER_A,
    SPEAKER_B,
    coerce_structure_id,
)
from config import (
    pipeline_logger as logger,
)
from services.agent.state import ReviewResult
from services.storyboard.helpers import calculate_min_scenes

VALID_SPEAKERS = {DEFAULT_SPEAKER, SPEAKER_A, SPEAKER_B}

_INFORMAL_SUFFIXES = ("야", "어", "지", "네", "게", "냐", "을게", "는데", "잖아", "거든", "니까")
_FORMAL_SUFFIXES = ("요", "세요", "습니다", "겠습니다", "시죠")

_COMPILED_CLICHE_PATTERNS: list[re.Pattern[str]] = []
for _pat in DIALOGUE_CLICHE_PATTERNS:
    try:
        _COMPILED_CLICHE_PATTERNS.append(re.compile(_pat))
    except re.error:
        logger.warning("[Review] 클리셰 패턴 컴파일 실패: %s", _pat)


def generate_user_summary(passed: bool, error_count: int, warning_count: int) -> str:
    """사용자용 요약 메시지를 생성한다."""
    if passed:
        if warning_count > 0:
            return f"✅ 검증 완료 (경고 {warning_count}개는 자동 개선됩니다)"
        return "✅ 검증 완료"

    if error_count > 0:
        return f"🔄 AI가 시나리오를 개선하고 있습니다 (문제 {error_count}개 수정 중)"

    return "🔄 시나리오 품질을 개선하고 있습니다"


def _validate_single_scene(
    scene: dict,
    idx: int,
    language: str,
) -> tuple[list[str], list[str]]:
    """단일 씬을 검증하고 (errors, warnings) 튜플을 반환한다."""
    errors: list[str] = []
    warnings: list[str] = []

    for field in ("script", "speaker", "duration", "image_prompt"):
        if field not in scene or scene[field] is None:
            errors.append(f"씬 {idx}: 필수 필드 '{field}' 누락")

    speaker = scene.get("speaker")
    if speaker and speaker not in VALID_SPEAKERS:
        errors.append(f"씬 {idx}: 유효하지 않은 speaker '{speaker}' (허용: {VALID_SPEAKERS})")

    scene_dur = scene.get("duration")
    if isinstance(scene_dur, (int, float)) and scene_dur <= 0:
        errors.append(f"씬 {idx}: duration이 0 이하 ({scene_dur})")

    script = scene.get("script", "")
    if isinstance(script, str):
        stripped = script.replace(".", "").replace(" ", "").strip()
        if not stripped:
            errors.append(f"씬 {idx}: 빈 스크립트 ('{script}')")
        elif len(stripped) < 5:
            warnings.append(f"씬 {idx}: 스크립트 너무 짧음 ({len(script)}자)")
        max_len = SCRIPT_LENGTH_KOREAN[1] if language == "korean" else REVIEW_SCRIPT_MAX_CHARS_OTHER
        if len(script) > max_len:
            warnings.append(f"씬 {idx}: 스크립트 길이 초과 ({len(script)}자 > {max_len}자)")

    img_prompt = scene.get("image_prompt")
    if isinstance(img_prompt, str) and not img_prompt.strip():
        warnings.append(f"씬 {idx}: image_prompt가 비어있음")

    return errors, warnings


# ---------------------------------------------------------------------------
# 대사 품질 검증 헬퍼 (순수 함수)
# ---------------------------------------------------------------------------


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """두 텍스트의 공백 기준 토큰 Jaccard 유사도를 반환한다."""
    tokens_a = set(text_a.split())
    tokens_b = set(text_b.split())
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


def _detect_speech_level(text: str | None) -> str | None:
    """한국어 텍스트의 반말/존댓말 수준을 판정한다. 'formal'/'informal'/None."""
    if not text:
        return None
    words = text.split()
    formal_count = 0
    informal_count = 0
    for word in words:
        if any(word.endswith(s) for s in _FORMAL_SUFFIXES):
            formal_count += 1
        elif any(word.endswith(s) for s in _INFORMAL_SUFFIXES):
            informal_count += 1
    if formal_count == 0 and informal_count == 0:
        return None
    if formal_count > informal_count:
        return "formal"
    if informal_count > formal_count:
        return "informal"
    return None  # 동률


def _check_speaker_alternation(scenes: list[dict], warnings: list[str]) -> None:
    """A-2: 동일 speaker가 3씬 이상 연속이면 WARNING."""
    if len(scenes) < 3:
        return
    streak_speaker: str | None = None
    streak_start = 0
    streak_count = 0
    for i, scene in enumerate(scenes):
        speaker = scene.get("speaker")
        if not speaker:
            if streak_count >= 3:
                warnings.append(
                    f"씬 {streak_start + 1}~{i}: {streak_speaker}가 {streak_count}씬 연속 독백 — 대화 교번 필요"
                )
            streak_speaker = None
            streak_count = 0
            continue
        if speaker == streak_speaker:
            streak_count += 1
        else:
            if streak_count >= 3:
                warnings.append(
                    f"씬 {streak_start + 1}~{i}: {streak_speaker}가 {streak_count}씬 연속 독백 — 대화 교번 필요"
                )
            streak_speaker = speaker
            streak_start = i
            streak_count = 1
    if streak_count >= 3:
        warnings.append(
            f"씬 {streak_start + 1}~{len(scenes)}: {streak_speaker}가 {streak_count}씬 연속 독백 — 대화 교번 필요"
        )


def _check_script_similarity(scenes: list[dict], warnings: list[str]) -> None:
    """A-3: 인접 씬 스크립트 Jaccard >= 0.7이면 WARNING."""
    for i in range(len(scenes) - 1):
        script_a = scenes[i].get("script")
        script_b = scenes[i + 1].get("script")
        if not script_a or not script_b:
            continue
        sim = _jaccard_similarity(script_a, script_b)
        if sim >= 0.7:
            warnings.append(f"씬 {i + 1}~{i + 2}: 스크립트 유사도 {sim:.0%} — 대사 차별화 필요")


def _check_cliches(scenes: list[dict], warnings: list[str]) -> None:
    """B-1: 한 씬에서 클리셰 패턴 2개 이상 매칭이면 WARNING."""
    for i, scene in enumerate(scenes):
        script = scene.get("script")
        if not script:
            continue
        matched: list[str] = []
        for compiled in _COMPILED_CLICHE_PATTERNS:
            if compiled.search(script):
                matched.append(compiled.pattern)
        if len(matched) >= 2:
            warnings.append(
                f"씬 {i + 1}: 클리셰 표현 {len(matched)}개 감지 ({', '.join(matched[:3])}) — 독창적 표현 권장"
            )


def _check_speech_consistency(scenes: list[dict], warnings: list[str]) -> None:
    """B-2: 동일 speaker의 반말/존댓말 혼용 (각 3씬 이상) WARNING."""
    speaker_levels: dict[str, dict[str, int]] = defaultdict(lambda: {"formal": 0, "informal": 0})
    for scene in scenes:
        speaker = scene.get("speaker")
        if not speaker or speaker == DEFAULT_SPEAKER:
            continue
        level = _detect_speech_level(scene.get("script"))
        if level:
            speaker_levels[speaker][level] += 1
    for speaker, counts in speaker_levels.items():
        if counts["formal"] >= 3 and counts["informal"] >= 3:
            warnings.append(
                f"speaker {speaker}: 반말({counts['informal']}씬)/존댓말({counts['formal']}씬) 혼용 — 문체 통일 필요"
            )


def validate_dialogue_quality(
    scenes: list[dict],
    structure: str,
) -> tuple[list[str], list[str]]:
    """씬 간 관계 기반 대사 품질 검증 (A-2, A-3, B-1, B-2).

    Returns (errors, warnings) 튜플. 현재 errors는 항상 빈 리스트.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # A-2: Speaker 교번 단절 (dialogue 구조만)
    if structure == "dialogue":
        _check_speaker_alternation(scenes, warnings)

    # A-3: 인접 씬 스크립트 유사도
    _check_script_similarity(scenes, warnings)

    # B-1: 클리셰 감지
    _check_cliches(scenes, warnings)

    # B-2: 문체 일관성 (dialogue 구조만)
    if structure == "dialogue":
        _check_speech_consistency(scenes, warnings)

    return errors, warnings


def validate_scenes(
    scenes: list[dict],
    duration: int,
    language: str,
    structure: str,
) -> ReviewResult:
    """씬 목록을 검증하고 ReviewResult를 반환한다 (순수 함수)."""
    errors: list[str] = []
    warnings: list[str] = []

    structure = coerce_structure_id(structure)
    expected_min = calculate_min_scenes(duration, structure)
    if len(scenes) < expected_min:
        errors.append(f"씬 개수 부족: {len(scenes)}개 (최소 {expected_min}개 필요, duration={duration}s)")

    # 총 duration 검증
    total_dur = sum(s.get("duration", 0) for s in scenes)
    threshold = duration * DURATION_DEFICIT_THRESHOLD
    if duration > 0 and total_dur < threshold:
        errors.append(f"총 duration 부족: {total_dur:.1f}s (목표 {duration}s의 85% = {threshold:.1f}s 미달)")

    overflow_limit = duration * DURATION_OVERFLOW_THRESHOLD
    if duration > 0 and total_dur > overflow_limit:
        errors.append(
            f"총 duration 초과: {total_dur:.1f}s (목표 {duration}s의 {DURATION_OVERFLOW_THRESHOLD * 100:.0f}% = {overflow_limit:.1f}s 초과)"
        )

    speakers_found: set[str] = set()
    for i, scene in enumerate(scenes):
        scene_errors, scene_warnings = _validate_single_scene(scene, i + 1, language)
        errors.extend(scene_errors)
        warnings.extend(scene_warnings)
        speaker = scene.get("speaker")
        if speaker:
            speakers_found.add(speaker)

    if structure == "monologue":
        invalid = speakers_found - {SPEAKER_A, DEFAULT_SPEAKER}
        if invalid:
            errors.append(
                f"{structure}는 speaker='{SPEAKER_A}' 또는 '{DEFAULT_SPEAKER}'만 허용 — 잘못된 speaker 발견: {', '.join(sorted(invalid))}"
            )
    elif structure in ("dialogue", "narrated_dialogue"):
        for s in (SPEAKER_A, SPEAKER_B):
            if s not in speakers_found:
                errors.append(
                    f"Dialogue 구조에서 speaker '{s}'가 등장하지 않음 — 반드시 {SPEAKER_A}와 {SPEAKER_B} 모두 포함해야 함"
                )

        # Speaker 비율 검증
        non_narrator = [sc for sc in scenes if sc.get("speaker") in (SPEAKER_A, SPEAKER_B)]
        if SPEAKER_A in speakers_found and SPEAKER_B in speakers_found and len(non_narrator) >= 2:
            a_count = sum(1 for sc in non_narrator if sc.get("speaker") == SPEAKER_A)
            b_count = len(non_narrator) - a_count
            total = len(non_narrator)
            for label, cnt in [(SPEAKER_A, a_count), (SPEAKER_B, b_count)]:
                pct = cnt / total * 100
                if pct < 20:
                    errors.append(
                        f"Dialogue 구조에서 speaker 비율 불균형 — {label}가 {pct:.0f}%로 최소 20% 미만 ({SPEAKER_A}={a_count}, {SPEAKER_B}={b_count}, 총 {total}씬)"
                    )

        # Narrator 존재 검증 (Narrated Dialogue 전용)
        if structure == "narrated_dialogue":
            if DEFAULT_SPEAKER not in speakers_found:
                errors.append(
                    f"Narrated Dialogue에서 {DEFAULT_SPEAKER} 씬 없음 — 최소 1개의 내레이션 씬 필수 (현재 {len(scenes)}씬 모두 캐릭터)"
                )

    # 대사 품질 검증 (씬 간 관계)
    dialogue_errors, dialogue_warnings = validate_dialogue_quality(scenes, structure)
    errors.extend(dialogue_errors)
    warnings.extend(dialogue_warnings)

    passed = len(errors) == 0
    user_summary = generate_user_summary(passed, len(errors), len(warnings))

    return ReviewResult(passed=passed, errors=errors, warnings=warnings, user_summary=user_summary)
