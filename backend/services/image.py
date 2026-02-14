"""Image utility functions for Shorts Producer Backend."""

from __future__ import annotations

import base64
from urllib.parse import urlparse

import numpy as np
from PIL import Image

# Platform-specific safe zones (bottom margin to avoid UI overlap)
# Values represent the bottom percentage of the screen to avoid
PLATFORM_SAFE_ZONES = {
    "youtube_shorts": 0.15,  # Bottom 15% (like button, comments, share)
    "tiktok": 0.20,  # Bottom 20% (more UI elements)
    "instagram_reels": 0.18,  # Bottom 18% (action buttons)
    "default": 0.15,  # Default fallback
}


def decode_data_url(data_url: str) -> bytes:
    """Decode a base64 data URL to bytes."""
    if not data_url:
        raise ValueError("Empty image data")
    b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
    return base64.b64decode(b64)


def load_image_bytes(source: str) -> bytes:
    """Load image bytes from various sources (data URL, HTTP URL, local path, or raw base64).

    Args:
        source: Data URL, HTTP URL, local path starting with /outputs/, or raw base64

    Returns:
        Image bytes

    Raises:
        ValueError: If source is empty, invalid, or unsupported
    """
    if not source:
        raise ValueError("Empty image data")
    if source.startswith("data:"):
        return decode_data_url(source)
    if source.startswith(("http://", "https://")):
        parsed = urlparse(source)
        path = parsed.path

        # Handle MinIO/S3 URLs: /{bucket_name}/{storage_key}
        # Extract storage_key by removing bucket prefix
        from config import MINIO_BUCKET

        if path.startswith(f"/{MINIO_BUCKET}/"):
            storage_key = path.replace(f"/{MINIO_BUCKET}/", "", 1)
            try:
                from services.storage import get_storage

                storage = get_storage()
                local_path = storage.get_local_path(storage_key)
                return local_path.read_bytes()
            except Exception as e:
                raise ValueError(f"Failed to load image from storage URL: {e}") from e
    else:
        path = source

    # Legacy redirect for /assets/ to shared storage
    if path.startswith("/assets/references/"):
        storage_key = path.replace("/assets/references/", "shared/references/", 1).lstrip("/")
        try:
            from services.storage import get_storage

            return get_storage().get_local_path(storage_key).read_bytes()
        except Exception:
            pass
    if path.startswith("/assets/poses/"):
        storage_key = path.replace("/assets/poses/", "shared/poses/", 1).lstrip("/")
        try:
            from services.storage import get_storage

            return get_storage().get_local_path(storage_key).read_bytes()
        except Exception:
            pass

    if path.startswith("/outputs/"):
        storage_key = path.replace("/outputs/", "", 1)

        # 1. Try direct local file first (e.g., if switching storage modes)
        try:
            from config import OUTPUT_DIR
            from services.path_security import safe_storage_path

            direct_path = safe_storage_path(OUTPUT_DIR, storage_key)
            if direct_path.exists():
                return direct_path.read_bytes()
        except Exception:
            pass

        # 2. Try storage service (S3 download or local lookup)
        try:
            from services.storage import get_storage

            storage = get_storage()
            local_path = storage.get_local_path(storage_key)
            return local_path.read_bytes()
        except Exception as e:
            raise ValueError(f"Failed to load image from storage: {e}") from e
    # Try raw base64 as fallback
    try:
        return base64.b64decode(source)
    except Exception as exc:
        raise ValueError("Unsupported image source") from exc


def load_as_data_url(source: str) -> str:
    """Load image from source and return as data URL string."""
    image_bytes = load_image_bytes(source)
    return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"


def analyze_bottom_complexity(image: Image.Image, region_ratio: float = 0.2) -> float:
    """Analyze complexity of bottom region of image.

    Args:
        image: PIL Image to analyze
        region_ratio: Ratio of bottom region to analyze (0.2 = bottom 20%)

    Returns:
        Complexity score (0.0 to 1.0). Higher = more complex.
        - 0.0-0.3: Simple/empty (can place subtitle lower)
        - 0.3-0.7: Moderate complexity
        - 0.7-1.0: High complexity (move subtitle up)
    """
    # Convert to grayscale for complexity analysis
    gray = image.convert("L")
    width, height = gray.size

    # Extract bottom region
    bottom_height = int(height * region_ratio)
    bottom_region = gray.crop((0, height - bottom_height, width, height))

    # Convert to numpy array
    pixels = np.array(bottom_region, dtype=np.float32)

    # Calculate standard deviation (normalized to 0-1)
    # std_dev represents pixel value variation across the region
    std_dev = np.std(pixels) / 255.0

    # Calculate edge density using simple gradient
    grad_x = np.abs(np.diff(pixels, axis=1))
    grad_y = np.abs(np.diff(pixels, axis=0))
    edge_density = (np.mean(grad_x) + np.mean(grad_y)) / (2 * 255.0)

    # Combine metrics (weighted average)
    # std_dev: overall variation, edge_density: detail/texture
    # Edge density is weighted higher as it better captures visual complexity
    complexity = std_dev * 0.3 + edge_density * 0.7

    # Clamp to 0-1
    return float(min(1.0, max(0.0, complexity)))


def calculate_optimal_scene_text_y(
    image: Image.Image,
    default_y_ratio: float = 0.12,
    layout_style: str = "full",
    platform: str = "default",
) -> float:
    """Calculate optimal Y position for scene text based on image content.

    Args:
        image: PIL Image to analyze
        default_y_ratio: Default Y position ratio (0.68 = bottom 68%)
        layout_style: "full" or "post" layout
        platform: Target platform ("youtube_shorts", "tiktok", "instagram_reels", "default")

    Returns:
        Optimal Y position ratio (0.0 to 1.0)
    """
    complexity = analyze_bottom_complexity(image)

    # Thresholds for adjustment (calibrated for std_dev + edge_density metric)
    HIGH_COMPLEXITY = 0.20  # Move scene text up if complexity > 0.20
    LOW_COMPLEXITY = 0.10  # Move scene text down if complexity < 0.10

    if layout_style == "full":
        # Full layout: scene text is at bottom (68-72% from top)
        # Dynamic adjustment within bottom region to avoid platform UI / image detail

        # Apply platform-specific safe zone
        safe_zone = PLATFORM_SAFE_ZONES.get(platform, 0.15)
        max_y = 1.0 - safe_zone  # e.g., 0.85 for 15% bottom margin

        if complexity > HIGH_COMPLEXITY:
            y_pos = 0.65  # Move slightly higher to avoid complex bottom
        elif complexity < LOW_COMPLEXITY:
            y_pos = 0.72  # Slightly lower if bottom is simple
        else:
            y_pos = 0.68 if default_y_ratio < 0.2 else default_y_ratio

        # Ensure scene text doesn't enter platform UI zone
        return min(y_pos, max_y)
    else:
        # Post layout: scene text stays in bottom region
        if complexity > HIGH_COMPLEXITY:
            return 0.78
        elif complexity < LOW_COMPLEXITY:
            return 0.85
        else:
            return default_y_ratio


def analyze_text_region_brightness(image: Image.Image, text_y_ratio: float) -> float:
    """Analyze brightness of the text region for adaptive text color.

    Args:
        image: PIL Image to analyze
        text_y_ratio: Y position ratio of text (0.0-1.0)

    Returns:
        Average brightness (0-255)
    """
    width, height = image.size
    text_y = int(height * text_y_ratio)
    text_height = int(height * 0.15)  # Text region height (approximately)

    # Crop text region
    y_end = min(text_y + text_height, height)
    text_region = image.crop((0, text_y, width, y_end))

    # Convert to grayscale and calculate average brightness
    gray = text_region.convert("L")
    pixels = list(gray.getdata())
    avg_brightness = sum(pixels) / len(pixels) if pixels else 128

    return avg_brightness


def detect_face(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Detect face in image using OpenCV Haar Cascade.

    Args:
        image: PIL Image to analyze

    Returns:
        (x, y, width, height) of largest face, or None if no face detected
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        # OpenCV not available, return None
        return None

    try:
        # Convert PIL Image to OpenCV format
        img_array = np.array(image.convert("RGB"))
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # Load Haar Cascade classifier
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) == 0:
            return None

        # Return largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        return tuple(largest_face)
    except Exception:
        # Face detection failed, return None
        return None


def calculate_face_centered_crop(
    image_width: int,
    image_height: int,
    face_rect: tuple[int, int, int, int],
    target_aspect_ratio: float = 1.0,
) -> tuple[int, int, int, int]:
    """Calculate crop box centered on face.

    Args:
        image_width: Original image width
        image_height: Original image height
        face_rect: (x, y, width, height) of detected face
        target_aspect_ratio: Target aspect ratio (width/height)

    Returns:
        (x, y, width, height) crop box
    """
    face_x, face_y, face_w, face_h = face_rect
    face_center_x = face_x + face_w // 2
    face_center_y = face_y + face_h // 2

    # Calculate crop dimensions
    if image_width / image_height > target_aspect_ratio:
        # Image is wider than target
        crop_height = image_height
        crop_width = int(crop_height * target_aspect_ratio)
    else:
        # Image is taller than target
        crop_width = image_width
        crop_height = int(crop_width / target_aspect_ratio)

    # Center crop on face
    crop_x = face_center_x - crop_width // 2
    crop_y = face_center_y - crop_height // 2

    # Clamp to image boundaries
    crop_x = max(0, min(crop_x, image_width - crop_width))
    crop_y = max(0, min(crop_y, image_height - crop_height))

    return (crop_x, crop_y, crop_width, crop_height)
