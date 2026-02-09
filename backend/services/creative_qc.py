"""Quality Control validation for Creative Lab V2 pipeline outputs."""

from __future__ import annotations

from config import logger


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

    # Script length check
    length_pass = 0
    for i, s in enumerate(scripts):
        script_text = s.get("script", "")
        if language == "Korean":
            ok = 5 <= len(script_text) <= 40
        else:
            ok = 3 <= len(script_text.split()) <= 20
        if ok:
            length_pass += 1
        else:
            issues.append(f"Scene {i}: script length out of range ({len(script_text)} chars)")
    checks["script_length"] = "PASS" if length_pass == count else f"WARN {length_pass}/{count}"

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
    checks["speaker_rule"] = "PASS" if speaker_ok else "FAIL"

    # Duration sum check
    total_dur = sum(s.get("duration", 0) for s in scripts)
    dur_tolerance = duration * 0.3
    if abs(total_dur - duration) <= dur_tolerance:
        checks["duration_sum"] = "PASS"
    else:
        checks["duration_sum"] = "WARN"
        issues.append(f"Total duration {total_dur:.1f}s vs target {duration}s")

    ok = all(v == "PASS" for v in checks.values())
    if not ok:
        logger.info("[CreativeQC] Script issues: %s", issues)
    return {"ok": ok, "issues": issues, "checks": checks}


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

    ok = all(v == "PASS" for v in checks.values())
    if not ok:
        logger.info("[CreativeQC] Visual issues: %s", issues)
    return {"ok": ok, "issues": issues, "checks": checks}


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
