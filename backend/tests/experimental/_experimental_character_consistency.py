"""캐릭터 일관성 실험: Reference-only vs IP-Adapter 비교

목표:
1. 단일 캐릭터 포즈/배경 변화 시 일관성 유지
2. Reference-only와 IP-Adapter 성능 비교
3. 두 가지 조합 테스트

실험 시나리오:
- Scenario 1: 기준 이미지 생성 (full body)
- Scenario 2: Reference-only로 포즈 변화 (4가지)
- Scenario 3: IP-Adapter로 포즈 변화 (4가지)
- Scenario 4: 조합 (Reference-only + IP-Adapter)

실행:
    python -m tests._experimental_character_consistency

결과:
    outputs/consistency_test/
    ├── 1_base_fullbody.png          # 기준 이미지
    ├── 2_ref_standing.png           # Reference-only
    ├── 2_ref_walking.png
    ├── 2_ref_sitting.png
    ├── 2_ref_running.png
    ├── 3_ip_standing.png            # IP-Adapter
    ├── 3_ip_walking.png
    ├── 3_ip_sitting.png
    ├── 3_ip_running.png
    ├── 4_combo_standing.png         # 조합
    ├── 4_combo_walking.png
    ├── 4_combo_sitting.png
    └── 4_combo_running.png
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
from services.controlnet import build_ip_adapter_args, build_reference_only_args

# Configuration
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/consistency_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Character settings
CHARACTER_LORA = "eureka_v9"  # 변경 가능
LORA_WEIGHT = 0.8
BASE_PROMPT = f"<lora:{CHARACTER_LORA}:{LORA_WEIGHT}>, 1girl, eureka, school uniform, masterpiece, best quality"
NEGATIVE = "nsfw, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"

# Test poses
POSES = {
    "standing": "standing, arms at sides, neutral pose",
    "walking": "walking, one leg forward, casual walk",
    "sitting": "sitting, on chair, hands on lap",
    "running": "running, dynamic pose, motion",
}

# Test backgrounds
BACKGROUNDS = {
    "library": "library, bookshelf, indoors, soft lighting",
    "classroom": "classroom, desk, blackboard, indoors",
    "outdoor": "park, trees, outdoors, sunny day",
    "street": "city street, buildings, outdoors",
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

    # ControlNet args 추가
    if controlnet_args:
        payload["alwayson_scripts"] = {"controlnet": {"args": controlnet_args}}

    try:
        print(f"  📤 Request: {prompt[:80]}...")
        if controlnet_args:
            for i, arg in enumerate(controlnet_args):
                module = arg.get("module", "unknown")
                weight = arg.get("weight", 0)
                print(f"     ControlNet[{i}]: {module} (weight={weight})")

        with httpx.Client(timeout=180.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()

            if "images" not in data or not data["images"]:
                print("  ❌ No images in response")
                return None

            img_b64 = data["images"][0]
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_bytes))
            print(f"  ✅ Generated: {img.size}")
            return img

    except httpx.HTTPError as e:
        print(f"  ❌ SD Error: {e}")
        return None


def scenario_1_base_image():
    """Scenario 1: 기준 이미지 생성 (전신, 심플)."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 1: 기준 이미지 생성")
    print("=" * 60)
    print("목적: Reference-only/IP-Adapter용 기준 이미지 생성")
    print("요구사항: 전신(full body), 단순 배경, 중립 포즈")
    print("-" * 60)

    prompt = f"{BASE_PROMPT}, full body, standing, simple background, white background"

    img = generate_image(prompt, seed=12345)  # seed 고정
    if img:
        output_path = OUTPUT_DIR / "1_base_fullbody.png"
        img.save(output_path)
        print(f"💾 Saved: {output_path}")
        return img
    else:
        print("❌ Failed to generate base image")
        return None


def scenario_2_reference_only(base_image: Image.Image):
    """Scenario 2: Reference-only로 포즈 변화."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 2: Reference-only 테스트")
    print("=" * 60)
    print("방법: Reference-only ControlNet")
    print("설정: weight=0.5, guidance_end=0.8")
    print("-" * 60)

    base_b64 = image_to_base64(base_image)

    for pose_name, pose_desc in POSES.items():
        print(f"\n📸 Pose: {pose_name}")
        prompt = f"{BASE_PROMPT}, {pose_desc}, library, indoors"

        # Reference-only args
        controlnet_args = [
            build_reference_only_args(
                reference_image=base_b64,
                weight=0.5,
                guidance_end=0.8,
            )
        ]

        img = generate_image(prompt, controlnet_args=controlnet_args, seed=-1)
        if img:
            output_path = OUTPUT_DIR / f"2_ref_{pose_name}.png"
            img.save(output_path)
            print(f"  💾 Saved: {output_path}")


def scenario_3_ip_adapter(base_image: Image.Image):
    """Scenario 3: IP-Adapter로 포즈 변화."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 3: IP-Adapter 테스트")
    print("=" * 60)
    print("방법: IP-Adapter (CLIP model)")
    print("설정: weight=0.75, model=clip_face")
    print("-" * 60)

    base_b64 = image_to_base64(base_image)

    for pose_name, pose_desc in POSES.items():
        print(f"\n📸 Pose: {pose_name}")
        prompt = f"{BASE_PROMPT}, {pose_desc}, library, indoors"

        # IP-Adapter args
        controlnet_args = [
            build_ip_adapter_args(
                reference_image=base_b64,
                weight=0.75,
                model="clip_face",
            )
        ]

        img = generate_image(prompt, controlnet_args=controlnet_args, seed=-1)
        if img:
            output_path = OUTPUT_DIR / f"3_ip_{pose_name}.png"
            img.save(output_path)
            print(f"  💾 Saved: {output_path}")


def scenario_4_combined(base_image: Image.Image):
    """Scenario 4: Reference-only + IP-Adapter 조합."""
    print("\n" + "=" * 60)
    print("🧪 Scenario 4: 조합 테스트 (Reference-only + IP-Adapter)")
    print("=" * 60)
    print("방법: Reference-only (스타일) + IP-Adapter (얼굴)")
    print("설정: Reference weight=0.5, IP-Adapter weight=0.7")
    print("-" * 60)

    base_b64 = image_to_base64(base_image)

    for pose_name, pose_desc in POSES.items():
        print(f"\n📸 Pose: {pose_name}")
        prompt = f"{BASE_PROMPT}, {pose_desc}, library, indoors"

        # Combined args
        controlnet_args = [
            build_reference_only_args(
                reference_image=base_b64,
                weight=0.5,
                guidance_end=0.8,
            ),
            build_ip_adapter_args(
                reference_image=base_b64,
                weight=0.7,
                model="clip_face",
            ),
        ]

        img = generate_image(prompt, controlnet_args=controlnet_args, seed=-1)
        if img:
            output_path = OUTPUT_DIR / f"4_combo_{pose_name}.png"
            img.save(output_path)
            print(f"  💾 Saved: {output_path}")


def main():
    """실험 실행."""
    print("\n" + "=" * 60)
    print("🔬 캐릭터 일관성 실험 시작")
    print("=" * 60)
    print(f"Character: {CHARACTER_LORA}")
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
    base_image = scenario_1_base_image()
    if not base_image:
        print("\n❌ 기준 이미지 생성 실패. 실험 중단.")
        return

    scenario_2_reference_only(base_image)
    scenario_3_ip_adapter(base_image)
    scenario_4_combined(base_image)

    print("\n" + "=" * 60)
    print("✅ 실험 완료!")
    print("=" * 60)
    print(f"결과 확인: {OUTPUT_DIR}")
    print("\n비교 분석:")
    print("  1. 기준 이미지 vs 각 방법별 결과 비교")
    print("  2. 얼굴/헤어스타일/의상 일관성 확인")
    print("  3. 포즈 자유도 vs 일관성 트레이드오프 평가")
    print("=" * 60)


if __name__ == "__main__":
    main()
