"""ControlNet integration service.

Provides pose and composition control for SD image generation.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import requests

from config import SD_BASE_URL, logger

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
    "faceid": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",
}

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

    for pose in pose_priority:
        if pose in prompt_tags:
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


def save_reference_image(character_key: str, image_b64: str) -> str:
    """Save a reference image for IP-Adapter.

    Args:
        character_key: Unique key for the character (e.g., "eureka", "midoriya")
        image_b64: Base64 encoded image (with or without data URI prefix)

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
    return filename


def load_reference_image(character_key: str) -> str | None:
    """Load a reference image for IP-Adapter.

    Args:
        character_key: Unique key for the character

    Returns:
        Base64 encoded image or None if not found
    """
    filepath = REFERENCE_DIR / f"{character_key}.png"
    if not filepath.exists():
        return None
    return base64.b64encode(filepath.read_bytes()).decode("utf-8")


def list_reference_images() -> list[dict[str, str]]:
    """List all saved reference images.

    Returns:
        List of dicts with character_key and filename
    """
    ensure_reference_dir()
    refs = []
    for path in REFERENCE_DIR.glob("*.png"):
        refs.append({
            "character_key": path.stem,
            "filename": path.name,
        })
    return refs


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


def build_ip_adapter_args(
    reference_image: str,
    weight: float = 0.8,
    model: str = "faceid",
) -> dict[str, Any]:
    """Build IP-Adapter arguments for txt2img.

    Args:
        reference_image: Base64 encoded reference face image
        weight: IP-Adapter influence weight (0.0-1.5)
        model: IP-Adapter model type ("faceid")

    Returns:
        ControlNet args dict for IP-Adapter
    """
    model_name = IP_ADAPTER_MODELS.get(model)
    if not model_name:
        raise ValueError(f"Unknown IP-Adapter model: {model}")

    return {
        "enabled": True,
        "image": reference_image,
        "module": "ip-adapter_face_id_plus",
        "model": model_name,
        "weight": weight,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": "Balanced",
        "pixel_perfect": False,
    }


def build_combined_controlnet_args(
    pose_image: str | None = None,
    reference_image: str | None = None,
    pose_weight: float = 0.8,
    ip_adapter_weight: float = 0.7,
) -> list[dict[str, Any]]:
    """Build combined ControlNet + IP-Adapter args.

    Args:
        pose_image: Base64 encoded pose reference (optional)
        reference_image: Base64 encoded face reference for IP-Adapter (optional)
        pose_weight: OpenPose weight
        ip_adapter_weight: IP-Adapter weight

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
        ))

    return args
