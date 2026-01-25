"""포옹 장면 합성 테스트: 캐릭터 + 배경 레이어 합성.

테스트 항목:
1. 배경 생성: 비 오는 풍경
2. 캐릭터 생성: 포옹 포즈 (LoRA 적용)
3. 레이어 합성: 배경 + 캐릭터들
4. 비교: 단일 생성 vs 분리 합성

실행: python -m tests.test_hug_composite
"""

from __future__ import annotations

import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageEnhance, ImageFilter

try:
    from rembg import remove as remove_bg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("⚠️  rembg 미설치")

import pytest
from PIL import Image

from config import SD_BASE_URL
from services.image import (
    build_ip_adapter_args,
    generate_image_advanced,
    save_reference_image,
)

# Configuration for testing

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/hug_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# LoRA 설정 (사용 가능한 LoRA 중 선택)
LORA_NAME = "eureka_v9"  # 또는 다른 LoRA
LORA_WEIGHT = 0.7


def generate_image(prompt: str, negative: str, seed: int = -1, **kwargs) -> Image.Image | None:
    """SD API로 이미지 생성."""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "width": kwargs.get("width", 512),
        "height": kwargs.get("height", 768),
        "steps": kwargs.get("steps", 20),
        "cfg_scale": kwargs.get("cfg_scale", 7),
        "sampler_name": kwargs.get("sampler_name", "DPM++ 2M"),
        "seed": seed,
    }

    try:
        with httpx.Client(timeout=180.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()

            if "images" not in data or not data["images"]:
                return None

            img_b64 = data["images"][0]
            img_bytes = base64.b64decode(img_b64)
            return Image.open(BytesIO(img_bytes))
    except httpx.HTTPError as e:
        print(f"  ❌ SD 오류: {e}")
        return None


def test_single_generation_hug():
    """방법 1: SD에서 직접 2인 포옹 장면 생성."""
    print("\n" + "=" * 50)
    print("🧪 방법 1: 단일 이미지로 포옹 장면 생성")
    print("=" * 50)

    prompt = f"""2girls, hug, hugging, embrace, from side,
1girl short brown hair blue eyes school uniform,
1girl long black hair red eyes hoodie,
rain, rainy day, wet, water droplets,
city background, street, emotional, beautiful lighting,
<lora:{LORA_NAME}:{LORA_WEIGHT}>,
masterpiece, best quality, detailed"""

    negative = """lowres, bad anatomy, bad hands, text, error,
missing fingers, extra digit, fewer digits, cropped,
worst quality, low quality, normal quality, jpeg artifacts,
signature, watermark, username, blurry,
extra arms, extra legs, bad proportions, gross proportions"""

    print(f"  📤 생성 중 (LoRA: {LORA_NAME})...")
    img = generate_image(prompt, negative, seed=42, width=768, height=768)

    if img:
        path = OUTPUT_DIR / "method1_single_hug.png"
        img.save(path)
        print(f"  ✅ 저장: {path}")
        return img
    else:
        print("  ❌ 생성 실패")
        return None


def test_layered_composite_hug():
    """방법 2: 배경 + 캐릭터 분리 생성 후 합성."""
    print("\n" + "=" * 50)
    print("🧪 방법 2: 레이어 분리 합성")
    print("=" * 50)

    # Step 1: 배경 생성
    print("\n  [Step 1] 배경 생성 (비 오는 풍경)...")
    bg_prompt = """rain, rainy day, city street, wet ground,
water droplets, puddles, street lights, evening,
atmospheric, moody lighting, no people, empty street,
masterpiece, best quality, detailed background"""

    bg_negative = "people, person, character, anime character, text, watermark"

    bg_img = generate_image(bg_prompt, bg_negative, seed=100, width=768, height=1024)
    if bg_img:
        bg_path = OUTPUT_DIR / "layer_background.png"
        bg_img.save(bg_path)
        print(f"  ✅ 배경 저장: {bg_path}")
    else:
        print("  ❌ 배경 생성 실패")
        return None

    # Step 2: 포옹하는 캐릭터들 (투명 배경)
    print("\n  [Step 2] 포옹 캐릭터 생성...")
    char_prompt = f"""2girls, hug, hugging, embrace, from side,
1girl short brown hair blue eyes school uniform,
1girl long black hair red eyes hoodie,
full body, standing,
white background, simple background,
<lora:{LORA_NAME}:{LORA_WEIGHT}>,
masterpiece, best quality"""

    char_negative = """lowres, bad anatomy, bad hands, text, error,
worst quality, low quality, jpeg artifacts, watermark,
extra arms, extra legs, bad proportions"""

    char_img = generate_image(char_prompt, char_negative, seed=42, width=512, height=768)
    if char_img:
        char_path = OUTPUT_DIR / "layer_characters.png"
        char_img.save(char_path)
        print(f"  ✅ 캐릭터 저장: {char_path}")

        # 배경 제거
        if HAS_REMBG:
            print("  🔄 배경 제거 중...")
            char_nobg = remove_bg(char_img)
            char_nobg_path = OUTPUT_DIR / "layer_characters_nobg.png"
            char_nobg.save(char_nobg_path)
            print(f"  ✅ 배경 제거 완료: {char_nobg_path}")
        else:
            char_nobg = char_img
    else:
        print("  ❌ 캐릭터 생성 실패")
        return None

    # Step 3: 합성
    print("\n  [Step 3] 레이어 합성...")
    composite = composite_layers(bg_img, char_nobg)
    if composite:
        comp_path = OUTPUT_DIR / "method2_layered_hug.png"
        composite.save(comp_path)
        print(f"  ✅ 합성 완료: {comp_path}")
        return composite

    return None


def composite_layers(background: Image.Image, characters: Image.Image) -> Image.Image:
    """배경 위에 캐릭터 합성."""
    # 캔버스 크기 맞추기
    canvas = background.copy().convert("RGBA")

    # 캐릭터 리사이즈 (배경의 70% 높이)
    target_h = int(canvas.height * 0.75)
    ratio = target_h / characters.height
    target_w = int(characters.width * ratio)
    char_resized = characters.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # 중앙 하단에 배치
    x = (canvas.width - target_w) // 2
    y = canvas.height - target_h - 20  # 하단에서 20px 위

    # 합성
    if char_resized.mode == "RGBA":
        canvas.paste(char_resized, (x, y), char_resized)
    else:
        canvas.paste(char_resized, (x, y))

    # 비 효과 오버레이 (선택적)
    canvas = add_rain_overlay(canvas)

    return canvas


def add_rain_overlay(img: Image.Image) -> Image.Image:
    """비 효과 오버레이 추가."""
    # 간단한 비 효과: 세로선 + 블러
    from PIL import ImageDraw
    import random

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 빗줄기 그리기
    for _ in range(100):
        x = random.randint(0, img.width)
        y = random.randint(0, img.height)
        length = random.randint(20, 50)
        draw.line([(x, y), (x + 2, y + length)], fill=(200, 200, 255, 30), width=1)

    # 블러 적용
    overlay = overlay.filter(ImageFilter.GaussianBlur(1))

    # 합성
    result = Image.alpha_composite(img.convert("RGBA"), overlay)
    return result


def test_individual_poses():
    """방법 3: 개별 캐릭터 포옹 포즈 생성 후 수동 합성."""
    print("\n" + "=" * 50)
    print("🧪 방법 3: 개별 포옹 포즈 생성")
    print("=" * 50)

    # 캐릭터 A: 포옹하는 포즈 (왼쪽에서)
    print("\n  [캐릭터 A] 포옹 포즈 (안는 쪽)...")
    char_a_prompt = f"""1girl, short brown hair, blue eyes, school uniform,
hugging pose, arms forward, leaning forward, eyes closed, happy,
from side, white background, simple background,
<lora:{LORA_NAME}:{LORA_WEIGHT}>,
masterpiece, best quality"""

    char_a = generate_image(char_a_prompt, "lowres, bad anatomy, worst quality", seed=123)
    if char_a:
        path = OUTPUT_DIR / "pose_char_a_hug.png"
        char_a.save(path)
        print(f"  ✅ 저장: {path}")

        if HAS_REMBG:
            char_a_nobg = remove_bg(char_a)
            char_a_nobg.save(OUTPUT_DIR / "pose_char_a_hug_nobg.png")

    # 캐릭터 B: 포옹 받는 포즈
    print("\n  [캐릭터 B] 포옹 포즈 (안기는 쪽)...")
    char_b_prompt = f"""1girl, long black hair, red eyes, hoodie,
being hugged, arms around, leaning back slightly, smile, blush,
from side, white background, simple background,
<lora:{LORA_NAME}:{LORA_WEIGHT}>,
masterpiece, best quality"""

    char_b = generate_image(char_b_prompt, "lowres, bad anatomy, worst quality", seed=456)
    if char_b:
        path = OUTPUT_DIR / "pose_char_b_hug.png"
        char_b.save(path)
        print(f"  ✅ 저장: {path}")

        if HAS_REMBG:
            char_b_nobg = remove_bg(char_b)
            char_b_nobg.save(OUTPUT_DIR / "pose_char_b_hug_nobg.png")


def check_sd_connection():
    """SD WebUI 연결 확인."""
    print("🔌 SD WebUI 연결 확인...")
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SD_BASE_URL}/sdapi/v1/options")
            res.raise_for_status()
            data = res.json()
            model = data.get("sd_model_checkpoint", "Unknown")
            print(f"  ✅ 연결됨 - 모델: {model}")
            return True
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        return False


def main():
    print("🤗 포옹 장면 합성 테스트")
    print(f"   LoRA: {LORA_NAME} (weight: {LORA_WEIGHT})")
    print("=" * 50)

    if not check_sd_connection():
        sys.exit(1)

    # 방법 1: 단일 생성
    test_single_generation_hug()

    # 방법 2: 레이어 합성
    test_layered_composite_hug()

    # 방법 3: 개별 포즈 (참고용)
    test_individual_poses()

    print("\n" + "=" * 50)
    print(f"✅ 테스트 완료! 결과: {OUTPUT_DIR}/")
    print("\n📊 비교 포인트:")
    print("  - method1_single_hug.png: SD 직접 생성")
    print("  - method2_layered_hug.png: 배경+캐릭터 합성")
    print("=" * 50)


if __name__ == "__main__":
    main()
