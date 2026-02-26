"""Danbooru API Service for tag classification.

Provides tag category information from Danbooru's database.
Used by TagClassifier for unknown tag classification.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from config import DANBOORU_API_BASE, DANBOORU_API_TIMEOUT, DANBOORU_USER_AGENT, logger

# Circuit breaker: 연속 실패 시 Danbooru 호출 건너뛰기
_CIRCUIT_FAILURE_THRESHOLD = 3  # 연속 N회 실패 시 차단
_CIRCUIT_COOLDOWN_SEC = 60  # 차단 후 N초 후 재시도
_circuit_failures = 0
_circuit_open_until = 0.0

# Danbooru category IDs
DANBOORU_CATEGORIES = {
    0: "general",
    1: "artist",
    3: "copyright",
    4: "character",
    5: "meta",
}

# Mapping from Danbooru category to SD group
DANBOORU_TO_SD_GROUP = {
    "artist": "style",
    "character": "identity",
    "meta": "quality",
    # "general" needs further analysis
    # "copyright" is usually not useful
}


async def get_tag_info(tag_name: str) -> dict | None:
    """Get tag information from Danbooru API.

    Args:
        tag_name: Tag name (with underscores, e.g., "blue_hair")

    Returns:
        Tag info dict or None if not found
    """
    # Always normalize to pure tag name for Danbooru
    from .keywords.core import normalize_prompt_token

    normalized = normalize_prompt_token(tag_name)

    # Skip API calls for known quality/style tags that won't have useful Danbooru info
    from .keywords.patterns import CATEGORY_PATTERNS

    if normalized in CATEGORY_PATTERNS.get("quality", []) or normalized in CATEGORY_PATTERNS.get("style", []):
        return None

    # Circuit breaker check
    global _circuit_failures, _circuit_open_until
    now = time.monotonic()
    if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD and now < _circuit_open_until:
        return None
    if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD and now >= _circuit_open_until:
        logger.info("🔄 [Danbooru] Circuit breaker: retrying after cooldown")
        _circuit_failures = 0

    try:
        headers = {"User-Agent": DANBOORU_USER_AGENT}
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(
                f"{DANBOORU_API_BASE}/tags.json",
                params={"search[name]": normalized, "limit": 1},
                timeout=DANBOORU_API_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            _circuit_failures = 0  # 성공 시 리셋
            if data and len(data) > 0:
                tag_data = data[0]
                return {
                    "name": tag_data.get("name"),
                    "category": tag_data.get("category"),
                    "category_name": DANBOORU_CATEGORIES.get(tag_data.get("category")),
                    "post_count": tag_data.get("post_count", 0),
                }
            return None
    except (httpx.ConnectTimeout, httpx.ConnectError):
        _circuit_failures += 1
        if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD:
            _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN_SEC
            logger.warning(
                "⚡ [Danbooru] Circuit breaker OPEN — %d failures, skip for %ds",
                _circuit_failures,
                _CIRCUIT_COOLDOWN_SEC,
            )
        return None
    except httpx.HTTPError as e:
        logger.debug("⚠️ [Danbooru] API error for '%s': %s", normalized, e)
        return None
    except Exception as e:
        logger.error("❌ [Danbooru] Unexpected error for '%s': %s", tag_name, e)
        return None


async def get_wiki_info(tag_name: str) -> dict | None:
    """Get wiki information for a tag from Danbooru.

    Args:
        tag_name: Tag name

    Returns:
        Wiki info dict or None if not found
    """
    normalized = tag_name.lower().replace(" ", "_").strip()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DANBOORU_API_BASE}/wiki_pages/{normalized}.json",
                timeout=DANBOORU_API_TIMEOUT,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

            return {
                "title": data.get("title"),
                "body": data.get("body", ""),
                "other_names": data.get("other_names", []),
            }
    except httpx.HTTPError as e:
        logger.warning("⚠️ [Danbooru] Wiki API error for '%s': %s", tag_name, e)
        return None
    except Exception as e:
        logger.error("❌ [Danbooru] Unexpected wiki error for '%s': %s", tag_name, e)
        return None


def classify_from_danbooru(tag_info: dict) -> str | None:
    """Classify a tag based on Danbooru category.

    Args:
        tag_info: Tag info from get_tag_info()

    Returns:
        SD group name or None if cannot classify
    """
    if not tag_info:
        return None

    category_name = tag_info.get("category_name")

    # Direct mapping for non-general categories
    if category_name in DANBOORU_TO_SD_GROUP:
        return DANBOORU_TO_SD_GROUP[category_name]

    # General category needs further analysis based on tag name patterns
    if category_name == "general":
        name = tag_info.get("name", "")
        return _classify_general_tag(name)

    return None


def _classify_general_tag(tag_name: str) -> str | None:
    """Classify a general Danbooru tag using pattern matching.

    This is a fallback for when we can't determine the category
    from Danbooru's category alone.
    """
    name = tag_name.lower()

    # Hair patterns
    if "hair" in name:
        if any(
            c in name
            for c in [
                "blue",
                "red",
                "pink",
                "green",
                "white",
                "black",
                "brown",
                "blonde",
                "silver",
                "purple",
                "aqua",
                "orange",
            ]
        ):
            return "hair_color"
        if any(length in name for length in ["long", "short", "medium", "very long"]):
            return "hair_length"
        if any(s in name for s in ["twintails", "ponytail", "braid", "bun", "bob"]):
            return "hair_style"
        return "hair_style"

    # Eye patterns
    if "eyes" in name:
        return "eye_color"

    # Expression patterns
    if any(e in name for e in ["smile", "crying", "blush", "angry", "sad", "happy", "frown", "grin"]):
        return "expression"

    # Pose patterns
    if any(p in name for p in ["standing", "sitting", "lying", "kneeling", "crouching"]):
        return "pose"

    # Action patterns — try CATEGORY_PATTERNS exact match first
    from services.keywords.patterns import CATEGORY_PATTERNS

    for group_name, patterns in CATEGORY_PATTERNS.items():
        if name in patterns:
            return group_name

    # Fallback: suffix/keyword heuristics for novel tags
    if any(a in name for a in ["holding", "grabbing", "reaching", "pointing", "waving", "carrying"]):
        return "action_hand"
    if any(a in name for a in ["running", "walking", "jumping", "swimming", "fighting", "kicking"]):
        return "action_body"
    if any(a in name for a in ["eating", "drinking", "reading", "cooking", "sleeping", "bathing"]):
        return "action_daily"

    # Camera patterns
    if any(c in name for c in ["close-up", "portrait", "full body", "cowboy shot", "from above", "from below"]):
        return "camera"

    # Clothing patterns
    if any(c in name for c in ["dress", "uniform", "kimono", "outfit", "swimsuit"]):
        return "clothing_outfit"
    if any(c in name for c in ["shirt", "jacket", "coat", "sweater", "hoodie", "blazer", "vest"]):
        return "clothing_top"
    if any(c in name for c in ["skirt", "pants", "jeans", "shorts", "leggings"]):
        return "clothing_bottom"
    if any(c in name for c in ["thighhighs", "stockings", "pantyhose", "socks", "garter"]):
        return "legwear"
    if any(c in name for c in ["shoes", "boots", "sneakers", "sandals", "heels", "footwear", "barefoot"]):
        return "footwear"
    if any(c in name for c in ["hat", "glasses", "earrings", "necklace", "bag", "gloves", "choker"]):
        return "accessory"
    if any(c in name for c in ["sleeves", "collar", "ribbon", "frills", "lace", "belt", "hood"]):
        return "clothing_detail"

    # Location patterns
    if any(
        loc in name for loc in ["indoor", "outdoor", "room", "street", "forest", "beach", "city", "school", "office"]
    ):
        return "location_indoor" if "indoor" in name or "room" in name else "location_outdoor"

    # Time/Weather/Particle patterns
    if any(t in name for t in ["falling", "petals", "fireflies", "bubbles", "sparkles", "confetti", "particles"]):
        return "particle"
    if any(t in name for t in ["rain", "snow", "fog", "storm", "cloud", "wind"]):
        return "weather"
    if any(t in name for t in ["day", "night", "sunset", "sunrise", "morning", "evening", "dawn", "dusk"]):
        return "time_of_day"

    # Cannot classify
    return None


async def get_post_image(tag_name: str) -> dict | None:
    """Fetch a safe preview image URL for a tag from Danbooru posts.

    Queries ``rating:g`` (general) posts sorted by score descending and returns
    the first result's preview URL.

    Returns:
        ``{"preview_url": str, "post_id": int}`` or ``None``
    """
    global _circuit_failures, _circuit_open_until
    now = time.monotonic()
    if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD and now < _circuit_open_until:
        return None
    if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD and now >= _circuit_open_until:
        _circuit_failures = 0

    normalized = tag_name.lower().replace(" ", "_").strip()
    try:
        headers = {"User-Agent": DANBOORU_USER_AGENT}
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(
                f"{DANBOORU_API_BASE}/posts.json",
                params={
                    "tags": f"{normalized} rating:g score:>10",
                    "limit": 1,
                },
                timeout=DANBOORU_API_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            _circuit_failures = 0
            if data and len(data) > 0:
                post = data[0]
                preview = post.get("preview_file_url") or post.get("large_file_url")
                if preview:
                    return {"preview_url": preview, "post_id": post.get("id")}
            return None
    except (httpx.ConnectTimeout, httpx.ConnectError):
        _circuit_failures += 1
        if _circuit_failures >= _CIRCUIT_FAILURE_THRESHOLD:
            _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN_SEC
        return None
    except httpx.HTTPError as e:
        logger.debug("[Danbooru] Post image error for '%s': %s", normalized, e)
        return None
    except Exception as e:
        logger.error("[Danbooru] Unexpected post image error for '%s': %s", tag_name, e)
        return None


# Synchronous wrapper for use in non-async contexts
def get_tag_info_sync(tag_name: str) -> dict | None:
    """Synchronous version of get_tag_info.

    Safe to call from any thread (main, AnyIO worker, ThreadPoolExecutor).
    Always creates a fresh event loop via asyncio.run().
    """
    try:
        return asyncio.run(get_tag_info(tag_name))
    except Exception as e:
        logger.error("❌ [Danbooru] Sync wrapper error: %s", e)
        return None


def schedule_background_classification(unknown_tags: list[str]) -> None:
    """Schedule background Danbooru classification for unknown tags.

    Safe to call from both async and sync contexts.
    - async: uses run_in_executor to avoid blocking the event loop
    - sync: runs _classify_tags_background directly
    """
    if not unknown_tags:
        return

    unique_tags = list(set(unknown_tags))
    logger.info("[Danbooru] Scheduling background classification for %d tags", len(unique_tags))

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _classify_tags_background, unique_tags)
    except RuntimeError:
        _classify_tags_background(unique_tags)


def _classify_tags_background(tags: list[str]) -> None:
    """Classify tags via Danbooru API in background (runs in thread)."""
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
        from database import SessionLocal
        from models.tag import Tag

        db = SessionLocal()
        try:
            existing = db.query(Tag).filter(Tag.name == tag_name).first()
            if not existing:
                category = str(tag_info.get("category", "unknown"))
                new_tag = Tag(name=tag_name, category=category, group_name="danbooru_validated")
                db.add(new_tag)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.debug("[Danbooru BG] DB store error for '%s': %s", tag_name, e)
