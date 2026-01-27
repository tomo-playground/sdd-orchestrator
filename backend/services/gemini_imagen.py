"""Gemini Image Generation Service (Nano Banana).

Generates pose reference images using Gemini's native image generation models.
Uses Standard API Key (No Vertex AI/GCP required).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from config import (
    gemini_client,
    GEMINI_IMAGE_MODEL,
    logger,
    ASSETS_DIR
)
from google.genai import types

# Directory to save generated poses
POSE_CACHE_DIR = ASSETS_DIR / "poses" / "generated"
POSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def generate_pose_image_via_gemini(description: str) -> str | None:
    """Generate a pose reference image using Gemini (Nano Banana).

    Args:
        description: Description of the pose (e.g., "dynamic backflip kick")

    Returns:
        Path to the saved image file (relative to project root) or None if failed.
    """
    if not gemini_client:
        logger.warning("⚠️ [Gemini Image] Client not initialized. Check GEMINI_API_KEY.")
        return None

    # 1. Check Cache (Deduplication)
    # Hash the description to create a unique filename
    # Include model name in hash so changing models invalidates cache
    cache_key = f"{description}|{GEMINI_IMAGE_MODEL}"
    prompt_hash = hashlib.md5(cache_key.encode()).hexdigest()
    output_filename = f"gemini_{prompt_hash}.png"
    output_path = POSE_CACHE_DIR / output_filename

    if output_path.exists():
        logger.info(f"✨ [Gemini Image] Using cached pose for: '{description}'")
        return str(output_path)

    # 2. Construct Prompt
    # Optimized for ControlNet Skeleton extraction
    prompt = (
        f"Full body sketch of a person doing a {description}, "
        "minimalist line art, white background, high contrast, "
        "clean lines, continuous lines, no shading, stick figure style, "
        "anatomically correct, wide shot, full body visible"
    )

    logger.info(f"🎨 [Gemini Image] Generating with {GEMINI_IMAGE_MODEL}: '{description}'...")

    try:
        # 3. Call Gemini API
        # Nano Banana supports generate_images method
        response = gemini_client.models.generate_images(
            model=GEMINI_IMAGE_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="3:4", # Portrait for character poses
                # 'person_generation' param might vary by model version, omitting for broad compatibility
                # unless specifically required. Nano Banana usually allows generic figures.
            )
        )

        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            
            logger.info(f"✅ [Gemini Image] Success! Saved to: {output_path}")
            return str(output_path)
        else:
            logger.warning(f"⚠️ [Gemini Image] No images returned from {GEMINI_IMAGE_MODEL}.")
            return None

    except Exception as e:
        logger.error(f"❌ [Gemini Image] Generation failed: {e}")
        return None
