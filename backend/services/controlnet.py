"""ControlNet integration service.

Provides pose and composition control for SD image generation.
"""

from __future__ import annotations

import base64
import io
import os
import random
from typing import Any

import httpx
import requests
from PIL import Image
from sqlalchemy.orm import Session

from config import (
    CONTROLNET_API_TIMEOUT,
    CONTROLNET_DEFAULT_SAMPLER,
    CONTROLNET_DETECT_TIMEOUT,
    CONTROLNET_GENERATE_TIMEOUT,
    DEFAULT_CHARACTER_PRESET,
    DEFAULT_IP_ADAPTER_GUIDANCE_END_CLIP,
    DEFAULT_IP_ADAPTER_GUIDANCE_END_FACEID,
    DEFAULT_IP_ADAPTER_GUIDANCE_START,
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    SD_BASE_URL,
    SD_TXT2IMG_URL,
    logger,
)
from models import Character
from services.image import load_image_bytes
from services.prompt import normalize_negative_prompt

# Dynamic import to avoid initialization order issues

# Pose tag to reference image mapping (Danbooru underscore format)
# Primary entries map exact pose tags to asset files.
# Alias entries (marked with # alias) map common Danbooru pose variants
# to the closest existing asset, expanding coverage without new assets.
POSE_MAPPING: dict[str, str] = {
    # Standing poses
    "standing": "standing_neutral.png",
    "waving": "standing_waving.png",
    "arms_up": "standing_arms_up.png",
    "arms_crossed": "standing_arms_crossed.png",
    "crossed_arms": "standing_arms_crossed.png",  # alias
    "thumbs_up": "standing_thumbs_up.png",
    "hands_on_hips": "standing_hands_on_hips.png",
    "looking_at_viewer": "looking_at_viewer_neutral.png",
    "from_behind": "standing_from_behind.png",
    "looking_back": "standing_from_behind.png",  # alias
    "hand_on_hip": "standing_hands_on_hips.png",  # alias (singular)
    "standing_on_one_leg": "standing_neutral.png",  # alias
    # Sitting poses
    "sitting": "sitting_neutral.png",
    "sitting_on_chair": "sitting_neutral.png",  # alias
    "seiza": "sitting_neutral.png",  # alias
    "wariza": "sitting_neutral.png",  # alias
    "indian_style": "sitting_neutral.png",  # alias
    "chin_rest": "sitting_chin_rest.png",
    "head_rest": "sitting_chin_rest.png",  # alias
    "leaning": "sitting_leaning.png",
    "leaning_forward": "sitting_leaning.png",  # alias
    # Action/Storytelling poses
    "walking": "walking.png",
    "running": "running.png",
    "jumping": "jumping.png",
    "lying": "lying_neutral.png",
    "lying_down": "lying_neutral.png",  # alias
    "on_back": "lying_neutral.png",  # alias
    "on_stomach": "lying_neutral.png",  # alias
    "kneeling": "kneeling_neutral.png",
    "on_knees": "kneeling_neutral.png",  # alias
    "crouching": "crouching_neutral.png",
    "squatting": "crouching_neutral.png",  # alias
    "pointing_forward": "pointing_forward.png",
    "pointing": "pointing_forward.png",  # alias
    "covering_face": "covering_face.png",
    "hands_on_face": "covering_face.png",  # alias
    # Daily life / interaction poses
    "holding_object": "holding_object.png",
    "holding": "holding_object.png",  # alias
    "eating": "eating.png",
    "cooking": "cooking.png",
    "holding_umbrella": "holding_umbrella.png",
    "writing": "writing.png",
    "reading": "writing.png",  # alias (similar posture)
    "profile_standing": "profile_standing.png",
    "from_side": "profile_standing.png",  # alias
    "standing_looking_up": "standing_looking_up.png",
    "looking_up": "standing_looking_up.png",  # alias
    "leaning_wall": "leaning_wall.png",
    "leaning_against_wall": "leaning_wall.png",  # alias
    "sitting_eating": "sitting_eating.png",
}

# Poses that require IP-Adapter weight reduction to avoid reference-pose conflict.
# Omitted poses default to "front" direction (max weight = 1.0).
POSE_DIRECTION: dict[str, str] = {
    "from_behind": "back",
    "profile_standing": "side",
    "walking": "side",
    "leaning_wall": "side",
}

IP_ADAPTER_WEIGHT_CLAMP: dict[str, float] = {
    "back": 0.2,
    "side": 0.5,
    "front": 1.0,
}


def clamp_ip_adapter_weight(weight: float, pose_name: str | None) -> float:
    """Clamp IP-Adapter weight based on pose direction to avoid reference conflict."""
    direction = POSE_DIRECTION.get(pose_name or "", "front")
    max_w = IP_ADAPTER_WEIGHT_CLAMP.get(direction, 1.0)
    if weight > max_w:
        logger.info("[IP-Adapter Clamp] %.2f -> %.2f (pose=%s)", weight, max_w, pose_name)
        return max_w
    return weight


# ControlNet models
CONTROLNET_MODELS = {
    "openpose": "control_v11p_sd15_openpose [cab727d4]",
    "depth": "control_v11f1p_sd15_depth [cfd03158]",
    "canny": "control_v11p_sd15_canny [d14c016b]",
    "reference": "None",  # Reference-only doesn't need a specific model if using the preprocessor
}

# IP-Adapter models
IP_ADAPTER_MODELS = {
    "faceid": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",  # Real face only
    "clip": "ip-adapter-plus_sd15 [836b5c2e]",  # Anime/illustration (recommended)
    "clip_face": "ip-adapter-plus-face_sd15 [7f7a633a]",  # Face + style
}

# Default IP-Adapter for anime characters
DEFAULT_IP_ADAPTER_MODEL = "clip_face"


def check_controlnet_available() -> bool:
    """Check if ControlNet extension is available."""
    try:
        resp = requests.get(f"{SD_BASE_URL}/controlnet/version", timeout=CONTROLNET_API_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def get_controlnet_models() -> list[str]:
    """Get list of available ControlNet models."""
    try:
        resp = requests.get(f"{SD_BASE_URL}/controlnet/model_list", timeout=CONTROLNET_API_TIMEOUT)
        if resp.status_code == 200:
            return resp.json().get("model_list", [])
    except Exception as e:
        logger.warning(f"Failed to get ControlNet models: {e}")
    return []


def load_pose_reference(pose_name: str) -> str | None:
    """Load a pose reference image as base64 using StorageService.

    Args:
        pose_name: Name of the pose (e.g., "standing", "waving")

    Returns:
        Base64 encoded image or None if not found
    """
    from services.storage import get_storage

    storage = get_storage()

    filename = POSE_MAPPING.get(pose_name)
    if not filename:
        return None

    storage_key = f"shared/poses/{filename}"
    if not storage.exists(storage_key):
        logger.warning(f"Pose reference not found in storage: {storage_key}")
        return None

    try:
        return base64.b64encode(storage.get_local_path(storage_key).read_bytes()).decode("utf-8")
    except Exception:
        logger.error("Failed to load pose from storage %s", storage_key, exc_info=True)
        return None


def detect_pose_from_prompt(prompt: str) -> str | None:
    """Fallback: 프롬프트에서 POSE_MAPPING 키를 정확히 매칭 (longest-match 우선).

    POSE_MAPPING 키는 언더바 형식이지만, 프롬프트에는 공백 형식이 올 수 있으므로
    양쪽 형식 모두 매칭합니다.
    """
    prompt_lower = prompt.lower()
    best: str | None = None
    best_len = 0
    for pose_name in POSE_MAPPING:
        # 언더바 형식(DB 표준)과 공백 형식(레거시) 모두 매칭
        pose_space = pose_name.replace("_", " ")
        if (pose_name in prompt_lower or pose_space in prompt_lower) and len(pose_name) > best_len:
            best = pose_name
            best_len = len(pose_name)
    return best


def build_controlnet_args(
    input_image: str,
    model: str = "openpose",
    weight: float = 1.0,
    control_mode: str = "Balanced",
    preprocessor: str | None = None,
) -> dict[str, Any]:
    """Build ControlNet arguments for txt2img.

    Args:
        input_image: Base64 encoded input image
        model: ControlNet model type ("openpose", "depth", "canny", "reference")
        weight: ControlNet weight (0.0-2.0)
        control_mode: "Balanced", "My prompt is more important", "ControlNet is more important"
        preprocessor: Preprocessor module (None for auto)

    Returns:
        ControlNet args dict for alwayson_scripts
    """
    args = {
        "enabled": True,
        "image": input_image,
        "model": CONTROLNET_MODELS.get(model, model),
        "module": preprocessor or model,  # Default module same as model name (e.g. openpose, canny)
        "weight": weight,
        "control_mode": control_mode,  # "Balanced", "My prompt is more important", "ControlNet is more important"
        "pixel_perfect": True,
        "low_vram": False,
        "guidance_start": 0.0,
        "guidance_end": 1.0,
    }

    if model == "reference":
        args["module"] = "reference_only"
        args["model"] = "None"
        args["guidance_end"] = 0.75  # Allow prompt to take over in later steps for better flexibility

    return args


def generate_with_controlnet(
    prompt: str,
    negative_prompt: str,
    pose_image: str,
    width: int = 512,
    height: int = 768,
    steps: int = 20,
    cfg_scale: float = 7.0,
    controlnet_weight: float = 1.0,
) -> dict[str, Any]:
    """Generate image with ControlNet pose control.

    Args:
        prompt: Positive prompt
        negative_prompt: Negative prompt
        pose_image: Base64 encoded pose reference image
        width: Image width
        height: Image height
        steps: Sampling steps
        cfg_scale: CFG scale
        controlnet_weight: ControlNet influence weight

    Returns:
        Generation result with images
    """
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "sampler_name": CONTROLNET_DEFAULT_SAMPLER,
        "alwayson_scripts": {
            "controlnet": {
                "args": [
                    build_controlnet_args(
                        input_image=pose_image,
                        model="openpose",
                        weight=controlnet_weight,
                    )
                ]
            }
        },
    }

    resp = requests.post(
        f"{SD_BASE_URL}/sdapi/v1/txt2img",
        json=payload,
        timeout=CONTROLNET_GENERATE_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def create_pose_from_image(image_b64: str) -> dict[str, Any]:
    """Extract pose skeleton from an image using OpenPose.

    Args:
        image_b64: Base64 encoded image

    Returns:
        Pose detection result with skeleton image
    """
    payload = {
        "controlnet_module": "openpose_full",
        "controlnet_input_images": [image_b64],
        "controlnet_processor_res": 512,
    }

    resp = requests.post(
        f"{SD_BASE_URL}/controlnet/detect",
        json=payload,
        timeout=CONTROLNET_DETECT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# IP-Adapter Functions (Character Consistency)
# ============================================================


def save_reference_image(character_key: str, image_b64: str, db: Session | None = None) -> str:
    """Save a reference image for IP-Adapter using StorageService.

    Args:
        character_key: Unique key for the character (e.g., "eureka", "midoriya")
        image_b64: Base64 encoded image (with or without data URI prefix)
        db: Optional DB session to update character.preview_image_url

    Returns:
        Saved filename
    """
    from services.storage import get_storage

    # Remove data URI prefix if present
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    image_bytes = base64.b64decode(image_b64)
    filename = f"{character_key}.png"
    storage_key = f"shared/references/{filename}"

    try:
        storage = get_storage()
        storage.save(storage_key, image_bytes, content_type="image/png")
        logger.info(f"Saved reference image to storage: {storage_key}")
    except Exception:
        logger.error("Failed to save reference image to storage", exc_info=True)
        # Continue with DB registration if possible or handles as needed

    # Register asset via AssetService if DB is available (preferred)
    if db:
        from services.asset_service import AssetService

        asset_service = AssetService(db)
        char = db.query(Character).filter(Character.name == character_key, Character.deleted_at.is_(None)).first()
        asset = asset_service.register_asset(
            file_name=filename,
            file_type="image",
            storage_key=storage_key,
            owner_type="character",
            owner_id=char.id if char else None,
            mime_type="image/png",
            file_size=len(image_bytes),
            checksum=AssetService.compute_checksum(image_bytes),
        )

        if char:
            char.preview_image_asset_id = asset.id
            db.commit()
            logger.info(f"Updated character preview Asset ID in DB for: {character_key} (Asset: {asset.id})")

    return filename


def load_reference_image(character_key: str, db: Session | None = None) -> str | None:
    """Load a reference image for IP-Adapter from DB.

    Args:
        character_key: Character name to load
        db: Optional DB session

    Returns:
        Base64 encoded image or None if not found
    """
    if not db:
        return None

    # Load from DB preview_image_url
    char = db.query(Character).filter(Character.name == character_key, Character.deleted_at.is_(None)).first()
    if not char or not char.preview_image_url:
        return None

    try:
        img_bytes = load_image_bytes(char.preview_image_url)
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to load image for {character_key}: {e}")
        return None


def list_reference_images(db: Session | None = None) -> list[dict[str, str | int]]:
    """List all characters with preview images from DB.

    Returns:
        List of dicts with character_key, character_id, and filename
    """
    if not db:
        return []

    # Get all characters with preview images
    chars = (
        db.query(Character)
        .filter(Character.preview_image_asset_id.isnot(None), Character.deleted_at.is_(None))
        .order_by(Character.id)
        .all()
    )

    return [
        {
            "character_key": char.name,
            "character_id": char.id,
            "filename": os.path.basename(char.preview_image_url) if char.preview_image_url else "",
        }
        for char in chars
    ]


def delete_reference_image(character_key: str) -> bool:
    """Delete a reference image from storage.

    Args:
        character_key: Character key to delete

    Returns:
        True if deleted, False if not found
    """
    from services.storage import get_storage

    try:
        storage = get_storage()
        storage_key = f"shared/references/{character_key}.png"
        if storage.exists(storage_key):
            return storage.delete(storage_key)
        return False
    except Exception:
        return False


def build_ip_adapter_args(
    reference_image: str,
    weight: float | None = None,
    model: str | None = None,
    guidance_start: float | None = None,
    guidance_end: float | None = None,
) -> dict[str, Any]:
    """Build IP-Adapter arguments for txt2img.

    Args:
        reference_image: Base64 encoded reference face image
        weight: IP-Adapter influence weight (0.0-1.5). If None, uses default.
        model: IP-Adapter model type ("clip", "clip_face", "faceid"). If None, uses default.
        guidance_start: Override guidance start. None = use per-model default.
        guidance_end: Override guidance end. None = use per-model default.

    Returns:
        ControlNet args dict for IP-Adapter
    """
    preset = DEFAULT_CHARACTER_PRESET

    # Use provided values or fall back to preset
    if weight is None:
        weight = preset.get("weight", 0.35)
    if model is None:
        model = preset.get("model", DEFAULT_IP_ADAPTER_MODEL)

    model_name = IP_ADAPTER_MODELS.get(model or "")
    if not model_name:
        raise ValueError(f"Unknown IP-Adapter model: {model}")

    # Select module and control_mode based on model type
    if model == "faceid":
        module = "ip-adapter_face_id_plus"  # For real faces (InsightFace)
        control_mode = "ControlNet is more important"  # Prioritize face identity
        default_end = DEFAULT_IP_ADAPTER_GUIDANCE_END_FACEID
    else:
        module = "ip-adapter_clip_sd15"  # For anime/illustration (CLIP)
        control_mode = "Balanced"
        default_end = DEFAULT_IP_ADAPTER_GUIDANCE_END_CLIP

    return {
        "enabled": True,
        "image": reference_image,
        "module": module,
        "model": model_name,
        "weight": weight,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": control_mode,
        "pixel_perfect": False,
        "guidance_start": guidance_start if guidance_start is not None else DEFAULT_IP_ADAPTER_GUIDANCE_START,
        "guidance_end": guidance_end if guidance_end is not None else default_end,
    }


def build_reference_only_args(
    reference_image: str,
    weight: float = 0.5,
    guidance_start: float = 0.0,
    guidance_end: float = 0.8,
) -> dict[str, Any]:
    """Build Reference-only ControlNet arguments for character consistency.

    Reference-only는 IP-Adapter보다 전신 스타일 일관성이 우수합니다.
    실험 결과 (CHARACTER_RENDERING_REPORT.md): ⭐⭐⭐⭐⭐

    Args:
        reference_image: Base64 encoded reference image (full body recommended)
        weight: Control weight (0.3-0.7). Lower = more pose freedom
        guidance_start: Start of guidance (default 0.0)
        guidance_end: End of guidance (0.6-0.9). Lower = more prompt priority in later steps

    Returns:
        ControlNet args dict for reference_only

    Best Practices:
        - Base image: full body, standing, simple background
        - Weight: 0.5 (balanced), 0.3 (high variation), 0.7 (strict consistency)
        - Guidance end: 0.8 (allows prompt to override in final steps)
    """
    return {
        "enabled": True,
        "image": reference_image,
        "module": "reference_only",
        "model": "None",  # reference_only doesn't use a model
        "weight": weight,
        "guidance_start": guidance_start,
        "guidance_end": guidance_end,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": "Balanced",
        "pixel_perfect": False,
    }


def build_combined_controlnet_args(
    pose_image: str | None = None,
    reference_image: str | None = None,
    pose_weight: float = 0.8,
    ip_adapter_weight: float | None = None,
) -> list[dict[str, Any]]:
    """Build combined ControlNet + IP-Adapter args.

    Args:
        pose_image: Base64 encoded pose reference (optional)
        reference_image: Base64 encoded face reference for IP-Adapter (optional)
        pose_weight: OpenPose weight
        ip_adapter_weight: IP-Adapter weight (None = use default)

    Returns:
        List of ControlNet args for alwayson_scripts
    """
    args = []

    if pose_image:
        args.append(
            build_controlnet_args(
                input_image=pose_image,
                model="openpose",
                weight=pose_weight,
            )
        )

    if reference_image:
        args.append(
            build_ip_adapter_args(
                reference_image=reference_image,
                weight=ip_adapter_weight,
            )
        )

    return args


def _validate_reference_image(image_b64: str, required_tags: list[str], threshold: float = 0.5) -> dict[str, Any]:
    """Validate a reference image using WD14.

    Args:
        image_b64: Base64 encoded image
        required_tags: Tags that should be detected (e.g., ["looking_at_viewer"])
        threshold: Minimum confidence threshold

    Returns:
        {"valid": bool, "detected": list, "missing": list, "details": dict}
    """
    from services.validation import wd14_predict_tags

    # Decode image
    image_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Get WD14 tags
    tags = wd14_predict_tags(image, threshold=0.35)
    detected_names = {t["tag"].replace(" ", "_") for t in tags}

    # Check required tags
    missing = []
    found = []
    tag_details = {}

    for req_tag in required_tags:
        # Normalize tag name
        normalized = req_tag.replace(" ", "_")
        # Check if any detected tag contains the required tag
        matched = any(normalized in det or det in normalized for det in detected_names)
        if matched:
            found.append(req_tag)
            # Find score
            for t in tags:
                if normalized in t["tag"].replace(" ", "_") or t["tag"].replace(" ", "_") in normalized:
                    tag_details[req_tag] = t["score"]
                    break
        else:
            missing.append(req_tag)

    return {
        "valid": len(missing) == 0,
        "detected": found,
        "missing": missing,
        "details": tag_details,
        "all_tags": [t["tag"] for t in tags[:20]],  # Top 20 for debugging
    }


async def generate_reference_for_character(
    db: Session, character: Character, max_attempts: int = 3, validate: bool = True
) -> str:
    """Generate and save a reference image for a character with validation.

    # INTENTIONAL BYPASS: This function intentionally does NOT use
    # generate_image_with_v3() because reference images use the character's
    # own reference_base_prompt + reference_negative_prompt (special logic
    # for IP-Adapter/Reference-only reference images).

    Args:
        db: Database session
        character: Character model instance
        max_attempts: Maximum generation attempts if validation fails
        validate: Whether to validate with WD14

    Returns:
        Saved filename
    """
    # Build prompt using V3 12-Layer system (alias/conflict resolution, batch LoRA query)
    from config import SD_DEFAULT_SAMPLER, SD_REFERENCE_CFG_SCALE, SD_REFERENCE_STEPS
    from services.characters.preview import _resolve_quality_tags_for_character
    from services.prompt.v3_composition import V3PromptBuilder
    from services.style_context import resolve_style_context_from_group

    quality_tags = _resolve_quality_tags_for_character(character, db)

    # Resolve StyleContext via Group (needed for reference_env_tags/camera_tags + params)
    style_ctx = resolve_style_context_from_group(character.group_id, db)

    builder = V3PromptBuilder(db)
    full_prompt = builder.compose_for_reference(character, quality_tags=quality_tags, style_ctx=style_ctx)

    # Construct negative prompt: DB 고유 태그 + 상수 공통 머지
    base_negative = character.reference_negative_prompt or ""
    if character.recommended_negative:
        extras = [n for n in character.recommended_negative if n not in base_negative]
        if extras:
            base_negative += ", " + ", ".join(extras)
    # Always merge DEFAULT_REFERENCE_NEGATIVE_PROMPT (공통 품질/배경/멀티뷰 억제)
    existing_tags = {t.strip() for t in base_negative.split(",") if t.strip()}
    for tag in DEFAULT_REFERENCE_NEGATIVE_PROMPT.split(", "):
        if tag and tag not in existing_tags:
            base_negative = (base_negative + ", " + tag) if base_negative else tag
    steps = style_ctx.default_steps if (style_ctx and style_ctx.default_steps is not None) else SD_REFERENCE_STEPS
    cfg_scale = (
        style_ctx.default_cfg_scale
        if (style_ctx and style_ctx.default_cfg_scale is not None)
        else SD_REFERENCE_CFG_SCALE
    )
    sampler_name = (
        style_ctx.default_sampler_name if (style_ctx and style_ctx.default_sampler_name) else SD_DEFAULT_SAMPLER
    )

    # Required tags for IP-Adapter reference (must detect these)
    required_tags = ["looking_at_viewer"]

    best_image = None
    best_score = -1

    for attempt in range(max_attempts):
        payload = {
            "prompt": full_prompt,
            "negative_prompt": normalize_negative_prompt(base_negative),
            "steps": steps,
            "width": 512,
            "height": 512,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": random.randint(0, 2**32 - 1) if attempt > 0 else -1,
        }

        logger.info(f"🎨 [{attempt + 1}/{max_attempts}] Generating reference for {character.name}...")
        logger.info(f"  Prompt: {payload['prompt'][:200]}...")
        logger.info(f"  Negative: {payload['negative_prompt'][:100]}...")

        # 5. Call SD
        async with httpx.AsyncClient() as client:
            resp = await client.post(SD_TXT2IMG_URL, json=payload, timeout=CONTROLNET_GENERATE_TIMEOUT)
            resp.raise_for_status()
            r = resp.json()
            image_b64 = r["images"][0]

        if not validate:
            return save_reference_image(character.name, image_b64)

        # 6. Validate with WD14
        validation = _validate_reference_image(image_b64, required_tags)
        score = len(validation["detected"]) / len(required_tags) if required_tags else 1.0

        logger.info(
            f"🔍 [{attempt + 1}] Validation: valid={validation['valid']}, "
            f"detected={validation['detected']}, missing={validation['missing']}"
        )

        if validation["valid"]:
            logger.info("✅ Reference image validated successfully!")
            return save_reference_image(character.name, image_b64)

        # Track best attempt
        if score > best_score:
            best_score = score
            best_image = image_b64

    # If all attempts failed, save the best one
    logger.warning(f"⚠️ Validation failed after {max_attempts} attempts. Using best image (score={best_score:.1%})")
    fallback = best_image or ""
    return save_reference_image(character.name, fallback)
