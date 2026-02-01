"""PoC: Layer Composite - 캐릭터/배경 분리 생성 + 합성.

Flat Color Girl (id=8) 캐릭터로 부엌 장면 생성.
비교: Single-pass vs Layer Composite.

실행: cd backend && python -m tests.experimental._poc_layer_composite
"""

from __future__ import annotations

import base64
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

try:
    from rembg import remove as remove_bg

    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("rembg not installed. pip install rembg")
    sys.exit(1)

from config import SD_BASE_URL

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/poc_layer_composite")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Flat Color Girl Character Data (from DB id=8) ---
CHARACTER_LORA = "<lora:flat_color:0.76>"
CHARACTER_TRIGGER = "flat color"
CHARACTER_IDENTITY = "1girl, solo, white_shirt, pleated_skirt"
CHARACTER_NEGATIVE = (
    "easynegative, lowres, bad_anatomy, bad_hands, text, error, "
    "missing_fingers, extra_digit, fewer_digits, cropped, "
    "worst_quality, low_quality, jpeg_artifacts, signature, "
    "watermark, username, blurry, verybadimagenegative_v1.3"
)

# --- Scene: Kitchen with knife ---
SCENE_EXPRESSION = "(surprised:1.1)"
SCENE_GAZE = "(looking_at_viewer:1.1)"
SCENE_POSE = "(standing:1.1)"
SCENE_ACTION = "holding_knife"
SCENE_CAMERA = "upper_body"
SCENE_ENVIRONMENT = "kitchen, indoors, bright, day"

SD_BASE_PARAMS = {
    "width": 512,
    "height": 768,
    "steps": 27,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 42,
    "override_settings": {"CLIP_stop_at_last_layers": 2},
    "override_settings_restore_afterwards": True,
}


def call_sd(prompt: str, negative: str, label: str) -> Image.Image | None:
    """SD API call and return PIL Image."""
    payload = {**SD_BASE_PARAMS, "prompt": prompt, "negative_prompt": negative}
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"  Prompt: {prompt[:120]}...")
    print(f"  Negative: {negative[:80]}...")
    t0 = time.time()
    try:
        with httpx.Client(timeout=180.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()
        if "images" not in data or not data["images"]:
            print("  No images returned")
            return None
        img = Image.open(BytesIO(base64.b64decode(data["images"][0])))
        elapsed = time.time() - t0
        print(f"  Done: {img.size} in {elapsed:.1f}s")
        return img
    except Exception as e:
        print(f"  FAILED: {e}")
        return None


def test_1_single_pass() -> Image.Image | None:
    """현재 방식: 모든 태그를 하나의 프롬프트로."""
    prompt = (
        f"masterpiece, best_quality, {CHARACTER_IDENTITY}, {CHARACTER_LORA}, "
        f"BREAK, {SCENE_EXPRESSION}, {SCENE_GAZE}, {SCENE_POSE}, "
        f"{CHARACTER_TRIGGER}, {SCENE_ACTION}, "
        f"BREAK, {SCENE_CAMERA}, {SCENE_ENVIRONMENT}, anime_style, anime"
    )
    img = call_sd(prompt, CHARACTER_NEGATIVE, "TEST 1: Single-Pass (Current)")
    if img:
        img.save(OUTPUT_DIR / "1_single_pass.png")
    return img


def test_2_character_layer() -> Image.Image | None:
    """캐릭터만 생성 (white background, no environment)."""
    prompt = (
        f"masterpiece, best_quality, {CHARACTER_IDENTITY}, {CHARACTER_LORA}, "
        f"{CHARACTER_TRIGGER}, "
        f"{SCENE_EXPRESSION}, {SCENE_GAZE}, {SCENE_POSE}, {SCENE_ACTION}, "
        f"white_background, simple_background"
    )
    negative = (
        f"{CHARACTER_NEGATIVE}, "
        "detailed_background, scenery, outdoors, indoors, landscape"
    )
    img = call_sd(prompt, negative, "TEST 2: Character Layer (white bg)")
    if img:
        img.save(OUTPUT_DIR / "2_character_raw.png")
    return img


def test_3_rembg(char_img: Image.Image) -> Image.Image | None:
    """rembg로 배경 제거."""
    print(f"\n{'='*60}")
    print("[TEST 3: Background Removal (rembg)]")
    t0 = time.time()
    result = remove_bg(char_img)
    elapsed = time.time() - t0
    print(f"  Done: {result.size}, mode={result.mode} in {elapsed:.1f}s")
    result.save(OUTPUT_DIR / "3_character_nobg.png")
    return result


def test_4_background_layer() -> Image.Image | None:
    """배경만 생성 (no character)."""
    prompt = (
        f"masterpiece, best_quality, detailed_background, no_humans, "
        f"{SCENE_CAMERA}, {SCENE_ENVIRONMENT}, anime_style"
    )
    negative = (
        "1girl, 1boy, person, human, face, body, character, "
        "lowres, worst_quality, low_quality, text, watermark"
    )
    img = call_sd(prompt, negative, "TEST 4: Background Layer (no humans)")
    if img:
        img.save(OUTPUT_DIR / "4_background.png")
    return img


def test_5_composite(
    char_rgba: Image.Image, bg_img: Image.Image
) -> Image.Image | None:
    """캐릭터 + 배경 합성."""
    print(f"\n{'='*60}")
    print("[TEST 5: Composite (character on background)]")

    bg_w, bg_h = bg_img.size

    # upper_body: character fills ~65% of background height
    camera_scale = 0.65
    target_h = int(bg_h * camera_scale)
    scale_factor = target_h / char_rgba.height
    target_w = int(char_rgba.width * scale_factor)

    # Clamp width
    if target_w > int(bg_w * 0.9):
        target_w = int(bg_w * 0.9)
        target_h = int(char_rgba.height * (target_w / char_rgba.width))

    char_resized = char_rgba.resize((target_w, target_h), Image.LANCZOS)

    # Center horizontally, slight offset from top
    x = (bg_w - target_w) // 2
    y = int(bg_h * 0.05)
    if y + target_h > bg_h:
        y = bg_h - target_h

    bg_rgba = bg_img.convert("RGBA")
    bg_rgba.paste(char_resized, (x, y), char_resized)
    final = bg_rgba.convert("RGB")

    print(f"  Character: {char_resized.size} at ({x}, {y})")
    print(f"  Background: {bg_img.size}")
    print(f"  Final: {final.size}")
    final.save(OUTPUT_DIR / "5_composite.png")
    return final


def test_6_composite_variants(
    char_rgba: Image.Image, bg_img: Image.Image
) -> None:
    """다른 카메라 태그로 합성 변형."""
    print(f"\n{'='*60}")
    print("[TEST 6: Composite Variants (different camera tags)]")

    camera_configs = {
        "close-up": (0.0, 0.45),
        "upper_body": (0.05, 0.65),
        "cowboy_shot": (0.0, 0.80),
        "full_body": (0.0, 0.95),
    }

    bg_w, bg_h = bg_img.size

    for tag, (y_ratio, scale) in camera_configs.items():
        target_h = int(bg_h * scale)
        factor = target_h / char_rgba.height
        target_w = int(char_rgba.width * factor)
        if target_w > int(bg_w * 0.9):
            target_w = int(bg_w * 0.9)
            target_h = int(char_rgba.height * (target_w / char_rgba.width))

        char_resized = char_rgba.resize((target_w, target_h), Image.LANCZOS)
        x = (bg_w - target_w) // 2
        y = int(bg_h * y_ratio)
        if y + target_h > bg_h:
            y = bg_h - target_h

        canvas = bg_img.convert("RGBA")
        canvas.paste(char_resized, (x, y), char_resized)
        out = canvas.convert("RGB")
        out.save(OUTPUT_DIR / f"6_variant_{tag.replace('-', '_')}.png")
        print(f"  {tag}: scale={scale}, pos=({x},{y}), size={char_resized.size}")


def check_sd_connection() -> bool:
    """SD WebUI 연결 확인."""
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SD_BASE_URL}/sdapi/v1/options")
            res.raise_for_status()
            model = res.json().get("sd_model_checkpoint", "?")
            print(f"SD WebUI: {model}")
            return True
    except Exception as e:
        print(f"SD WebUI not available: {e}")
        return False


def main():
    print("=" * 60)
    print("PoC: Layer Composite Image Generation")
    print(f"Character: Flat Color Girl (id=8)")
    print(f"Scene: Kitchen + surprised + holding knife")
    print(f"Output: {OUTPUT_DIR}/")
    print("=" * 60)

    if not check_sd_connection():
        sys.exit(1)

    # Test 1: Current single-pass approach
    single = test_1_single_pass()

    # Test 2: Character layer (white background)
    char_raw = test_2_character_layer()
    if not char_raw:
        print("\nCharacter generation failed. Stopping.")
        sys.exit(1)

    # Test 3: Background removal
    char_nobg = test_3_rembg(char_raw)
    if not char_nobg:
        print("\nBackground removal failed. Stopping.")
        sys.exit(1)

    # Test 4: Background layer (no character)
    bg = test_4_background_layer()
    if not bg:
        print("\nBackground generation failed. Stopping.")
        sys.exit(1)

    # Test 5: Composite
    composite = test_5_composite(char_nobg, bg)

    # Test 6: Camera variants
    test_6_composite_variants(char_nobg, bg)

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS")
    print("=" * 60)
    files = sorted(OUTPUT_DIR.glob("*.png"))
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:40s} {size_kb:6.0f} KB")
    print(f"\nTotal: {len(files)} images in {OUTPUT_DIR}/")
    print("\nCompare:")
    print(f"  1_single_pass.png     = Current method (all in one)")
    print(f"  5_composite.png       = Layer composite (char + bg)")
    print(f"  6_variant_*.png       = Different camera framings")


if __name__ == "__main__":
    main()
