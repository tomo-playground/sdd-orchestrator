"""Simple avatar generation without SD WebUI."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib


def generate_simple_avatar(
    avatar_key: str,
    output_path: Path,
    size: int = 256,
) -> None:
    """Generate a simple colored avatar with initials.

    Args:
        avatar_key: The avatar key (e.g., channel name)
        output_path: Path to save the avatar
        size: Avatar size in pixels (default: 256)
    """
    # Generate a color based on the avatar_key hash
    hash_value = hashlib.md5(avatar_key.encode()).hexdigest()
    r = int(hash_value[0:2], 16)
    g = int(hash_value[2:4], 16)
    b = int(hash_value[4:6], 16)

    # Create a gradient background
    image = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Draw gradient circle
    for i in range(size):
        ratio = i / size
        color = (
            int(r * (1 - ratio * 0.3)),
            int(g * (1 - ratio * 0.3)),
            int(b * (1 - ratio * 0.3)),
        )
        draw.ellipse(
            (i // 2, i // 2, size - i // 2, size - i // 2),
            fill=color,
        )

    # Get initial letter
    initial = (avatar_key.strip()[:1] or "A").upper()

    # Draw text
    try:
        # Try to use a nice font
        font_size = size // 2
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()

    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), initial, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size - text_w) // 2
    text_y = (size - text_h) // 2 - size // 20

    # Draw text with shadow for better visibility
    shadow_offset = size // 50
    draw.text((text_x + shadow_offset, text_y + shadow_offset), initial, fill=(0, 0, 0, 128), font=font)
    draw.text((text_x, text_y), initial, fill=(255, 255, 255), font=font)

    # Save as PNG
    image.save(output_path, "PNG")
