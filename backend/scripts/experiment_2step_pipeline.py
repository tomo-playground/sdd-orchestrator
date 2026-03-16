"""
2-Step 파이프라인 실험
=====================
Step 1: ControlNet OpenPose + 프롬프트 → 포즈 정확한 이미지 생성
Step 2: Step 1 결과를 IP-Adapter 레퍼런스로 → 캐릭터 일관성 적용

비교:
  A) 1-step: IP-Adapter 0.90 only (포즈 고정 문제)
  B) 2-step: CN으로 포즈 잡기 → IPA로 일관성 적용
  C) 2-step 변형: 동일 레퍼런스로 프롬프트만 바꿔서 재생성

Usage:
  cd backend
  .venv/bin/python scripts/experiment_2step_pipeline.py
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
EXPERIMENT_DIR = Path(__file__).parent.parent.parent / "experiments" / "2step_pipeline"
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

IP_ADAPTER_MODEL = "NOOB-IPA-MARK1 [13579d81]"
IP_ADAPTER_MODULE = "CLIP-ViT-bigG (IPAdapter)"
CONTROLNET_OPENPOSE_MODEL = "noobaiXLControlnet_openposeModel [d23fc679]"

# ─── 씬 정의 ────────────────────────────────────────────────

SCENES = [
    {
        "id": "running",
        "label": "달리기",
        "scene_tags": "running, school, hallway, dynamic_angle, excited, full_body, from_side",
        "pose_file": "running.png",
    },
    {
        "id": "umbrella",
        "label": "우산",
        "scene_tags": "standing, holding_umbrella, rain, night, city_lights, cowboy_shot, from_front",
        "pose_file": "holding_umbrella.png",
    },
    {
        "id": "waving",
        "label": "손흔들기",
        "scene_tags": "standing, waving, park, outdoors, cherry_blossoms, happy, full_body, from_front",
        "pose_file": "standing_waving.png",
    },
    {
        "id": "back",
        "label": "뒷모습",
        "scene_tags": "standing, from_behind, looking_back, city, sunset, evening, full_body",
        "pose_file": "standing_from_behind.png",
    },
    {
        "id": "sitting",
        "label": "카페 앉기",
        "scene_tags": "sitting, cafe, window, natural_light, indoor, cozy, cup, upper_body",
        "pose_file": "sitting_neutral.png",
    },
]

# Step 2에서 동일 레퍼런스로 씬만 바꾸는 테스트 (Group C)
REUSE_VARIATIONS = [
    {
        "ref_scene_id": "running",
        "label": "달리기 레퍼런스 → 점프로 변환",
        "scene_tags": "jumping, excited, outdoors, sky, full_body, from_front",
    },
    {
        "ref_scene_id": "umbrella",
        "label": "우산 레퍼런스 → 실내 서기로 변환",
        "scene_tags": "standing, indoor, library, bookshelf, reading, cowboy_shot, from_front",
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


def build_payload_cn_only(prompt: str, negative: str, pose_b64: str) -> dict:
    """Step 1: ControlNet OpenPose만 (IP-Adapter 없음)"""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        **SD_PARAMS,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
        "batch_size": 1,
    }
    payload["alwayson_scripts"] = {
        "controlnet": {
            "args": [
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
                },
                {"enabled": False},
                {"enabled": False},
            ]
        }
    }
    return payload


def build_payload_ipa_only(prompt: str, negative: str, ref_b64: str, ip_weight: float = 0.90) -> dict:
    """Step 2 또는 1-step: IP-Adapter만 (ControlNet 없음)"""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        **SD_PARAMS,
        "override_settings": {"CLIP_stop_at_last_layers": 2},
        "override_settings_restore_afterwards": True,
        "batch_size": 1,
    }
    payload["alwayson_scripts"] = {
        "controlnet": {
            "args": [
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
                },
                {"enabled": False},
                {"enabled": False},
            ]
        }
    }
    return payload


async def generate(client: httpx.AsyncClient, payload: dict, name: str, output_dir: Path) -> dict:
    print(f"  [{name}] 생성 중...")
    start = time.time()
    resp = await client.post(f"{SD_BASE_URL}/sdapi/v1/txt2img", json=payload, timeout=180.0)
    resp.raise_for_status()
    data = resp.json()
    elapsed = time.time() - start

    images = data.get("images", [])
    if not images:
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
    return {"name": name, "seed": seed, "elapsed": round(elapsed, 1), "file": img_path.name}


async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = EXPERIMENT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"실험 결과 저장: {output_dir}\n")

    # 포즈 사전 로드
    pose_cache: dict[str, str] = {}
    for scene in SCENES:
        pf = scene["pose_file"]
        if pf not in pose_cache:
            p = POSE_DIR / pf
            if p.exists():
                pose_cache[pf] = load_image_b64(p)

    # 이전 실험 레퍼런스 (1-step baseline용)
    prev_ref_path = (
        Path(__file__).parent.parent.parent
        / "experiments"
        / "ip_adapter_consistency"
        / "20260316_220654"
        / "scene_concept_reference.png"
    )
    prev_ref_b64 = load_image_b64(prev_ref_path) if prev_ref_path.exists() else None

    results = []
    step1_refs: dict[str, str] = {}  # scene_id → base64 (Step 1 결과)

    async with httpx.AsyncClient() as client:
        prompt_base = build_prompt("")
        negative = build_negative()

        # ═══ Group A: 1-step baseline (IP-Adapter 0.90 only) ═══
        print("=" * 60)
        print("Group A: 1-step IP-Adapter 0.90 only (baseline)")
        print("=" * 60)

        for scene in SCENES:
            prompt = build_prompt(scene["scene_tags"])
            payload = build_payload_ipa_only(prompt, negative, prev_ref_b64)
            meta = await generate(client, payload, f"A_{scene['id']}", output_dir)
            meta["group"] = "A"
            meta["description"] = f"1-step IPA 0.90: {scene['label']}"
            results.append(meta)

        # ═══ Group B: 2-step pipeline ═══
        print(f"\n{'=' * 60}")
        print("Group B: 2-step pipeline (Step1: CN → Step2: IPA)")
        print("=" * 60)

        for scene in SCENES:
            # Step 1: ControlNet OpenPose → 포즈 정확한 이미지
            prompt = build_prompt(scene["scene_tags"])
            pose_b64 = pose_cache.get(scene["pose_file"])
            if not pose_b64:
                print(f"  포즈 파일 없음: {scene['pose_file']}, 스킵")
                continue

            step1_payload = build_payload_cn_only(prompt, negative, pose_b64)
            step1_name = f"B_{scene['id']}_step1_cn"
            step1_meta = await generate(client, step1_payload, step1_name, output_dir)
            step1_meta["group"] = "B"
            step1_meta["step"] = 1
            step1_meta["description"] = f"Step1 CN: {scene['label']}"
            results.append(step1_meta)

            # Step 1 결과를 레퍼런스로 로드
            step1_path = output_dir / f"{step1_name}.png"
            step1_ref_b64 = load_image_b64(step1_path)
            step1_refs[scene["id"]] = step1_ref_b64

            # Step 2: IP-Adapter 0.90으로 캐릭터 일관성 적용
            step2_payload = build_payload_ipa_only(prompt, negative, step1_ref_b64)
            step2_name = f"B_{scene['id']}_step2_ipa"
            step2_meta = await generate(client, step2_payload, step2_name, output_dir)
            step2_meta["group"] = "B"
            step2_meta["step"] = 2
            step2_meta["description"] = f"Step2 IPA 0.90: {scene['label']}"
            results.append(step2_meta)

        # ═══ Group C: 동일 레퍼런스로 씬 변환 ═══
        print(f"\n{'=' * 60}")
        print("Group C: 2-step 레퍼런스 재활용 (다른 프롬프트)")
        print("=" * 60)

        for var in REUSE_VARIATIONS:
            ref_b64 = step1_refs.get(var["ref_scene_id"])
            if not ref_b64:
                print(f"  레퍼런스 없음: {var['ref_scene_id']}, 스킵")
                continue

            prompt = build_prompt(var["scene_tags"])
            payload = build_payload_ipa_only(prompt, negative, ref_b64)
            name = f"C_{var['ref_scene_id']}_to_new"
            meta = await generate(client, payload, name, output_dir)
            meta["group"] = "C"
            meta["description"] = var["label"]
            meta["ref_from"] = var["ref_scene_id"]
            results.append(meta)

    # 리포트
    report = {
        "experiment": "2-Step 파이프라인: ControlNet(포즈) → IP-Adapter(일관성)",
        "timestamp": timestamp,
        "character": "하린 (ID=44)",
        "pipeline": {
            "step1": "ControlNet OpenPose 1.0 (포즈 정밀 제어, IP-Adapter 없음)",
            "step2": "IP-Adapter 0.90 (Step1 결과를 레퍼런스로, ControlNet 없음)",
        },
        "groups": {
            "A": "1-step baseline (IPA 0.90 only, 카페 레퍼런스)",
            "B": "2-step (CN→IPA) 각 씬별",
            "C": "2-step 레퍼런스 재활용 테스트",
        },
        "results": results,
        "total_images": len(results),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== 실험 완료! 총 {len(results)}장 ===")
    print(f"결과: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
