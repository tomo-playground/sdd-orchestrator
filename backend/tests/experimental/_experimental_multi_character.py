"""멀티 캐릭터 실험: 2인 장면 생성 테스트

목표:
1. 상호작용 장면 (포옹, 손잡기) - 단일 생성
2. 대화 장면 (좌우 배치) - 분리 생성 + 합성

실험 시나리오:
- Scenario 1: 상호작용 (단일 생성 + Reference-only)
- Scenario 2: 대화 (분리 생성 + 합성)
- Scenario 3: LoRA 조합 테스트

실행:
    python -m tests._experimental_multi_character

결과:
    outputs/multi_char_test/
    ├── 1_interaction_hug.png        # 포옹 (단일 생성)
    ├── 1_interaction_hands.png      # 손잡기
    ├── 2_dialogue_left.png          # 대화 (왼쪽 캐릭터)
    ├── 2_dialogue_right.png         # 오른쪽 캐릭터
    ├── 2_dialogue_composite.png     # 합성 결과
    └── 3_lora_combo.png             # 다중 LoRA 조합
"""

from __future__ import annotations

import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SD_BASE_URL
from services.controlnet import build_reference_only_args

# Configuration
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/multi_char_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Character settings
CHAR_A_LORA = "eureka_v9"  # 변경 가능
CHAR_B_LORA = "eureka_v9"  # 같은 캐릭터 또는 다른 LoRA
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
        print(f"  📤 Request: {prompt[:80]}...")
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
        print(f"  ❌ SD Error: {e}")
        return None


def scenario_1_interaction():
    """Scenario 1: 상호작용 장면 (단일 생성)."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 1: 상호작용 장면 (포옹, 손잡기)")
    print("=" * 60)
    print("방법: 단일 이미지 생성 (리포트 권장)")
    print("특징: 자연스러운 신체 접촉, 조명 일관성")
    print("-" * 60)

    # Test 1-1: Hug
    print("\n📸 Test 1-1: 포옹")
    lora_weight = 0.6  # 다중 캐릭터는 weight 낮춤
    prompt = f"""<lora:{CHAR_A_LORA}:{lora_weight}>,
2girls, hug, hugging, embrace, from side,
school uniform, smile,
park, outdoors, trees,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "1_interaction_hug.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")

    # Test 1-2: Holding hands
    print("\n📸 Test 1-2: 손잡기")
    prompt = f"""<lora:{CHAR_A_LORA}:{lora_weight}>,
2girls, holding hands, walking together,
school uniform, smile,
street, outdoors, sunny,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "1_interaction_hands.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")


def scenario_2_dialogue():
    """Scenario 2: 대화 장면 (분리 생성 + 합성)."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 2: 대화 장면 (좌우 배치)")
    print("=" * 60)
    print("방법: 분리 생성 후 레이어 합성")
    print("특징: 캐릭터별 LoRA 완전 분리 가능")
    print("-" * 60)

    # Generate character A (left)
    print("\n📸 캐릭터 A (왼쪽) 생성")
    prompt_a = f"""<lora:{CHAR_A_LORA}:0.8>,
1girl, solo, cowboy shot,
school uniform, smile, happy,
looking at viewer,
simple background, white background,
masterpiece, best quality"""

    img_a = generate_image(prompt_a, seed=12345)
    if img_a:
        output_path = OUTPUT_DIR / "2_dialogue_left.png"
        img_a.save(output_path)
        print(f"  💾 Saved: {output_path}")

    # Generate character B (right)
    print("\n📸 캐릭터 B (오른쪽) 생성")
    prompt_b = f"""<lora:{CHAR_B_LORA}:0.8>,
1girl, solo, cowboy shot,
school uniform, surprised, open mouth,
looking at viewer,
simple background, white background,
masterpiece, best quality"""

    img_b = generate_image(prompt_b, seed=67890)
    if img_b:
        output_path = OUTPUT_DIR / "2_dialogue_right.png"
        img_b.save(output_path)
        print(f"  💾 Saved: {output_path}")

    # Composite (simple side-by-side)
    if img_a and img_b:
        print("\n🎨 레이어 합성")
        # Create canvas
        canvas = Image.new("RGB", (512, 768), (255, 255, 255))

        # Resize and place characters (simple crop + paste)
        # Left character (crop right half)
        width_a = img_a.width // 2
        left_crop = img_a.crop((0, 0, width_a, img_a.height))
        canvas.paste(left_crop, (0, 0))

        # Right character (crop left half)
        width_b = img_b.width // 2
        right_crop = img_b.crop((width_b, 0, img_b.width, img_b.height))
        canvas.paste(right_crop, (256, 0))

        output_path = OUTPUT_DIR / "2_dialogue_composite.png"
        canvas.save(output_path)
        print(f"  💾 Saved: {output_path}")
        print("  ℹ️  단순 좌우 합성 (배경 제거 없음)")
        print("  ℹ️  rembg 설치 시 더 나은 결과 가능")


def scenario_3_lora_combination():
    """Scenario 3: 다중 LoRA 조합 테스트."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 3: 다중 LoRA 조합")
    print("=" * 60)
    print("방법: 2개 LoRA 동시 사용 (weight 분산)")
    print("특징: 각 캐릭터 특징 혼합됨 (완전 분리 어려움)")
    print("-" * 60)

    # 주의: 같은 LoRA 2번 사용 시 효과 없음
    # 실제로는 다른 LoRA를 사용해야 함
    print("\n📸 2개 LoRA 조합 (상호작용)")
    weight_per_lora = 0.5
    prompt = f"""<lora:{CHAR_A_LORA}:{weight_per_lora}>,
2girls, sitting together, close, smile,
school uniform,
classroom, indoors,
masterpiece, best quality"""

    img = generate_image(prompt, seed=-1)
    if img:
        output_path = OUTPUT_DIR / "3_lora_combo.png"
        img.save(output_path)
        print(f"  💾 Saved: {output_path}")
        print("  ℹ️  현재: 같은 LoRA 사용")
        print("  ℹ️  실제: 다른 LoRA (eureka + midoriya 등) 사용 권장")


def main():
    """실험 실행."""
    print("\n" + "=" * 60)
    print("🔬 멀티 캐릭터 실험 시작")
    print("=" * 60)
    print(f"Character A LoRA: {CHAR_A_LORA}")
    print(f"Character B LoRA: {CHAR_B_LORA}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"SD API: {SD_BASE_URL}")
    print("=" * 60)

    # Check SD WebUI
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SD_BASE_URL}/sdapi/v1/sd-models")
            res.raise_for_status()
            print("✅ SD WebUI 연결됨")
    except Exception as e:
        print(f"❌ SD WebUI 연결 실패: {e}")
        print("힌트: SD WebUI를 --api 옵션으로 실행하세요")
        return

    # Run scenarios
    scenario_1_interaction()
    scenario_2_dialogue()
    scenario_3_lora_combination()

    print("\n" + "=" * 60)
    print("✅ 실험 완료!")
    print("=" * 60)
    print(f"결과 확인: {OUTPUT_DIR}")
    print("\n분석 포인트:")
    print("  1. 상호작용 장면: 자연스러움, 신체 접촉 품질")
    print("  2. 대화 장면: 합성 경계, 배경 일관성")
    print("  3. LoRA 조합: 각 캐릭터 특징 보존 정도")
    print("\n다음 단계:")
    print("  - rembg 설치 → 배경 제거 + 정교한 합성")
    print("  - 다른 LoRA 테스트 → 캐릭터 구분 확인")
    print("  - Reference-only 추가 → 캐릭터 일관성 향상")
    print("=" * 60)


if __name__ == "__main__":
    main()
