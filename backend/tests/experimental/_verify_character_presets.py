"""캐릭터 프리셋 검증: Generic Anime Girl & Boy

목표: Reference-only 방식으로 프리셋이 잘 작동하는지 확인
"""
import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CHARACTER_PRESETS, SD_BASE_URL
from services.controlnet import build_reference_only_args

OUTPUT_DIR = Path("outputs/preset_verification")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("✅ Character Presets 검증")
print("=" * 60)

# Test cases: 각 프리셋당 2개 포즈
test_cases = [
    {
        "preset": "Generic Anime Girl",
        "tests": [
            {
                "name": "running",
                "prompt": "1girl, running, dynamic pose, outdoors, park, trees, sunny day",
            },
            {
                "name": "waving",
                "prompt": "1girl, waving hand, cheerful, classroom, indoors, window",
            },
        ],
    },
    {
        "preset": "Generic Anime Boy",
        "tests": [
            {
                "name": "walking",
                "prompt": "1boy, walking, casual pose, street, outdoors, buildings",
            },
            {
                "name": "sitting",
                "prompt": "1boy, sitting on bench, reading book, library, indoors",
            },
        ],
    },
]


def generate_with_preset(preset_name: str, additional_prompt: str, output_name: str):
    """프리셋을 사용하여 이미지 생성."""
    preset = CHARACTER_PRESETS[preset_name]

    # 참조 이미지 로드
    ref_path = Path(preset["reference_image"])
    if not ref_path.exists():
        print(f"  ❌ Reference image not found: {ref_path}")
        return None

    with open(ref_path, "rb") as f:
        ref_b64 = base64.b64encode(f.read()).decode()

    # Reference-only ControlNet args
    controlnet_args = [
        build_reference_only_args(
            reference_image=ref_b64,
            weight=preset["reference_weight"],
            guidance_end=1.0,
        )
    ]

    # 프롬프트 구성
    full_prompt = f"""{additional_prompt},
masterpiece, best quality, high resolution"""

    negative = """nsfw, lowres, bad anatomy, bad hands, text, error,
missing fingers, extra digit, fewer digits, cropped,
worst quality, low quality, normal quality,
jpeg artifacts, signature, watermark, username, blurry,
multiple girls, multiple boys"""

    payload = {
        "prompt": full_prompt,
        "negative_prompt": negative,
        "width": 512,
        "height": 768,
        "steps": 27,
        "cfg_scale": 7,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
        "clip_skip": 2,
        "alwayson_scripts": {"controlnet": {"args": controlnet_args}},
    }

    try:
        print(f"  📤 Generating: {additional_prompt[:50]}...")
        with httpx.Client(timeout=180.0) as client:
            res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
            res.raise_for_status()
            data = res.json()

            img_b64 = data["images"][0]
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_bytes))

            output_path = OUTPUT_DIR / output_name
            img.save(output_path)
            print(f"  ✅ Saved: {output_path}")
            return img
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


# SD WebUI 연결 확인
try:
    with httpx.Client(timeout=5.0) as client:
        res = client.get(f"{SD_BASE_URL}/sdapi/v1/sd-models")
        res.raise_for_status()
        print("✅ SD WebUI 연결됨\n")
except Exception as e:
    print(f"❌ SD WebUI 연결 실패: {e}")
    sys.exit(1)

# 각 프리셋 검증
total_generated = 0
for case in test_cases:
    preset_name = case["preset"]
    print("=" * 60)
    print(f"🧪 Testing: {preset_name}")
    print("=" * 60)

    preset = CHARACTER_PRESETS[preset_name]
    print(f"Reference Image: {preset['reference_image']}")
    print(f"Reference Weight: {preset['reference_weight']}")
    print("-" * 60)

    for test in case["tests"]:
        print(f"\n📸 Test: {test['name']}")
        output_name = f"{preset_name.lower().replace(' ', '_')}_{test['name']}.png"
        img = generate_with_preset(preset_name, test["prompt"], output_name)
        if img:
            total_generated += 1

print("\n" + "=" * 60)
print("✅ 검증 완료!")
print("=" * 60)
print(f"생성된 이미지: {total_generated}/4")
print(f"결과 확인: {OUTPUT_DIR}")
print("\n확인 포인트:")
print("  1. 얼굴/머리 일관성: 각 프리셋의 참조 이미지와 비교")
print("  2. 복장 일관성: 포즈가 달라도 복장이 유지되는지")
print("  3. 자연스러움: 포즈/배경과 캐릭터가 자연스럽게 어우러지는지")
print("=" * 60)
