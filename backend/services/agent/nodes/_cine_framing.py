"""Framing Agent — 카메라, 시선, Ken Burns, 서사 구조 매핑.

Cinematographer Team의 첫 번째 에이전트.
각 씬의 카메라 앵글, 시선 방향, Ken Burns 모션을 결정한다.
"""

from __future__ import annotations

from config import pipeline_logger as logger

_SYSTEM = (
    "You are a Framing Specialist for AI-generated short-form videos. "
    "Your ONLY job: assign camera angle, gaze direction, and Ken Burns motion to each scene. "
    "Respond ONLY in valid JSON. No markdown, no explanation."
)

_RULES = """\
## Rules
1. **Camera variety**: Use at least 3 different angles across scenes.
   Available: close-up, cowboy_shot, upper_body, full_body, from_above, from_below, dutch_angle
   ⚠️ SITTING + CAMERA: sitting requires upper_body or cowboy_shot ONLY.
2. **Gaze variety**: Do NOT use looking_at_viewer on more than 2 scenes.
   - Introspective: looking_down, looking_to_the_side, closed_eyes
   - Dramatic: looking_back, looking_up, looking_afar
   - Direct (hook/climax only): looking_at_viewer
   Best pairings: looking_back→from_behind, looking_up→from_below, looking_down→from_above
3. **Narrative → Camera**:
   | Role | Camera | Purpose |
   | Hook (scene 0-1) | dutch_angle, close-up | Grab attention |
   | Rising | from_side, cowboy_shot | Build tension |
   | Climax | from_below, close-up | Maximum impact |
   | Resolution | wide_shot, from_above | Release |
4. **Ken Burns** (no consecutive repeats):
   Hook: zoom_in_center, zoom_in_bottom | Rising: pan_zoom_up, zoom_pan_right
   Climax: zoom_in_center, zoom_in_top | Resolution: zoom_out_center, pan_down_vertical
   Available: slow_zoom, zoom_in_center, zoom_out_center, pan_left, pan_right, pan_up, pan_down,
   zoom_pan_left, zoom_pan_right, pan_up_vertical, pan_down_vertical, zoom_in_bottom,
   zoom_in_top, pan_zoom_up, pan_zoom_down
5. **Narrator scenes** (speaker="narrator"): wide_shot or from_above preferred. ken_burns still required.
   - Crowd Narrator: wide_shot strongly preferred to capture multiple people."""


async def run_framing(
    scenes_json: str,
    visual_direction: str,
    writer_plan_section: str,
) -> dict | None:
    """Framing Agent 실행 — 카메라/시선/Ken Burns 결정.

    Returns:
        {"scenes": [{"order": N, "camera": "...", "gaze": "...",
                      "ken_burns_preset": "...", "narrative_function": "..."}]}
    """
    from services.agent.nodes._cine_common import call_sub_agent  # noqa: PLC0415

    prompt = _build_prompt(scenes_json, visual_direction, writer_plan_section)
    try:
        logger.info("[CineFraming] 실행 시작")
        result = await call_sub_agent(
            prompt=prompt,
            system_instruction=_SYSTEM,
            trace_name="cinematographer.framing",
            agent_name="CineFraming",
            metadata={"template": "creative/cinematographer/framing"},
        )
        if result:
            logger.info("[CineFraming] 완료: %d scenes", len(result.get("scenes", [])))
        return result
    except Exception as e:
        logger.warning("[CineFraming] 실패: %s", e)
        return None


def _build_prompt(scenes_json: str, visual_direction: str, writer_plan_section: str) -> str:
    parts = ["## Task", "Assign camera, gaze, and ken_burns_preset to each scene.", "", "## Scenes", scenes_json]
    if visual_direction:
        parts.extend(["", "## Visual Direction (from Director)", visual_direction])
    if writer_plan_section:
        parts.extend(["", writer_plan_section])
    parts.extend(["", _RULES])
    parts.extend(
        [
            "",
            "## Output (JSON only)",
            '{"scenes": [{"order": 0, "camera": "close-up", "gaze": "looking_down", '
            '"ken_burns_preset": "zoom_in_center", "narrative_function": "hook"}, ...]}',
        ]
    )
    return "\n".join(parts)
