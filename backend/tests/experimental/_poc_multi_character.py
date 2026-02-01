"""PoC: Multi-Character Scene - 2캐릭터 동시 출현 실험.

조합:
  Pair 1: Flat Color Girl(id=8) + Flat Color Boy(id=12) - 동일 LoRA
  Pair 2: Flat Color Girl(id=8) + Midoriya(id=3) - 다른 LoRA

실행: cd backend && python -m tests.experimental._poc_multi_character [--seed 42]
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
OUTPUT_DIR = Path("outputs/poc_multi_character")

IP_ADAPTER_MODELS = {
    "clip": "ip-adapter-plus_sd15 [836b5c2e]",
    "clip_face": "ip-adapter-plus-face_sd15 [7f7a633a]",
}

NEGATIVE = (
    "easynegative, lowres, bad_anatomy, bad_hands, text, error, "
    "missing_fingers, extra_digit, fewer_digits, cropped, "
    "worst_quality, low_quality, jpeg_artifacts, signature, "
    "watermark, username, blurry, verybadimagenegative_v1.3"
)

SD_BASE_PARAMS = {
    "width": 512,
    "height": 768,
    "steps": 27,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "seed": 42,
    "override_settings": {"CLIP_stop_at_last_layers": 2},
    "override_settings_restore_afterwards": True,
}

# ====== Pair 1: Flat Color Girl + Flat Color Boy (같은 LoRA) ======

# 같은 flat_color LoRA 공유, 성별로 구분
PAIR1_PROMPT_NO_BREAK = (
    "masterpiece, best_quality, "
    "1boy, 1girl, 2others, "
    "<lora:flat_color:0.6>, flat color, "
    "classroom, indoors, school_desk, "
    "(facing_each_other:1.2), sitting, "
    "upper_body, anime_style"
)

PAIR1_PROMPT_DETAILED = (
    "masterpiece, best_quality, "
    "1boy AND 1girl, "
    "<lora:flat_color:0.6>, flat color, "
    "boy on left, short_hair, blue_eyes, white_shirt, "
    "girl on right, long_hair, blue_eyes, pleated_skirt, white_shirt, "
    "classroom, indoors, school_desk, "
    "(facing_each_other:1.2), sitting, "
    "upper_body, anime_style"
)

# ====== Pair 2: Flat Color Girl + Midoriya (다른 LoRA) ======

PAIR2_PROMPT_DUAL_LORA = (
    "masterpiece, best_quality, "
    "1boy, 1girl, "
    "<lora:flat_color:0.5>, flat color, "
    "<lora:mha_midoriya-10:0.5>, Midoriya_Izuku, "
    "classroom, indoors, school_desk, "
    "(facing_each_other:1.2), sitting, "
    "upper_body, anime_style"
)

PAIR2_PROMPT_MIDORIYA_ONLY = (
    "masterpiece, best_quality, "
    "1boy, 1girl, "
    "<lora:mha_midoriya-10:0.6>, Midoriya_Izuku, "
    "green_hair, freckles, school_uniform, "
    "1girl, blue_hair, white_shirt, pleated_skirt, "
    "classroom, indoors, school_desk, "
    "(facing_each_other:1.2), sitting, "
    "upper_body, anime_style"
)


def load_references() -> dict[str, str]:
    """DB에서 캐릭터 레퍼런스 이미지 로드."""
    from database import SessionLocal
    from models import Character
    from services.controlnet import load_reference_image

    db = SessionLocal()
    refs = {}
    try:
        for cid, key in [(8, "girl"), (12, "boy"), (3, "midoriya")]:
            char = db.query(Character).filter(Character.id == cid).first()
            if char:
                ref = load_reference_image(char.name, db=db)
                if ref:
                    refs[key] = ref
                    print(f"  Loaded: {char.name} ({len(ref)} chars)")
        return refs
    finally:
        db.close()


def build_ip_args(ref_image: str, model_key: str, weight: float) -> dict:
    """IP-Adapter ControlNet unit 빌드."""
    return {
        "enabled": True,
        "image": ref_image,
        "module": "ip-adapter_clip_sd15",
        "model": IP_ADAPTER_MODELS[model_key],
        "weight": weight,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": "Balanced",
        "pixel_perfect": False,
    }


def call_sd(
    prompt: str,
    negative: str,
    label: str,
    controlnet_args: list[dict] | None = None,
) -> Image.Image | None:
    """SD API 호출."""
    payload = {
        **SD_BASE_PARAMS,
        "prompt": prompt,
        "negative_prompt": negative,
    }
    if controlnet_args:
        payload["alwayson_scripts"] = {
            "controlnet": {"args": controlnet_args}
        }

    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"  Prompt: {prompt[:140]}...")
    if controlnet_args:
        for i, arg in enumerate(controlnet_args):
            print(f"  IP-Adapter #{i}: {arg['model'][:35]} w={arg['weight']}")
    else:
        print("  IP-Adapter: OFF")

    t0 = time.time()
    try:
        with httpx.Client(timeout=300.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()
        if "images" not in data or not data["images"]:
            print("  No images returned")
            return None
        img = Image.open(BytesIO(base64.b64decode(data["images"][0])))
        elapsed = time.time() - t0
        print(f"  Done: {img.size} in {elapsed:.1f}s")
        return img
    except Exception as e:
        print(f"  FAILED: {e}")
        return None


def check_sd() -> bool:
    """SD WebUI 연결 확인."""
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SD_BASE_URL}/sdapi/v1/options")
            res.raise_for_status()
            model = res.json().get("sd_model_checkpoint", "?")
            print(f"SD WebUI: {model}")
            return True
    except Exception as e:
        print(f"SD WebUI not available: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    seed = args.seed

    seed_dir = OUTPUT_DIR / f"seed_{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    SD_BASE_PARAMS["seed"] = seed

    print("=" * 60)
    print(f"PoC: Multi-Character Scene (seed={seed})")
    print("Pair 1: Flat Color Girl + Flat Color Boy (same LoRA)")
    print("Pair 2: Flat Color Girl + Midoriya (cross LoRA)")
    print(f"Output: {seed_dir}/")
    print("=" * 60)

    if not check_sd():
        sys.exit(1)

    print("\nLoading references...")
    refs = load_references()
    if len(refs) < 3:
        print(f"Need 3 references, got {len(refs)}")
        sys.exit(1)

    # ========== PAIR 1: Girl + Boy (same flat_color LoRA) ==========

    tests_pair1 = [
        # (filename, label, prompt, controlnet_args)
        (
            "p1_01_no_ip",
            "PAIR1-01: No IP-Adapter (LoRA only)",
            PAIR1_PROMPT_NO_BREAK,
            None,
        ),
        (
            "p1_02_girl_clip_face_035",
            "PAIR1-02: Girl clip_face 0.35 only",
            PAIR1_PROMPT_NO_BREAK,
            [build_ip_args(refs["girl"], "clip_face", 0.35)],
        ),
        (
            "p1_03_dual_clip_face_035",
            "PAIR1-03: Girl+Boy dual clip_face 0.35",
            PAIR1_PROMPT_NO_BREAK,
            [
                build_ip_args(refs["girl"], "clip_face", 0.35),
                build_ip_args(refs["boy"], "clip_face", 0.35),
            ],
        ),
        (
            "p1_04_dual_clip_face_020",
            "PAIR1-04: Girl+Boy dual clip_face 0.2",
            PAIR1_PROMPT_NO_BREAK,
            [
                build_ip_args(refs["girl"], "clip_face", 0.2),
                build_ip_args(refs["boy"], "clip_face", 0.2),
            ],
        ),
        (
            "p1_05_detailed_no_ip",
            "PAIR1-05: Detailed prompt, no IP",
            PAIR1_PROMPT_DETAILED,
            None,
        ),
        (
            "p1_06_detailed_dual_035",
            "PAIR1-06: Detailed + dual clip_face 0.35",
            PAIR1_PROMPT_DETAILED,
            [
                build_ip_args(refs["girl"], "clip_face", 0.35),
                build_ip_args(refs["boy"], "clip_face", 0.35),
            ],
        ),
    ]

    # ========== PAIR 2: Girl + Midoriya (cross LoRA) ==========

    tests_pair2 = [
        (
            "p2_01_dual_lora_no_ip",
            "PAIR2-01: Dual LoRA, no IP-Adapter",
            PAIR2_PROMPT_DUAL_LORA,
            None,
        ),
        (
            "p2_02_dual_lora_dual_ip_035",
            "PAIR2-02: Dual LoRA + dual clip_face 0.35",
            PAIR2_PROMPT_DUAL_LORA,
            [
                build_ip_args(refs["girl"], "clip_face", 0.35),
                build_ip_args(refs["midoriya"], "clip_face", 0.35),
            ],
        ),
        (
            "p2_03_midoriya_lora_dual_ip_035",
            "PAIR2-03: Midoriya LoRA only + dual clip_face 0.35",
            PAIR2_PROMPT_MIDORIYA_ONLY,
            [
                build_ip_args(refs["girl"], "clip_face", 0.35),
                build_ip_args(refs["midoriya"], "clip_face", 0.35),
            ],
        ),
        (
            "p2_04_dual_lora_dual_ip_020",
            "PAIR2-04: Dual LoRA + dual clip_face 0.2",
            PAIR2_PROMPT_DUAL_LORA,
            [
                build_ip_args(refs["girl"], "clip_face", 0.2),
                build_ip_args(refs["midoriya"], "clip_face", 0.2),
            ],
        ),
    ]

    all_tests = tests_pair1 + tests_pair2

    for filename, label, prompt, cn_args in all_tests:
        img = call_sd(prompt, NEGATIVE, label, cn_args)
        if img:
            img.save(seed_dir / f"{filename}.png")

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS")
    print("=" * 60)
    files = sorted(seed_dir.glob("*.png"))
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:45s} {size_kb:6.0f} KB")

    print(f"\n평가 기준:")
    print("  1. 두 캐릭터가 모두 등장하는가?")
    print("  2. 캐릭터 간 외모 구분이 가능한가?")
    print("  3. 배경(classroom)이 보이는가?")
    print("  4. IP-Adapter로 레퍼런스 유사도가 올라가는가?")
    print("  5. 다른 LoRA 조합이 충돌하지 않는가?")


if __name__ == "__main__":
    main()
