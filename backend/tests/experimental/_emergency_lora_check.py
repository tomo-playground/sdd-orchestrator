"""eureka_v9 LoRA 긴급 검증

문제: "1girl, solo" 프롬프트인데 2명 생성됨
목표: LoRA 없이 vs LoRA 있이 vs 다른 seed 테스트
"""
import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SD_BASE_URL

OUTPUT_DIR = Path("outputs/lora_emergency_check")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("🚨 eureka_v9 LoRA 긴급 검증")
print("=" * 60)

negative = """nsfw, lowres, bad anatomy, bad hands, text, error,
missing fingers, extra digit, fewer digits, cropped,
worst quality, low quality, normal quality,
jpeg artifacts, signature, watermark, username, blurry,
2girls, multiple girls, 2boys, multiple boys"""

# Test 1: LoRA 없이 (baseline)
print("\n" + "=" * 60)
print("🧪 Test 1: LoRA 없이 (Baseline)")
print("=" * 60)

prompt_no_lora = """1girl, solo, full body, standing,
school uniform, white shirt, blue skirt, red ribbon,
simple background, white background,
masterpiece, best quality"""

payload = {
    "prompt": prompt_no_lora,
    "negative_prompt": negative,
    "width": 512,
    "height": 768,
    "steps": 27,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 12345,
    "clip_skip": 2,
}

print("📤 Generating without LoRA (seed 12345)...")
with httpx.Client(timeout=180.0) as client:
    res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
    res.raise_for_status()
    data = res.json()
    img_b64 = data["images"][0]
    img = Image.open(BytesIO(base64.b64decode(img_b64)))
    output_path = OUTPUT_DIR / "1_no_lora_seed12345.png"
    img.save(output_path)
    print(f"✅ Saved: {output_path}")

# Test 2: eureka_v9 LoRA + 다른 seed
print("\n" + "=" * 60)
print("🧪 Test 2: eureka_v9 LoRA + Random Seed")
print("=" * 60)

prompt_with_lora = """<lora:eureka_v9:0.8>,
1girl, solo, eureka, full body, standing,
school uniform, white shirt, blue skirt, red ribbon,
simple background, white background,
masterpiece, best quality"""

payload["prompt"] = prompt_with_lora
payload["seed"] = -1  # Random seed

print("📤 Generating with LoRA (random seed)...")
with httpx.Client(timeout=180.0) as client:
    res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
    res.raise_for_status()
    data = res.json()
    img_b64 = data["images"][0]
    img = Image.open(BytesIO(base64.b64decode(img_b64)))
    output_path = OUTPUT_DIR / "2_with_lora_random.png"
    img.save(output_path)
    print(f"✅ Saved: {output_path}")

# Test 3: eureka_v9 LoRA + weight 0.5 (낮춤)
print("\n" + "=" * 60)
print("🧪 Test 3: eureka_v9 LoRA + Lower Weight (0.5)")
print("=" * 60)

prompt_low_weight = """<lora:eureka_v9:0.5>,
1girl, solo, eureka, full body, standing,
school uniform, white shirt, blue skirt, red ribbon,
simple background, white background,
masterpiece, best quality"""

payload["prompt"] = prompt_low_weight
payload["seed"] = -1

print("📤 Generating with LoRA weight 0.5...")
with httpx.Client(timeout=180.0) as client:
    res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
    res.raise_for_status()
    data = res.json()
    img_b64 = data["images"][0]
    img = Image.open(BytesIO(base64.b64decode(img_b64)))
    output_path = OUTPUT_DIR / "3_with_lora_weight05.png"
    img.save(output_path)
    print(f"✅ Saved: {output_path}")

# Test 4: 강력한 negative + LoRA
print("\n" + "=" * 60)
print("🧪 Test 4: Strong Negative + LoRA")
print("=" * 60)

strong_negative = """nsfw, lowres, bad anatomy, bad hands,
2girls, multiple girls, 2boys, multiple boys,
twins, sisters, duplicate, copy,
text, error, cropped, worst quality, low quality"""

payload["prompt"] = """<lora:eureka_v9:0.8>,
1girl, solo, eureka, full body, standing,
school uniform, white shirt, blue skirt, red ribbon,
simple background, white background,
masterpiece, best quality"""
payload["negative_prompt"] = strong_negative
payload["seed"] = -1

print("📤 Generating with strong negative...")
with httpx.Client(timeout=180.0) as client:
    res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
    res.raise_for_status()
    data = res.json()
    img_b64 = data["images"][0]
    img = Image.open(BytesIO(base64.b64decode(img_b64)))
    output_path = OUTPUT_DIR / "4_strong_negative.png"
    img.save(output_path)
    print(f"✅ Saved: {output_path}")

print("\n" + "=" * 60)
print("✅ 검증 완료!")
print("=" * 60)
print(f"결과: {OUTPUT_DIR}")
print("\n확인 포인트:")
print("  1. Test 1 (LoRA 없음): 1명만 나오는가?")
print("  2. Test 2-4 (LoRA 있음): 2명이 계속 나오는가?")
print("  3. → LoRA 파일이 문제일 가능성 높음")
print("=" * 60)
