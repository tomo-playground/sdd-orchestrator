"""Review 규칙 기반 검증 — 씬 유효성 검사 (순수 함수).

review.py에서 분리. Revise 노드가 에러 패턴을 파싱하여 자동 수정에 사용한다.
"""

from __future__ import annotations

from config import (
    DURATION_DEFICIT_THRESHOLD,
    DURATION_OVERFLOW_THRESHOLD,
    REVIEW_SCRIPT_MAX_CHARS_OTHER,
    SCRIPT_LENGTH_KOREAN,
)
from services.agent.state import ReviewResult
from services.storyboard.helpers import calculate_min_scenes, normalize_structure

VALID_SPEAKERS = {"Narrator", "A", "B"}


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
        max_len = SCRIPT_LENGTH_KOREAN[1] if language == "Korean" else REVIEW_SCRIPT_MAX_CHARS_OTHER
        if len(script) > max_len:
            warnings.append(f"씬 {idx}: 스크립트 길이 초과 ({len(script)}자 > {max_len}자)")

    img_prompt = scene.get("image_prompt")
    if isinstance(img_prompt, str) and not img_prompt.strip():
        warnings.append(f"씬 {idx}: image_prompt가 비어있음")

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

    structure = normalize_structure(structure)
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

    if structure in ("Monologue", "Confession"):
        invalid = speakers_found - {"A", "Narrator"}
        if invalid:
            errors.append(
                f"{structure}는 speaker='A' 또는 'Narrator'만 허용 — 잘못된 speaker 발견: {', '.join(sorted(invalid))}"
            )
    elif structure.replace("_", " ") in ("Dialogue", "Narrated Dialogue"):
        for s in ("A", "B"):
            if s not in speakers_found:
                errors.append(f"Dialogue 구조에서 speaker '{s}'가 등장하지 않음 — 반드시 A와 B 모두 포함해야 함")

        # Speaker 비율 검증
        non_narrator = [sc for sc in scenes if sc.get("speaker") in ("A", "B")]
        if "A" in speakers_found and "B" in speakers_found and len(non_narrator) >= 2:
            a_count = sum(1 for sc in non_narrator if sc.get("speaker") == "A")
            b_count = len(non_narrator) - a_count
            total = len(non_narrator)
            for label, cnt in [("A", a_count), ("B", b_count)]:
                pct = cnt / total * 100
                if pct < 20:
                    errors.append(
                        f"Dialogue 구조에서 speaker 비율 불균형 — {label}가 {pct:.0f}%로 최소 20% 미만 (A={a_count}, B={b_count}, 총 {total}씬)"
                    )

        # Narrator 존재 검증 (Narrated Dialogue 전용)
        if structure.replace("_", " ") == "Narrated Dialogue":
            if "Narrator" not in speakers_found:
                errors.append(
                    f"Narrated Dialogue에서 Narrator 씬 없음 — 최소 1개의 내레이션 씬 필수 (현재 {len(scenes)}씬 모두 캐릭터)"
                )

    passed = len(errors) == 0
    user_summary = generate_user_summary(passed, len(errors), len(warnings))

    return ReviewResult(passed=passed, errors=errors, warnings=warnings, user_summary=user_summary)
