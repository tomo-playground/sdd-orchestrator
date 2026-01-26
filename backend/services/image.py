"""Image utility functions for Shorts Producer Backend."""

from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from PIL import Image

from config import OUTPUT_DIR


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
    else:
        path = source
    if path.startswith("/outputs/"):
        rel_path = path.replace("/outputs/", "", 1)
        candidate = (OUTPUT_DIR / rel_path).resolve()
        if OUTPUT_DIR.resolve() not in candidate.parents and candidate != OUTPUT_DIR.resolve():
            raise ValueError("Invalid image path")
        return candidate.read_bytes()
    # Try raw base64 as fallback
    try:
        return base64.b64decode(source)
    except Exception:
        raise ValueError("Unsupported image source")


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

    # Calculate variance (normalized to 0-1)
    variance = np.var(pixels) / (255.0 ** 2)

    # Calculate edge density using simple gradient
    grad_x = np.abs(np.diff(pixels, axis=1))
    grad_y = np.abs(np.diff(pixels, axis=0))
    edge_density = (np.mean(grad_x) + np.mean(grad_y)) / (2 * 255.0)

    # Combine metrics (weighted average)
    complexity = variance * 0.6 + edge_density * 0.4

    # Clamp to 0-1
    return min(1.0, max(0.0, complexity))


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

    # Thresholds for adjustment
    HIGH_COMPLEXITY = 0.6
    LOW_COMPLEXITY = 0.3

    if complexity > HIGH_COMPLEXITY:
        # High complexity: move subtitle up significantly
        return 0.60 if layout_style == "full" else 0.78
    elif complexity < LOW_COMPLEXITY:
        # Low complexity: can place subtitle lower
        return 0.75 if layout_style == "full" else 0.85
    else:
        # Moderate complexity: use default
        return default_y_ratio
