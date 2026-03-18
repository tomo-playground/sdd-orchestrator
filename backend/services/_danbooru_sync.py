"""Danbooru sync wrappers — async context 안전한 동기 호출 + 백그라운드 분류.

danbooru.py에서 분리. LangGraph 파이프라인(async) 안에서도 안전하게 호출 가능.
순환 import 방지를 위해 danbooru 모듈은 함수 내부에서 lazy import한다.
"""

from __future__ import annotations

import asyncio

from config import logger


def get_tag_info_sync(tag_name: str) -> dict | None:
    """Synchronous version of get_tag_info.

    Detects running event loop (e.g. inside LangGraph pipeline) and
    uses it directly instead of asyncio.run() which would fail.
    """
    from services.danbooru import get_tag_info  # noqa: PLC0415

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures  # noqa: PLC0415

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, get_tag_info(tag_name))
            try:
                return future.result(timeout=10)
            except Exception as e:
                logger.error("❌ [Danbooru] Thread wrapper error: %s", e)
                return None
    else:
        try:
            return asyncio.run(get_tag_info(tag_name))
        except Exception as e:
            logger.error("❌ [Danbooru] Sync wrapper error: %s", e)
            return None


def schedule_background_classification(unknown_tags: list[str]) -> None:
    """Schedule background Danbooru classification for unknown tags."""
    if not unknown_tags:
        return

    unique_tags = list(set(unknown_tags))
    logger.info("[Danbooru] Scheduling background classification for %d tags", len(unique_tags))

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _classify_tags_background, unique_tags)
    except RuntimeError:
        _classify_tags_background(unique_tags)


def _classify_general_tag(tag_name: str) -> str | None:
    """General 카테고리 태그의 SD group을 추론한다."""
    from services.keywords.patterns import CATEGORY_PATTERNS  # noqa: PLC0415

    tag_lower = tag_name.lower()
    for group, patterns in CATEGORY_PATTERNS.items():
        if tag_lower in patterns:
            return group
    return None


def _classify_tags_background(tags: list[str]) -> None:
    """Classify tags via Danbooru API in background (runs in thread)."""
    from services.danbooru import get_tag_info  # noqa: PLC0415

    for tag in tags:
        try:
            tag_info = asyncio.run(get_tag_info(tag))
            if tag_info and tag_info.get("post_count", 0) > 0:
                _store_tag_in_db(tag, tag_info)
                logger.info("[Danbooru BG] Classified: %s (%d posts)", tag, tag_info.get("post_count", 0))
            else:
                logger.debug("[Danbooru BG] Not found: %s", tag)
        except Exception as e:
            logger.debug("[Danbooru BG] Error for '%s': %s", tag, e)


def _store_tag_in_db(tag_name: str, tag_info: dict) -> None:
    """Store a validated tag in the DB for future fast-path lookups."""
    try:
        from database import SessionLocal  # noqa: PLC0415
        from models.tag import Tag  # noqa: PLC0415
        from services.danbooru import DANBOORU_CATEGORIES, classify_from_danbooru  # noqa: PLC0415

        db = SessionLocal()
        try:
            existing = db.query(Tag).filter(Tag.name == tag_name).first()
            if not existing:
                danbooru_cat_id = tag_info.get("category")
                danbooru_cat_name = DANBOORU_CATEGORIES.get(danbooru_cat_id, "general")
                sd_group = classify_from_danbooru(tag_info) or _classify_general_tag(tag_name)

                if danbooru_cat_name == "character":
                    category = "character"
                elif danbooru_cat_name == "meta" or sd_group == "quality":
                    category = "meta"
                else:
                    category = "scene"
                group_name = sd_group or "danbooru_validated"

                new_tag = Tag(name=tag_name, category=category, group_name=group_name)
                db.add(new_tag)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.debug("[Danbooru BG] DB store error for '%s': %s", tag_name, e)
