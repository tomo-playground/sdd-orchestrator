"""Generic Anime Boy 참조 이미지 생성

목표: Generic Anime Boy 캐릭터 프리셋용 기준 이미지 생성
"""
import httpx
import base64
from io import BytesIO
from PIL import Image
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SD_BASE_URL

OUTPUT_DIR = Path("outputs/character_presets")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("🧑 Generic Anime Boy 기준 이미지 생성")
print("=" * 60)

# Generic Anime Boy: 학생복 입은 평범한 남학생
prompt = """1boy, male focus, solo, full body, standing,
school uniform, white shirt, black pants, blazer,
brown hair, short hair, green eyes,
simple background, white background,
looking at viewer, neutral expression,
masterpiece, best quality, high resolution"""

negative = """nsfw, lowres, bad anatomy, bad hands, text, error,
missing fingers, extra digit, fewer digits, cropped,
worst quality, low quality, normal quality,
jpeg artifacts, signature, watermark, username, blurry,
1girl, multiple boys"""

payload = {
    "prompt": prompt,
    "negative_prompt": negative,
    "width": 512,
    "height": 768,
    "steps": 27,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 54321,  # 고정 시드
    "clip_skip": 2,
}

print(f"\n📤 Generating Generic Anime Boy...")

with httpx.Client(timeout=180.0) as client:
    res = client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload)
    res.raise_for_status()
    data = res.json()

    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(BytesIO(img_bytes))

    output_path = OUTPUT_DIR / "generic_anime_boy.png"
    img.save(output_path)
    print(f"✅ Saved: {output_path}")
    print(f"   Size: {img.size}")

print("\n" + "=" * 60)
print("✅ 완료!")
print("=" * 60)
print(f"확인: open {output_path}")
