"""복장 일관성 개선 실험 (Strong Reference-only)

목표: 복장(교복) 디테일까지 정확히 고정

개선사항:
1. Reference-only weight: 0.5 → 0.75 (강화)
2. guidance_end: 0.8 → 1.0 (끝까지 참조)
3. LoRA weight: 0.8 → 0.6 (Reference와 충돌 방지)
4. 프롬프트에 복장 디테일 추가

실행:
    python -m tests._experimental_clothing_consistency

결과:
    outputs/clothing_test/
    ├── 1_base_detailed.png         # 디테일한 기준 이미지
    ├── 2_strong_ref_standing.png   # 강화된 Reference-only
    ├── 2_strong_ref_walking.png
    ├── 2_strong_ref_sitting.png
    └── 2_strong_ref_running.png
"""

from __future__ import annotations

import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SD_BASE_URL
from services.controlnet import build_reference_only_args

# Configuration
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/clothing_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Character settings - LoRA weight 낮춤
CHARACTER_LORA = "eureka_v9"
LORA_WEIGHT = 0.6  # 0.8 → 0.6 (Reference와 충돌 방지)

# 복장 디테일 명시
CLOTHING_DETAILS = "school uniform, white shirt, blue skirt, red ribbon, sailor collar"
BASE_PROMPT = f"<lora:{CHARACTER_LORA}:{LORA_WEIGHT}>, 1girl, eureka, {CLOTHING_DETAILS}, masterpiece, best quality"
NEGATIVE = "nsfw, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, multiple outfits, changing clothes"

# Test poses
POSES = {
    "standing": "standing, arms at sides, neutral pose",
    "walking": "walking, one leg forward, casual walk",
    "sitting": "sitting, on chair, hands on lap",
    "running": "running, dynamic pose, motion",
}


def image_to_base64(img: Image.Image) -> str:
    """PIL 이미지를 Base64로 변환."""
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_image(
    prompt: str,
    negative: str = NEGATIVE,
    seed: int = -1,
    controlnet_args: list | None = None,
    **kwargs,
) -> Image.Image | None:
    """SD API로 이미지 생성."""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "width": 512,
        "height": 768,
        "steps": kwargs.get("steps", 27),
        "cfg_scale": kwargs.get("cfg_scale", 7),
        "sampler_name": kwargs.get("sampler_name", "DPM++ 2M Karras"),
        "seed": seed,
        "clip_skip": 2,
    }

    if controlnet_args:
        payload["alwayson_scripts"] = {"controlnet": {"args": controlnet_args}}

    try:
        print(f"  📤 Generating: {prompt[:60]}...")
        if controlnet_args:
            for arg in controlnet_args:
                module = arg.get("module", "unknown")
                weight = arg.get("weight", 0)
                guidance_end = arg.get("guidance_end", 1.0)
                print(f"     ControlNet: {module} (weight={weight}, guidance_end={guidance_end})")

        with httpx.Client(timeout=180.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()

            if "images" not in data or not data["images"]:
                return None

            img_b64 = data["images"][0]
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_bytes))
            print(f"  ✅ Generated: {img.size}")
            return img

    except httpx.HTTPError as e:
        print(f"  ❌ Error: {e}")
        return None


def step1_create_detailed_base():
    """Step 1: 복장 디테일이 명확한 기준 이미지 생성."""
    print("\n" + "=" * 60)
    print("🧪 Step 1: 디테일한 기준 이미지 생성")
    print("=" * 60)
    print("개선사항:")
    print("  - 복장 디테일 명시: white shirt, blue skirt, red ribbon")
    print("  - LoRA weight: 0.8 → 0.6 (Reference와 충돌 방지)")
    print("-" * 60)

    prompt = f"{BASE_PROMPT}, full body, standing, simple background, white background"

    img = generate_image(prompt, seed=12345)
    if img:
        output_path = OUTPUT_DIR / "1_base_detailed.png"
        img.save(output_path)
        print(f"💾 Saved: {output_path}")
        return img
    else:
        print("❌ Failed to generate base image")
        return None


def step2_strong_reference_test(base_image: Image.Image):
    """Step 2: 강화된 Reference-only 테스트."""
    print("\n" + "=" * 60)
    print("🧪 Step 2: 강화된 Reference-only 테스트")
    print("=" * 60)
    print("개선사항:")
    print("  - weight: 0.5 → 0.75 (강화)")
    print("  - guidance_end: 0.8 → 1.0 (끝까지 참조)")
    print("-" * 60)

    base_b64 = image_to_base64(base_image)

    for pose_name, pose_desc in POSES.items():
        print(f"\n📸 Pose: {pose_name}")
        prompt = f"{BASE_PROMPT}, {pose_desc}, library, indoors"

        # 강화된 Reference-only args
        controlnet_args = [
            build_reference_only_args(
                reference_image=base_b64,
                weight=0.75,  # 0.5 → 0.75 증가
                guidance_end=1.0,  # 0.8 → 1.0 증가
            )
        ]

        img = generate_image(prompt, controlnet_args=controlnet_args, seed=-1)
        if img:
            output_path = OUTPUT_DIR / f"2_strong_ref_{pose_name}.png"
            img.save(output_path)
            print(f"  💾 Saved: {output_path}")


def step3_ultra_strong_test(base_image: Image.Image):
    """Step 3: 초강화 Reference-only (weight=0.9)."""
    print("\n" + "=" * 60)
    print("🧪 Step 3: 초강화 Reference-only (weight=0.9)")
    print("=" * 60)
    print("설정: weight=0.9, guidance_end=1.0")
    print("목적: 최대 일관성 테스트 (포즈 자유도는 희생 가능)")
    print("-" * 60)

    base_b64 = image_to_base64(base_image)

    for pose_name, pose_desc in POSES.items():
        print(f"\n📸 Pose: {pose_name}")
        prompt = f"{BASE_PROMPT}, {pose_desc}, library, indoors"

        # 초강화 Reference-only args
        controlnet_args = [
            build_reference_only_args(
                reference_image=base_b64,
                weight=0.9,  # 최대 강화
                guidance_end=1.0,
            )
        ]

        img = generate_image(prompt, controlnet_args=controlnet_args, seed=-1)
        if img:
            output_path = OUTPUT_DIR / f"3_ultra_ref_{pose_name}.png"
            img.save(output_path)
            print(f"  💾 Saved: {output_path}")


def main():
    """실험 실행."""
    print("\n" + "=" * 60)
    print("🔬 복장 일관성 개선 실험")
    print("=" * 60)
    print(f"Character: {CHARACTER_LORA} (LoRA weight: {LORA_WEIGHT})")
    print(f"Clothing: {CLOTHING_DETAILS}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    # Check SD WebUI
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SD_BASE_URL}/sdapi/v1/sd-models")
            res.raise_for_status()
            print("✅ SD WebUI 연결됨")
    except Exception as e:
        print(f"❌ SD WebUI 연결 실패: {e}")
        return

    # Run steps
    base_image = step1_create_detailed_base()
    if not base_image:
        print("\n❌ 기준 이미지 생성 실패. 실험 중단.")
        return

    step2_strong_reference_test(base_image)
    step3_ultra_strong_test(base_image)

    print("\n" + "=" * 60)
    print("✅ 실험 완료!")
    print("=" * 60)
    print(f"결과 확인: {OUTPUT_DIR}")
    print("\n비교:")
    print("  1. 기준 이미지의 복장 디테일 확인")
    print("  2. Strong (0.75) vs Ultra (0.9) 복장 일관성 비교")
    print("  3. 포즈 자유도 vs 복장 일관성 트레이드오프 평가")
    print("=" * 60)


if __name__ == "__main__":
    main()
