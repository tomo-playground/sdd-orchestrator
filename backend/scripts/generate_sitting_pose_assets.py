"""sitting 계열 포즈 에셋 자동 생성 스크립트.

txt2img로 포즈 레퍼런스 이미지 생성 → ControlNet OpenPose detect → 스켈레톤 PNG 저장.

Usage:
    python scripts/generate_sitting_pose_assets.py [--pose all|sitting_side|sitting_floor|sitting_knees_up]

출력: backend/assets/poses/{pose_name}.png
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

import requests

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import SD_BASE_URL  # noqa: E402

SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"

ASSETS_DIR = BACKEND_DIR / "assets" / "poses"

# ── 생성할 포즈 정의 ──────────────────────────────────────────────────────────
# prompt: SD txt2img로 레퍼런스 이미지 생성용
# controlnet_pose: 사용할 ControlNet OpenPose 모듈 (openpose_full 권장)
_BASE_NEG = (
    "nsfw, deformed, bad anatomy, bad legs, missing legs, extra legs, "
    "upper_body, cowboy_shot, close-up, cropped, multiple people, "
    "blurry, low quality"
)

POSE_TARGETS: dict[str, dict] = {
    "sitting_side": {
        "desc": "측면 앉기 — from_side 씬용",
        "prompt": (
            "1girl, solo, sitting on floor, from_side, profile view, "
            "knees bent, hands on lap, feet visible, full_body, "
            "white_background, simple_background, "
            "anime style, masterpiece, best_quality, "
            "entire body visible, whole body"
        ),
        "negative": _BASE_NEG,
    },
    "sitting_floor": {
        "desc": "바닥 앉기 — 무릎 세우기",
        "prompt": (
            "1girl, solo, sitting on floor, knees up, hugging knees, "
            "arms wrapped around legs, feet on floor, front view, "
            "full_body, white_background, simple_background, "
            "anime style, masterpiece, best_quality, "
            "entire body visible, whole body"
        ),
        "negative": _BASE_NEG,
    },
    "sitting_knees_up": {
        "desc": "무릎 끌어안기 — 감성 씬용",
        "prompt": (
            "1girl, solo, sitting on floor, knees to chest, arms around knees, "
            "looking down, feet visible, full_body, "
            "white_background, simple_background, "
            "anime style, masterpiece, best_quality, "
            "entire body visible, whole body"
        ),
        "negative": _BASE_NEG,
    },
}

# ── SD 파라미터 ───────────────────────────────────────────────────────────────
TXT2IMG_PARAMS = {
    "steps": 28,
    "cfg_scale": 4.5,
    "width": 832,
    "height": 1216,
    "sampler_name": "Euler",
}


def generate_reference_image(prompt: str, negative: str) -> str:
    """txt2img로 레퍼런스 이미지 생성 → base64 반환."""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        **TXT2IMG_PARAMS,
    }
    resp = requests.post(SD_TXT2IMG_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["images"][0]


def extract_openpose_skeleton(image_b64: str) -> str:
    """ControlNet detect API로 OpenPose 스켈레톤 추출 → base64 반환.

    openpose_full: 전신 keypoints 감지 (현재 WebUI에서 사용 가능한 최적 전처리기).
    """
    payload = {
        "controlnet_input_images": [image_b64],
        "controlnet_module": "openpose_full",
        "controlnet_processor_res": 832,
    }
    resp = requests.post(
        f"{SD_BASE_URL}/controlnet/detect",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # detect API는 images 또는 poses 키로 결과 반환
    images = data.get("images") or data.get("poses")
    if not images:
        raise ValueError(f"detect API 응답에 이미지 없음: {list(data.keys())}")
    return images[0]


def save_b64_png(b64: str, path: Path) -> None:
    """base64 → PNG 파일 저장."""
    # data URI prefix 제거
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    path.write_bytes(base64.b64decode(b64))


def generate_pose(name: str, config: dict) -> None:
    """단일 포즈 에셋 생성."""
    output_path = ASSETS_DIR / f"{name}.png"
    print(f"\n[{name}] {config['desc']}")

    if output_path.exists():
        print(f"  → 이미 존재: {output_path} (--force 옵션으로 덮어쓰기 가능)")
        return

    print("  1) txt2img 레퍼런스 이미지 생성 중...")
    ref_b64 = generate_reference_image(config["prompt"], config["negative"])
    print("  2) OpenPose 스켈레톤 추출 중...")
    skeleton_b64 = extract_openpose_skeleton(ref_b64)
    print(f"  3) 저장: {output_path}")
    save_b64_png(skeleton_b64, output_path)
    print("  ✓ 완료")


def main() -> None:
    parser = argparse.ArgumentParser(description="sitting 포즈 에셋 자동 생성")
    parser.add_argument(
        "--pose",
        default="all",
        choices=["all", *POSE_TARGETS.keys()],
        help="생성할 포즈 (기본: all)",
    )
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    args = parser.parse_args()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    targets = POSE_TARGETS if args.pose == "all" else {args.pose: POSE_TARGETS[args.pose]}

    print(f"SD URL: {SD_BASE_URL}")
    print(f"출력 디렉토리: {ASSETS_DIR}")
    print(f"생성 대상: {list(targets.keys())}")

    # force 옵션 처리
    if args.force:
        for name in targets:
            path = ASSETS_DIR / f"{name}.png"
            if path.exists():
                path.unlink()

    for name, config in targets.items():
        try:
            generate_pose(name, config)
        except Exception as e:
            print(f"  ✗ 실패: {e}")

    print("\n완료. 생성된 에셋을 controlnet.py POSE_MAPPING에 등록하세요.")
    print("예시:")
    for name in targets:
        print(f'    "{name}": "{name}.png",')


if __name__ == "__main__":
    main()
