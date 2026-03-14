"""Pre-render validation and timeline calculation."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from config import TTS_CACHE_DIR
from schemas import (
    PreValidateIssue,
    PreValidateRequest,
    PreValidateResponse,
    TimelineRequest,
    TimelineResponse,
    TimelineSceneOutput,
)


def preview_timeline(req: TimelineRequest) -> TimelineResponse:
    """Calculate timeline data for all scenes."""
    from services.video.utils import calculate_speed_params, has_speakable_content

    transition_dur, tts_padding, clamped_speed = calculate_speed_params(req.speed_multiplier)

    scenes_out: list[TimelineSceneOutput] = []
    cumulative = 0.0

    for i, scene in enumerate(req.scenes):
        has_tts = has_speakable_content(scene.script) if scene.script.strip() else False
        tts_dur = scene.tts_duration

        if has_tts and tts_dur and tts_dur > 0:
            xfade_tail = transition_dur if i < len(req.scenes) - 1 else 0.0
            effective = max(
                scene.duration / clamped_speed,
                transition_dur + tts_dur + tts_padding + xfade_tail,
            )
        else:
            effective = scene.duration / clamped_speed

        start = cumulative
        end = cumulative + effective
        cumulative = end

        scenes_out.append(
            TimelineSceneOutput(
                scene_index=i,
                effective_duration=round(effective, 2),
                tts_duration=round(tts_dur, 2) if tts_dur else None,
                has_tts=has_tts,
                start_time=round(start, 2),
                end_time=round(end, 2),
            )
        )

    return TimelineResponse(
        scenes=scenes_out,
        total_duration=round(cumulative, 2),
    )


async def preview_validate(
    req: PreValidateRequest,
    db: Session,
) -> PreValidateResponse:
    """Run pre-render validation checks on a storyboard."""
    from models.storyboard import Storyboard

    storyboard = (
        db.query(Storyboard)
        .options(
            joinedload(Storyboard.scenes),
            joinedload(Storyboard.characters),
            joinedload(Storyboard.group),
        )
        .filter(Storyboard.id == req.storyboard_id, Storyboard.deleted_at.is_(None))
        .first()
    )
    if not storyboard:
        raise ValueError("스토리보드를 찾을 수 없습니다.")

    scenes = sorted(
        [s for s in storyboard.scenes if s.deleted_at is None],
        key=lambda s: s.order,
    )
    issues: list[PreValidateIssue] = []

    if not scenes:
        issues.append(PreValidateIssue(level="error", scene_index=None, category="scenes", message="씬이 없습니다."))
        return PreValidateResponse(is_ready=False, issues=issues, total_scenes=0)

    cached_tts = _check_scenes(scenes, issues)
    _check_characters(storyboard, issues)
    _check_voice_preset(storyboard, issues)
    _check_duration(scenes, issues)

    return PreValidateResponse(
        is_ready=not any(i.level == "error" for i in issues),
        issues=issues,
        total_duration=round(sum((s.duration or 3.0) for s in scenes), 2),
        cached_tts_count=cached_tts,
        total_scenes=len(scenes),
    )


def _check_scenes(scenes, issues: list[PreValidateIssue]) -> int:
    """Validate each scene's image, script, and TTS cache. Returns cached TTS count."""
    from services.video.tts_helpers import tts_cache_key
    from services.video.utils import clean_script_for_tts, has_speakable_content

    cached_tts = 0
    for i, scene in enumerate(scenes):
        if not scene.image_asset_id and not _scene_has_image(scene):
            issues.append(PreValidateIssue(
                level="error", scene_index=i, category="image",
                message=f"씬 {i + 1}: 이미지가 없습니다.",
            ))

        script = scene.script or ""
        if not script.strip():
            issues.append(PreValidateIssue(
                level="warning", scene_index=i, category="script",
                message=f"씬 {i + 1}: 스크립트가 비어있습니다.",
            ))
        elif len(script) > 500:
            issues.append(PreValidateIssue(
                level="warning", scene_index=i, category="script",
                message=f"씬 {i + 1}: 스크립트가 매우 깁니다 ({len(script)}자).",
            ))

        if has_speakable_content(script):
            cleaned = clean_script_for_tts(script)
            ck = tts_cache_key(cleaned, None, None, "korean", speaker=getattr(scene, "speaker", None))
            if (TTS_CACHE_DIR / f"{ck}.wav").exists():
                cached_tts += 1
            else:
                issues.append(PreValidateIssue(
                    level="info", scene_index=i, category="tts",
                    message=f"씬 {i + 1}: TTS 캐시 없음 (렌더링 시 생성됩니다).",
                ))
    return cached_tts


def _check_duration(scenes, issues: list[PreValidateIssue]) -> None:
    """Warn if estimated total duration exceeds 60 seconds."""
    total_dur = sum((s.duration or 3.0) for s in scenes)
    if total_dur > 60:
        issues.append(PreValidateIssue(
            level="warning", scene_index=None, category="duration",
            message=f"예상 영상 길이가 {total_dur:.0f}초로 60초를 초과합니다.",
        ))


def _scene_has_image(scene) -> bool:
    """Check if scene has any image source."""
    candidates = scene.candidates or []
    return bool(candidates and any(c.get("media_asset_id") for c in candidates))


def _check_characters(storyboard, issues: list[PreValidateIssue]) -> None:
    """Warn if no character is assigned to the storyboard."""
    has_character = bool(storyboard.characters)
    if not has_character:
        issues.append(
            PreValidateIssue(
                level="warning",
                scene_index=None,
                category="character",
                message="캐릭터가 배정되지 않았습니다. 기본 설정으로 렌더링됩니다.",
            )
        )


def _check_voice_preset(storyboard, issues: list[PreValidateIssue]) -> None:
    """Warn if the group has no narrator voice preset configured."""
    group = storyboard.group
    if not group or not group.narrator_voice_preset_id:
        issues.append(
            PreValidateIssue(
                level="warning",
                scene_index=None,
                category="voice",
                message="음성 프리셋이 설정되지 않았습니다. 기본 음성으로 렌더링됩니다.",
            )
        )
