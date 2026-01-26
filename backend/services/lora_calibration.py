"""LoRA weight calibration service.

Automatically finds optimal weight for scene expression.
"""

from __future__ import annotations

import base64
import io

import httpx
from PIL import Image

from config import SD_TIMEOUT_SECONDS, SD_TXT2IMG_URL, logger
from services.controlnet import build_controlnet_args, load_pose_reference
from services.validation import compare_prompt_to_tags, wd14_predict_tags

# Standard test prompt for calibration
CALIBRATION_PROMPT = "1girl, standing, waving, classroom, school uniform, smile, anime style, best quality"
CALIBRATION_NEGATIVE = "nsfw, worst quality, lowres"
CALIBRATION_TAGS = ["standing", "waving", "classroom", "school uniform", "smile"]
CALIBRATION_SEED = 42  # Fixed seed for reproducibility


async def generate_test_image(
    lora_name: str,
    lora_weight: float,
    trigger_word: str | None = None,
    use_controlnet: bool = True,
) -> bytes | None:
    """Generate a test image with specified LoRA weight.

    Args:
        lora_name: LoRA filename (without extension)
        lora_weight: Weight to test
        trigger_word: Optional trigger word for the LoRA
        use_controlnet: Whether to use ControlNet for pose

    Returns:
        Image bytes or None if failed
    """
    # Build prompt with LoRA
    trigger = f"{trigger_word}, " if trigger_word else ""
    prompt = f"1girl, {trigger}<lora:{lora_name}:{lora_weight}>, standing, waving, classroom, school uniform, smile, anime style, best quality"

    payload = {
        "prompt": prompt,
        "negative_prompt": CALIBRATION_NEGATIVE,
        "steps": 20,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": CALIBRATION_SEED,
        "width": 512,
        "height": 768,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
    }

    # Add ControlNet if enabled
    if use_controlnet:
        pose_image = load_pose_reference("waving")
        if pose_image:
            controlnet_args = build_controlnet_args(
                input_image=pose_image,
                model="openpose",
                weight=0.8,
            )
            payload["alwayson_scripts"] = {
                "controlnet": {"args": [controlnet_args]}
            }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(SD_TXT2IMG_URL, json=payload, timeout=SD_TIMEOUT_SECONDS)
            res.raise_for_status()
            data = res.json()
            img_b64 = data.get("images", [None])[0]
            if img_b64:
                return base64.b64decode(img_b64)
    except Exception as e:
        logger.warning(f"Calibration image generation failed: {e}")

    return None


def evaluate_image(image_bytes: bytes) -> tuple[float, list[str], list[str]]:
    """Evaluate image against calibration tags.

    Args:
        image_bytes: Image bytes to evaluate

    Returns:
        Tuple of (match_rate, matched_tags, missing_tags)
    """
    image = Image.open(io.BytesIO(image_bytes))
    tags = wd14_predict_tags(image, threshold=0.35)

    comparison = compare_prompt_to_tags(", ".join(CALIBRATION_TAGS), tags)
    matched = comparison["matched"]
    missing = comparison["missing"]

    total = len(matched) + len(missing)
    match_rate = (len(matched) / total * 100) if total > 0 else 0.0

    return match_rate, matched, missing


async def calibrate_lora(
    lora_name: str,
    trigger_word: str | None = None,
    weights_to_test: list[float] | None = None,
) -> dict:
    """Calibrate LoRA to find optimal weight for scene expression.

    Args:
        lora_name: LoRA filename (without extension)
        trigger_word: Optional trigger word
        weights_to_test: List of weights to test (default: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

    Returns:
        Calibration result with optimal_weight and scores
    """
    if weights_to_test is None:
        weights_to_test = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    logger.info(f"🔧 [Calibration] Starting for {lora_name}")

    results = []

    for weight in weights_to_test:
        logger.info(f"🔧 [Calibration] Testing weight {weight}")

        image_bytes = await generate_test_image(
            lora_name=lora_name,
            lora_weight=weight,
            trigger_word=trigger_word,
            use_controlnet=True,
        )

        if image_bytes is None:
            logger.warning(f"🔧 [Calibration] Failed to generate at weight {weight}")
            continue

        match_rate, matched, missing = evaluate_image(image_bytes)

        results.append({
            "weight": weight,
            "match_rate": match_rate,
            "matched": matched,
            "missing": missing,
        })

        logger.info(f"🔧 [Calibration] weight={weight} → {match_rate:.0f}% ({matched})")

    if not results:
        return {
            "success": False,
            "error": "All weight tests failed",
            "lora_name": lora_name,
        }

    # Find optimal weight (highest match rate, prefer lower weight on tie)
    best = max(results, key=lambda x: (x["match_rate"], -x["weight"]))

    # Determine LoRA type based on impact
    baseline_rate = 80.0  # Expected baseline without LoRA
    impact = best["match_rate"] - baseline_rate

    if impact < -10:
        lora_type = "character"  # Significant negative impact
    elif impact > 10:
        lora_type = "style"  # Positive impact (enhances)
    else:
        lora_type = "style"  # Neutral impact

    logger.info(f"🔧 [Calibration] Complete: optimal={best['weight']}, score={best['match_rate']:.0f}%, type={lora_type}")

    return {
        "success": True,
        "lora_name": lora_name,
        "optimal_weight": best["weight"],
        "calibration_score": best["match_rate"],
        "lora_type": lora_type,
        "all_results": results,
    }


def get_effective_weight(lora: dict) -> float:
    """Get effective weight for a LoRA (optimal > default > 0.7).

    Args:
        lora: LoRA dict with weight fields

    Returns:
        Effective weight to use
    """
    if lora.get("optimal_weight") is not None:
        return float(lora["optimal_weight"])
    if lora.get("default_weight") is not None:
        return float(lora["default_weight"])
    return 0.7


def get_optimal_weights_from_db(lora_names: list[str]) -> dict[str, float]:
    """Fetch optimal weights for LoRAs from database.

    Args:
        lora_names: List of LoRA names to look up

    Returns:
        Dict mapping normalized LoRA names to optimal weights
    """
    from database import SessionLocal
    from models import LoRA

    if not lora_names:
        return {}

    weights = {}
    db = SessionLocal()
    try:
        # Normalize names for lookup
        normalized_names = [
            name.lower().replace(".safetensors", "")
            for name in lora_names
        ]

        loras = db.query(LoRA).filter(
            LoRA.name.in_(lora_names) | LoRA.name.in_(normalized_names)
        ).all()

        for lora in loras:
            weight = get_effective_weight({
                "optimal_weight": lora.optimal_weight,
                "default_weight": lora.default_weight,
            })
            # Store with normalized name for matching
            normalized = lora.name.lower().replace(".safetensors", "")
            weights[normalized] = weight
            logger.info("🔧 [LoRA Weight] %s → %.2f", lora.name, weight)

    finally:
        db.close()

    return weights
