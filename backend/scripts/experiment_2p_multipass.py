"""실험: 2P 멀티패스 파이프라인.

ComfyUI 파이프라인 핵심 — 한번에 그리지 않고 단계별로 처리:
  1패스: ControlNet Pose + 프롬프트 → 베이스 이미지 (구도/배경)
  2패스: 얼굴 감지 → 좌/우 분리 → 각 얼굴에 IP-Adapter 개별 적용
"""

import asyncio
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

COMFYUI_URL = "http://localhost:8188"
INPUT_DIR = Path("/home/tomo/ComfyUI/input")


def create_pose_image(width: int = 832, height: int = 1216):
    """2인 OpenPose 스켈레톤 이미지 생성."""
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    def draw_skeleton(draw, kps, color):
        conns = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),
            (1, 5),
            (5, 6),
            (6, 7),
            (1, 8),
            (8, 9),
            (9, 10),
            (1, 11),
            (11, 12),
            (12, 13),
        ]
        for i, j in conns:
            if i < len(kps) and j < len(kps):
                x1, y1 = kps[i]
                x2, y2 = kps[j]
                if x1 > 0 and x2 > 0:
                    draw.line([(x1, y1), (x2, y2)], fill=color, width=4)
        for x, y in kps:
            if x > 0:
                draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)

    char_a = [
        (250, 200),
        (250, 350),
        (190, 350),
        (170, 500),
        (160, 620),
        (310, 350),
        (330, 500),
        (340, 620),
        (220, 700),
        (210, 900),
        (200, 1100),
        (280, 700),
        (290, 900),
        (300, 1100),
    ]
    char_b = [
        (580, 220),
        (580, 370),
        (520, 370),
        (500, 520),
        (490, 640),
        (640, 370),
        (660, 520),
        (670, 640),
        (550, 720),
        (540, 920),
        (530, 1120),
        (610, 720),
        (620, 920),
        (630, 1120),
    ]

    draw_skeleton(draw, char_a, (255, 0, 0))
    draw_skeleton(draw, char_b, (0, 0, 255))
    img.save(INPUT_DIR / "pose_2p_standing.png")

    # 얼굴 영역 마스크 생성 (포즈 머리 좌표 기반, feathered)
    def make_face_mask(head_xy, w, h, radius=120, feather=40):
        mask = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mask)
        cx, cy = head_xy
        d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=255)
        return mask.filter(ImageFilter.GaussianBlur(radius=feather))

    make_face_mask(char_a[0], width, height).save(INPUT_DIR / "mask_face_left.png")
    make_face_mask(char_b[0], width, height).save(INPUT_DIR / "mask_face_right.png")
    print("✅ Pose + face masks created")


def build_multipass_workflow(
    ref_a: str,
    ref_b: str,
    positive: str,
    negative: str,
    seed: int = 42,
    ip_weight: float = 0.6,
    ip_end_at: float = 0.6,
    denoise: float = 0.4,
) -> dict:
    """멀티패스 파이프라인 워크플로우.

    1패스: Pose + 프롬프트 → 베이스
    2패스: 얼굴 감지 → x1 정렬 → 좌측 얼굴 SEGS
    3패스: DetailerForEach(좌측, IP-Adapter A)
    4패스: 나머지 얼굴 → DetailerForEach(우측, IP-Adapter B)
    """
    return {
        # ── 공통 로더 ──
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
        # ── 1패스: 베이스 이미지 (Pose + 프롬프트, IP-Adapter 없이) ──
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["lora", 1]}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["lora", 1]}},
        "cn_loader": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "noobaiXLControlnet_openposeModel.safetensors"},
        },
        "cn_pose": {"class_type": "LoadImage", "inputs": {"image": "pose_2p_standing.png"}},
        "cn_apply": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["pos", 0],
                "negative": ["neg", 0],
                "control_net": ["cn_loader", 0],
                "image": ["cn_pose", 0],
                "strength": 0.8,
                "start_percent": 0.0,
                "end_percent": 0.35,
            },
        },
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "sampler_base": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["dynthres", 0],
                "positive": ["cn_apply", 0],
                "negative": ["cn_apply", 1],
                "latent_image": ["latent", 0],
            },
        },
        "decode_base": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["sampler_base", 0], "vae": ["ckpt", 2]},
        },
        # ── 2패스: 포즈 기반 마스크 (감지기 불필요) ──
        "mask_left_img": {"class_type": "LoadImage", "inputs": {"image": "mask_face_left.png"}},
        "mask_left": {"class_type": "ImageToMask", "inputs": {"image": ["mask_left_img", 0], "channel": "red"}},
        "mask_right_img": {"class_type": "LoadImage", "inputs": {"image": "mask_face_right.png"}},
        "mask_right": {"class_type": "ImageToMask", "inputs": {"image": ["mask_right_img", 0], "channel": "red"}},
        # ── 3패스: 좌측 얼굴 → IP-Adapter A (하은) ──
        "ip_model": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"},
        },
        "clip_vision": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
        },
        "ref_a_img": {"class_type": "LoadImage", "inputs": {"image": ref_a}},
        "ip_apply_a": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["dynthres", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["ref_a_img", 0],
                "weight": ip_weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": ip_end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── 3패스: 좌측 inpaint (하은) ──
        "encode_base_a": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["decode_base", 0], "vae": ["ckpt", 2]},
        },
        "set_mask_a": {
            "class_type": "SetLatentNoiseMask",
            "inputs": {"samples": ["encode_base_a", 0], "mask": ["mask_left", 0]},
        },
        "inpaint_a": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed + 100,
                "steps": 20,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": denoise,
                "model": ["ip_apply_a", 0],
                "positive": ["pos", 0],
                "negative": ["neg", 0],
                "latent_image": ["set_mask_a", 0],
            },
        },
        "decode_a": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["inpaint_a", 0], "vae": ["ckpt", 2]},
        },
        # ── 4패스: 우측 inpaint (재민) ──
        "ref_b_img": {"class_type": "LoadImage", "inputs": {"image": ref_b}},
        "ip_apply_b": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["dynthres", 0],
                "ipadapter": ["ip_model", 0],
                "clip_vision": ["clip_vision", 0],
                "image": ["ref_b_img", 0],
                "weight": ip_weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": ip_end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        "encode_base_b": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["decode_a", 0], "vae": ["ckpt", 2]},
        },
        "set_mask_b": {
            "class_type": "SetLatentNoiseMask",
            "inputs": {"samples": ["encode_base_b", 0], "mask": ["mask_right", 0]},
        },
        "inpaint_b": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed + 200,
                "steps": 20,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": denoise,
                "model": ["ip_apply_b", 0],
                "positive": ["pos", 0],
                "negative": ["neg", 0],
                "latent_image": ["set_mask_b", 0],
            },
        },
        "decode_b": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["inpaint_b", 0], "vae": ["ckpt", 2]},
        },
        # ── 출력 ──
        "save": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "SP_2p_multipass", "images": ["decode_b", 0]},
        },
    }


async def queue_and_wait(workflow: dict, timeout: float = 300) -> dict | None:
    import time

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
        resp.raise_for_status()
        prompt_id = resp.json()["prompt_id"]
        print(f"📤 Queued: {prompt_id}")

    start = time.time()
    async with httpx.AsyncClient(timeout=10) as client:
        while time.time() - start < timeout:
            resp = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            data = resp.json()
            if prompt_id in data:
                h = data[prompt_id]
                status = h.get("status", {})
                if status.get("completed"):
                    for nid, out in h.get("outputs", {}).items():
                        if "images" in out:
                            for img in out["images"]:
                                print(f"✅ {img['subfolder']}/{img['filename']}")
                    return h
                if status.get("status_str") == "error":
                    msgs = status.get("messages", [])
                    for m in msgs:
                        if m[0] == "execution_error":
                            print(f"❌ Node: {m[1].get('node_id')} | {m[1].get('exception_message', '')[:200]}")
                    return h
            await asyncio.sleep(3)
    print("⏱️ Timeout")
    return None


async def main():
    create_pose_image()

    workflow = build_multipass_workflow(
        ref_a="ip_ref_haeun_sq.png",
        ref_b="ip_ref_jaemin_sq.png",
        positive="masterpiece, best_quality, high_quality, anime coloring, 2people, 1girl, 1boy, standing, facing_viewer, looking_at_viewer, school_uniform, classroom, indoors, window, bright, daylight",
        negative="(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic, dark, from_behind, back",
        seed=42,
        ip_weight=0.8,
        ip_end_at=0.9,
        denoise=0.5,
    )

    await queue_and_wait(workflow)
    print("\n🎉 완료!")


if __name__ == "__main__":
    asyncio.run(main())
