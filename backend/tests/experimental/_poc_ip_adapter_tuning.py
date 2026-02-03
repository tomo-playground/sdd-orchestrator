"""PoC: IP-Adapter Tuning - model/weight/BREAK 구조 변경 실험.

Flat Color Girl (id=8) 캐릭터로 부엌 장면 생성.
기존 single-pass 파이프라인 유지하면서 IP-Adapter 설정만 변경.

실행: cd backend && python -m tests.experimental._poc_ip_adapter_tuning
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
OUTPUT_DIR = Path("outputs/poc_ip_adapter_tuning")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- IP-Adapter Model Map ---
IP_ADAPTER_MODELS = {
    "clip": "ip-adapter-plus_sd15 [836b5c2e]",
    "clip_face": "ip-adapter-plus-face_sd15 [7f7a633a]",
}

# --- V3 Prompt: Kitchen Scene (BREAK after L6) ---
# L0-L6: quality, subject, identity, body, clothing, accessory + LoRA
# BREAK
# L7-L11: expression, action, camera, environment, atmosphere
PROMPT_CURRENT_BREAK = (
    "masterpiece, best_quality, "
    "1girl, solo, "
    "<lora:flat_color:0.6>, flat color, "
    "BREAK, "
    "(surprised:1.1), (looking_at_viewer:1.1), "
    "(standing:1.1), (holding_knife:1.1), "
    "upper_body, "
    "kitchen, indoors, bright, day, "
    "anime_style, anime"
)

# --- Alternative: Environment in Block 1 (before BREAK) ---
# L0: quality + environment
# L1-L6: subject, identity, body, clothing, accessory + LoRA
# BREAK
# L7-L8: expression, action
# Camera stays in Block 2
PROMPT_ENV_FIRST = (
    "masterpiece, best_quality, "
    "kitchen, indoors, bright, day, "
    "1girl, solo, "
    "<lora:flat_color:0.6>, flat color, "
    "BREAK, "
    "(surprised:1.1), (looking_at_viewer:1.1), "
    "(standing:1.1), (holding_knife:1.1), "
    "upper_body, "
    "anime_style, anime"
)

# --- Alternative: No BREAK at all ---
PROMPT_NO_BREAK = (
    "masterpiece, best_quality, "
    "1girl, solo, "
    "<lora:flat_color:0.6>, flat color, "
    "(surprised:1.1), (looking_at_viewer:1.1), "
    "(standing:1.1), (holding_knife:1.1), "
    "upper_body, "
    "kitchen, indoors, bright, day, "
    "anime_style, anime"
)

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
    "seed": 42,  # overridden by --seed arg
    "override_settings": {"CLIP_stop_at_last_layers": 2},
    "override_settings_restore_afterwards": True,
}


def load_reference_from_db() -> str:
    """DB에서 Flat Color Girl 레퍼런스 이미지 로드."""
    from database import SessionLocal
    from models import Character
    from services.controlnet import load_reference_image

    db = SessionLocal()
    try:
        char = db.query(Character).filter(Character.id == 8).first()
        if not char:
            print("Character id=8 not found")
            sys.exit(1)
        ref = load_reference_image(char.name, db=db)
        if not ref:
            print(f"No reference image for {char.name}")
            sys.exit(1)
        print(f"Loaded reference: {char.name} ({len(ref)} chars)")
        return ref
    finally:
        db.close()


def build_ip_adapter_args(
    ref_image: str, model_key: str, weight: float
) -> dict:
    """IP-Adapter ControlNet args 빌드."""
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
    ip_adapter: dict | None = None,
) -> Image.Image | None:
    """SD API 호출."""
    payload = {
        **SD_BASE_PARAMS,
        "prompt": prompt,
        "negative_prompt": negative,
    }
    if ip_adapter:
        payload["alwayson_scripts"] = {
            "controlnet": {"args": [ip_adapter]}
        }

    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"  Prompt: {prompt[:120]}...")
    if ip_adapter:
        print(f"  IP-Adapter: {ip_adapter['model'][:40]} w={ip_adapter['weight']}")
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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    seed = args.seed

    seed_dir = OUTPUT_DIR / f"seed_{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)

    SD_BASE_PARAMS["seed"] = seed

    print("=" * 60)
    print(f"PoC: IP-Adapter Tuning (seed={seed})")
    print("Character: Flat Color Girl (id=8)")
    print("Scene: Kitchen + surprised + holding_knife")
    print(f"Output: {seed_dir}/")
    print("=" * 60)

    if not check_sd():
        sys.exit(1)

    ref_image = load_reference_from_db()

    tests = [
        # (filename, label, prompt, ip_model, ip_weight)
        (
            "0_baseline_clip_0.7",
            "BASELINE: clip 0.7 + BREAK after L6 (현재)",
            PROMPT_CURRENT_BREAK,
            "clip", 0.7,
        ),
        (
            "1_no_ip_adapter",
            "TEST 1: IP-Adapter OFF (LoRA only)",
            PROMPT_CURRENT_BREAK,
            None, 0,
        ),
        (
            "2_clip_face_0.7",
            "TEST 2: clip_face 0.7 (얼굴만 전이)",
            PROMPT_CURRENT_BREAK,
            "clip_face", 0.7,
        ),
        (
            "3_clip_0.35",
            "TEST 3: clip 0.35 (weight 절반)",
            PROMPT_CURRENT_BREAK,
            "clip", 0.35,
        ),
        (
            "4_clip_face_0.35",
            "TEST 4: clip_face 0.35",
            PROMPT_CURRENT_BREAK,
            "clip_face", 0.35,
        ),
        (
            "5_env_first_clip_0.7",
            "TEST 5: 환경 Block 1 이동 + clip 0.7",
            PROMPT_ENV_FIRST,
            "clip", 0.7,
        ),
        (
            "6_env_first_clip_face_0.35",
            "TEST 6: 환경 Block 1 + clip_face 0.35",
            PROMPT_ENV_FIRST,
            "clip_face", 0.35,
        ),
        (
            "7_no_break_clip_0.7",
            "TEST 7: BREAK 제거 + clip 0.7",
            PROMPT_NO_BREAK,
            "clip", 0.7,
        ),
        (
            "8_no_break_clip_face_0.35",
            "TEST 8: BREAK 제거 + clip_face 0.35 (최적 조합)",
            PROMPT_NO_BREAK,
            "clip_face", 0.35,
        ),
    ]

    results = []
    for filename, label, prompt, ip_model, ip_weight in tests:
        ip_args = None
        if ip_model:
            ip_args = build_ip_adapter_args(ref_image, ip_model, ip_weight)

        img = call_sd(prompt, NEGATIVE, label, ip_args)
        if img:
            img.save(seed_dir / f"{filename}.png")
            results.append((filename, True))
        else:
            results.append((filename, False))

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS")
    print("=" * 60)
    files = sorted(seed_dir.glob("*.png"))
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:45s} {size_kb:6.0f} KB")

    print("\n비교 포인트:")
    print("  0 (baseline) vs 나머지: 배경(kitchen)이 보이는가?")
    print("  0 vs 1: IP-Adapter 없으면 어떤가?")
    print("  0 vs 2: clip → clip_face 모델 변경 효과")
    print("  0 vs 3: weight 0.7 → 0.35 효과")
    print("  0 vs 5: 환경 태그를 BREAK 앞으로 이동한 효과")
    print("  0 vs 7: BREAK 제거 효과")
    print("  8 = 최적 조합 (BREAK 제거 + clip_face 0.35)")


if __name__ == "__main__":
    main()
