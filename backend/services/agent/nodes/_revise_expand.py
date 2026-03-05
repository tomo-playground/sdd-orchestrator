"""Revise Tier 2: 씬 개수 부족 시 기존 씬 보존 + 부족분만 확장 생성.

전체 재생성(Tier 3) 대신 Gemini에 새 씬만 요청하여 비용·시간·품질을 개선한다.
"""

from __future__ import annotations

import json
import re

from config import SCENE_DURATION_RANGE, logger
from services.agent.observability import trace_llm_call
from services.agent.state import ScriptState, extract_selected_concept
from services.storyboard.helpers import strip_markdown_codeblock

_DEFICIT_RE = re.compile(r"씬 개수 부족:\s*(\d+)개\s*\(최소\s*(\d+)개")

# 규칙 수정 가능한 에러 패턴 (Tier 1에서 처리)
_RULE_FIXABLE_RE = re.compile(r"씬 \d+: (duration이 0 이하|필수 필드)")


def parse_scene_deficit(errors: list[str]) -> tuple[int, int] | None:
    """에러 목록에서 씬 개수 부족 정보를 파싱한다.

    Returns:
        (current_count, target_min) 또는 매치 없으면 None.
    """
    for err in errors:
        if m := _DEFICIT_RE.search(err):
            return int(m.group(1)), int(m.group(2))
    return None


def can_use_expansion(errors: list[str]) -> bool:
    """씬 부족이 유일한 미해결 에러(규칙 수정 불가)인지 판단한다."""
    non_deficit = []
    has_deficit = False
    for err in errors:
        if _DEFICIT_RE.search(err):
            has_deficit = True
        elif _RULE_FIXABLE_RE.search(err):
            pass  # Tier 1에서 처리 가능 → 무시
        else:
            non_deficit.append(err)
    return has_deficit and len(non_deficit) == 0


def merge_expanded_scenes(existing: list[dict], new_scenes: list[dict]) -> list[dict]:
    """insert_after 기반으로 새 씬을 삽입하고 scene_id를 재번호화한다."""
    # insert_after → 삽입할 씬 목록 매핑
    inserts: dict[int, list[dict]] = {}
    for ns in new_scenes:
        pos = ns.get("insert_after", len(existing) - 1)
        pos = max(-1, min(pos, len(existing) - 1))
        inserts.setdefault(pos, []).append(ns)

    result: list[dict] = []
    # insert_after=-1 → 맨 앞
    for ns in inserts.get(-1, []):
        result.append(ns)
    for i, scene in enumerate(existing):
        result.append(scene)
        for ns in inserts.get(i, []):
            result.append(ns)

    # scene_id 재번호화 + insert_after 제거
    for idx, scene in enumerate(result):
        scene["scene_id"] = idx + 1
        scene.pop("insert_after", None)
        scene["order"] = idx

    return result


def redistribute_durations(scenes: list[dict], target_duration: int, language: str = "Korean") -> None:
    """총 duration을 target_duration에 맞게 비례 재분배한다.

    스케일다운: reading-time floor 적용.
    스케일업: 원래 duration을 floor로 사용하여 확대 여지를 확보한다.
    2차 보정: 총합이 target에 부족하면 균등 분배한다.
    """
    from services.storyboard.helpers import estimate_reading_duration

    if not scenes:
        return

    total = sum(s.get("duration", 0) for s in scenes)
    if total <= 0 or abs(total - target_duration) < 0.5:
        return

    from config import SCENE_DURATION_MAX

    ratio = target_duration / total

    for scene in scenes:
        script = scene.get("script", "").strip()
        min_dur = estimate_reading_duration(script, language) if script else 2.0
        raw = scene.get("duration", min_dur) * ratio
        # 스케일업 시: reading-time floor 대신 원래 duration을 floor로 사용
        floor = scene.get("duration", min_dur) if ratio > 1 else min_dur
        scene["duration"] = round(max(floor, min(SCENE_DURATION_MAX, raw)), 1)

    # 2차 보정: 총합이 target에 부족하면 균등 분배
    new_total = sum(s["duration"] for s in scenes)
    gap = target_duration - new_total
    if gap > 0.5:
        per_scene = gap / len(scenes)
        for scene in scenes:
            scene["duration"] = round(min(SCENE_DURATION_MAX, scene["duration"] + per_scene), 1)


def postprocess_new_scenes(new_scenes: list[dict], language: str = "Korean") -> None:
    """새 씬에만 태그 정규화 + negative prompt + duration 재계산을 적용한다."""
    from config import DEFAULT_SCENE_NEGATIVE_PROMPT, ENABLE_DANBOORU_VALIDATION
    from services.keywords import filter_prompt_tokens
    from services.prompt import (
        normalize_and_fix_tags,
        normalize_prompt_tokens,
        validate_tags_with_danbooru,
    )
    from services.storyboard.helpers import estimate_reading_duration

    for scene in new_scenes:
        # Duration auto-calculation from reading time
        script = scene.get("script", "").strip()
        if script:
            scene["duration"] = estimate_reading_duration(script, language)
        raw_prompt = scene.get("image_prompt", "")
        if not raw_prompt:
            continue

        normalized = normalize_and_fix_tags(raw_prompt)

        if ENABLE_DANBOORU_VALIDATION:
            tags = [t.strip() for t in normalized.split(",") if t.strip()]
            validated = validate_tags_with_danbooru(tags)
            normalized = ", ".join(validated)

        filtered = filter_prompt_tokens(normalized)
        if not filtered:
            filtered = normalize_prompt_tokens(normalized)

        scene["image_prompt"] = filtered

        if not scene.get("negative_prompt"):
            scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT


async def postprocess_new_scenes_async(new_scenes: list[dict], language: str = "Korean") -> list[str]:
    """Async version: DB cache only, returns unknown tags for background classification."""
    from config import DEFAULT_SCENE_NEGATIVE_PROMPT, ENABLE_DANBOORU_VALIDATION
    from services.keywords import filter_prompt_tokens
    from services.prompt import normalize_and_fix_tags, normalize_prompt_tokens
    from services.prompt.prompt import validate_tags_with_danbooru_async
    from services.storyboard.helpers import estimate_reading_duration

    all_unknown: list[str] = []

    for scene in new_scenes:
        script = scene.get("script", "").strip()
        if script:
            scene["duration"] = estimate_reading_duration(script, language)
        raw_prompt = scene.get("image_prompt", "")
        if not raw_prompt:
            continue

        normalized = normalize_and_fix_tags(raw_prompt)

        if ENABLE_DANBOORU_VALIDATION:
            tags = [t.strip() for t in normalized.split(",") if t.strip()]
            validated, unknown = await validate_tags_with_danbooru_async(tags)
            normalized = ", ".join(validated)
            all_unknown.extend(unknown)

        filtered = filter_prompt_tokens(normalized)
        if not filtered:
            filtered = normalize_prompt_tokens(normalized)

        scene["image_prompt"] = filtered

        if not scene.get("negative_prompt"):
            scene["negative_prompt"] = DEFAULT_SCENE_NEGATIVE_PROMPT

    return all_unknown


async def try_scene_expand(
    scenes: list[dict],
    state: ScriptState,
    deficit: int,
    target_min: int,
) -> list[dict] | None:
    """Gemini에 부족한 씬만 생성 요청하여 기존 씬에 병합한다.

    실패 시 None을 반환하여 Tier 3(전체 재생성)으로 fallback.
    """

    from google.genai import types

    from config import GEMINI_SAFETY_SETTINGS, GEMINI_TEXT_MODEL, gemini_client, template_env

    if not gemini_client:
        logger.warning("[Revise] Expansion: Gemini 클라이언트 없음, 건너뜀")
        return None

    try:
        tmpl = template_env.get_template("creative/scene_expand.j2")

        # 피드백 수집
        review = state.get("review_result") or {}
        feedback_parts: list[str] = []
        if errs := review.get("errors"):
            feedback_parts.append(f"Errors: {'; '.join(errs)}")
        if reflection := state.get("review_reflection"):
            feedback_parts.append(reflection)

        # 캐릭터 컨텍스트
        char_ctx = ""
        if cid := state.get("character_id"):
            char_ctx = f"character_id={cid}"

        min_dur, max_dur = SCENE_DURATION_RANGE

        prompt = tmpl.render(
            existing_scenes_json=json.dumps(scenes, ensure_ascii=False, indent=2),
            existing_count=len(scenes),
            target_min=target_min,
            deficit=deficit,
            duration=state.get("duration", 10),
            topic=state.get("topic", ""),
            language=state.get("language", "Korean"),
            structure=state.get("structure", "Monologue"),
            style=state.get("style", "Anime"),
            selected_concept=extract_selected_concept(state),
            character_context=char_ctx,
            scene_dur_min=min_dur,
            scene_dur_max=max_dur,
            feedback="\n".join(feedback_parts) if feedback_parts else "",
        )

        expand_config = types.GenerateContentConfig(
            system_instruction="You are a scene expansion specialist for short-form video scripts. Generate new scenes that seamlessly integrate with existing ones.",
            safety_settings=GEMINI_SAFETY_SETTINGS,
        )
        async with trace_llm_call(name="revise_scene_expand", input_text=prompt[:2000]) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
                config=expand_config,
            )
            llm.record(response)

        raw = strip_markdown_codeblock(response.text or "")
        new_scenes = json.loads(raw)

        if not isinstance(new_scenes, list) or len(new_scenes) == 0:
            logger.warning("[Revise] Expansion: 빈 결과 반환")
            return None

        from services.danbooru import schedule_background_classification

        unknown_tags = await postprocess_new_scenes_async(new_scenes, language=state.get("language", "Korean"))
        schedule_background_classification(unknown_tags)
        merged = merge_expanded_scenes([s.copy() for s in scenes], new_scenes)

        logger.info(
            "[Revise] Expansion 완료: %d → %d씬 (+%d)",
            len(scenes),
            len(merged),
            len(new_scenes),
        )
        return merged

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("[Revise] Expansion 파싱 실패: %s", e)
        return None
    except Exception as e:
        logger.warning("[Revise] Expansion Gemini 호출 실패: %s", e)
        return None
