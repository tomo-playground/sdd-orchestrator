"""
IP-Adapter 캐릭터 일관성 실험
=============================
목적: 씬 컨셉 레퍼런스 이미지 + IP-Adapter 0.90으로
      프롬프트만으로 다양한 포즈/연출 변경 시 캐릭터 일관성 테스트

실험 흐름:
  1. 실제 씬 수준의 고품질 레퍼런스 이미지 생성 (흰 배경 X)
  2. 해당 레퍼런스를 IP-Adapter에 투입 (weight=0.90, ControlNet OFF)
  3. 다양한 프롬프트로 포즈/구도/연출 변화 테스트

Usage:
  cd backend
  .venv/bin/python scripts/experiment_ip_adapter_consistency.py
"""

import asyncio
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# backend/ 를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SD_BASE_URL

# ─── 실험 설정 ──────────────────────────────────────────────
EXPERIMENT_DIR = Path(__file__).parent.parent.parent / "experiments" / "ip_adapter_consistency"
MINIO_URL = "http://localhost:9000/shorts-producer"
REF_STORAGE_KEY = "characters/44/reference/character_44_reference_c97318f239a9399d.png"

# 하린 캐릭터 정보 (DB에서 조회한 값)
CHARACTER_POSITIVE = (
    "1girl, (auburn_hair:1.3), (long_hair:1.2), (blunt_bangs:1.2), "
    "(amber_eyes:1.25), (oversized_denim_jacket:1.3), (yellow_crop_top:1.2), "
    "(high-waist_skirt:1.2), (ribbon:1.15), (soft_smile:1.1)"
)
CHARACTER_NEGATIVE = "(3d:1.3), (realistic:1.3), (photorealistic:1.3)"

# StyleProfile #11 "Romantic Warm Anime"
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

# Style LoRAs
STYLE_LORAS = [
    {"name": "noobai_vpred_1_flat_color_v2", "weight": 0.3, "trigger": "flat color"},
    {"name": "NOOB_vp1_detailer_by_volnovik_v1", "weight": 0.35, "trigger": ""},
]

# SD 생성 파라미터 (StyleProfile 기본값)
SD_PARAMS = {
    "steps": 28,
    "cfg_scale": 4.5,
    "sampler_name": "Euler",
    "width": 832,
    "height": 1216,
    "seed": -1,
}

# IP-Adapter 설정
IP_ADAPTER_MODEL = "NOOB-IPA-MARK1 [13579d81]"
IP_ADAPTER_MODULE = "CLIP-ViT-bigG (IPAdapter)"

# ─── 실험 시나리오 ──────────────────────────────────────────

# Phase 1: 씬 컨셉 레퍼런스 생성 (흰 배경 아닌 실제 장면)
SCENE_CONCEPT_REFERENCE = {
    "name": "scene_concept_reference",
    "description": "카페에서 창밖을 보는 따뜻한 장면 (레퍼런스용)",
    "scene_tags": (
        "sitting, cafe, window, natural_light, "
        "cup, table, indoor, cozy, "
        "looking_out_window, relaxed, "
        "upper_body, from_side"
    ),
}

# Phase 2: 레퍼런스를 IP-Adapter로 투입하고 다양한 연출
VARIATION_SCENARIOS = [
    {
        "name": "01_same_scene_front",
        "description": "같은 카페, 정면 시점",
        "scene_tags": (
            "sitting, cafe, window, natural_light, "
            "cup, table, indoor, cozy, "
            "looking_at_viewer, smile, "
            "upper_body, from_front"
        ),
        "ip_weight": 0.90,
    },
    {
        "name": "02_standing_outdoor",
        "description": "야외 공원에서 서있는 포즈",
        "scene_tags": (
            "standing, park, outdoors, trees, "
            "sunlight, cherry_blossoms, spring, "
            "looking_at_viewer, happy, "
            "cowboy_shot, from_front"
        ),
        "ip_weight": 0.90,
    },
    {
        "name": "03_walking_street",
        "description": "거리를 걸으며 뒤돌아보는 장면",
        "scene_tags": (
            "walking, street, urban, city_lights, "
            "evening, sunset, golden_hour, "
            "looking_back, over_shoulder, "
            "full_body, from_behind"
        ),
        "ip_weight": 0.90,
    },
    {
        "name": "04_close_up_emotion",
        "description": "감정적 클로즈업 (슬픈 표정)",
        "scene_tags": (
            "close-up, face_focus, tears, crying, sad, emotional, blurry_background, bokeh, looking_down, solo"
        ),
        "ip_weight": 0.90,
    },
    {
        "name": "05_action_running",
        "description": "달리는 역동적 장면",
        "scene_tags": (
            "running, motion_blur, dynamic_angle, school, hallway, indoor, determined, excited, full_body, from_side"
        ),
        "ip_weight": 0.90,
    },
    {
        "name": "06_night_rain",
        "description": "비오는 밤, 우산 아래",
        "scene_tags": (
            "rain, night, umbrella, wet, "
            "city_lights, reflection, puddle, "
            "standing, holding_umbrella, "
            "cowboy_shot, from_front, looking_up"
        ),
        "ip_weight": 0.90,
    },
    {
        "name": "07_low_weight_comparison",
        "description": "비교용: IP-Adapter 0.35 (기존 설정)",
        "scene_tags": (
            "sitting, cafe, window, natural_light, "
            "cup, table, indoor, cozy, "
            "looking_at_viewer, smile, "
            "upper_body, from_front"
        ),
        "ip_weight": 0.35,
    },
    {
        "name": "08_mid_weight_comparison",
        "description": "비교용: IP-Adapter 0.60",
        "scene_tags": (
            "sitting, cafe, window, natural_light, "
            "cup, table, indoor, cozy, "
            "looking_at_viewer, smile, "
            "upper_body, from_front"
        ),
        "ip_weight": 0.60,
    },
]


# ─── 유틸리티 ───────────────────────────────────────────────


def build_prompt(scene_tags: str) -> str:
    """Style + Character + Scene 프롬프트 조합"""
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
    """Negative 프롬프트 조합"""
    return f"{STYLE_NEGATIVE}, {CHARACTER_NEGATIVE}"


def build_payload(
    prompt: str,
    negative: str,
    ip_adapter_image_b64: str | None = None,
    ip_weight: float = 0.90,
) -> dict:
    """SD WebUI txt2img 페이로드 생성"""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        **SD_PARAMS,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
        "batch_size": 1,
    }

    controlnet_args = []
    if ip_adapter_image_b64:
        controlnet_args.append(
            {
                "enabled": True,
                "image": ip_adapter_image_b64,
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
    else:
        controlnet_args.append({"enabled": False})

    # Slot 2, 3 비활성 (Forge 3-slot)
    controlnet_args.extend([{"enabled": False}, {"enabled": False}])

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
    """SD WebUI txt2img 호출 및 결과 저장"""
    print(f"  [{name}] 생성 중... (prompt: {payload['prompt'][:80]}...)")
    start = time.time()

    resp = await client.post(
        f"{SD_BASE_URL}/sdapi/v1/txt2img",
        json=payload,
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    elapsed = time.time() - start

    # 이미지 저장
    images = data.get("images", [])
    if not images:
        print(f"  [{name}] 이미지 없음!")
        return {"name": name, "error": "no images"}

    img_b64 = images[0]
    img_bytes = base64.b64decode(img_b64)
    img_path = output_dir / f"{name}.png"
    img_path.write_bytes(img_bytes)

    # info 파싱
    info = {}
    try:
        info = json.loads(data.get("info", "{}"))
    except (json.JSONDecodeError, TypeError):
        pass

    seed = info.get("seed", "unknown")
    print(f"  [{name}] 완료! ({elapsed:.1f}s, seed={seed}, {len(img_bytes) // 1024}KB)")

    # 메타데이터 저장
    meta = {
        "name": name,
        "prompt": payload["prompt"],
        "negative_prompt": payload["negative_prompt"],
        "seed": seed,
        "elapsed_seconds": round(elapsed, 1),
        "ip_adapter_weight": (
            payload["alwayson_scripts"]["controlnet"]["args"][0].get("weight")
            if payload["alwayson_scripts"]["controlnet"]["args"][0].get("enabled")
            else None
        ),
        "file": str(img_path.name),
    }
    return meta


async def load_reference_from_minio() -> str:
    """MinIO에서 기존 레퍼런스 이미지 로드 → base64"""
    url = f"{MINIO_URL}/{REF_STORAGE_KEY}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode("utf-8")


# ─── 메인 실험 ──────────────────────────────────────────────


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = EXPERIMENT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"실험 결과 저장: {output_dir}")

    results = []

    async with httpx.AsyncClient() as client:
        # ── Phase 1: 씬 컨셉 레퍼런스 생성 ──
        print("\n=== Phase 1: 씬 컨셉 레퍼런스 이미지 생성 ===")
        print(f"  컨셉: {SCENE_CONCEPT_REFERENCE['description']}")

        ref_prompt = build_prompt(SCENE_CONCEPT_REFERENCE["scene_tags"])
        ref_negative = build_negative()
        ref_payload = build_payload(ref_prompt, ref_negative)  # IP-Adapter 없이

        ref_meta = await generate_image(
            client,
            ref_payload,
            SCENE_CONCEPT_REFERENCE["name"],
            output_dir,
        )
        results.append(ref_meta)

        # 생성된 레퍼런스를 base64로 로드
        ref_img_path = output_dir / f"{SCENE_CONCEPT_REFERENCE['name']}.png"
        scene_ref_b64 = base64.b64encode(ref_img_path.read_bytes()).decode("utf-8")

        # 기존 흰배경 레퍼런스도 로드 (비교용)
        print("\n  기존 흰배경 레퍼런스도 로드 (비교용)...")
        original_ref_b64 = await load_reference_from_minio()

        # ── Phase 2: 씬 컨셉 레퍼런스 기반 변형 ──
        print("\n=== Phase 2: 씬 컨셉 레퍼런스 + IP-Adapter 변형 ===")

        for scenario in VARIATION_SCENARIOS:
            print(f"\n--- {scenario['name']}: {scenario['description']} ---")

            prompt = build_prompt(scenario["scene_tags"])
            negative = build_negative()
            payload = build_payload(
                prompt,
                negative,
                ip_adapter_image_b64=scene_ref_b64,
                ip_weight=scenario["ip_weight"],
            )

            meta = await generate_image(
                client,
                payload,
                f"scene_ref_{scenario['name']}",
                output_dir,
            )
            meta["reference_type"] = "scene_concept"
            results.append(meta)

        # ── Phase 3: 기존 흰배경 레퍼런스로 동일 시나리오 (비교) ──
        print("\n=== Phase 3: 기존 흰배경 레퍼런스 비교 (동일 시드 없음, 동일 프롬프트) ===")

        comparison_scenarios = [
            VARIATION_SCENARIOS[0],  # 01_same_scene_front (0.90)
            VARIATION_SCENARIOS[1],  # 02_standing_outdoor (0.90)
            VARIATION_SCENARIOS[3],  # 04_close_up_emotion (0.90)
        ]

        for scenario in comparison_scenarios:
            print(f"\n--- [원본 ref] {scenario['name']}: {scenario['description']} ---")

            prompt = build_prompt(scenario["scene_tags"])
            negative = build_negative()
            payload = build_payload(
                prompt,
                negative,
                ip_adapter_image_b64=original_ref_b64,
                ip_weight=scenario["ip_weight"],
            )

            meta = await generate_image(
                client,
                payload,
                f"orig_ref_{scenario['name']}",
                output_dir,
            )
            meta["reference_type"] = "original_white_bg"
            results.append(meta)

    # ── 결과 리포트 ──
    report = {
        "experiment": "IP-Adapter 캐릭터 일관성 테스트",
        "timestamp": timestamp,
        "character": "하린 (ID=44)",
        "style_profile": "Romantic Warm Anime (ID=11)",
        "sd_model": "NoobAI-XL V-Pred 1.0",
        "ip_adapter_model": IP_ADAPTER_MODEL,
        "hypothesis": ("씬 컨셉 레퍼런스(배경 포함) + IP-Adapter 0.90이 흰배경 레퍼런스보다 캐릭터 일관성이 높을 것"),
        "phases": {
            "phase1": "씬 컨셉 레퍼런스 생성 (카페 장면, IP-Adapter 없음)",
            "phase2": "씬 컨셉 레퍼런스 + IP-Adapter 변형 (6종 + weight 비교 2종)",
            "phase3": "기존 흰배경 레퍼런스로 동일 시나리오 비교 (3종)",
        },
        "results": results,
        "total_images": len(results),
    }

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== 실험 완료! 총 {len(results)}장 생성 ===")
    print(f"결과: {output_dir}")
    print(f"리포트: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
