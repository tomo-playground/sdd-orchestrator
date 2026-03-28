"""Mask generation utilities for dual IP-Adapter (SP-115).

Generates character (elliptical center) and background (inverted) masks
for attn_mask-based IP-Adapter region separation.
"""

from __future__ import annotations

import base64
import io

from PIL import Image, ImageDraw, ImageFilter


def generate_character_mask(width: int, height: int) -> str:
    """Generate center ellipse character mask as base64 PNG.

    White (255) = character region, Black (0) = masked out.
    Gaussian blur for soft feathering at edges.
    """
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    # Ellipse centered, covering ~60% width / ~70% height
    cx, cy = width // 2, height // 2
    rx, ry = int(width * 0.30), int(height * 0.35)
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)

    # Feather: gaussian blur for soft edge transition
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(width, height) // 16))

    return _image_to_b64(mask.convert("RGB"))


def generate_background_mask(width: int, height: int) -> str:
    """Generate background mask (inverted character mask) as base64 PNG."""
    mask = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(mask)

    cx, cy = width // 2, height // 2
    rx, ry = int(width * 0.30), int(height * 0.35)
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=0)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(width, height) // 16))

    return _image_to_b64(mask.convert("RGB"))


def _image_to_b64(image: Image.Image) -> str:
    """Convert PIL Image to base64 PNG string."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
