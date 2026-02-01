"""Regional Prompter 2캐릭터(다른 LoRA) 안정성 테스트 - 10시드 반복.

Girl(flat_color) + Midoriya(mha_midoriya-10), Regional Prompter ON.
성공률 측정 목적.

실행: cd backend && python -m tests.experimental._poc_regional_10seeds
"""

from __future__ import annotations

import base64
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from config import SD_BASE_URL

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/poc_regional_10seeds")

IP_ADAPTER_MODELS = {
    "clip_face": "ip-adapter-plus-face_sd15 [7f7a633a]",
}

NEGATIVE = (
    "easynegative, lowres, bad_anatomy, bad_hands, text, error, "
    "missing_fingers, extra_digit, fewer_digits, cropped, "
    "worst_quality, low_quality, jpeg_artifacts, signature, "
    "watermark, username, blurry, verybadimagenegative_v1.3"
)

SD_BASE_PARAMS = {
    "width": 768,
    "height": 512,
    "steps": 27,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 42,
    "override_settings": {"CLIP_stop_at_last_layers": 2},
    "override_settings_restore_afterwards": True,
}

PROMPT_REGIONAL = (
    "masterpiece, best_quality, 2others, 1boy, 1girl, "
    "classroom, indoors, school_desk, chalkboard, "
    "sitting, studying, upper_body, anime_style "
    "ADDCOMM "
    "1girl, (blue_hair:1.3), blue_eyes, white_shirt, pleated_skirt, "
    "<lora:flat_color:0.6>, flat color "
    "ADDCOL "
    "1boy, (green_hair:1.3), freckles, school_uniform, "
    "<lora:mha_midoriya-10:0.6>, Midoriya_Izuku"
)

SEEDS = [42, 100, 200, 300, 400, 500, 777, 1234, 2025, 9999]


def regional_prompter_args() -> dict:
    return {
        "Regional Prompter": {
            "args": [
                True, False, "Matrix", "Columns", "Mask", "Prompt",
                "1,1", "0.2", False, True, True, "Attention",
                False, "0", "0", "0", "", "0", "0", False,
            ]
        }
    }


def load_references() -> dict[str, str]:
    from database import SessionLocal
    from models import Character
    from services.controlnet import load_reference_image

    db = SessionLocal()
    refs = {}
    try:
        for cid, key in [(8, "girl"), (3, "midoriya")]:
            char = db.query(Character).filter(Character.id == cid).first()
            if char:
                ref = load_reference_image(char.name, db=db)
                if ref:
                    refs[key] = ref
                    print(f"  {char.name}: OK")
        return refs
    finally:
        db.close()


def call_sd(seed: int, alwayson: dict) -> Image.Image | None:
    payload = {
        **SD_BASE_PARAMS,
        "seed": seed,
        "prompt": PROMPT_REGIONAL,
        "negative_prompt": NEGATIVE,
        "alwayson_scripts": alwayson,
    }

    t0 = time.time()
    try:
        with httpx.Client(timeout=300.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()
        if "images" not in data or not data["images"]:
            return None
        img = Image.open(BytesIO(base64.b64decode(data["images"][0])))
        print(f"  seed {seed}: {img.size} in {time.time()-t0:.1f}s")
        return img
    except Exception as e:
        print(f"  seed {seed}: FAILED - {e}")
        return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Regional Prompter 안정성 테스트 (10 seeds)")
    print("  Girl(flat_color) + Midoriya(mha_midoriya-10)")
    print(f"  Seeds: {SEEDS}")
    print("=" * 60)

    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(f"{SD_BASE_URL}/sdapi/v1/options")
            print(f"SD: {r.json().get('sd_model_checkpoint', '?')}")
    except Exception as e:
        print(f"SD not available: {e}")
        sys.exit(1)

    rp = regional_prompter_args()

    for seed in SEEDS:
        img = call_sd(seed, rp)
        if img:
            img.save(OUTPUT_DIR / f"seed_{seed}.png")

    files = sorted(OUTPUT_DIR.glob("seed_*.png"))
    print(f"\n{'='*60}")
    print(f"완료: {len(files)}/{len(SEEDS)} 이미지 생성")
    print(f"Output: {OUTPUT_DIR}/")
    for f in files:
        print(f"  {f.name:25s} {f.stat().st_size/1024:6.0f} KB")


if __name__ == "__main__":
    main()
