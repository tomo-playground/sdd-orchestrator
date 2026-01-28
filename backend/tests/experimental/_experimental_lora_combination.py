"""LoRA 조합 실험: 서로 다른 캐릭터 LoRA 조합

목표:
1. 다른 캐릭터 LoRA 조합 시 각 특징 유지되는지 확인
2. 최적 weight 분산 비율 찾기
3. Reference-only 추가 시 일관성 개선 확인

테스트 조합:
- Character A: eureka_v9 (여자)
- Character B: mha_midoriya-10 (남자)

실행:
    python -m tests._experimental_lora_combination

결과:
    outputs/lora_combo_test/
    ├── 1_equal_hug.png              # 0.5 / 0.5 (포옹)
    ├── 1_equal_hands.png            # 0.5 / 0.5 (손잡기)
    ├── 2_biased_a_hug.png           # 0.6 / 0.4 (Eureka 강조)
    ├── 2_biased_b_hug.png           # 0.4 / 0.6 (Midoriya 강조)
    ├── 3_with_reference_hug.png     # Reference-only 추가
    └── 4_single_eureka.png          # 비교용 (단일 캐릭터)
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
OUTPUT_DIR = Path("outputs/lora_combo_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Character LoRAs
CHAR_A_LORA = "eureka_v9"  # 여자
CHAR_B_LORA = "mha_midoriya-10"  # 남자

NEGATIVE = "nsfw, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"


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


def test1_equal_weight():
    """Test 1: 균등 weight (0.5 / 0.5)."""
    print("\n" + "=" * 60)
    print("🧪 Test 1: 균등 Weight (0.5 / 0.5)")
    print("=" * 60)
    print("설정: eureka(0.5) + midoriya(0.5)")
    print("기대: 두 캐릭터 특징이 균등하게 나타남")
    print("-" * 60)

    # Test 1-1: Hug
    print("\n📸 Hug scene")
    prompt = f"""<lora:{CHAR_A_LORA}:0.5>, <lora:{CHAR_B_LORA}:0.5>,
1boy, 1girl, hug, hugging, embrace, from side,
school uniform, happy, smile,
park, outdoors, trees,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "1_equal_hug.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")

    # Test 1-2: Holding hands
    print("\n📸 Holding hands")
    prompt = f"""<lora:{CHAR_A_LORA}:0.5>, <lora:{CHAR_B_LORA}:0.5>,
1boy, 1girl, holding hands, walking together,
school uniform, smile,
street, outdoors, sunny,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "1_equal_hands.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")


def test2_biased_weight():
    """Test 2: 편향 weight."""
    print("\n" + "=" * 60)
    print("🧪 Test 2: 편향 Weight")
    print("=" * 60)
    print("목적: 한 캐릭터 특징을 더 강조")
    print("-" * 60)

    # Test 2-1: Eureka 강조 (0.6 / 0.4)
    print("\n📸 Eureka 강조 (0.6 / 0.4)")
    prompt = f"""<lora:{CHAR_A_LORA}:0.6>, <lora:{CHAR_B_LORA}:0.4>,
1boy, 1girl, hug, embrace,
school uniform,
park, outdoors,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "2_biased_a_hug.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")

    # Test 2-2: Midoriya 강조 (0.4 / 0.6)
    print("\n📸 Midoriya 강조 (0.4 / 0.6)")
    prompt = f"""<lora:{CHAR_A_LORA}:0.4>, <lora:{CHAR_B_LORA}:0.6>,
1boy, 1girl, hug, embrace,
school uniform,
park, outdoors,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "2_biased_b_hug.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")


def test3_with_reference():
    """Test 3: Reference-only 추가 (일관성 강화)."""
    print("\n" + "=" * 60)
    print("🧪 Test 3: Reference-only 추가")
    print("=" * 60)
    print("목적: Reference-only로 각 캐릭터 일관성 강화")
    print("제약: 현재는 1개 Reference만 가능 (Eureka)")
    print("-" * 60)

    # 먼저 Eureka 기준 이미지 생성
    print("\n📸 Step 1: Eureka 기준 이미지 생성")
    prompt = f"""<lora:{CHAR_A_LORA}:0.6>,
1girl, eureka, full body, standing,
school uniform, white shirt, blue skirt, red ribbon,
simple background, white background,
masterpiece, best quality"""

    base_img = generate_image(prompt, seed=12345)
    if not base_img:
        print("  ❌ 기준 이미지 생성 실패")
        return

    output_path = OUTPUT_DIR / "3_base_eureka.png"
    base_img.save(output_path)
    print(f"  💾 Saved: {output_path}")

    # Reference-only로 포옹 장면 생성
    print("\n📸 Step 2: Reference-only + LoRA 조합")
    base_b64 = base64.b64encode(
        BytesIO(lambda: (buf := BytesIO(), base_img.save(buf, "PNG"), buf.getvalue())[-1])()
    ).decode()

    prompt = f"""<lora:{CHAR_A_LORA}:0.5>, <lora:{CHAR_B_LORA}:0.5>,
1boy, 1girl, hug, embrace,
school uniform,
park, outdoors,
masterpiece, best quality"""

    controlnet_args = [
        build_reference_only_args(
            reference_image=base_b64,
            weight=0.75,
            guidance_end=1.0,
        )
    ]

    img = generate_image(prompt, controlnet_args=controlnet_args, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "3_with_reference_hug.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")


def test4_single_character_baseline():
    """Test 4: 단일 캐릭터 비교용."""
    print("\n" + "=" * 60)
    print("🧪 Test 4: 단일 캐릭터 기준선")
    print("=" * 60)
    print("목적: 다중 LoRA와 품질 비교")
    print("-" * 60)

    # Eureka 단독
    print("\n📸 Eureka 단독 (LoRA 0.8)")
    prompt = f"""<lora:{CHAR_A_LORA}:0.8>,
1girl, eureka, standing,
school uniform, white shirt, blue skirt, red ribbon,
library, indoors,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "4_single_eureka.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")

    # Midoriya 단독
    print("\n📸 Midoriya 단독 (LoRA 0.8)")
    prompt = f"""<lora:{CHAR_B_LORA}:0.8>,
1boy, midoriya, standing,
hero costume, green outfit,
classroom, indoors,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "4_single_midoriya.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")


def main():
    """실험 실행."""
    print("\n" + "=" * 60)
    print("🔬 LoRA 조합 실험 시작")
    print("=" * 60)
    print(f"Character A: {CHAR_A_LORA} (Eureka)")
    print(f"Character B: {CHAR_B_LORA} (Midoriya)")
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

    # Run tests
    test1_equal_weight()
    test2_biased_weight()
    test3_with_reference()
    test4_single_character_baseline()

    print("\n" + "=" * 60)
    print("✅ 실험 완료!")
    print("=" * 60)
    print(f"결과 확인: {OUTPUT_DIR}")
    print("\n분석 포인트:")
    print("  1. 균등 vs 편향 weight: 각 캐릭터 특징 유지 정도")
    print("  2. Reference-only 효과: Eureka 일관성 개선 여부")
    print("  3. 단일 vs 조합: 품질 저하 정도")
    print("\n다음 단계:")
    print("  - 최적 weight 비율 결정")
    print("  - 캐릭터별 Reference-only 적용 (현재는 1개만)")
    print("  - 프로덕션 통합")
    print("=" * 60)


if __name__ == "__main__":
    main()
