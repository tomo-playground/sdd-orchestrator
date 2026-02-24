"""Auto-regeneration helpers for critical failure recovery.

Validates generated images for critical failures (gender swap, missing subject,
count mismatch) and provides seed shifting for retry attempts.
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image

from config import SEED_ANCHOR_OFFSET, logger


def validate_for_critical_failure(result: dict, prompt: str) -> dict[str, Any] | None:
    """Check a generation result for critical failures via WD14.

    Args:
        result: Generation result dict containing "image" (base64 PNG).
        prompt: The prompt used for generation.

    Returns:
        CriticalFailure dict if failure detected, None if OK or WD14 unavailable.
    """
    image_b64 = result.get("image")
    if not image_b64 or not prompt:
        return None

    try:
        from services.image import load_image_bytes
        from services.validation import wd14_predict_tags

        image_bytes = load_image_bytes(f"data:image/png;base64,{image_b64}")
        image = Image.open(io.BytesIO(image_bytes))
        tags = wd14_predict_tags(image)

        from services.critical_failure import detect_critical_failure

        failure_result = detect_critical_failure(prompt, tags)
        if failure_result.has_failure:
            return failure_result.to_dict()
        return None
    except Exception as exc:
        logger.warning("WD14 critical failure check skipped: %s", exc)
        return None


def has_critical_failure(result: dict) -> bool:
    """Check if a result dict contains critical failure info."""
    cf = result.get("_critical_failure")
    return bool(cf and cf.get("has_failure"))


_FAILURE_LABELS: dict[str, str] = {
    "gender_swap": "성별 반전",
    "no_subject": "인물 미감지",
    "count_mismatch": "인물수 불일치",
}


def describe_failure(result: dict) -> str:
    """Return human-readable description of critical failure."""
    cf = result.get("_critical_failure")
    if not cf or not cf.get("failures"):
        return ""
    labels: list[str] = [_FAILURE_LABELS.get(f["failure_type"], f["failure_type"]) for f in cf["failures"]]
    return ", ".join(labels)


def shift_seed_for_retry(request, retry_count: int) -> None:
    """Shift seed for retry attempt.

    - seed == -1: keep (SD generates random seed each time)
    - seed > 0: offset by SEED_ANCHOR_OFFSET * retry_count
    """
    current_seed = getattr(request, "seed", -1)
    if current_seed <= 0:
        return
    new_seed = (current_seed + SEED_ANCHOR_OFFSET * retry_count) % (2**31)
    request.seed = new_seed
    logger.info("[Auto-Regen] Seed shifted: %d → %d (retry #%d)", current_seed, new_seed, retry_count)
