"""PoC: 3-Character Scene - 3캐릭터(각각 다른 LoRA) 동시 출현.

캐릭터:
  - Flat Color Girl (id=8): flat_color LoRA, 파란머리 여자
  - Midoriya (id=3): mha_midoriya-10 LoRA, 초록머리 남자
  - Harukaze Doremi (id=9): harukaze-doremi-casual LoRA, 빨간머리 여자

실행: cd backend && python -m tests.experimental._poc_three_characters [--seeds 42,100,200]
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from config import SD_BASE_URL

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/poc_three_characters")

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

# --- Triple LoRA 프롬프트 ---

# A: 3 LoRA + 캐릭터 묘사
PROMPT_A = (
    "masterpiece, best_quality, "
    "3others, 1boy, 2girls, group, "
    "<lora:flat_color:0.4>, flat color, "
    "<lora:mha_midoriya-10:0.4>, Midoriya_Izuku, "
    "<lora:harukaze-doremi-casual:0.4>, hrkzdrm_cs, "
    "(green_hair:1.2) boy on left, "
    "(blue_hair:1.2) girl in center, "
    "(red_hair:1.2) girl on right, "
    "classroom, indoors, school_desk, chalkboard, "
    "sitting, studying, upper_body, anime_style"
)

# B: LoRA weight 높임 (0.5)
PROMPT_B = (
    "masterpiece, best_quality, "
    "3others, 1boy, 2girls, group, "
    "<lora:flat_color:0.5>, flat color, "
    "<lora:mha_midoriya-10:0.5>, Midoriya_Izuku, "
    "<lora:harukaze-doremi-casual:0.5>, hrkzdrm_cs, "
    "(green_hair:1.2) boy, (freckles:1.1), "
    "(blue_hair:1.2) girl, blue_eyes, white_shirt, "
    "(red_hair:1.2) girl, hair_bun, "
    "classroom, indoors, school_desk, chalkboard, "
    "sitting, studying, upper_body, anime_style"
)

# C: wide shot
PROMPT_C = (
    "masterpiece, best_quality, "
    "3others, 1boy, 2girls, group, "
    "<lora:flat_color:0.4>, flat color, "
    "<lora:mha_midoriya-10:0.4>, Midoriya_Izuku, "
    "<lora:harukaze-doremi-casual:0.4>, hrkzdrm_cs, "
    "green_hair boy, blue_hair girl, red_hair girl, "
    "classroom, indoors, school_desk, chalkboard, "
    "sitting, studying, wide_shot, anime_style"
)

# D: LoRA 2개만 (flat_color + midoriya), doremi는 IP-Adapter만
PROMPT_D = (
    "masterpiece, best_quality, "
    "3others, 1boy, 2girls, group, "
    "<lora:flat_color:0.5>, flat color, "
    "<lora:mha_midoriya-10:0.5>, Midoriya_Izuku, "
    "(green_hair:1.2) boy on left, "
    "(blue_hair:1.2) girl in center, "
    "(red_hair:1.2) girl on right, "
    "classroom, indoors, school_desk, chalkboard, "
    "sitting, studying, upper_body, anime_style"
)


def load_references() -> dict[str, str]:
    from database import SessionLocal
    from models import Character
    from services.controlnet import load_reference_image

    db = SessionLocal()
    refs = {}
    try:
        for cid, key in [(8, "girl"), (3, "midoriya"), (9, "doremi")]:
            char = db.query(Character).filter(Character.id == cid).first()
            if char:
                ref = load_reference_image(char.name, db=db)
                if ref:
                    refs[key] = ref
                    print(f"  {char.name}: OK")
        return refs
    finally:
        db.close()


def build_ip(ref: str, weight: float) -> dict:
    return {
        "enabled": True,
        "image": ref,
        "module": "ip-adapter_clip_sd15",
        "model": IP_ADAPTER_MODELS["clip_face"],
        "weight": weight,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": "Balanced",
        "pixel_perfect": False,
    }


def call_sd(
    prompt: str, negative: str, label: str,
    cn_args: list[dict] | None = None,
) -> Image.Image | None:
    payload = {
        **SD_BASE_PARAMS,
        "prompt": prompt,
        "negative_prompt": negative,
    }
    if cn_args:
        payload["alwayson_scripts"] = {"controlnet": {"args": cn_args}}

    print(f"\n{'='*60}")
    print(f"[{label}]")
    if cn_args:
        ws = [f"{a['weight']}" for a in cn_args]
        print(f"  IP units: {len(cn_args)}, weights: {', '.join(ws)}")
    else:
        print("  IP-Adapter: OFF")

    t0 = time.time()
    try:
        with httpx.Client(timeout=300.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()
        if "images" not in data or not data["images"]:
            print("  No images")
            return None
        img = Image.open(BytesIO(base64.b64decode(data["images"][0])))
        print(f"  Done: {img.size} in {time.time()-t0:.1f}s")
        return img
    except Exception as e:
        print(f"  FAILED: {e}")
        return None


def run_seed(seed: int, refs: dict[str, str]):
    seed_dir = OUTPUT_DIR / f"seed_{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    SD_BASE_PARAMS["seed"] = seed

    print(f"\n{'#'*60}")
    print(f"# SEED {seed}")
    print(f"{'#'*60}")

    ip3_035 = [build_ip(refs["girl"], 0.35), build_ip(refs["midoriya"], 0.35), build_ip(refs["doremi"], 0.35)]
    ip3_020 = [build_ip(refs["girl"], 0.2), build_ip(refs["midoriya"], 0.2), build_ip(refs["doremi"], 0.2)]

    tests = [
        ("01_3lora_no_ip",       "3 LoRA, no IP",                    PROMPT_A, None),
        ("02_3lora_3ip_035",     "3 LoRA + 3x clip_face 0.35",      PROMPT_A, ip3_035),
        ("03_3lora_3ip_020",     "3 LoRA + 3x clip_face 0.2",       PROMPT_A, ip3_020),
        ("04_detail_no_ip",      "Detailed, no IP",                  PROMPT_B, None),
        ("05_detail_3ip_035",    "Detailed + 3x clip_face 0.35",    PROMPT_B, ip3_035),
        ("06_wide_no_ip",        "Wide shot, no IP",                 PROMPT_C, None),
        ("07_wide_3ip_035",      "Wide + 3x clip_face 0.35",        PROMPT_C, ip3_035),
        ("08_2lora_3ip_035",     "2 LoRA + 3x clip_face 0.35",      PROMPT_D, ip3_035),
    ]

    for fn, label, prompt, cn in tests:
        img = call_sd(prompt, NEGATIVE, f"[s{seed}] {label}", cn)
        if img:
            img.save(seed_dir / f"{fn}.png")

    files = sorted(seed_dir.glob("*.png"))
    print(f"\n--- Seed {seed}: {len(files)} images ---")
    for f in files:
        print(f"  {f.name:40s} {f.stat().st_size/1024:6.0f} KB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=str, default="42,100,200")
    args = parser.parse_args()
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    print("=" * 60)
    print("PoC: 3-Character Scene (768x512)")
    print("  Flat Color Girl (blue hair) + Midoriya (green hair)")
    print("  + Doremi (red hair)")
    print(f"Seeds: {seeds} | Tests/seed: 8 | Total: {len(seeds)*8}")
    print("=" * 60)

    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(f"{SD_BASE_URL}/sdapi/v1/options")
            print(f"SD: {r.json().get('sd_model_checkpoint','?')}")
    except Exception as e:
        print(f"SD not available: {e}")
        sys.exit(1)

    print("\nLoading references...")
    refs = load_references()
    if len(refs) < 3:
        print(f"Need 3, got {len(refs)}")
        sys.exit(1)

    for seed in seeds:
        run_seed(seed, refs)

    print(f"\n{'='*60}")
    print(f"DONE - {len(seeds)*8} images across {len(seeds)} seeds")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
