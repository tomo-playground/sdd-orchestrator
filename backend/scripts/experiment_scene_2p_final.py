"""실험: 최종 2P — Attention Couple + BG/Char IP-Adapter 3중 체이닝 + 1024x1024."""

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
W, H = 1024, 1024


def create_masks(feather: int = 40):
    mask_l = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask_l).ellipse([W * 0.02, H * 0.02, W * 0.52, H * 0.95], fill=255)
    mask_l = mask_l.filter(ImageFilter.GaussianBlur(radius=feather))
    mask_l.save(INPUT_DIR / "mf_left.png")

    mask_r = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask_r).ellipse([W * 0.48, H * 0.02, W * 0.98, H * 0.95], fill=255)
    mask_r = mask_r.filter(ImageFilter.GaussianBlur(radius=feather))
    mask_r.save(INPUT_DIR / "mf_right.png")

    combined = Image.new("L", (W, H), 0)
    combined.paste(mask_l, mask=mask_l)
    combined.paste(mask_r, mask=mask_r)
    ImageOps.invert(combined).save(INPUT_DIR / "mf_bg.png")
    print("  ✅ Masks created")


def build(
    char_a: str,
    char_b: str,
    bg: str,
    pos_a: str,
    pos_b: str,
    neg: str,
    seed: int,
    cw: float = 0.6,
    bw: float = 0.3,
    ce: float = 0.5,
    be: float = 0.7,
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
        # ── 마스크 ──
        "ml_img": {"class_type": "LoadImage", "inputs": {"image": "mf_left.png"}},
        "ml": {"class_type": "ImageToMask", "inputs": {"image": ["ml_img", 0], "channel": "red"}},
        "mr_img": {"class_type": "LoadImage", "inputs": {"image": "mf_right.png"}},
        "mr": {"class_type": "ImageToMask", "inputs": {"image": ["mr_img", 0], "channel": "red"}},
        "mb_img": {"class_type": "LoadImage", "inputs": {"image": "mf_bg.png"}},
        "mb": {"class_type": "ImageToMask", "inputs": {"image": ["mb_img", 0], "channel": "red"}},
        # ── Attention Couple: 캐릭터별 프롬프트 영역 분리 ──
        "prompt_a": {"class_type": "CLIPTextEncode", "inputs": {"text": pos_a, "clip": ["lora", 1]}},
        "prompt_b": {"class_type": "CLIPTextEncode", "inputs": {"text": pos_b, "clip": ["lora", 1]}},
        "cond_a": {
            "class_type": "ConditioningSetMask",
            "inputs": {"conditioning": ["prompt_a", 0], "mask": ["ml", 0], "strength": 1.0, "set_cond_area": "default"},
        },
        "cond_b": {
            "class_type": "ConditioningSetMask",
            "inputs": {"conditioning": ["prompt_b", 0], "mask": ["mr", 0], "strength": 1.0, "set_cond_area": "default"},
        },
        "cond_combined": {
            "class_type": "ConditioningCombine",
            "inputs": {"conditioning_1": ["cond_a", 0], "conditioning_2": ["cond_b", 0]},
        },
        "neg_enc": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["lora", 1]}},
        # ── IP-Adapter 공통 ──
        "ip_model": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"}},
        "clip_v": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
        },
        # ── 1. 배경 IP-Adapter ──
        "bg_ref": {"class_type": "LoadImage", "inputs": {"image": bg}},
        "ip_bg": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["dynthres", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_v", 0],
                "image": ["bg_ref", 0],
                "attn_mask": ["mb", 0],
                "weight": bw,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": be,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── 2. 캐릭터 A (하은, 좌) ──
        "ref_a": {"class_type": "LoadImage", "inputs": {"image": char_a}},
        "ip_a": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["ip_bg", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_v", 0],
                "image": ["ref_a", 0],
                "attn_mask": ["ml", 0],
                "weight": cw,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": ce,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── 3. 캐릭터 B (재민, 우) ──
        "ref_b": {"class_type": "LoadImage", "inputs": {"image": char_b}},
        "ip_b": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["ip_a", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_v", 0],
                "image": ["ref_b", 0],
                "attn_mask": ["mr", 0],
                "weight": cw,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": ce,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── Attention Couple 적용 (IP-Adapter 후) ──
        "ac": {
            "class_type": "Attention couple",
            "inputs": {
                "model": ["ip_b", 0],
                "positive": ["cond_combined", 0],
                "negative": ["neg_enc", 0],
                "mode": "Attention",
            },
        },
        # ── Sampler ──
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["ac", 0],
                "positive": ["ac", 1],
                "negative": ["ac", 2],
                "latent_image": ["latent", 0],
            },
        },
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
        "save": {"class_type": "SaveImage", "inputs": {"filename_prefix": "SP_2p_final", "images": ["decode", 0]}},
    }


async def queue_and_wait(wf, timeout=300):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{COMFYUI_URL}/prompt", json={"prompt": wf})
        r.raise_for_status()
        pid = r.json()["prompt_id"]
        print(f"  📤 {pid}")
    t = time.time()
    async with httpx.AsyncClient(timeout=10) as c:
        while time.time() - t < timeout:
            r = await c.get(f"{COMFYUI_URL}/history/{pid}")
            d = r.json()
            if pid in d:
                s = d[pid].get("status", {})
                if s.get("completed"):
                    for o in d[pid].get("outputs", {}).values():
                        if "images" in o:
                            for i in o["images"]:
                                print(f"  ✅ {i['filename']}")
                                return i["filename"]
                    return "__cached__"
                if s.get("status_str") == "error":
                    for m in s.get("messages", []):
                        if m[0] == "execution_error":
                            print(f"  ❌ {m[1].get('node_id')}: {m[1].get('exception_message', '')[:200]}")
                    return None
            await asyncio.sleep(3)
    return None


async def main():
    print("=" * 60)
    print("🎬 Final: AC + BG/Char IP-Adapter 3-chain (1024x1024)")
    print("=" * 60)

    create_masks()

    bg_files = sorted(
        glob.glob(str(OUTPUT_DIR / "SP_2p_pb_base_*.png")), key=lambda f: Path(f).stat().st_mtime, reverse=True
    )
    bg = "bg_ref_classroom.png"
    if bg_files:
        shutil.copy(bg_files[0], INPUT_DIR / bg)

    wf = build(
        char_a="ip_ref_haeun_sq.png",
        char_b="ip_ref_jaemin_sq.png",
        bg=bg,
        pos_a="masterpiece, best_quality, anime coloring, 1girl, young_woman, standing, facing_viewer, school_uniform, classroom, indoors, window, bright",
        pos_b="masterpiece, best_quality, anime coloring, 1boy, young_man, standing, facing_viewer, school_uniform, classroom, indoors, window, bright",
        neg="(worst quality, low quality:1.4), bad anatomy, 3d, realistic, dark, from_behind",
        seed=42,
    )
    r = await queue_and_wait(wf)
    if r and r != "__cached__":
        print(f"\n✨ /home/tomo/ComfyUI/output/{r}")


if __name__ == "__main__":
    asyncio.run(main())
