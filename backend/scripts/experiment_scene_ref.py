"""실험: 배경 + 인물 분리 IP-Adapter.

1패스에서 attn_mask로 영역 분리:
  - 배경 영역 → 환경 레퍼런스 IP-Adapter
  - 인물 영역 → 캐릭터 레퍼런스 IP-Adapter

1인 씬부터 테스트.
"""

import asyncio
import glob
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

COMFYUI_URL = "http://localhost:8188"
INPUT_DIR = Path("/home/tomo/ComfyUI/input")
OUTPUT_DIR = Path("/home/tomo/ComfyUI/output")


def create_character_mask(width: int = 832, height: int = 1216, feather: int = 40):
    """인물 영역 마스크 (중앙 인물 실루엣)."""
    # 인물: 중앙 타원, 상단~하단 80%
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([width * 0.2, height * 0.03, width * 0.8, height * 0.85], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
    mask.save(INPUT_DIR / "mask_character.png")

    # 배경: 인물의 반전
    from PIL import ImageOps

    bg_mask = ImageOps.invert(mask)
    bg_mask.save(INPUT_DIR / "mask_background.png")

    print("  ✅ Character/Background masks created")


def build_workflow(
    char_ref: str,
    bg_ref: str,
    positive: str,
    negative: str,
    seed: int = 42,
    char_weight: float = 0.6,
    bg_weight: float = 0.4,
    char_end_at: float = 0.5,
    bg_end_at: float = 0.8,
) -> dict:
    """배경 + 인물 분리 IP-Adapter (듀얼 체이닝 + attn_mask)."""
    return {
        "ckpt": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "noobaiXLNAIXL_vPred10Version.safetensors"},
        },
        "lora": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "noobai_vpred_1_flat_color_v2.safetensors",
                "strength_model": 0.6,
                "strength_clip": 0.6,
                "model": ["ckpt", 0],
                "clip": ["ckpt", 1],
            },
        },
        "dynthres": {
            "class_type": "DynamicThresholdingFull",
            "inputs": {
                "model": ["lora", 0],
                "mimic_scale": 5.0,
                "threshold_percentile": 1.0,
                "mimic_mode": "Half Cosine Down",
                "mimic_scale_min": 3.0,
                "cfg_mode": "Half Cosine Down",
                "cfg_scale_min": 3.0,
                "sched_val": 1.0,
                "separate_feature_channels": "enable",
                "scaling_startpoint": "MEAN",
                "variability_measure": "AD",
                "interpolate_phi": 1.0,
            },
        },
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["lora", 1]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["lora", 1]}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        # ── 마스크 ──
        "mask_char_img": {"class_type": "LoadImage", "inputs": {"image": "mask_character.png"}},
        "mask_char": {"class_type": "ImageToMask", "inputs": {"image": ["mask_char_img", 0], "channel": "red"}},
        "mask_bg_img": {"class_type": "LoadImage", "inputs": {"image": "mask_background.png"}},
        "mask_bg": {"class_type": "ImageToMask", "inputs": {"image": ["mask_bg_img", 0], "channel": "red"}},
        # ── IP-Adapter 공통 ──
        "ip_model": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"}},
        "clip_vision": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
        },
        # ── 배경 IP-Adapter (환경 레퍼런스 + 배경 마스크) ──
        "bg_ref": {"class_type": "LoadImage", "inputs": {"image": bg_ref}},
        "ip_bg": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["dynthres", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["bg_ref", 0],
                "attn_mask": ["mask_bg", 0],
                "weight": bg_weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": bg_end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── 인물 IP-Adapter (캐릭터 레퍼런스 + 인물 마스크) ──
        "char_ref": {"class_type": "LoadImage", "inputs": {"image": char_ref}},
        "ip_char": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["ip_bg", 0],  # 배경 IP-Adapter 위에 체이닝
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["char_ref", 0],
                "attn_mask": ["mask_char", 0],
                "weight": char_weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": char_end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── Sampler ──
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["ip_char", 0],
                "positive": ["pos", 0],
                "negative": ["neg", 0],
                "latent_image": ["latent", 0],
            },
        },
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"filename_prefix": "SP_scene_ref", "images": ["decode", 0]}},
    }


async def queue_and_wait(workflow: dict, timeout: float = 300) -> str | None:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]
        print(f"  📤 Queued: {prompt_id}")

    start = time.time()
    async with httpx.AsyncClient(timeout=10) as client:
        while time.time() - start < timeout:
            resp = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            data = resp.json()
            if prompt_id in data:
                h = data[prompt_id]
                status = h.get("status", {})
                if status.get("completed"):
                    for out in h.get("outputs", {}).values():
                        if "images" in out:
                            for img in out["images"]:
                                print(f"  ✅ {img['filename']}")
                                return img["filename"]
                    return "__cached__"
                if status.get("status_str") == "error":
                    for m in status.get("messages", []):
                        if m[0] == "execution_error":
                            print(f"  ❌ {m[1].get('node_id')}: {m[1].get('exception_message', '')[:200]}")
                    return None
            await asyncio.sleep(3)
    print("  ⏱️ Timeout")
    return None


async def main():
    print("=" * 60)
    print("🎬 Scene Reference: Background + Character IP-Adapter")
    print("=" * 60)

    create_character_mask()

    # 배경 레퍼런스: 이전에 잘 나온 교실 이미지 사용
    # (없으면 프롬프트만으로 생성)
    bg_ref_candidates = sorted(
        glob.glob(str(OUTPUT_DIR / "SP_2p_pb_base_*.png")),
        key=lambda f: Path(f).stat().st_mtime,
        reverse=True,
    )
    if bg_ref_candidates:
        import shutil

        bg_name = "bg_ref_classroom.png"
        shutil.copy(bg_ref_candidates[0], INPUT_DIR / bg_name)
        print(f"  📂 Background ref: {bg_name}")
    else:
        bg_name = "ip_ref_haeun_sq.png"  # fallback
        print("  ⚠️ No background ref, using character ref as fallback")

    print("\n[Run] Background + Character IP-Adapter (1인 씬)")
    wf = build_workflow(
        char_ref="ip_ref_jaemin_sq.png",
        bg_ref=bg_name,
        positive="masterpiece, best_quality, high_quality, anime coloring, 1boy, standing, looking_at_viewer, school_uniform, classroom, indoors, window, bright, daylight",
        negative="(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic, dark",
        seed=55,
        char_weight=0.6,
        bg_weight=0.3,
        char_end_at=0.5,
        bg_end_at=0.7,
    )
    result = await queue_and_wait(wf)

    print(f"\n{'=' * 60}")
    if result and result != "__cached__":
        print(f"✨ Result: /home/tomo/ComfyUI/output/{result}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
