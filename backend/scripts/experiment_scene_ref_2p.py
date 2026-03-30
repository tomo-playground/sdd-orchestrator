"""실험: 배경 + 2인 분리 IP-Adapter.

3중 체이닝:
  1. 배경 IP-Adapter (배경 마스크)
  2. 캐릭터 A IP-Adapter (좌측 마스크)
  3. 캐릭터 B IP-Adapter (우측 마스크)
"""

import asyncio
import glob
import shutil
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageOps

COMFYUI_URL = "http://localhost:8188"
INPUT_DIR = Path("/home/tomo/ComfyUI/input")
OUTPUT_DIR = Path("/home/tomo/ComfyUI/output")


def create_masks(width: int = 1024, height: int = 1024, feather: int = 40):
    """배경 + 좌측 인물 + 우측 인물 마스크 생성."""
    # 좌측 인물
    mask_l = Image.new("L", (width, height), 0)
    draw_l = ImageDraw.Draw(mask_l)
    draw_l.ellipse([width * 0.05, height * 0.02, width * 0.5, height * 0.85], fill=255)
    mask_l = mask_l.filter(ImageFilter.GaussianBlur(radius=feather))
    mask_l.save(INPUT_DIR / "mask_2p_char_left.png")

    # 우측 인물
    mask_r = Image.new("L", (width, height), 0)
    draw_r = ImageDraw.Draw(mask_r)
    draw_r.ellipse([width * 0.5, height * 0.02, width * 0.95, height * 0.85], fill=255)
    mask_r = mask_r.filter(ImageFilter.GaussianBlur(radius=feather))
    mask_r.save(INPUT_DIR / "mask_2p_char_right.png")

    # 배경: 인물 영역의 반전 (좌+우 합친 것의 반전)
    combined = Image.new("L", (width, height), 0)
    combined.paste(mask_l, mask=mask_l)
    combined.paste(mask_r, mask=mask_r)
    bg_mask = ImageOps.invert(combined)
    bg_mask.save(INPUT_DIR / "mask_2p_bg.png")

    print("  ✅ 3-zone masks created (left/right/bg)")


def build_workflow(
    char_a_ref: str,
    char_b_ref: str,
    bg_ref: str,
    positive: str,
    negative: str,
    seed: int = 42,
    char_weight: float = 0.6,
    bg_weight: float = 0.3,
    char_end_at: float = 0.5,
    bg_end_at: float = 0.7,
) -> dict:
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
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        # ── 마스크 ──
        "m_bg_img": {"class_type": "LoadImage", "inputs": {"image": "mask_2p_bg.png"}},
        "m_bg": {"class_type": "ImageToMask", "inputs": {"image": ["m_bg_img", 0], "channel": "red"}},
        "m_left_img": {"class_type": "LoadImage", "inputs": {"image": "mask_2p_char_left.png"}},
        "m_left": {"class_type": "ImageToMask", "inputs": {"image": ["m_left_img", 0], "channel": "red"}},
        "m_right_img": {"class_type": "LoadImage", "inputs": {"image": "mask_2p_char_right.png"}},
        "m_right": {"class_type": "ImageToMask", "inputs": {"image": ["m_right_img", 0], "channel": "red"}},
        # ── IP-Adapter 공통 ──
        "ip_model": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"}},
        "clip_vision": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
        },
        # ── 1. 배경 IP-Adapter ──
        "bg_ref": {"class_type": "LoadImage", "inputs": {"image": bg_ref}},
        "ip_bg": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["dynthres", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["bg_ref", 0],
                "attn_mask": ["m_bg", 0],
                "weight": bg_weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": bg_end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── 2. 캐릭터 A (하은, 좌측) ──
        "ref_a": {"class_type": "LoadImage", "inputs": {"image": char_a_ref}},
        "ip_a": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["ip_bg", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["ref_a", 0],
                "attn_mask": ["m_left", 0],
                "weight": char_weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": char_end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── 3. 캐릭터 B (재민, 우측) ──
        "ref_b": {"class_type": "LoadImage", "inputs": {"image": char_b_ref}},
        "ip_b": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["ip_a", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["ref_b", 0],
                "attn_mask": ["m_right", 0],
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
                "model": ["ip_b", 0],
                "positive": ["pos", 0],
                "negative": ["neg", 0],
                "latent_image": ["latent", 0],
            },
        },
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"filename_prefix": "SP_scene_2p", "images": ["decode", 0]}},
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
    print("🎬 Scene Reference: BG + 2 Characters (3-chain)")
    print("=" * 60)

    create_masks()

    # 배경 레퍼런스
    bg_candidates = sorted(
        glob.glob(str(OUTPUT_DIR / "SP_2p_pb_base_*.png")), key=lambda f: Path(f).stat().st_mtime, reverse=True
    )
    bg_name = "bg_ref_classroom.png"
    if bg_candidates:
        shutil.copy(bg_candidates[0], INPUT_DIR / bg_name)
    print(f"  📂 BG ref: {bg_name}")

    print("\n[Run] BG + 하은(L) + 재민(R)")
    wf = build_workflow(
        char_a_ref="ip_ref_haeun_sq.png",
        char_b_ref="ip_ref_jaemin_sq.png",
        bg_ref=bg_name,
        positive="masterpiece, best_quality, high_quality, anime coloring, 2people, 1girl, 1boy, standing, facing_viewer, looking_at_viewer, school_uniform, classroom, indoors, window, bright, daylight",
        negative="(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic, dark, from_behind",
        seed=42,
        char_weight=0.6,
        bg_weight=0.3,
        char_end_at=0.5,
        bg_end_at=0.7,
    )
    result = await queue_and_wait(wf)

    print(f"\n{'=' * 60}")
    if result and result != "__cached__":
        print(f"✨ /home/tomo/ComfyUI/output/{result}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
