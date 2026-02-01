"""PoC: Single Character 30 Scenarios - 다양한 포즈/액션/환경 일관성 테스트.

Flat Color Girl (id=8) + clip_face 0.35 + no BREAK.
30개 시나리오로 프롬프트 준수율 평가.

실행: cd backend && python -m tests.experimental._poc_single_char_30scenes
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
OUTPUT_DIR = Path("outputs/poc_single_char_30scenes")

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

# 캐릭터 공통 (BREAK 없음, clip_face 0.35 최적 설정)
CHAR_BASE = (
    "masterpiece, best_quality, 1girl, solo, "
    "<lora:flat_color:0.6>, flat color"
)

# 30 scenarios: (filename, label, pose/action/env tags)
SCENARIOS = [
    # --- 포즈 변형 (5) ---
    ("01_standing_classroom", "서서 교실",
     "standing, classroom, indoors, chalkboard, upper_body"),
    ("02_sitting_cafe", "앉아서 카페",
     "sitting, cafe, indoors, table, coffee_cup, upper_body"),
    ("03_crouching_garden", "웅크려 정원",
     "crouching, garden, outdoors, flowers, full_body"),
    ("04_lying_bedroom", "누워서 침실",
     "lying, on_bed, bedroom, indoors, pillow, from_above"),
    ("05_leaning_wall", "벽에 기대기",
     "leaning_against_wall, alley, outdoors, brick_wall, cowboy_shot"),

    # --- 표정 변형 (5) ---
    ("06_happy_park", "웃는 공원",
     "happy, smile, open_mouth, park, outdoors, trees, upper_body"),
    ("07_crying_rain", "우는 비",
     "crying, tears, rain, outdoors, wet, umbrella, upper_body"),
    ("08_angry_office", "화난 사무실",
     "angry, clenched_teeth, office, indoors, desk, upper_body"),
    ("09_surprised_kitchen", "놀란 부엌",
     "(surprised:1.1), open_mouth, kitchen, indoors, bright, upper_body"),
    ("10_sad_bench", "슬픈 벤치",
     "sad, looking_down, park_bench, outdoors, autumn, upper_body"),

    # --- 물건 들기 (5) ---
    ("11_holding_book", "책 들기",
     "holding_book, reading, library, indoors, bookshelf, upper_body"),
    ("12_holding_knife", "칼 들기",
     "(holding_knife:1.1), kitchen, indoors, cutting_board, upper_body"),
    ("13_holding_phone", "폰 들기",
     "holding_phone, looking_at_phone, bedroom, indoors, upper_body"),
    ("14_holding_umbrella", "우산 들기",
     "holding_umbrella, rain, street, outdoors, wet_ground, full_body"),
    ("15_holding_bag", "가방 들기",
     "holding_bag, shopping_bag, street, outdoors, storefront, cowboy_shot"),

    # --- 액션 (5) ---
    ("16_running_track", "달리기",
     "running, track, outdoors, stadium, wind, full_body"),
    ("17_cooking_kitchen", "요리",
     "cooking, apron, kitchen, indoors, stove, pot, upper_body"),
    ("18_studying_desk", "공부",
     "writing, notebook, pencil, desk, classroom, indoors, upper_body"),
    ("19_eating_ramen", "라면 먹기",
     "eating, chopsticks, ramen, noodles, restaurant, indoors, upper_body"),
    ("20_painting_studio", "그림 그리기",
     "painting, paintbrush, easel, art_studio, indoors, upper_body"),

    # --- 환경 변형 (5) ---
    ("21_beach_sunset", "해변 석양",
     "standing, beach, sunset, ocean, wind, hair_blowing, cowboy_shot"),
    ("22_snow_winter", "눈 겨울",
     "standing, snow, winter, scarf, coat, outdoors, breath, upper_body"),
    ("23_night_city", "밤 도시",
     "standing, night, city, neon_lights, street, outdoors, upper_body"),
    ("24_forest_morning", "숲 아침",
     "standing, forest, morning, sunlight, trees, outdoors, cowboy_shot"),
    ("25_rooftop_sky", "옥상 하늘",
     "standing, rooftop, sky, clouds, wind, school_uniform, upper_body"),

    # --- 카메라/구도 변형 (5) ---
    ("26_closeup_face", "클로즈업",
     "looking_at_viewer, smile, classroom, indoors, close-up"),
    ("27_from_behind", "뒷모습",
     "from_behind, looking_back, hallway, indoors, school, cowboy_shot"),
    ("28_from_below", "아래에서",
     "from_below, standing, sky, outdoors, looking_down_at_viewer, full_body"),
    ("29_profile_view", "옆모습",
     "profile, looking_away, window, indoors, sunlight, upper_body"),
    ("30_wide_shot", "와이드샷",
     "standing, school_gate, outdoors, cherry_blossoms, full_body, wide_shot"),
]


def load_reference() -> str:
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
            print(f"No reference for {char.name}")
            sys.exit(1)
        print(f"  {char.name}: OK")
        return ref
    finally:
        db.close()


def build_ip(ref: str) -> dict:
    return {
        "enabled": True,
        "image": ref,
        "module": "ip-adapter_clip_sd15",
        "model": "ip-adapter-plus-face_sd15 [7f7a633a]",
        "weight": 0.35,
        "resize_mode": "Crop and Resize",
        "processor_res": 512,
        "control_mode": "Balanced",
        "pixel_perfect": False,
    }


def call_sd(prompt: str, label: str, ip_args: dict) -> Image.Image | None:
    payload = {
        **SD_BASE_PARAMS,
        "prompt": prompt,
        "negative_prompt": NEGATIVE,
        "alwayson_scripts": {"controlnet": {"args": [ip_args]}},
    }
    t0 = time.time()
    try:
        with httpx.Client(timeout=300.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()
        if "images" not in data or not data["images"]:
            print(f"  [{label}] No images")
            return None
        img = Image.open(BytesIO(base64.b64decode(data["images"][0])))
        print(f"  [{label}] {img.size} in {time.time()-t0:.1f}s")
        return img
    except Exception as e:
        print(f"  [{label}] FAILED: {e}")
        return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Single Character 30 Scenarios")
    print("  Character: Flat Color Girl (id=8)")
    print("  IP-Adapter: clip_face 0.35 (no BREAK)")
    print(f"  Scenarios: {len(SCENARIOS)}")
    print("=" * 60)

    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(f"{SD_BASE_URL}/sdapi/v1/options")
            print(f"SD: {r.json().get('sd_model_checkpoint', '?')}")
    except Exception as e:
        print(f"SD not available: {e}")
        sys.exit(1)

    print("\nLoading reference...")
    ref = load_reference()
    ip_args = build_ip(ref)

    results = []
    for fn, label, scene_tags in SCENARIOS:
        prompt = f"{CHAR_BASE}, {scene_tags}"
        img = call_sd(prompt, label, ip_args)
        if img:
            img.save(OUTPUT_DIR / f"{fn}.png")
            results.append((fn, label, True))
        else:
            results.append((fn, label, False))

    print(f"\n{'='*60}")
    print(f"완료: {sum(1 for _,_,ok in results if ok)}/{len(results)}")
    print(f"Output: {OUTPUT_DIR}/")
    for fn, label, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  {fn:35s} {label:15s} [{status}]")


if __name__ == "__main__":
    main()
