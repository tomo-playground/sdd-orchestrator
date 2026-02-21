"""Seed Anchoring — deterministic seed resolution for consistent scene generation.

Ensures scenes within the same storyboard start from similar latent regions
by deriving seeds from a base_seed + scene_order offset.

Seed priority:
1. Explicit seed (request.seed != -1) → use as-is
2. Storyboard base_seed + offset → anchored deterministic seed
3. Neither → -1 (random, legacy behavior)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from config import SEED_ANCHOR_OFFSET, logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# SD WebUI seed range: 0 ~ 2^31-1
_SEED_MAX = 2**31 - 1


def generate_base_seed() -> int:
    """Generate a random base seed in the valid SD range [1, 2^31-1]."""
    return random.randint(1, _SEED_MAX)


def resolve_scene_seed(
    requested_seed: int,
    storyboard_id: int | None,
    scene_order: int,
    db: Session,
) -> int:
    """Determine the seed for a scene generation.

    Returns:
        Resolved seed (positive int), or -1 for random.
    """
    # Priority 1: explicit seed from request
    if requested_seed != -1:
        return requested_seed

    # Priority 2: storyboard base_seed + offset
    if storyboard_id is not None:
        from models.storyboard import Storyboard

        sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
        if sb and sb.base_seed is not None:
            anchored = (sb.base_seed + scene_order * SEED_ANCHOR_OFFSET) % (_SEED_MAX + 1)
            logger.info(
                "🔗 [Seed Anchor] storyboard=%d base=%d order=%d → seed=%d",
                storyboard_id,
                sb.base_seed,
                scene_order,
                anchored,
            )
            return anchored

    # Priority 3: random (legacy)
    return -1


def set_storyboard_base_seed(
    storyboard_id: int,
    base_seed: int | None,
    db: Session,
) -> int | None:
    """Set or clear the base_seed for a storyboard.

    Args:
        base_seed: None → auto-generate, 0 → clear, positive → set explicitly.

    Returns:
        The final base_seed value (None if cleared).
    """
    from models.storyboard import Storyboard

    sb = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if sb is None:
        return None

    if base_seed is None:
        sb.base_seed = generate_base_seed()
    elif base_seed == 0:
        sb.base_seed = None
    else:
        sb.base_seed = base_seed

    db.commit()
    db.refresh(sb)
    logger.info("🔗 [Seed Anchor] storyboard=%d base_seed=%s", storyboard_id, sb.base_seed)
    return sb.base_seed
