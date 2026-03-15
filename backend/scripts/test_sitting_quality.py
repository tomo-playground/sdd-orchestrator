"""sitting 포즈 품질 평가 스크립트.

ControlNet OFF(현재) vs ON(openpose_pre) 비교 이미지 생성.

Usage:
    python scripts/test_sitting_quality.py
출력: /tmp/sitting_test/
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import SD_BASE_URL, SD_TXT2IMG_URL  # noqa: E402

OUTPUT_DIR = Path("/tmp/sitting_test")
POSES_DIR = BACKEND_DIR / "assets" / "poses"

BASE_PROMPT = (
    "1girl, solo, hrkzdrm_cs, black_hair, brown_eyes, school_uniform, "
    "indoors, classroom, best_quality, masterpiece"
)
NEGATIVE = (
    "lowres, bad_anatomy, bad_hands, deformed, ugly, blurry, "
    "nsfw, multiple_girls, bad_legs, deformed_legs"
)

PARAMS = {
    "steps": 28,
    "cfg_scale": 4.5,
    "width": 832,
    "height": 1216,
    "sampler_name": "Euler",
    "negative_prompt": NEGATIVE,
}

TEST_CASES = [
    {
        "name": "sitting_neutral__no_cn",
        "prompt": BASE_PROMPT + ", sitting, sitting_on_chair, upper_body",
        "use_controlnet": False,
        "pose_file": None,
        "label": "sitting_neutral — ControlNet OFF (현재)",
    },
    {
        "name": "sitting_neutral__with_cn",
        "prompt": BASE_PROMPT + ", sitting, sitting_on_chair, upper_body",
        "use_controlnet": True,
        "pose_file": "sitting_neutral.png",
        "label": "sitting_neutral — ControlNet ON",
    },
    {
        "name": "sitting_leaning__no_cn",
        "prompt": BASE_PROMPT + ", sitting, leaning_forward, upper_body",
        "use_controlnet": False,
        "pose_file": None,
        "label": "sitting_leaning — ControlNet OFF (현재)",
    },
    {
        "name": "sitting_leaning__with_cn",
        "prompt": BASE_PROMPT + ", sitting, leaning_forward, upper_body",
        "use_controlnet": True,
        "pose_file": "sitting_leaning.png",
        "label": "sitting_leaning — ControlNet ON",
    },
]


def load_pose_b64(filename: str) -> str:
    path = POSES_DIR / filename
    return base64.b64encode(path.read_bytes()).decode()


def generate(case: dict) -> bytes:
    payload = {
        "prompt": case["prompt"],
        **PARAMS,
    }

    if case["use_controlnet"] and case["pose_file"]:
        pose_b64 = load_pose_b64(case["pose_file"])
        payload["alwayson_scripts"] = {
            "ControlNet": {
                "args": [
                    {
                        "enabled": True,
                        "image": pose_b64,
                        "module": "none",
                        "model": "noobaiXLControlnet_openposeModel",
                        "weight": 0.65,
                        "resize_mode": 1,
                        "processor_res": 832,
                        "guidance_start": 0.0,
                        "guidance_end": 1.0,
                    }
                ]
            }
        }

    resp = requests.post(SD_TXT2IMG_URL, json=payload, timeout=180)
    resp.raise_for_status()
    b64 = resp.json()["images"][0]
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    return base64.b64decode(b64)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"출력: {OUTPUT_DIR}")
    print(f"SD: {SD_BASE_URL}\n")

    for case in TEST_CASES:
        print(f"[{case['name']}] {case['label']}")
        try:
            img_bytes = generate(case)
            out = OUTPUT_DIR / f"{case['name']}.png"
            out.write_bytes(img_bytes)
            print(f"  → 저장: {out} ({len(img_bytes)//1024}KB)")
        except Exception as e:
            print(f"  ✗ 실패: {e}")

    print("\n완료. 결과 이미지를 비교해서 품질 차이를 확인하세요.")
    print(f"  {OUTPUT_DIR}/")
    for case in TEST_CASES:
        print(f"  - {case['name']}.png : {case['label']}")


if __name__ == "__main__":
    main()
