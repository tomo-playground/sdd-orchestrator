"""Danbooru API Service for tag classification.

Provides tag category information from Danbooru's database.
Used by TagClassifier for unknown tag classification.
"""

from __future__ import annotations

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
            logger.warning("⚡ [Danbooru] Circuit breaker OPEN — %d failures, skip for %ds", _circuit_failures, _CIRCUIT_COOLDOWN_SEC)
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

    # Action patterns
    if any(a in name for a in ["holding", "running", "walking", "jumping", "eating", "drinking", "reading"]):
        return "action"

    # Camera patterns
    if any(c in name for c in ["close-up", "portrait", "full body", "cowboy shot", "from above", "from below"]):
        return "camera"

    # Clothing patterns
    if any(
        c in name for c in ["dress", "shirt", "skirt", "uniform", "jacket", "coat", "hat", "glasses", "shoes", "boots"]
    ):
        return "clothing"

    # Location patterns
    if any(
        loc in name for loc in ["indoor", "outdoor", "room", "street", "forest", "beach", "city", "school", "office"]
    ):
        return "location_indoor" if "indoor" in name or "room" in name else "location_outdoor"

    # Time/Weather patterns
    if any(t in name for t in ["day", "night", "sunset", "rain", "snow", "sky", "cloud"]):
        return "time_weather"

    # Cannot classify
    return None


# Synchronous wrapper for use in non-async contexts
def get_tag_info_sync(tag_name: str) -> dict | None:
    """Synchronous version of get_tag_info."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create new loop
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_tag_info(tag_name))
                return future.result(timeout=5)
        else:
            return loop.run_until_complete(get_tag_info(tag_name))
    except Exception as e:
        logger.error("❌ [Danbooru] Sync wrapper error: %s", e)
        return None
