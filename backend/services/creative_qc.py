"""Quality Control validation for Creative Lab V2 pipeline outputs."""

from __future__ import annotations

from config import SCRIPT_LENGTH_KOREAN, SCRIPT_LENGTH_OTHER, coerce_structure_id, logger
from services.keywords.patterns import CATEGORY_PATTERNS
from services.storyboard.helpers import calculate_max_scenes, calculate_min_scenes

_GAZE_TAGS: frozenset[str] = frozenset(CATEGORY_PATTERNS.get("gaze", []))
_POSE_TAGS: frozenset[str] = frozenset(CATEGORY_PATTERNS.get("pose", []))

# Narrator는 모든 구조에서 선택적으로 허용 (CLAUDE.md 설계 원칙)
_VALID_SPEAKERS: dict[str, frozenset[str]] = {
    "monologue": frozenset({"A", "Narrator"}),
    "dialogue": frozenset({"A", "B", "Narrator"}),
    "narrated_dialogue": frozenset({"Narrator", "A", "B"}),
}


def _extract_tags_from_prompt(prompt: str, tag_set: frozenset[str]) -> list[str]:
    """프롬프트에서 특정 카테고리 태그를 추출한다."""
    return [t.strip() for t in prompt.split(",") if t.strip() in tag_set]


def _check_consecutive_gaze(gaze_per_scene: list[list[str]]) -> list[str]:
    """인접 씬의 동일 gaze 반복 검출. Returns issue strings."""
    issues = []
    for i in range(len(gaze_per_scene) - 1):
        overlap = set(gaze_per_scene[i]) & set(gaze_per_scene[i + 1])
        if overlap:
            issues.append(f"Scene {i}→{i + 1} 동일 gaze 반복: {', '.join(sorted(overlap))}")
    return issues


def validate_scripts(
    scripts: list[dict],
    structure: str,
    duration: int,
    language: str,
) -> dict:
    """Validate scriptwriter output against rules.

    Returns: {"ok": bool, "issues": [str], "checks": {name: "PASS"|"FAIL"}}
    """
    issues: list[str] = []
    checks: dict[str, str] = {}

    structure = coerce_structure_id(structure)
    # Scene count check (SSOT: storyboard helpers)
    min_scenes = calculate_min_scenes(duration, structure)
    max_scenes = calculate_max_scenes(duration, structure)
    count = len(scripts)
    if min_scenes <= count <= max_scenes:
        checks["scene_count"] = "PASS"
    else:
        checks["scene_count"] = "FAIL"
        issues.append(f"Scene count {count} outside range [{min_scenes}, {max_scenes}]")

    # Script length check (SSOT: config.py SCRIPT_LENGTH_*)
    ko_min, ko_max = SCRIPT_LENGTH_KOREAN
    other_min, other_max = SCRIPT_LENGTH_OTHER
    length_pass = 0
    for i, s in enumerate(scripts):
        script_text = s.get("script", "")
        if language == "korean":
            ok = ko_min <= len(script_text) <= ko_max
        else:
            ok = other_min <= len(script_text.split()) <= other_max
        if ok:
            length_pass += 1
        else:
            issues.append(f"Scene {i}: script length out of range ({len(script_text)} chars)")
    checks["script_length"] = "PASS" if length_pass == count else "FAIL"

    # Per-scene duration check: reading-time-aware (±1.0s tolerance)
    from services.storyboard.helpers import estimate_reading_duration

    dur_range_ok = True
    for i, s in enumerate(scripts):
        d = s.get("duration", 0)
        script_text = s.get("script", "").strip()
        if script_text:
            expected = estimate_reading_duration(script_text, language)
            if abs(d - expected) > 1.0:
                dur_range_ok = False
                issues.append(f"Scene {i}: duration {d}s vs reading-time {expected}s (gap > 1.0s)")
        elif d <= 0:
            dur_range_ok = False
            issues.append(f"Scene {i}: duration {d}s invalid")
    checks["scene_duration_range"] = "PASS" if dur_range_ok else "WARN"

    # Speaker rules — Narrator is optional in all structures (see module-level _VALID_SPEAKERS)
    speaker_ok = True
    for i, s in enumerate(scripts):
        speaker = s.get("speaker", "")
        # 미등록 structure는 A+Narrator만 허용 (새 structure 추가 시 _VALID_SPEAKERS에 명시 필요)
        valid = _VALID_SPEAKERS.get(structure, frozenset({"A", "Narrator"}))
        if speaker not in valid:
            speaker_ok = False
            issues.append(f"Scene {i}: {structure} expects speaker in {sorted(valid)}, got '{speaker}'")
    checks["speaker_rule"] = "PASS" if speaker_ok else "FAIL"

    # Speaker distribution check
    speakers_found = {s.get("speaker", "") for s in scripts}
    if structure == "dialogue":
        missing = {"A", "B"} - speakers_found
        if missing:
            checks["speaker_distribution"] = "FAIL"
            issues.append(f"Dialogue requires both A and B, missing: {', '.join(sorted(missing))}")
        else:
            checks["speaker_distribution"] = "PASS"
    elif structure == "narrated_dialogue":
        missing = {"Narrator", "A", "B"} - speakers_found
        if missing:
            checks["speaker_distribution"] = "FAIL"
            issues.append(f"Narrated Dialogue requires Narrator, A, and B, missing: {', '.join(sorted(missing))}")
        else:
            checks["speaker_distribution"] = "PASS"

    # Duration sum check
    total_dur = sum(s.get("duration", 0) for s in scripts)
    dur_tolerance = duration * 0.3
    if abs(total_dur - duration) <= dur_tolerance:
        checks["duration_sum"] = "PASS"
    else:
        checks["duration_sum"] = "WARN"
        issues.append(f"Total duration {total_dur:.1f}s vs target {duration}s")

    has_fail = any(v == "FAIL" for v in checks.values())
    if has_fail:
        logger.info("[CreativeQC] Script FAIL: %s", issues)
    elif issues:
        logger.info("[CreativeQC] Script WARN: %s", issues)
    return {"ok": not has_fail, "issues": issues, "checks": checks}


def _check_environment_consistency(scenes: list[dict]) -> list[str]:
    """연속 대화 씬(speaker A↔B 교대)의 배경 불일치를 검출한다."""
    issues: list[str] = []
    if len(scenes) < 2:
        return issues

    # 연속 대화 그룹 식별: speaker가 교대되는 인접 씬들을 하나의 그룹으로 묶음
    groups: list[list[int]] = []
    current_group = [0]
    for i in range(1, len(scenes)):
        prev_speaker = scenes[i - 1].get("speaker", "")
        curr_speaker = scenes[i].get("speaker", "")
        # A↔B 교대이거나 동일 speaker 연속이면 같은 대화 그룹
        if prev_speaker and curr_speaker and prev_speaker != "Narrator" and curr_speaker != "Narrator":
            current_group.append(i)
        else:
            if len(current_group) >= 2:
                groups.append(current_group)
            current_group = [i]
    if len(current_group) >= 2:
        groups.append(current_group)

    # 각 대화 그룹 내 환경 불일치 검출
    for group in groups:
        envs: dict[int, list] = {}
        for idx in group:
            env = scenes[idx].get("environment") or []
            if isinstance(env, str):
                env = [env]
            envs[idx] = env
        # 유니크 환경 집합
        env_sets = {idx: frozenset(e) for idx, e in envs.items() if e}
        unique_envs = set(env_sets.values())
        if len(unique_envs) > 1:
            scene_envs = ", ".join(f"Scene {idx}: {list(envs[idx])}" for idx in group)
            issues.append(f"Consecutive dialogue scenes {group} have inconsistent environments: {scene_envs}")
    return issues


def validate_visuals(scenes: list[dict]) -> dict:
    """Validate cinematographer output for tag quality.

    Returns: {"ok": bool, "issues": [str], "checks": {name: "PASS"|"FAIL"}}
    """
    issues: list[str] = []
    checks: dict[str, str] = {}

    # image_prompt presence
    prompt_ok = True
    for i, s in enumerate(scenes):
        if not s.get("image_prompt"):
            prompt_ok = False
            issues.append(f"Scene {i}: missing image_prompt")
    checks["image_prompt_present"] = "PASS" if prompt_ok else "FAIL"

    # Camera diversity
    cameras = {s.get("camera", "") for s in scenes if s.get("camera")}
    if len(cameras) >= 3:
        checks["camera_diversity"] = "PASS"
    else:
        checks["camera_diversity"] = "WARN"
        issues.append(f"Only {len(cameras)} camera types used (need 3+)")

    # Gaze diversity (Phase 11)
    gaze_per_scene: list[list[str]] = []
    pose_per_scene: list[list[str]] = []
    for s in scenes:
        prompt = s.get("image_prompt", "")
        gaze_per_scene.append(_extract_tags_from_prompt(prompt, _GAZE_TAGS))
        pose_per_scene.append(_extract_tags_from_prompt(prompt, _POSE_TAGS))

    total = len(scenes)
    all_gazes = [g for scene_gazes in gaze_per_scene for g in scene_gazes]
    if total > 0 and all_gazes:
        unique_gazes = set(all_gazes)
        lat_count = all_gazes.count("looking_at_viewer")
        lat_ratio = lat_count / total

        if lat_ratio > 0.5:
            checks["gaze_diversity"] = "WARN"
            issues.append(f"looking_at_viewer used in {lat_count}/{total} scenes ({lat_ratio:.0%}), limit to 50%")
        elif len(unique_gazes) < 2 and total >= 4:
            checks["gaze_diversity"] = "WARN"
            issues.append(f"Only {len(unique_gazes)} gaze type(s) used (need 2+)")
        else:
            checks["gaze_diversity"] = "PASS"

    # Consecutive gaze repetition (Phase 11-P3)
    consec_issues = _check_consecutive_gaze(gaze_per_scene)
    if consec_issues:
        checks["gaze_consecutive"] = "WARN"
        issues.extend(consec_issues)
    elif total > 1:
        checks["gaze_consecutive"] = "PASS"

    all_poses = [p for scene_poses in pose_per_scene for p in scene_poses]
    if total > 0 and all_poses:
        unique_poses = set(all_poses)
        if len(unique_poses) < 2 and total >= 4:
            checks["pose_diversity"] = "WARN"
            issues.append(f"Only {len(unique_poses)} pose type(s) used (need 2+)")
        else:
            checks["pose_diversity"] = "PASS"

    # Environment presence
    env_ok = all(s.get("environment") for s in scenes)
    checks["environment_present"] = "PASS" if env_ok else "WARN"
    if not env_ok:
        missing = [i for i, s in enumerate(scenes) if not s.get("environment")]
        issues.append(f"Scenes {missing}: missing environment")

    # Environment consistency — 연속 대화 씬의 배경 불일치 검출
    env_consistency_issues = _check_environment_consistency(scenes)
    if env_consistency_issues:
        checks["environment_consistency"] = "WARN"
        issues.extend(env_consistency_issues)
    elif total > 1:
        checks["environment_consistency"] = "PASS"

    has_fail = any(v == "FAIL" for v in checks.values())
    if has_fail:
        logger.info("[CreativeQC] Visual FAIL: %s", issues)
    elif issues:
        logger.info("[CreativeQC] Visual WARN: %s", issues)
    return {"ok": not has_fail, "issues": issues, "checks": checks}


def validate_copyright(checks_list: list[dict]) -> dict:
    """Validate copyright reviewer output.

    Returns: {"ok": bool, "issues": [str], "checks": {name: "PASS"|"FAIL"|"WARN"}}
    """
    issues: list[str] = []
    checks: dict[str, str] = {}

    for item in checks_list:
        check_type = item.get("type", "unknown")
        status = item.get("status", "PASS")
        checks[check_type] = status
        if status == "FAIL":
            detail = item.get("detail") or "No detail provided"
            suggestion = item.get("suggestion")
            msg = f"{check_type}: {detail}"
            if suggestion:
                msg += f" (suggestion: {suggestion})"
            issues.append(msg)
        elif status == "WARN":
            detail = item.get("detail") or "Minor concern"
            issues.append(f"{check_type}: {detail}")

    has_fail = any(v == "FAIL" for v in checks.values())
    if has_fail:
        logger.info("[CreativeQC] Copyright FAIL: %s", issues)
    return {"ok": not has_fail, "issues": issues, "checks": checks}


def validate_music(recommendation: list[dict] | dict) -> dict:
    """Validate sound designer recommendation output.

    Returns: {"ok": bool, "issues": [str], "checks": {name: "PASS"|"FAIL"}}
    """
    rec = recommendation if isinstance(recommendation, dict) else (recommendation[0] if recommendation else {})
    issues: list[str] = []

    if not rec.get("prompt"):
        issues.append("Missing music prompt")
    if not rec.get("mood"):
        issues.append("Missing mood description")
    try:
        dur = int(rec.get("duration", 0))
    except (TypeError, ValueError):
        dur = 0
    if dur < 10:
        issues.append("Invalid duration (must be >= 10s)")

    status = "PASS" if not issues else "FAIL"
    if issues:
        logger.info("[CreativeQC] Music issues: %s", issues)
    return {"ok": len(issues) == 0, "issues": issues, "checks": {"music_recommendation": status}}


def validate_tts_design(tts_designs: list[dict], preset_speakers: set[str] | None = None) -> dict:
    """Validate tts designer output for emotional design quality.

    Returns: {"ok": bool, "issues": [str], "checks": {name: "PASS"|"FAIL"}}
    """
    issues: list[str] = []
    checks: dict[str, str] = {}
    preset_speakers = preset_speakers or set()

    if not tts_designs:
        issues.append("No TTS designs provided")
        checks["tts_design_present"] = "FAIL"
        return {"ok": False, "issues": issues, "checks": checks}

    # Prompt presence and pacing range
    prompt_ok = True
    pacing_ok = True
    for i, d in enumerate(tts_designs):
        # skip 노드는 검증 생략
        if d.get("skip"):
            continue

        speaker = d.get("speaker") or "Unknown"
        # 프리셋 화자가 아니거나, 프리셋 정보가 없는 경우에만 voice_design_prompt 필수 체크
        if speaker not in preset_speakers and not d.get("voice_design_prompt"):
            prompt_ok = False
            issues.append(f"Scene {i} (Speaker {speaker}): missing voice_design_prompt")

        pacing = d.get("pacing", {})
        head = pacing.get("head_padding", 0)
        tail = pacing.get("tail_padding", 0)
        if not (0 <= head <= 1.0) or not (0 <= tail <= 2.0):
            pacing_ok = False
            issues.append(f"Scene {i}: pacing values out of normal range (head={head}, tail={tail})")

    checks["tts_design_present"] = "PASS"
    checks["tts_prompt_present"] = "PASS" if prompt_ok else "FAIL"
    checks["tts_pacing_valid"] = "PASS" if pacing_ok else "WARN"

    has_fail = any(v == "FAIL" for v in checks.values())
    return {"ok": not has_fail, "issues": issues, "checks": checks}
