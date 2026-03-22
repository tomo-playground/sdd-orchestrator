"""Action Agent — 포즈, 액션, 감정, 소품, ControlNet 포즈.

Cinematographer Team의 두 번째 에이전트.
Framing 결과를 참조하여 각 씬의 동작/감정 레이어를 결정한다.
"""

from __future__ import annotations

import json

from config import pipeline_logger as logger

_SYSTEM = (
    "You are an Action Director for AI-generated short-form videos. "
    "Your ONLY job: assign emotion, action, pose, props, and controlnet_pose to each scene. "
    "Respond ONLY in valid JSON. No markdown, no explanation."
)

_RULES = """\
## Rules
0. **STAGE DIRECTION (최우선)**: If a scene has `stage_direction`, use it as the basis.
   - "문을 열고 들어선다" → full_body, from_behind, walking
   - "커피잔을 내려다본다" → holding_cup, looking_down
   - "놀라서 벌떡 일어난다" → standing, from_below
   - If no stage_direction, infer from script content.
1. **Emotion** (ONLY from this list):
   happy, excited, proud, confident, sad, lonely, grieving, anxious, nervous, scared,
   angry, frustrated, surprised, shocked, calm, peaceful, nostalgic, reflective,
   thoughtful, tense, determined, embarrassed, shy, hopeful, bittersweet, tired, confused,
   guilty, resigned, contempt
   ❌ FORBIDDEN: emotions not in list, compound emotions (lonely_expression)
2. **Pose variety**: Avoid standing + looking_at_viewer consecutively.
   - Standing combos: standing + (crossed_arms | hands_on_hips | arms_up | waving)
   - Sitting combos: sitting + (chin_rest | leaning_forward | eating)
   - Actions: walking, running, jumping, kneeling, crouching, lying, pointing_forward, covering_face
   - Daily: eating, cooking, holding_umbrella, writing, against_wall
   ❌ NEVER use generic `holding` alone — always specify: holding_phone, holding_cup, etc.
3. **Props** (based on script content):
   Phone scene: holding_phone, cellphone | Cooking: knife, frying_pan, plate
   Study: book, desk, pen | Office: computer, monitor | Outdoor: tree, bench
4. **ControlNet pose** (space format, NOT underscore):
   Valid: standing, waving, arms up, arms crossed, thumbs up, hands on hips,
   looking at viewer, from behind, sitting, chin rest, leaning, walking, running,
   jumping, lying, kneeling, crouching, pointing forward, covering face, eating,
   cooking, holding umbrella, writing, profile standing, standing looking up,
   leaning wall, sitting eating
   For Narrator scenes: set controlnet_pose to null.
5. **Narrator scenes**: No action/pose/emotion. Set all to null. Props only if relevant."""


async def run_action(
    scenes_json: str,
    framing_result: dict,
    characters_tags_block: str,
) -> dict | None:
    """Action Agent 실행 — 감정/액션/포즈/소품 결정.

    Returns:
        {"scenes": [{"order": N, "emotion": "...", "action": "...", "pose": "...",
                      "props": [...], "controlnet_pose": "..."}]}
    """
    from services.agent.nodes._cine_common import call_sub_agent  # noqa: PLC0415

    prompt = _build_prompt(scenes_json, framing_result, characters_tags_block)
    try:
        logger.info("[CineAction] 실행 시작")
        result = await call_sub_agent(
            prompt=prompt,
            system_instruction=_SYSTEM,
            trace_name="cinematographer.action",
            agent_name="CineAction",
            metadata={"template": "creative/cinematographer/action"},
        )
        if result:
            logger.info("[CineAction] 완료: %d scenes", len(result.get("scenes", [])))
        return result
    except Exception as e:
        logger.warning("[CineAction] 실패: %s", e)
        return None


def _build_prompt(scenes_json: str, framing_result: dict, characters_tags_block: str) -> str:
    framing_json = json.dumps(framing_result, ensure_ascii=False, indent=2) if framing_result else "{}"
    parts = [
        "## Task",
        "Assign emotion, action, pose, props, and controlnet_pose to each scene.",
        "Reference the Framing decisions to ensure consistency (e.g., camera=close-up → emotion should be intense).",
        "",
        "## Scenes",
        scenes_json,
        "",
        "## Framing Decisions (from Framing Agent)",
        framing_json,
    ]
    if characters_tags_block:
        parts.extend(["", characters_tags_block])
    parts.extend(["", _RULES])
    parts.extend(
        [
            "",
            "## Output (JSON only)",
            '{"scenes": [{"order": 0, "emotion": "nervous", "action": "holding_knife", '
            '"pose": "standing", "props": ["knife"], "controlnet_pose": "standing"}, ...]}',
        ]
    )
    return "\n".join(parts)
