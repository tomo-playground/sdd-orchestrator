"""Atmosphere Agent — 환경, 시네마틱 기법, 장소 연속성.

Cinematographer Team의 세 번째 에이전트.
Framing/Action 결과를 참조하여 각 씬의 환경과 분위기를 결정한다.
"""

from __future__ import annotations

import json

from config import REFERENCE_ADAIN_CONFLICTING_TAGS
from config import pipeline_logger as logger

_SYSTEM = (
    "You are an Atmosphere Designer for AI-generated short-form videos. "
    "Your ONLY job: assign environment tags and cinematic techniques to each scene. "
    "Respond ONLY in valid JSON. No markdown, no explanation."
)

_RULES = """\
## Rules
1. **Environment consistency**: Same location across consecutive scenes MUST use identical tags.
   - A location change is ONLY valid when script shows physical movement.
   - If a Location Map is provided, follow it exactly.
   - Include furniture/props that anchor the scene: office_chair, desk, bed, sofa
   - Do NOT add weather tags (rain, cloud, moon) unless script mentions them.
   - Indoor scenes: do NOT add outdoor tags.
2. **Cinematic techniques** (max 2 per scene):
   - Lighting: backlit, sidelighting, sunlight, moonlight, light_rays
   - Depth: depth_of_field, bokeh, blurry_background
   - Atmosphere: lens_flare, dust_particles, silhouette, chromatic_aberration
   - Time: sunset, dusk, dawn
   ❌ INVALID: rim_light, dramatic_lighting, cinematic_lighting, warm_lighting, cold_lighting
   - Consistency within a location: use similar "palette" unless emotion demands change.
3. **Emotion → Visual cues** (match the Action Agent's emotion):
   - Tension/Fear: dark, shadow
   - Sadness: moonlight, depth_of_field
   - Joy/Hope: sunlight, bright, light_rays
   - Determination: backlit
   - Loneliness: depth_of_field, silhouette
   - Anger: shadow, high_contrast
   - Nostalgia: sunset, bokeh, dusk
4. **Narrator scenes**: Use cinematic techniques aggressively.
   - depth_of_field, light_rays, sunset, silhouette, wide establishing shots."""

_CONFLICTING_TAGS_STR = ", ".join(sorted(REFERENCE_ADAIN_CONFLICTING_TAGS))
_ADAIN_WARNING = f"""\
## ⚠️ Reference AdaIN Active
이 영상은 배경 참조 이미지(Reference AdaIN)가 활성화되어 있습니다.
{_CONFLICTING_TAGS_STR}는 배경과 충돌하므로 사용하지 마세요.
대안: backlit, light_rays, dust_particles 등 비충돌 태그를 활용하세요."""


async def run_atmosphere(
    scenes_json: str,
    framing_result: dict,
    action_result: dict,
    style_section: str,
    writer_plan_section: str,
    has_environment_reference: bool = False,
) -> dict | None:
    """Atmosphere Agent 실행 — 환경/시네마틱 결정.

    Returns:
        {"scenes": [{"order": N, "environment": [...], "cinematic": [...]}]}
    """
    from services.agent.nodes._cine_common import call_sub_agent  # noqa: PLC0415

    prompt = _build_prompt(
        scenes_json, framing_result, action_result, style_section, writer_plan_section, has_environment_reference
    )
    try:
        logger.info("[CineAtmosphere] 실행 시작")
        result = await call_sub_agent(
            prompt=prompt,
            system_instruction=_SYSTEM,
            trace_name="cinematographer.atmosphere",
            agent_name="CineAtmosphere",
            metadata={"template": "creative/cinematographer/atmosphere"},
        )
        if result:
            logger.info("[CineAtmosphere] 완료: %d scenes", len(result.get("scenes", [])))
        return result
    except Exception as e:
        logger.warning("[CineAtmosphere] 실패: %s", e)
        return None


def _build_prompt(
    scenes_json: str,
    framing_result: dict,
    action_result: dict,
    style_section: str,
    writer_plan_section: str,
    has_environment_reference: bool = False,
) -> str:
    framing_json = json.dumps(framing_result, ensure_ascii=False, indent=2) if framing_result else "{}"
    action_json = json.dumps(action_result, ensure_ascii=False, indent=2) if action_result else "{}"
    parts = [
        "## Task",
        "Assign environment tags and cinematic techniques to each scene.",
        "Reference Framing (camera) and Action (emotion) to ensure visual coherence.",
        "",
        "## Scenes",
        scenes_json,
        "",
        "## Framing Decisions",
        framing_json,
        "",
        "## Action Decisions",
        action_json,
    ]
    if style_section:
        parts.extend(["", style_section])
    if writer_plan_section:
        parts.extend(["", writer_plan_section])
    parts.extend(["", _RULES])
    if has_environment_reference:
        parts.extend(
            [
                "",
                _ADAIN_WARNING,
            ]
        )
    parts.extend(
        [
            "",
            "## Output (JSON only)",
            '{"scenes": [{"order": 0, "environment": ["kitchen", "indoors"], "cinematic": ["depth_of_field"]}, ...]}',
        ]
    )
    return "\n".join(parts)
