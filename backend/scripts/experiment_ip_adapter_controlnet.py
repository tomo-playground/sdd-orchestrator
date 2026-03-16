"""
IP-Adapter 0.90 + ControlNet 포즈 실험
=======================================
목적: IP-Adapter 0.90으로 캐릭터 고정 + ControlNet OpenPose로 포즈 오버라이드
      → 캐릭터 일관성 + 포즈 다양성 동시 확보 가능한지 테스트

비교 그룹:
  A) IP-Adapter 0.90 only (포즈 프롬프트만) — 이전 실험에서 포즈 고정됨 확인
  B) IP-Adapter 0.90 + ControlNet OpenPose — 포즈 오버라이드 테스트
  C) IP-Adapter 0.70 + ControlNet OpenPose — weight 낮추면 어떤지

Usage:
  cd backend
  .venv/bin/python scripts/experiment_ip_adapter_controlnet.py
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
EXPERIMENT_DIR = Path(__file__).parent.parent.parent / "experiments" / "ip_adapter_controlnet"
POSE_DIR = Path(__file__).parent.parent / "assets" / "poses"
PREV_EXPERIMENT = Path(__file__).parent.parent.parent / "experiments" / "ip_adapter_consistency" / "20260316_220654"

# 이전 실험의 씬 컨셉 레퍼런스 재사용
SCENE_REF_PATH = PREV_EXPERIMENT / "scene_concept_reference.png"

# 캐릭터/스타일 설정 (이전 실험과 동일)
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

IP_ADAPTER_MODEL = "NOOB-IPA-MARK1 [13579d81]"
IP_ADAPTER_MODULE = "CLIP-ViT-bigG (IPAdapter)"
CONTROLNET_OPENPOSE_MODEL = "noobaiXLControlnet_openposeModel [d23fc679]"

# ─── 실험 시나리오 ──────────────────────────────────────────

SCENARIOS = [
    # ── Group A: IP-Adapter 0.90 only (baseline) ──
    {
        "name": "A1_ipa090_running",
        "description": "IP-Adapter 0.90 only — 달리기 프롬프트",
        "scene_tags": "running, school, hallway, dynamic_angle, full_body, from_side",
        "ip_weight": 0.90,
        "pose_file": None,
        "cn_weight": 0,
    },
    {
        "name": "A2_ipa090_standing",
        "description": "IP-Adapter 0.90 only — 서서 손흔들기",
        "scene_tags": "standing, waving, park, outdoors, cherry_blossoms, full_body, from_front",
        "ip_weight": 0.90,
        "pose_file": None,
        "cn_weight": 0,
    },
    {
        "name": "A3_ipa090_umbrella",
        "description": "IP-Adapter 0.90 only — 우산 들고 서기",
        "scene_tags": "standing, holding_umbrella, rain, night, city, cowboy_shot, from_front",
        "ip_weight": 0.90,
        "pose_file": None,
        "cn_weight": 0,
    },
    # ── Group B: IP-Adapter 0.90 + ControlNet OpenPose ──
    {
        "name": "B1_ipa090_cn_running",
        "description": "IP-Adapter 0.90 + OpenPose — 달리기",
        "scene_tags": "running, school, hallway, dynamic_angle, full_body, from_side",
        "ip_weight": 0.90,
        "pose_file": "running.png",
        "cn_weight": 1.0,
    },
    {
        "name": "B2_ipa090_cn_waving",
        "description": "IP-Adapter 0.90 + OpenPose — 손흔들기",
        "scene_tags": "standing, waving, park, outdoors, cherry_blossoms, full_body, from_front",
        "ip_weight": 0.90,
        "pose_file": "standing_waving.png",
        "cn_weight": 1.0,
    },
    {
        "name": "B3_ipa090_cn_umbrella",
        "description": "IP-Adapter 0.90 + OpenPose — 우산",
        "scene_tags": "standing, holding_umbrella, rain, night, city, cowboy_shot, from_front",
        "ip_weight": 0.90,
        "pose_file": "holding_umbrella.png",
        "cn_weight": 1.0,
    },
    {
        "name": "B4_ipa090_cn_jumping",
        "description": "IP-Adapter 0.90 + OpenPose — 점프",
        "scene_tags": "jumping, excited, outdoors, sky, full_body, from_front",
        "ip_weight": 0.90,
        "pose_file": "jumping.png",
        "cn_weight": 1.0,
    },
    {
        "name": "B5_ipa090_cn_profile",
        "description": "IP-Adapter 0.90 + OpenPose — 옆모습",
        "scene_tags": "standing, looking_away, sunset, outdoors, wind, full_body, from_side",
        "ip_weight": 0.90,
        "pose_file": "profile_standing.png",
        "cn_weight": 1.0,
    },
    {
        "name": "B6_ipa090_cn_back",
        "description": "IP-Adapter 0.90 + OpenPose — 뒷모습",
        "scene_tags": "standing, from_behind, looking_back, city, evening, full_body",
        "ip_weight": 0.90,
        "pose_file": "standing_from_behind.png",
        "cn_weight": 1.0,
    },
    # ── Group C: IP-Adapter 0.70 + ControlNet OpenPose ──
    {
        "name": "C1_ipa070_cn_running",
        "description": "IP-Adapter 0.70 + OpenPose — 달리기",
        "scene_tags": "running, school, hallway, dynamic_angle, full_body, from_side",
        "ip_weight": 0.70,
        "pose_file": "running.png",
        "cn_weight": 1.0,
    },
    {
        "name": "C2_ipa070_cn_umbrella",
        "description": "IP-Adapter 0.70 + OpenPose — 우산",
        "scene_tags": "standing, holding_umbrella, rain, night, city, cowboy_shot, from_front",
        "ip_weight": 0.70,
        "pose_file": "holding_umbrella.png",
        "cn_weight": 1.0,
    },
    {
        "name": "C3_ipa070_cn_jumping",
        "description": "IP-Adapter 0.70 + OpenPose — 점프",
        "scene_tags": "jumping, excited, outdoors, sky, full_body, from_front",
        "ip_weight": 0.70,
        "pose_file": "jumping.png",
        "cn_weight": 1.0,
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


def build_payload(
    prompt: str,
    negative: str,
    ref_b64: str,
    ip_weight: float,
    pose_b64: str | None = None,
    cn_weight: float = 1.0,
) -> dict:
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        **SD_PARAMS,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
        "batch_size": 1,
    }

    controlnet_args = []

    # Slot 0: IP-Adapter
    controlnet_args.append(
        {
            "enabled": True,
            "image": ref_b64,
            "module": IP_ADAPTER_MODULE,
            "model": IP_ADAPTER_MODEL,
            "weight": ip_weight,
            "resize_mode": "Crop and Resize",
            "processor_res": 832,
            "control_mode": "Balanced",
            "guidance_start": 0.0,
            "guidance_end": 1.0,
        }
    )

    # Slot 1: ControlNet OpenPose (있으면)
    if pose_b64:
        controlnet_args.append(
            {
                "enabled": True,
                "image": pose_b64,
                "module": "openpose_full",
                "model": CONTROLNET_OPENPOSE_MODEL,
                "weight": cn_weight,
                "resize_mode": "Crop and Resize",
                "processor_res": 832,
                "control_mode": "Balanced",
                "guidance_start": 0.0,
                "guidance_end": 1.0,
            }
        )
    else:
        controlnet_args.append({"enabled": False})

    # Slot 2: 비활성
    controlnet_args.append({"enabled": False})

    payload["alwayson_scripts"] = {
        "controlnet": {"args": controlnet_args},
    }

    return payload


async def generate_image(
    client: httpx.AsyncClient,
    payload: dict,
    name: str,
    output_dir: Path,
) -> dict:
    print(f"  [{name}] 생성 중...")
    start = time.time()

    resp = await client.post(
        f"{SD_BASE_URL}/sdapi/v1/txt2img",
        json=payload,
        timeout=180.0,
    )
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

    # CN 설정 추출
    cn_args = payload["alwayson_scripts"]["controlnet"]["args"]
    ip_w = cn_args[0].get("weight") if cn_args[0].get("enabled") else None
    cn_enabled = cn_args[1].get("enabled", False) if len(cn_args) > 1 else False
    cn_w = cn_args[1].get("weight") if cn_enabled else None

    return {
        "name": name,
        "seed": seed,
        "elapsed_seconds": round(elapsed, 1),
        "ip_adapter_weight": ip_w,
        "controlnet_openpose": cn_enabled,
        "controlnet_weight": cn_w,
        "file": img_path.name,
    }


# ─── 메인 ───────────────────────────────────────────────────


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = EXPERIMENT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"실험 결과 저장: {output_dir}")

    # 씬 컨셉 레퍼런스 로드
    if not SCENE_REF_PATH.exists():
        print(f"레퍼런스 이미지 없음: {SCENE_REF_PATH}")
        return
    ref_b64 = load_image_b64(SCENE_REF_PATH)
    print(f"씬 컨셉 레퍼런스 로드 완료: {SCENE_REF_PATH.name}")

    # 포즈 이미지 사전 로드
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
                pose_cache[pf] = None

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

            payload = build_payload(
                prompt,
                negative,
                ref_b64=ref_b64,
                ip_weight=scenario["ip_weight"],
                pose_b64=pose_b64,
                cn_weight=scenario.get("cn_weight", 1.0),
            )

            meta = await generate_image(client, payload, scenario["name"], output_dir)
            meta["group"] = group
            meta["description"] = scenario["description"]
            meta["pose_file"] = scenario.get("pose_file")
            results.append(meta)

    # 리포트 저장
    report = {
        "experiment": "IP-Adapter + ControlNet 포즈 오버라이드 테스트",
        "timestamp": timestamp,
        "character": "하린 (ID=44)",
        "reference": "씬 컨셉 레퍼런스 (카페 장면)",
        "hypothesis": (
            "IP-Adapter 0.90 + ControlNet OpenPose로 캐릭터 일관성(IP-Adapter)과 포즈 다양성(ControlNet)을 동시 확보"
        ),
        "groups": {
            "A": "IP-Adapter 0.90 only (baseline, 포즈 프롬프트만)",
            "B": "IP-Adapter 0.90 + ControlNet OpenPose 1.0",
            "C": "IP-Adapter 0.70 + ControlNet OpenPose 1.0",
        },
        "models": {
            "ip_adapter": IP_ADAPTER_MODEL,
            "controlnet": CONTROLNET_OPENPOSE_MODEL,
        },
        "results": results,
        "total_images": len(results),
    }

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== 실험 완료! 총 {len(results)}장 생성 ===")
    print(f"결과: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
