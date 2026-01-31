"""Image utility functions for Shorts Producer Backend."""

from __future__ import annotations

import base64
from urllib.parse import urlparse

import numpy as np
from PIL import Image


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
            direct_path = OUTPUT_DIR / storage_key
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


def calculate_optimal_subtitle_y(
    image: Image.Image,
    default_y_ratio: float = 0.72,
    layout_style: str = "full"
) -> float:
    """Calculate optimal Y position for subtitle based on image content.

    Args:
        image: PIL Image to analyze
        default_y_ratio: Default Y position ratio (0.72 = 72% from top)
        layout_style: "full" or "post" layout

    Returns:
        Optimal Y position ratio (0.0 to 1.0)
    """
    complexity = analyze_bottom_complexity(image)

    # Thresholds for adjustment (calibrated for std_dev + edge_density metric)
    HIGH_COMPLEXITY = 0.20  # Move subtitle up if complexity > 0.20
    LOW_COMPLEXITY = 0.10   # Move subtitle down if complexity < 0.10

    if complexity > HIGH_COMPLEXITY:
        # High complexity: move subtitle up significantly
        return 0.60 if layout_style == "full" else 0.78
    elif complexity < LOW_COMPLEXITY:
        # Low complexity: can place subtitle lower
        return 0.75 if layout_style == "full" else 0.85
    else:
        # Moderate complexity: use default
        return default_y_ratio
