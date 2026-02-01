"""PoC: Regional Prompter - 영역 분할 2캐릭터 동시 생성.

Regional Prompter 확장을 이용해 좌/우 영역에 각각 다른 캐릭터를 배치.
Pair 1: Flat Color Girl + Midoriya (다른 LoRA)
Pair 2: Flat Color Girl + Flat Color Boy (동일 LoRA)

실행: cd backend && python -m tests.experimental._poc_regional_prompter [--seeds 42,100,200]
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
OUTPUT_DIR = Path("outputs/poc_regional_prompter")

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


def regional_prompter_args(
    ratios: str = "1,1",
    calc_mode: str = "Attention",
) -> dict:
    """Regional Prompter alwayson_scripts args 빌드."""
    return {
        "Regional Prompter": {
            "args": [
                True,           # 0: Active
                False,          # 1: Debug
                "Matrix",       # 2: Mode
                "Columns",      # 3: Matrix sub-mode (Vertical split)
                "Mask",         # 4: Mask mode
                "Prompt",       # 5: Prompt mode
                ratios,         # 6: Divide ratios
                "0.2",          # 7: Base ratios
                False,          # 8: Use Base
                True,           # 9: Use Common (ADDCOMM)
                True,           # 10: Use Neg-Common
                calc_mode,      # 11: Calculation mode
                False,          # 12: Not Change AND
                "0",            # 13: LoRA Textencoder
                "0",            # 14: LoRA U-Net
                "0",            # 15: Threshold
                "",             # 16: Mask
                "0",            # 17: LoRA Stop Step
                "0",            # 18: LoRA Hires Stop Step
                False,          # 19: Flip
            ]
        }
    }


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


def load_references() -> dict[str, str]:
    from database import SessionLocal
    from models import Character
    from services.controlnet import load_reference_image

    db = SessionLocal()
    refs = {}
    try:
        for cid, key in [(8, "girl"), (3, "midoriya"), (12, "boy")]:
            char = db.query(Character).filter(Character.id == cid).first()
            if char:
                ref = load_reference_image(char.name, db=db)
                if ref:
                    refs[key] = ref
                    print(f"  {char.name}: OK")
        return refs
    finally:
        db.close()


def call_sd(
    prompt: str, negative: str, label: str,
    alwayson: dict | None = None,
    cn_args: list[dict] | None = None,
) -> Image.Image | None:
    payload = {
        **SD_BASE_PARAMS,
        "prompt": prompt,
        "negative_prompt": negative,
    }

    scripts = {}
    if alwayson:
        scripts.update(alwayson)
    if cn_args:
        scripts["controlnet"] = {"args": cn_args}
    if scripts:
        payload["alwayson_scripts"] = scripts

    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"  Prompt: {prompt[:150]}...")
    rp = "Regional Prompter" in scripts if scripts else False
    ip_count = len(cn_args) if cn_args else 0
    print(f"  Regional Prompter: {'ON' if rp else 'OFF'} | IP-Adapter: {ip_count}x")

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

    rp = regional_prompter_args("1,1")

    # ============================================================
    # PAIR 1: Flat Color Girl (좌) + Midoriya (우) - 다른 LoRA
    # ============================================================

    # 공통 프롬프트(ADDCOMM) + 좌측(ADDCOL) + 우측
    p1_regional = (
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

    # 비교: Regional 없이 동일 프롬프트 (기존 방식)
    p1_no_regional = (
        "masterpiece, best_quality, 1boy, 1girl, "
        "<lora:flat_color:0.5>, flat color, "
        "<lora:mha_midoriya-10:0.5>, Midoriya_Izuku, "
        "(green_hair:1.2) boy on left, "
        "(blue_hair:1.2) girl on right, "
        "classroom, indoors, school_desk, chalkboard, "
        "sitting, studying, upper_body, anime_style"
    )

    ip_girl_midoriya = [
        build_ip(refs["girl"], 0.35),
        build_ip(refs["midoriya"], 0.35),
    ]

    tests = [
        # --- Pair 1: Girl + Midoriya ---
        ("p1_01_no_regional_no_ip",
         "P1: 기존방식 (no Regional, no IP)",
         p1_no_regional, None, None),

        ("p1_02_no_regional_ip",
         "P1: 기존방식 + dual IP 0.35",
         p1_no_regional, None, ip_girl_midoriya),

        ("p1_03_regional_no_ip",
         "P1: Regional Prompter (no IP)",
         p1_regional, rp, None),

        ("p1_04_regional_ip",
         "P1: Regional + dual IP 0.35",
         p1_regional, rp, ip_girl_midoriya),

        ("p1_05_regional_ip_020",
         "P1: Regional + dual IP 0.2",
         p1_regional, rp, [
             build_ip(refs["girl"], 0.2),
             build_ip(refs["midoriya"], 0.2),
         ]),
    ]

    # ============================================================
    # PAIR 2: Flat Color Girl (좌) + Flat Color Boy (우) - 동일 LoRA
    # ============================================================

    p2_regional = (
        "masterpiece, best_quality, 2others, 1boy, 1girl, "
        "classroom, indoors, school_desk, chalkboard, "
        "sitting, studying, upper_body, anime_style "
        "ADDCOMM "
        "1girl, (blue_hair:1.3), long_hair, blue_eyes, white_shirt, pleated_skirt, "
        "<lora:flat_color:0.6>, flat color "
        "ADDCOL "
        "1boy, (dark_hair:1.3), short_hair, blue_eyes, school_uniform, "
        "<lora:flat_color:0.6>, flat color"
    )

    ip_girl_boy = [
        build_ip(refs["girl"], 0.35),
        build_ip(refs["boy"], 0.35),
    ]

    tests += [
        ("p2_01_regional_no_ip",
         "P2: Regional (same LoRA, no IP)",
         p2_regional, rp, None),

        ("p2_02_regional_ip",
         "P2: Regional + dual IP 0.35",
         p2_regional, rp, ip_girl_boy),

        ("p2_03_regional_ip_020",
         "P2: Regional + dual IP 0.2",
         p2_regional, rp, [
             build_ip(refs["girl"], 0.2),
             build_ip(refs["boy"], 0.2),
         ]),
    ]

    for fn, label, prompt, ao, cn in tests:
        img = call_sd(prompt, NEGATIVE, f"[s{seed}] {label}", ao, cn)
        if img:
            img.save(seed_dir / f"{fn}.png")

    files = sorted(seed_dir.glob("*.png"))
    print(f"\n--- Seed {seed}: {len(files)} images ---")
    for f in files:
        print(f"  {f.name:45s} {f.stat().st_size/1024:6.0f} KB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=str, default="42,100,200")
    args = parser.parse_args()
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    print("=" * 60)
    print("PoC: Regional Prompter - 2 Character Scene")
    print("  Pair 1: Girl + Midoriya (다른 LoRA)")
    print("  Pair 2: Girl + Boy (동일 LoRA)")
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
    print(f"DONE - {len(seeds)*8} images")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
