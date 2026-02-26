"""Finalize 단계 미분류 태그 사전 분류.

image_prompt의 미분류 태그를 LLM으로 분류 후 DB에 저장하여
이미지 생성 시 정확한 레이어 배정을 보장한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config import logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _extract_all_scene_tags(scenes: list[dict]) -> list[str]:
    """모든 scene의 image_prompt + context_tags에서 태그 추출 및 중복 제거."""
    all_tags: list[str] = []
    seen: set[str] = set()

    for scene in scenes:
        # image_prompt에서 추출
        prompt = scene.get("image_prompt", "")
        if prompt:
            for token in prompt.split(","):
                tag = token.strip()
                if tag and tag not in seen:
                    seen.add(tag)
                    all_tags.append(tag)

        # context_tags에서 Danbooru 태그 필드만 추출 (emotion 등 비태그 필드 제외)
        ctx = scene.get("context_tags") or {}
        _TAG_FIELDS = ("expression", "gaze", "pose", "camera", "mood")
        for key in _TAG_FIELDS:
            value = ctx.get(key)
            if isinstance(value, str) and value:
                if value not in seen:
                    seen.add(value)
                    all_tags.append(value)
        # environment는 리스트일 수 있음
        env = ctx.get("environment")
        if isinstance(env, list):
            for item in env:
                if isinstance(item, str) and item and item not in seen:
                    seen.add(item)
                    all_tags.append(item)
        elif isinstance(env, str) and env and env not in seen:
            seen.add(env)
            all_tags.append(env)

    return all_tags


async def classify_unknown_scene_tags(scenes: list[dict], db: Session) -> int:
    """image_prompt의 미분류 태그를 LLM으로 분류 후 DB 저장.

    Returns:
        분류된 태그 수
    """
    from services.prompt.v3_composition import V3PromptBuilder
    from services.tag_classifier import TagClassifier

    all_tags = _extract_all_scene_tags(scenes)
    if not all_tags:
        return 0

    builder = V3PromptBuilder(db)
    unknown_tags = builder.find_unknown_tags(all_tags)
    if not unknown_tags:
        logger.info("[Tag Classification] No unknown tags found")
        return 0

    logger.info("[Tag Classification] %d unknown tags detected, classifying via LLM...", len(unknown_tags))

    classifier = TagClassifier(db)
    results = await classifier.classify_batch_with_llm(unknown_tags)

    classified = sum(1 for r in results.values() if r.get("group"))
    logger.info("[Tag Classification] LLM: %d/%d reclassified", classified, len(unknown_tags))
    return classified
