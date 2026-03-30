"""실험: 2P Paste & Blend 기법.

정석이 아닌 창작 기법:
  1. 베이스 2P 생성 (포즈+프롬프트)
  2. 레퍼런스 얼굴을 직접 베이스 위에 합성
  3. 합성 이미지를 낮은 denoise로 img2img → 자연스럽게 녹임
  4. IP-Adapter도 함께 걸어서 스타일 일관성 보강

핵심: 모델한테 "이 얼굴을 만들어줘"가 아니라 "이 얼굴을 자연스럽게 녹여줘"
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


def create_pose_image(width: int = 832, height: int = 1216):
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    def skel(d, kps, color):
        for i, j in [
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
        ]:
            if i < len(kps) and j < len(kps):
                x1, y1 = kps[i]
                x2, y2 = kps[j]
                if x1 > 0 and x2 > 0:
                    d.line([(x1, y1), (x2, y2)], fill=color, width=4)
        for x, y in kps:
            if x > 0:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)

    a = [
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
    b = [
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

    skel(draw, a, (255, 0, 0))
    skel(draw, b, (0, 0, 255))
    img.save(INPUT_DIR / "pose_2p_standing.png")


def paste_faces_onto_base(base_path: str, ref_a: str, ref_b: str, face_positions: list[dict]) -> str:
    """레퍼런스 얼굴을 베이스 이미지 위에 직접 합성.

    face_positions: [{"cx": 250, "cy": 180, "size": 140, "ref": "a"}, ...]
    """
    base = Image.open(OUTPUT_DIR / base_path).convert("RGBA")
    ref_a_img = Image.open(INPUT_DIR / ref_a).convert("RGBA")
    ref_b_img = Image.open(INPUT_DIR / ref_b).convert("RGBA")

    # 합성용 마스크도 생성
    composite_mask = Image.new("L", base.size, 0)

    for fp in face_positions:
        ref_img = ref_a_img if fp["ref"] == "a" else ref_b_img

        # 레퍼런스에서 얼굴 영역 크롭 (중앙 상단)
        rw, rh = ref_img.size
        face_crop = ref_img.crop((int(rw * 0.15), int(rh * 0.05), int(rw * 0.85), int(rh * 0.75)))

        # 타겟 크기로 리사이즈
        target_size = fp["size"]
        face_crop = face_crop.resize((target_size, int(target_size * 1.1)), Image.LANCZOS)

        # 원형 마스크 생성 (부드러운 경계)
        fw, fh = face_crop.size
        circle_mask = Image.new("L", (fw, fh), 0)
        draw = ImageDraw.Draw(circle_mask)
        draw.ellipse([fw * 0.05, fh * 0.05, fw * 0.95, fh * 0.95], fill=255)
        circle_mask = circle_mask.filter(ImageFilter.GaussianBlur(radius=15))

        # 붙여넣기 위치
        paste_x = fp["cx"] - fw // 2
        paste_y = fp["cy"] - fh // 2

        # 합성
        base.paste(face_crop, (paste_x, paste_y), circle_mask)

        # 합성 마스크에도 기록 (inpaint 영역)
        mask_draw = ImageDraw.Draw(composite_mask)
        mask_draw.ellipse(
            [paste_x + fw * 0.05, paste_y + fh * 0.05, paste_x + fw * 0.95, paste_y + fh * 0.95], fill=255
        )

    # 합성 마스크 블러
    composite_mask = composite_mask.filter(ImageFilter.GaussianBlur(radius=20))

    # 저장
    pasted_name = "SP_2p_pasted.png"
    base.convert("RGB").save(INPUT_DIR / pasted_name)
    composite_mask.save(INPUT_DIR / "mask_pasted_faces.png")

    print(f"  🎨 Pasted faces: {pasted_name}")
    print("  🎭 Blend mask: mask_pasted_faces.png")
    return pasted_name


def _base_nodes():
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
    }


def build_step1(positive: str, negative: str, seed: int) -> dict:
    nodes = _base_nodes()
    nodes.update(
        {
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
            "sampler": {
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
            "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
            "save": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "SP_2p_pb_base", "images": ["decode", 0]},
            },
        }
    )
    return nodes


def build_blend(
    pasted_image: str, mask_image: str, positive: str, negative: str, seed: int, denoise: float = 0.3
) -> dict:
    """합성 이미지를 낮은 denoise로 블렌딩 — 얼굴을 자연스럽게 녹인다."""
    nodes = _base_nodes()
    nodes.update(
        {
            "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["lora", 1]}},
            "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["lora", 1]}},
            "pasted": {"class_type": "LoadImage", "inputs": {"image": pasted_image}},
            "encode": {"class_type": "VAEEncode", "inputs": {"pixels": ["pasted", 0], "vae": ["ckpt", 2]}},
            "mask_img": {"class_type": "LoadImage", "inputs": {"image": mask_image}},
            "mask": {"class_type": "ImageToMask", "inputs": {"image": ["mask_img", 0], "channel": "red"}},
            "set_mask": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["encode", 0], "mask": ["mask", 0]}},
            "sampler": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 20,
                    "cfg": 4.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": denoise,
                    "model": ["dynthres", 0],
                    "positive": ["pos", 0],
                    "negative": ["neg", 0],
                    "latent_image": ["set_mask", 0],
                },
            },
            "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
            "save": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "SP_2p_pb_final", "images": ["decode", 0]},
            },
        }
    )
    return nodes


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
                    for nid, out in h.get("outputs", {}).items():
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


def resolve_filename(result: str | None, prefix: str) -> str | None:
    if result and result != "__cached__":
        return result
    files = sorted(glob.glob(str(OUTPUT_DIR / f"{prefix}_*.png")), key=lambda f: Path(f).stat().st_mtime, reverse=True)
    return Path(files[0]).name if files else None


async def main():
    print("=" * 60)
    print("🎬 2P Paste & Blend Pipeline")
    print("=" * 60)

    # Step 1: 베이스 생성
    print("\n[Step 1] Base generation")
    create_pose_image()
    wf1 = build_step1(
        positive="masterpiece, best_quality, high_quality, anime coloring, 2people, 1girl, 1boy, standing, facing_viewer, looking_at_viewer, school_uniform, classroom, indoors, window, bright, daylight",
        negative="(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic, dark, from_behind, back",
        seed=1234,
    )
    r1 = await queue_and_wait(wf1)
    base = resolve_filename(r1, "SP_2p_pb_base")
    if not base:
        print("❌ Step 1 failed")
        return

    # Step 2: 레퍼런스 얼굴을 직접 합성
    print(f"\n[Step 2] Paste reference faces onto {base}")
    # 베이스 이미지를 보고 얼굴 위치 지정 (포즈 스켈레톤 기반)
    # 좌=남자(재민), 우=여자(하은) — 포즈 스켈레톤의 머리 좌표 사용
    pasted = paste_faces_onto_base(
        base_path=base,
        ref_a="ip_ref_jaemin_sq.png",  # 좌측=재민
        ref_b="ip_ref_haeun_sq.png",  # 우측=하은
        face_positions=[
            {"cx": 250, "cy": 170, "size": 130, "ref": "a"},  # 좌측 (포즈 char_a 머리)
            {"cx": 580, "cy": 190, "size": 120, "ref": "b"},  # 우측 (포즈 char_b 머리)
        ],
    )

    # Step 3: 블렌딩 — 낮은 denoise로 자연스럽게 녹임
    print("\n[Step 3] Blend pasted faces (low denoise)")
    wf3 = build_blend(
        pasted_image=pasted,
        mask_image="mask_pasted_faces.png",
        positive="masterpiece, best_quality, anime coloring, 2people, school_uniform, classroom, indoors, facing_viewer",
        negative="(worst quality, low quality:1.4), bad anatomy, 3d, realistic",
        seed=1999,
        denoise=0.45,
    )
    r3 = await queue_and_wait(wf3)
    final = resolve_filename(r3, "SP_2p_pb_final")

    print(f"\n{'=' * 60}")
    print(f"🎉 Base: /home/tomo/ComfyUI/output/{base}")
    print(f"🎨 Pasted: /home/tomo/ComfyUI/input/{pasted}")
    print(f"✨ Final: /home/tomo/ComfyUI/output/{final}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
