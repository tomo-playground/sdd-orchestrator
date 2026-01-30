"""eureka_v9 LoRA 단독 테스트"""
import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SD_BASE_URL

OUTPUT_DIR = Path("outputs/lora_test")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("🧪 eureka_v9 LoRA 단독 테스트")
print("=" * 60)
print("목적: LoRA가 정말 Eureka인지 확인")
print("설정: weight 0.8, seed 고정")
print("-" * 60)

prompt = """<lora:eureka_v9:0.8>,
1girl, eureka, full body, standing,
school uniform, white shirt, blue skirt, red ribbon,
simple background, white background,
masterpiece, best quality"""

negative = "nsfw, lowres, bad anatomy"

payload = {
    "prompt": prompt,
    "negative_prompt": negative,
    "width": 512,
    "height": 768,
    "steps": 27,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 12345,
    "clip_skip": 2,
}

print("\n📤 Generating with eureka_v9 LoRA (weight 0.8)...")

with httpx.Client(timeout=180.0) as client:
    res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
    res.raise_for_status()
    data = res.json()

    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(BytesIO(img_bytes))

    output_path = OUTPUT_DIR / "eureka_solo_weight08.png"
    img.save(output_path)
    print(f"✅ Saved: {output_path}")
    print(f"   Size: {img.size}")

print("\n" + "=" * 60)
print("✅ 완료!")
print("=" * 60)
print(f"확인: open {output_path}")
print("\n이 이미지가 Eureka가 맞는지 확인해주세요.")
print("만약 Eureka가 아니라면, eureka_v9 LoRA 파일이 잘못되었을 수 있습니다.")
print("=" * 60)
