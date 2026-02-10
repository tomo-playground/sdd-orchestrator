"""Quality Control validation for Creative Lab V2 pipeline outputs."""

from __future__ import annotations

from config import SCENE_DURATION_RANGE, SCRIPT_LENGTH_KOREAN, SCRIPT_LENGTH_OTHER, logger


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

    # Scene count check
    min_scenes = max(4, duration // 5)
    max_scenes = duration // 2
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
        if language == "Korean":
            ok = ko_min <= len(script_text) <= ko_max
        else:
            ok = other_min <= len(script_text.split()) <= other_max
        if ok:
            length_pass += 1
        else:
            issues.append(f"Scene {i}: script length out of range ({len(script_text)} chars)")
    checks["script_length"] = "PASS" if length_pass == count else "FAIL"

    # Per-scene duration range check (SSOT: config.py SCENE_DURATION_RANGE)
    dur_min, dur_max = SCENE_DURATION_RANGE
    dur_range_ok = True
    for i, s in enumerate(scripts):
        d = s.get("duration", 0)
        if not (dur_min <= d <= dur_max):
            dur_range_ok = False
            issues.append(f"Scene {i}: duration {d}s outside [{dur_min}-{dur_max}s]")
    checks["scene_duration_range"] = "PASS" if dur_range_ok else "FAIL"

    # Speaker rules
    speaker_ok = True
    for i, s in enumerate(scripts):
        speaker = s.get("speaker", "")
        if structure == "Monologue" and speaker != "A":
            speaker_ok = False
            issues.append(f"Scene {i}: Monologue expects speaker='A', got '{speaker}'")
        elif structure == "Dialogue" and speaker not in ("A", "B"):
            speaker_ok = False
            issues.append(f"Scene {i}: Dialogue expects speaker A/B, got '{speaker}'")
        elif structure == "Narrated Dialogue" and speaker not in ("Narrator", "A", "B"):
            speaker_ok = False
            issues.append(f"Scene {i}: Narrated Dialogue expects Narrator/A/B, got '{speaker}'")
    checks["speaker_rule"] = "PASS" if speaker_ok else "FAIL"

    # Speaker distribution check
    speakers_found = {s.get("speaker", "") for s in scripts}
    if structure == "Dialogue":
        missing = {"A", "B"} - speakers_found
        if missing:
            checks["speaker_distribution"] = "FAIL"
            issues.append(f"Dialogue requires both A and B, missing: {', '.join(sorted(missing))}")
        else:
            checks["speaker_distribution"] = "PASS"
    elif structure == "Narrated Dialogue":
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

    # Environment presence
    env_ok = all(s.get("environment") for s in scenes)
    checks["environment_present"] = "PASS" if env_ok else "WARN"
    if not env_ok:
        missing = [i for i, s in enumerate(scenes) if not s.get("environment")]
        issues.append(f"Scenes {missing}: missing environment")

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
