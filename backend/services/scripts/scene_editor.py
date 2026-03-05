"""Scene editor service — Gemini 기반 씬 일괄 편집."""

from __future__ import annotations

from config import logger
from schemas import ScriptEditedScene, ScriptEditResponse


async def edit_scenes(
    instruction: str,
    scenes: list[dict],
    context: dict,
) -> ScriptEditResponse:
    """Gemini를 호출하여 씬들을 편집 지시에 따라 수정한다."""

    from google.genai import types

    from config import GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client, template_env
    from services.creative_utils import parse_json_response

    fallback = ScriptEditResponse(edited_scenes=[], reasoning="", unchanged_count=len(scenes))

    if not gemini_client:
        logger.warning("[SceneEditor] Gemini 클라이언트 미설정, 빈 결과 반환")
        return fallback

    try:
        tmpl = template_env.get_template("creative/edit_scenes.j2")
        prompt = tmpl.render(instruction=instruction, scenes=scenes, context=context)
        edit_config = types.GenerateContentConfig(
            system_instruction="You are a scene editor for short-form video scripts. Edit scenes according to the given instruction while preserving overall narrative coherence.",
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=edit_config,
        )
        parsed = parse_json_response(response.text or "")
    except Exception as e:
        logger.warning("[SceneEditor] Gemini 호출/파싱 실패: %s", e)
        return fallback

    if not isinstance(parsed, dict):
        logger.warning("[SceneEditor] 응답이 dict가 아님: %s", type(parsed).__name__)
        return fallback

    return _validate_edit_response(parsed, len(scenes))


def _validate_edit_response(parsed: dict, total_scenes: int) -> ScriptEditResponse:
    """LLM 응답을 검증하고 ScriptEditResponse로 변환한다."""
    raw_scenes = parsed.get("edited_scenes", [])
    valid_fields = {"script", "speaker", "duration", "image_prompt", "image_prompt_ko"}

    edited: list[ScriptEditedScene] = []
    seen_indices: set[int] = set()
    for item in raw_scenes:
        idx = item.get("scene_index")
        if not isinstance(idx, int) or idx < 0 or idx >= total_scenes:
            continue
        if idx in seen_indices:
            continue
        seen_indices.add(idx)
        # 변경된 필드만 추출, 모든 필드가 None이면 무시
        changes = {k: item[k] for k in valid_fields if item.get(k) is not None}
        if not changes:
            continue
        edited.append(ScriptEditedScene(scene_index=idx, **changes))

    return ScriptEditResponse(
        edited_scenes=edited,
        reasoning=parsed.get("reasoning", ""),
        unchanged_count=total_scenes - len(edited),
    )
