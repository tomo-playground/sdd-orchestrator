"""Compositor — 크로스 도메인 정합성 추론 + 태그 검증 + 최종 JSON 조립.

Cinematographer Team의 마지막 에이전트.
Framing/Action/Atmosphere 3명의 결과를 통합하고, 충돌을 추론으로 해소하며,
최종 scenes JSON을 조립한다.
"""

from __future__ import annotations

import json

from config import pipeline_logger as logger
from services.agent.nodes._cine_common import parse_scenes

_SYSTEM = (
    "You are a Visual Compositor for AI-generated short-form videos. "
    "Your job: merge 3 specialists' outputs into a coherent final design, "
    "resolve cross-domain conflicts by REASONING (not rules), "
    "and produce the final scenes JSON. Respond ONLY in valid JSON."
)


async def run_compositor(
    scenes_json: str,
    framing_result: dict,
    action_result: dict,
    atmosphere_result: dict,
    characters_tags_block: str,
    style_section: str,
    image_prompt_ko_rules: str,
    emotion_consistency_rules: str,
    tools: list | None = None,
    tool_executors: dict | None = None,
    is_multi: bool = False,
    multi_rules_block: str = "",
) -> tuple[list[dict] | None, list]:
    """Compositor 실행 — 최종 scenes JSON 조립.

    Returns:
        (scenes_list, tool_logs) — scenes_list is None on failure
    """
    prompt = _build_prompt(
        scenes_json,
        framing_result,
        action_result,
        atmosphere_result,
        characters_tags_block,
        style_section,
        image_prompt_ko_rules,
        emotion_consistency_rules,
        multi_rules_block=multi_rules_block,
    )
    tool_logs: list = []

    try:
        logger.info("[CineCompositor] 실행 시작")
        if tools and tool_executors:
            from services.agent.tools.base import call_with_tools  # noqa: PLC0415

            response, tool_logs, _obs_id = await call_with_tools(
                prompt=prompt,
                tools=tools,
                tool_executors=tool_executors,
                max_calls=8,
                trace_name="cinematographer.compositor",
                temperature=0.2,
                system_instruction=_SYSTEM,
                metadata={"template": "creative/cinematographer/compositor"},
            )
        else:
            from services.agent.tools.base import call_direct  # noqa: PLC0415

            response = await call_direct(
                prompt=prompt,
                trace_name="cinematographer.compositor",
                temperature=0.2,
                system_instruction=_SYSTEM,
                metadata={"template": "creative/cinematographer/compositor"},
            )
        scenes = parse_scenes(response)
        if scenes:
            logger.info("[CineCompositor] 완료: %d scenes, %d tool calls", len(scenes), len(tool_logs))
        else:
            logger.warning("[CineCompositor] 파싱 실패")
        return scenes, tool_logs
    except Exception as e:
        logger.warning("[CineCompositor] 실패: %s", e)
        return None, tool_logs


def _build_prompt(
    scenes_json: str,
    framing_result: dict,
    action_result: dict,
    atmosphere_result: dict,
    characters_tags_block: str,
    style_section: str,
    image_prompt_ko_rules: str,
    emotion_consistency_rules: str,
    *,
    multi_rules_block: str = "",
) -> str:
    framing_json = json.dumps(framing_result, ensure_ascii=False, indent=2) if framing_result else "{}"
    action_json = json.dumps(action_result, ensure_ascii=False, indent=2) if action_result else "{}"
    atmo_json = json.dumps(atmosphere_result, ensure_ascii=False, indent=2) if atmosphere_result else "{}"

    return "\n".join(
        [
            "## Task",
            "Merge 3 specialists' visual decisions into the FINAL scenes JSON.",
            "Your key responsibility: **cross-domain consistency reasoning**.",
            "",
            "## Original Scenes",
            scenes_json,
            "",
            "## Framing Decisions (camera, gaze, ken_burns)",
            framing_json,
            "",
            "## Action Decisions (emotion, action, pose, props, controlnet_pose)",
            action_json,
            "",
            "## Atmosphere Decisions (environment, cinematic)",
            atmo_json,
            "",
            characters_tags_block or "",
            style_section or "",
            "",
            "## Cross-Domain Consistency (REASON, don't just apply rules)",
            "Examples of conflicts you MUST detect and resolve:",
            "- close-up camera + holding_phone → phone may not be visible in frame → widen to cowboy_shot OR remove phone",
            "- sitting + full_body → deformed legs → MUST use upper_body or cowboy_shot",
            "- dark environment + sunlight cinematic → contradiction → pick one",
            "- indoor environment + outdoor atmosphere → contradiction → fix environment",
            "- nervous emotion + smile expression → emotional contradiction → pick one",
            "When resolving: explain your reasoning in the `compositor_note` field (optional, for debugging).",
            "",
            "## Tag Rules",
            "- Use ONLY Danbooru-standard tags (underscore format: brown_hair, cowboy_shot)",
            "- ❌ FORBIDDEN: made-up tags, emotion adjectives, gender tags (system injects 1girl/1boy)",
            "- For Narrator scenes: add no_humans, scenery. Set negative_prompt_extra to '1girl, 1boy, person'",
            "- negative_prompt_extra: scene-specific exclusions only. Empty string if none needed.",
            "",
            f"## image_prompt_ko rules:\n{image_prompt_ko_rules}" if image_prompt_ko_rules else "",
            emotion_consistency_rules or "",
            "",
            multi_rules_block or "",
            "",
            "## Assembly Instructions",
            "For each scene, merge all agents' outputs into context_tags and build:",
            "1. context_tags: {emotion, camera, action, pose, gaze, environment, cinematic, props}",
            "2. image_prompt: flat comma-separated Danbooru tags (NO character identity/clothing)",
            "3. image_prompt_ko: ONE natural Korean sentence (action + emotion + environment)",
            "   **CRITICAL**: The location/place in image_prompt_ko MUST match context_tags.environment.",
            "   Use the Atmosphere agent's environment tags as the ONLY source of truth for the scene's location.",
            "   ❌ BAD: environment=['subway_car'] but image_prompt_ko mentions '사무실' (office)",
            "   ✅ GOOD: environment=['subway_car'] → image_prompt_ko: '지하철 안에서 미소 지으며 인사하는 모습'",
            "4. Keep original fields: order, script, speaker, duration",
            "5. Copy camera, environment (first item) to top-level fields",
            "6. Copy controlnet_pose and ken_burns_preset from sub-agents",
            "7. negative_prompt_extra and ip_adapter_weight (null)",
            "",
            "## JSON Safety",
            "Do NOT use backslashes in text. Avoid unescaped quotes inside strings.",
            "",
            _OUTPUT_FORMAT,
        ]
    )


_OUTPUT_FORMAT = """\
## Output Format (JSON only, no markdown wrapping)
{"scenes": [{"order": 0, "scene_mode": "single", "script": "원본 대사", "speaker": "A", "duration": 2.5,
"camera": "close-up", "environment": "kitchen",
"image_prompt": "nervous, holding_knife, kitchen, close-up, indoors, depth_of_field",
"image_prompt_ko": "어두운 주방에서 긴장한 표정으로 칼을 잡고 있는 모습",
"context_tags": {"emotion": "nervous", "camera": "close-up", "action": "holding_knife",
"pose": "standing", "gaze": "looking_down", "environment": ["kitchen", "indoors"],
"cinematic": ["depth_of_field"], "props": ["knife"]},
"controlnet_pose": "standing", "ip_adapter_weight": null,
"negative_prompt_extra": "", "ken_burns_preset": "zoom_in_center"}, ...]}"""
