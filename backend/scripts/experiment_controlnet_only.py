"""
ControlNet Only 실험 (IP-Adapter 없음)
======================================
목적: IP-Adapter 없이 ControlNet OpenPose만으로 포즈 제어가
      정확하게 동작하는지 확인

비교:
  A) 프롬프트만 (ControlNet/IP-Adapter 모두 없음)
  B) ControlNet OpenPose only (다양한 포즈)

Usage:
  cd backend
  .venv/bin/python scripts/experiment_controlnet_only.py
"""

import asyncio
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SD_BASE_URL

# ─── 설정 ───────────────────────────────────────────────────
EXPERIMENT_DIR = Path(__file__).parent.parent.parent / "experiments" / "controlnet_only"
POSE_DIR = Path(__file__).parent.parent / "assets" / "poses"

CHARACTER_POSITIVE = (
    "1girl, (auburn_hair:1.3), (long_hair:1.2), (blunt_bangs:1.2), "
    "(amber_eyes:1.25), (oversized_denim_jacket:1.3), (yellow_crop_top:1.2), "
    "(high-waist_skirt:1.2), (ribbon:1.15), (soft_smile:1.1)"
)
CHARACTER_NEGATIVE = "(3d:1.3), (realistic:1.3), (photorealistic:1.3)"
STYLE_POSITIVE = (
    "masterpiece, best_quality, anime_coloring, flat_color, "
    "(warm_lighting:1.3), backlighting, lens_flare, soft_focus, "
    "depth_of_field, pastel_colors"
)
STYLE_NEGATIVE = (
    "(worst quality, low quality:1.4), normal quality, bad anatomy, bad hands, "
    "bad proportions, blurry, watermark, text, error, signature, username, "
    "artist name, jpeg artifacts, cropped, ugly, extra fingers, mutated hands, "
    "poorly drawn hands, poorly drawn face, deformed, extra limbs, "
    "(3d:1.3), (realistic:1.3), (photorealistic:1.3)"
)
STYLE_LORAS = [
    {"name": "noobai_vpred_1_flat_color_v2", "weight": 0.3, "trigger": "flat color"},
    {"name": "NOOB_vp1_detailer_by_volnovik_v1", "weight": 0.35, "trigger": ""},
]

SD_PARAMS = {
    "steps": 28,
    "cfg_scale": 4.5,
    "sampler_name": "Euler",
    "width": 832,
    "height": 1216,
    "seed": -1,
}

CONTROLNET_OPENPOSE_MODEL = "noobaiXLControlnet_openposeModel [d23fc679]"

# ─── 시나리오 ───────────────────────────────────────────────

SCENARIOS = [
    # ── Group A: 프롬프트만 (baseline) ──
    {
        "name": "A1_prompt_running",
        "description": "프롬프트만 — 달리기",
        "scene_tags": "running, school, hallway, dynamic_angle, full_body, from_side",
        "pose_file": None,
    },
    {
        "name": "A2_prompt_jumping",
        "description": "프롬프트만 — 점프",
        "scene_tags": "jumping, excited, outdoors, sky, full_body, from_front",
        "pose_file": None,
    },
    {
        "name": "A3_prompt_umbrella",
        "description": "프롬프트만 — 우산",
        "scene_tags": "standing, holding_umbrella, rain, night, city, cowboy_shot, from_front",
        "pose_file": None,
    },
    {
        "name": "A4_prompt_profile",
        "description": "프롬프트만 — 옆모습",
        "scene_tags": "standing, looking_away, sunset, outdoors, wind, full_body, from_side",
        "pose_file": None,
    },
    {
        "name": "A5_prompt_back",
        "description": "프롬프트만 — 뒷모습",
        "scene_tags": "standing, from_behind, looking_back, city, evening, full_body",
        "pose_file": None,
    },
    # ── Group B: ControlNet OpenPose only ──
    {
        "name": "B1_cn_running",
        "description": "ControlNet OpenPose — 달리기",
        "scene_tags": "running, school, hallway, dynamic_angle, full_body, from_side",
        "pose_file": "running.png",
    },
    {
        "name": "B2_cn_jumping",
        "description": "ControlNet OpenPose — 점프",
        "scene_tags": "jumping, excited, outdoors, sky, full_body, from_front",
        "pose_file": "jumping.png",
    },
    {
        "name": "B3_cn_umbrella",
        "description": "ControlNet OpenPose — 우산",
        "scene_tags": "standing, holding_umbrella, rain, night, city, cowboy_shot, from_front",
        "pose_file": "holding_umbrella.png",
    },
    {
        "name": "B4_cn_profile",
        "description": "ControlNet OpenPose — 옆모습",
        "scene_tags": "standing, looking_away, sunset, outdoors, wind, full_body, from_side",
        "pose_file": "profile_standing.png",
    },
    {
        "name": "B5_cn_back",
        "description": "ControlNet OpenPose — 뒷모습",
        "scene_tags": "standing, from_behind, looking_back, city, evening, full_body",
        "pose_file": "standing_from_behind.png",
    },
    {
        "name": "B6_cn_waving",
        "description": "ControlNet OpenPose — 손흔들기",
        "scene_tags": "standing, waving, park, outdoors, cherry_blossoms, full_body, from_front",
        "pose_file": "standing_waving.png",
    },
    {
        "name": "B7_cn_sitting",
        "description": "ControlNet OpenPose — 앉기",
        "scene_tags": "sitting, cafe, window, natural_light, indoor, cozy, upper_body",
        "pose_file": "sitting_neutral.png",
    },
    {
        "name": "B8_cn_arms_crossed",
        "description": "ControlNet OpenPose — 팔짱",
        "scene_tags": "standing, arms_crossed, confident, school, indoor, cowboy_shot, from_front",
        "pose_file": "standing_arms_crossed.png",
    },
]


# ─── 유틸리티 ───────────────────────────────────────────────


def build_prompt(scene_tags: str) -> str:
    lora_str = ", ".join(f"<lora:{l['name']}:{l['weight']}>" for l in STYLE_LORAS)
    trigger_str = ", ".join(l["trigger"] for l in STYLE_LORAS if l["trigger"])
    parts = [STYLE_POSITIVE]
    if trigger_str:
        parts.append(trigger_str)
    parts.append(lora_str)
    parts.append(CHARACTER_POSITIVE)
    parts.append(scene_tags)
    return ", ".join(parts)


def build_negative() -> str:
    return f"{STYLE_NEGATIVE}, {CHARACTER_NEGATIVE}"


def load_image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def build_payload(prompt: str, negative: str, pose_b64: str | None = None) -> dict:
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        **SD_PARAMS,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
        "batch_size": 1,
    }

    controlnet_args = []

    if pose_b64:
        controlnet_args.append(
            {
                "enabled": True,
                "image": pose_b64,
                "module": "openpose_full",
                "model": CONTROLNET_OPENPOSE_MODEL,
                "weight": 1.0,
                "resize_mode": "Crop and Resize",
                "processor_res": 832,
                "control_mode": "Balanced",
                "guidance_start": 0.0,
                "guidance_end": 1.0,
            }
        )
    else:
        controlnet_args.append({"enabled": False})

    controlnet_args.extend([{"enabled": False}, {"enabled": False}])

    payload["alwayson_scripts"] = {
        "controlnet": {"args": controlnet_args},
    }
    return payload


async def generate_image(client: httpx.AsyncClient, payload: dict, name: str, output_dir: Path) -> dict:
    print(f"  [{name}] 생성 중...")
    start = time.time()

    resp = await client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload, timeout=180.0)
    resp.raise_for_status()
    data = resp.json()
    elapsed = time.time() - start

    images = data.get("images", [])
    if not images:
        print(f"  [{name}] 이미지 없음!")
        return {"name": name, "error": "no images"}

    img_bytes = base64.b64decode(images[0])
    img_path = output_dir / f"{name}.png"
    img_path.write_bytes(img_bytes)

    info = {}
    try:
        info = json.loads(data.get("info", "{}"))
    except (json.JSONDecodeError, TypeError):
        pass

    seed = info.get("seed", "unknown")
    print(f"  [{name}] 완료! ({elapsed:.1f}s, seed={seed}, {len(img_bytes) // 1024}KB)")

    return {
        "name": name,
        "seed": seed,
        "elapsed_seconds": round(elapsed, 1),
        "file": img_path.name,
    }


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = EXPERIMENT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"실험 결과 저장: {output_dir}")

    # 포즈 사전 로드
    pose_cache: dict[str, str] = {}
    for s in SCENARIOS:
        pf = s.get("pose_file")
        if pf and pf not in pose_cache:
            pose_path = POSE_DIR / pf
            if pose_path.exists():
                pose_cache[pf] = load_image_b64(pose_path)
                print(f"포즈 로드: {pf}")
            else:
                print(f"포즈 파일 없음: {pose_path}")

    results = []

    async with httpx.AsyncClient() as client:
        for i, scenario in enumerate(SCENARIOS):
            group = scenario["name"][0]
            print(f"\n[{i + 1}/{len(SCENARIOS)}] === {scenario['name']}: {scenario['description']} ===")

            prompt = build_prompt(scenario["scene_tags"])
            negative = build_negative()

            pose_b64 = None
            if scenario.get("pose_file"):
                pose_b64 = pose_cache.get(scenario["pose_file"])

            payload = build_payload(prompt, negative, pose_b64=pose_b64)
            meta = await generate_image(client, payload, scenario["name"], output_dir)
            meta["group"] = group
            meta["description"] = scenario["description"]
            meta["pose_file"] = scenario.get("pose_file")
            results.append(meta)

    report = {
        "experiment": "ControlNet Only (IP-Adapter 없음) 포즈 제어 테스트",
        "timestamp": timestamp,
        "character": "하린 (ID=44)",
        "hypothesis": "IP-Adapter 없이 ControlNet OpenPose만 사용하면 포즈 제어가 정확하게 동작할 것",
        "groups": {
            "A": "프롬프트만 (baseline)",
            "B": "ControlNet OpenPose 1.0 (IP-Adapter 없음)",
        },
        "controlnet_model": CONTROLNET_OPENPOSE_MODEL,
        "results": results,
        "total_images": len(results),
    }

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== 실험 완료! 총 {len(results)}장 생성 ===")
    print(f"결과: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
