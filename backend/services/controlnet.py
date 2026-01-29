"""ControlNet integration service.

Provides pose and composition control for SD image generation.
"""

from __future__ import annotations

import base64
import io
import random
from pathlib import Path
import os
from typing import Any

import httpx
import requests
from PIL import Image
from sqlalchemy.orm import Session

from config import (
    CHARACTER_PRESETS,
    DEFAULT_CHARACTER_PRESET,
    DEFAULT_REFERENCE_BASE_PROMPT,
    DEFAULT_REFERENCE_NEGATIVE_PROMPT,
    SD_BASE_URL,
    SD_TXT2IMG_URL,
    logger,
)
from models import Character, LoRA, Tag
from services.image import load_image_bytes

# Pose reference directory
POSE_DIR = Path("assets/poses")

# Pose tag to reference image mapping
POSE_MAPPING: dict[str, str] = {
    # Standing poses
    "standing": "standing_neutral.png",
    "waving": "standing_waving.png",
    "arms up": "standing_arms_up.png",
    "arms crossed": "standing_arms_crossed.png",
    "hands on hips": "standing_hands_on_hips.png",
    # Sitting poses
    "sitting": "sitting_neutral.png",
    "chin rest": "sitting_chin_rest.png",
    "leaning": "sitting_leaning.png",
    # Action poses
    "walking": "walking.png",
    "running": "running.png",
    "jumping": "jumping.png",
}

# ControlNet models
CONTROLNET_MODELS = {
    "openpose": "control_v11p_sd15_openpose [cab727d4]",
    "depth": "control_v11f1p_sd15_depth [cfd03158]",
    "canny": "control_v11p_sd15_canny [d14c016b]",
}

# IP-Adapter models
IP_ADAPTER_MODELS = {
    "faceid": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",  # Real face only
    "clip": "ip-adapter-plus_sd15 [836b5c2e]",  # Anime/illustration (recommended)
    "clip_face": "ip-adapter-plus-face_sd15 [7f7a633a]",  # Face + style
}

# Default IP-Adapter for anime characters
DEFAULT_IP_ADAPTER_MODEL = "clip_face"

# Reference image directory for IP-Adapter
REFERENCE_DIR = Path("assets/references")


def check_controlnet_available() -> bool:
    """Check if ControlNet extension is available."""
    try:
        resp = requests.get(f"{SD_BASE_URL}/controlnet/version", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def get_controlnet_models() -> list[str]:
    """Get list of available ControlNet models."""
    try:
        resp = requests.get(f"{SD_BASE_URL}/controlnet/model_list", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("model_list", [])
    except Exception as e:
        logger.warning(f"Failed to get ControlNet models: {e}")
    return []


def load_pose_reference(pose_name: str) -> str | None:
    """Load a pose reference image as base64.

    Args:
        pose_name: Name of the pose (e.g., "standing", "waving")

    Returns:
        Base64 encoded image or None if not found
    """
    filename = POSE_MAPPING.get(pose_name)
    if not filename:
        return None

    pose_path = POSE_DIR / filename
    if not pose_path.exists():
        logger.warning(f"Pose reference not found: {pose_path}")
        return None

    return base64.b64encode(pose_path.read_bytes()).decode("utf-8")


def detect_pose_from_prompt(prompt_tags: list[str]) -> str | None:
    """Detect the primary pose from prompt tags.

    Args:
        prompt_tags: List of tags from the prompt

    Returns:
        Detected pose name or None
    """
    # Priority order for pose detection
    pose_priority = [
        "waving", "arms up", "arms crossed", "hands on hips",
        "jumping", "running", "walking",
        "chin rest", "leaning",
        "sitting", "standing",
    ]

    # Synonyms mapping for more robust detection
    pose_synonyms = {
        "waving": ["wave", "greeting", "signaling"],
        "arms up": ["hands up", "raising hands", "stretching", "cheering"],
        "arms crossed": ["folding arms", "crossed arms"],
        "hands on hips": ["akimbo"],
        "jumping": ["jump", "leap", "leaping"],
        "running": ["run", "sprinting", "jogging", "chasing"],
        "walking": ["walk", "stroll", "strolling"],
        "sitting": ["seated", "sits", "chair", "bench", "couch", "sofa"],
        "standing": ["stands", "wait", "waiting"],
    }

    for pose in pose_priority:
        # Check exact match
        if pose in prompt_tags:
            return pose
        
        # Check synonyms
        if pose in pose_synonyms:
            for synonym in pose_synonyms[pose]:
                if synonym in prompt_tags:
                    return pose
                # Check for partial match in tags (e.g. "walking away" matches "walking")
                for tag in prompt_tags:
                    if synonym in tag or pose in tag:
                        return pose

    return None


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
        model: ControlNet model type ("openpose", "depth", "canny")
        weight: ControlNet weight (0.0-2.0)
        control_mode: "Balanced", "My prompt is more important", "ControlNet is more important"
        preprocessor: Preprocessor module (None for auto)

    Returns:
        ControlNet args dict for alwayson_scripts
    """
    model_name = CONTROLNET_MODELS.get(model)
    if not model_name:
        raise ValueError(f"Unknown ControlNet model: {model}")

    # Default preprocessors
    default_preprocessors = {
        "openpose": "openpose_full",
        "depth": "depth_midas",
        "canny": "canny",
    }

    return {
        "enabled": True,
        "image": input_image,
        "module": preprocessor or default_preprocessors.get(model, "none"),
        "model": model_name,
        "weight": weight,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": control_mode,
        "pixel_perfect": True,
    }


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
        "sampler_name": "Euler a",
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
        timeout=180,
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
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# IP-Adapter Functions (Character Consistency)
# ============================================================


def ensure_reference_dir() -> Path:
    """Ensure reference directory exists."""
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    return REFERENCE_DIR


def save_reference_image(character_key: str, image_b64: str, db: Session | None = None) -> str:
    """Save a reference image for IP-Adapter.

    Args:
        character_key: Unique key for the character (e.g., "eureka", "midoriya")
        image_b64: Base64 encoded image (with or without data URI prefix)
        db: Optional DB session to update character.preview_image_url

    Returns:
        Saved filename
    """
    ensure_reference_dir()

    # Remove data URI prefix if present
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    filename = f"{character_key}.png"
    filepath = REFERENCE_DIR / filename
    filepath.write_bytes(base64.b64decode(image_b64))
    logger.info(f"Saved reference image: {filepath}")

    # If db session provided, update character record (V3 compatibility)
    if db:
        char = db.query(Character).filter(Character.name == character_key).first()
        if char:
            char.preview_image_url = f"/assets/references/{filename}"
            db.commit()
            logger.info(f"Updated character preview URL in DB for: {character_key}")

    return filename


def load_reference_image(character_key: str, db: Session | None = None) -> str | None:
    """Load a reference image for IP-Adapter.
    Prioritizes DB preview_image_url if available.

    Args:
        character_key: Unique key for the character
        db: Optional DB session

    Returns:
        Base64 encoded image or None if not found
    """
    # 1. Try DB first (V3)
    if db:
        char = db.query(Character).filter(Character.name == character_key).first()
        if char and char.preview_image_url:
            try:
                img_bytes = load_image_bytes(char.preview_image_url)
                return base64.b64encode(img_bytes).decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to load image from DB path {char.preview_image_url}: {e}")

    # 2. Fallback to physical file in assets/references
    filepath = REFERENCE_DIR / f"{character_key}.png"
    if filepath.exists():
        return base64.b64encode(filepath.read_bytes()).decode("utf-8")
    
    return None


def list_reference_images(db: Session | None = None) -> list[dict[str, str]]:
    """List all saved reference images.
    Merges physical files in assets/references with characters in DB that have previews.

    Returns:
        List of dicts with character_key and filename
    """
    ensure_reference_dir()
    unique_refs = {}

    # 1. Add physical files
    for path in REFERENCE_DIR.glob("*.png"):
        key = path.stem
        unique_refs[key] = {
            "character_key": key,
            "filename": path.name,
        }

    # 2. Add/Override with DB characters (V3)
    if db:
        chars = db.query(Character).filter(Character.preview_image_url.isnot(None)).all()
        for char in chars:
            unique_refs[char.name] = {
                "character_key": char.name,
                "filename": os.path.basename(char.preview_image_url),
                "is_db": True
            }

    return list(unique_refs.values())


def delete_reference_image(character_key: str) -> bool:
    """Delete a reference image.

    Args:
        character_key: Character key to delete

    Returns:
        True if deleted, False if not found
    """
    filepath = REFERENCE_DIR / f"{character_key}.png"
    if filepath.exists():
        filepath.unlink()
        logger.info(f"Deleted reference image: {filepath}")
        return True
    return False


def get_character_preset(character_key: str) -> dict[str, Any]:
    """Get IP-Adapter preset for a character.

    Args:
        character_key: Character name/key

    Returns:
        Preset dict with weight, model, and description
    """
    preset = CHARACTER_PRESETS.get(character_key, DEFAULT_CHARACTER_PRESET)
    logger.info(f"📋 Character preset for '{character_key}': weight={preset.get('weight')}, model={preset.get('model')}")
    return preset


def build_ip_adapter_args(
    reference_image: str,
    weight: float | None = None,
    model: str | None = None,
    character_key: str | None = None,
) -> dict[str, Any]:
    """Build IP-Adapter arguments for txt2img.

    Args:
        reference_image: Base64 encoded reference face image
        weight: IP-Adapter influence weight (0.0-1.5). If None, uses character preset.
        model: IP-Adapter model type ("clip", "clip_face", "faceid"). If None, uses character preset.
        character_key: Character name to load preset from. Used when weight/model not specified.

    Returns:
        ControlNet args dict for IP-Adapter
    """
    # Load preset if character_key provided
    preset = get_character_preset(character_key) if character_key else DEFAULT_CHARACTER_PRESET

    # Use provided values or fall back to preset
    if weight is None:
        weight = preset.get("weight", 0.75)
    if model is None:
        model = preset.get("model", DEFAULT_IP_ADAPTER_MODEL)

    model_name = IP_ADAPTER_MODELS.get(model)
    if not model_name:
        raise ValueError(f"Unknown IP-Adapter model: {model}")

    # Select module based on model type
    if model == "faceid":
        module = "ip-adapter_face_id_plus"  # For real faces (InsightFace)
    else:
        module = "ip-adapter_clip_sd15"  # For anime/illustration (CLIP)

    return {
        "enabled": True,
        "image": reference_image,
        "module": module,
        "model": model_name,
        "weight": weight,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": "Balanced",
        "pixel_perfect": False,
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
    character_key: str | None = None,
) -> list[dict[str, Any]]:
    """Build combined ControlNet + IP-Adapter args.

    Args:
        pose_image: Base64 encoded pose reference (optional)
        reference_image: Base64 encoded face reference for IP-Adapter (optional)
        pose_weight: OpenPose weight
        ip_adapter_weight: IP-Adapter weight (None = use character preset)
        character_key: Character name for loading IP-Adapter preset

    Returns:
        List of ControlNet args for alwayson_scripts
    """
    args = []

    if pose_image:
        args.append(build_controlnet_args(
            input_image=pose_image,
            model="openpose",
            weight=pose_weight,
        ))

    if reference_image:
        args.append(build_ip_adapter_args(
            reference_image=reference_image,
            weight=ip_adapter_weight,
            character_key=character_key,
        ))

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
        "all_tags": [t["tag"] for t in tags[:20]]  # Top 20 for debugging
    }


async def generate_reference_for_character(
    db: Session,
    character: Character,
    max_attempts: int = 3,
    validate: bool = True
) -> str:
    """Generate and save a reference image for a character with validation.

    Args:
        db: Database session
        character: Character model instance
        max_attempts: Maximum generation attempts if validation fails
        validate: Whether to validate with WD14

    Returns:
        Saved filename
    """
    # 1. Build prompt from tags
    tag_list = [char_tag.tag.name.replace("_", " ") for char_tag in character.tags]

    # 2. Build LoRA prompt
    lora_prompt_parts = []
    if character.loras:
        for lora_entry in character.loras:
            lora_obj = db.query(LoRA).filter(LoRA.id == lora_entry['lora_id']).first()
            if lora_obj:
                weight = lora_entry.get('weight', 1.0)
                lora_prompt_parts.append(f"<lora:{lora_obj.name}:{weight}>")
                if lora_obj.trigger_words:
                    tag_list.extend(lora_obj.trigger_words)

    # 3. Construct prompt
    # Use character's reference_base_prompt or fallback to default
    base_positive = character.reference_base_prompt or DEFAULT_REFERENCE_BASE_PROMPT

    # Remove duplicate tags (simple set)
    unique_tags = list(dict.fromkeys(tag_list))

    # Build full prompt (only add tags/loras if they exist)
    prompt_parts = [base_positive]
    if unique_tags:
        prompt_parts.append(', '.join(unique_tags))
    if lora_prompt_parts:
        prompt_parts.append(' '.join(lora_prompt_parts))
    full_prompt = ', '.join(prompt_parts)

    # 4. Construct negative prompt
    # Use character's reference_negative_prompt or fallback to default
    base_negative = character.reference_negative_prompt or DEFAULT_REFERENCE_NEGATIVE_PROMPT

    if character.recommended_negative:
        # Append recommended negative if not already in base
        extras = [n for n in character.recommended_negative if n not in base_negative]
        if extras:
            base_negative += ", " + ", ".join(extras)

    # Required tags for IP-Adapter reference (must detect these)
    required_tags = ["looking_at_viewer"]

    best_image = None
    best_score = -1

    for attempt in range(max_attempts):
        payload = {
            "prompt": full_prompt,
            "negative_prompt": base_negative,
            "steps": 25,
            "width": 512,
            "height": 512,
            "cfg_scale": 7.0,
            "sampler_name": "Euler a",
            "seed": random.randint(0, 2**32 - 1) if attempt > 0 else -1
        }

        logger.info(f"🎨 [{attempt+1}/{max_attempts}] Generating reference for {character.name}...")
        logger.info(f"  Prompt: {payload['prompt'][:200]}...")
        logger.info(f"  Negative: {payload['negative_prompt'][:100]}...")

        # 5. Call SD
        async with httpx.AsyncClient() as client:
            resp = await client.post(SD_TXT2IMG_URL, json=payload, timeout=120)
            resp.raise_for_status()
            r = resp.json()
            image_b64 = r['images'][0]

        if not validate:
            return save_reference_image(character.name, image_b64)

        # 6. Validate with WD14
        validation = _validate_reference_image(image_b64, required_tags)
        score = len(validation["detected"]) / len(required_tags) if required_tags else 1.0

        logger.info(f"🔍 [{attempt+1}] Validation: valid={validation['valid']}, "
                   f"detected={validation['detected']}, missing={validation['missing']}")

        if validation["valid"]:
            logger.info("✅ Reference image validated successfully!")
            return save_reference_image(character.name, image_b64)

        # Track best attempt
        if score > best_score:
            best_score = score
            best_image = image_b64

    # If all attempts failed, save the best one
    logger.warning(f"⚠️ Validation failed after {max_attempts} attempts. Using best image (score={best_score:.1%})")
    return save_reference_image(character.name, best_image or image_b64)
