"""실험: 2P 진짜 멀티패스 파이프라인 v2.

Python에서 단계 제어 — ComfyUI 워크플로우를 여러 번 큐잉:
  Step 1: ControlNet Pose + 프롬프트 → 베이스 이미지
  Step 2: 베이스 이미지 다운 → Python 얼굴 감지 → 정확한 마스크 생성
  Step 3: 좌측 얼굴 inpaint (IP-Adapter A)
  Step 4: 우측 얼굴 inpaint (IP-Adapter B)
"""

import asyncio
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

COMFYUI_URL = "http://localhost:8188"
INPUT_DIR = Path("/home/tomo/ComfyUI/input")
OUTPUT_DIR = Path("/home/tomo/ComfyUI/output")

# ── 공통 노드 빌더 ──


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


# ── Step 1: 베이스 생성 ──


def build_step1_base(positive: str, negative: str, seed: int = 42) -> dict:
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
                "inputs": {"filename_prefix": "SP_2p_step1_base", "images": ["decode", 0]},
            },
        }
    )
    return nodes


# ── Step 3/4: 얼굴 영역 inpaint ──


def build_step_inpaint(
    base_image: str,
    mask_image: str,
    ref_image: str,
    positive: str,
    negative: str,
    seed: int,
    weight: float = 0.8,
    end_at: float = 0.9,
    denoise: float = 0.5,
    prefix: str = "SP_2p_step_inpaint",
) -> dict:
    nodes = _base_nodes()
    nodes.update(
        {
            "pos": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["lora", 1]}},
            "neg": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["lora", 1]}},
            # 베이스 이미지 로드
            "base_img": {"class_type": "LoadImage", "inputs": {"image": base_image}},
            "encode_base": {"class_type": "VAEEncode", "inputs": {"pixels": ["base_img", 0], "vae": ["ckpt", 2]}},
            # 마스크
            "mask_img": {"class_type": "LoadImage", "inputs": {"image": mask_image}},
            "mask": {"class_type": "ImageToMask", "inputs": {"image": ["mask_img", 0], "channel": "red"}},
            "set_mask": {
                "class_type": "SetLatentNoiseMask",
                "inputs": {"samples": ["encode_base", 0], "mask": ["mask", 0]},
            },
            # IP-Adapter
            "ip_model": {
                "class_type": "IPAdapterModelLoader",
                "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"},
            },
            "clip_vision": {
                "class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
            },
            "ref_img": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
            "ip_apply": {
                "class_type": "IPAdapterAdvanced",
                "inputs": {
                    "model": ["dynthres", 0],
                    "ipadapter": ["ip_model", 0],
                    "clip_vision": ["clip_vision", 0],
                    "image": ["ref_img", 0],
                    "weight": weight,
                    "weight_type": "linear",
                    "start_at": 0.0,
                    "end_at": end_at,
                    "combine_embeds": "concat",
                    "embeds_scaling": "V only",
                },
            },
            # Inpaint
            "sampler": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 20,
                    "cfg": 4.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": denoise,
                    "model": ["ip_apply", 0],
                    "positive": ["pos", 0],
                    "negative": ["neg", 0],
                    "latent_image": ["set_mask", 0],
                },
            },
            "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["ckpt", 2]}},
            "save": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["decode", 0]}},
        }
    )
    return nodes


# ── ComfyUI API ──


async def queue_and_wait(workflow: dict, timeout: float = 300) -> tuple[str | None, dict | None]:
    """워크플로우 큐잉 → 결과 대기. 출력 파일명 반환."""
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
                                filename = img["filename"]
                                print(f"  ✅ {filename}")
                                return filename, h
                    # outputs 비어있어도 completed면 성공 (캐시)
                    print("  ✅ Completed (cached, no new output)")
                    return "__cached__", h
                if status.get("status_str") == "error":
                    for m in status.get("messages", []):
                        if m[0] == "execution_error":
                            print(f"  ❌ {m[1].get('node_id')}: {m[1].get('exception_message', '')[:200]}")
                    return None, h
            await asyncio.sleep(3)
    print("  ⏱️ Timeout")
    return None, None


# ── Step 2: Python 얼굴 감지 ──


def detect_faces_and_create_masks(image_path: str, feather: int = 32) -> list[str]:
    """이미지에서 얼굴 위치 감지 → 마스크 생성.

    anime 얼굴은 일반 face detector가 잘 안 잡으므로,
    이미지를 좌/우 반분할 + 상단 60% 영역으로 마스크 생성.
    (실제 프로덕션에서는 포즈 스켈레톤의 머리 좌표 사용)
    """
    img = Image.open(OUTPUT_DIR / image_path)
    w, h = img.size

    masks = []
    # 좌측 얼굴: 머리~어깨 (crop_factor ~1.8 상당)
    mask_l = Image.new("L", (w, h), 0)
    draw_l = ImageDraw.Draw(mask_l)
    draw_l.ellipse([w * 0.15, h * 0.05, w * 0.42, h * 0.35], fill=255)
    mask_l = mask_l.filter(ImageFilter.GaussianBlur(radius=feather))
    mask_l_path = "mask_detect_left.png"
    mask_l.save(INPUT_DIR / mask_l_path)
    masks.append(mask_l_path)

    # 우측 얼굴: 머리~어깨
    mask_r = Image.new("L", (w, h), 0)
    draw_r = ImageDraw.Draw(mask_r)
    draw_r.ellipse([w * 0.58, h * 0.05, w * 0.85, h * 0.35], fill=255)
    mask_r = mask_r.filter(ImageFilter.GaussianBlur(radius=feather))
    mask_r_path = "mask_detect_right.png"
    mask_r.save(INPUT_DIR / mask_r_path)
    masks.append(mask_r_path)

    print(f"  🎭 Face masks: {masks}")
    return masks


# ── 포즈 이미지 생성 ──


def create_pose_image(width: int = 832, height: int = 1216):
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    def draw_skeleton(d, kps, color):
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
                    d.line([(x1, y1), (x2, y2)], fill=color, width=4)
        for x, y in kps:
            if x > 0:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)

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
    print("  ✅ Pose image created")


# ── Main ──


async def main():
    print("=" * 60)
    print("🎬 2P Multi-Pass Pipeline v2")
    print("=" * 60)

    # Step 1: 베이스 생성
    print("\n[Step 1] Base generation (Pose + Prompt, no IP-Adapter)")
    create_pose_image()
    wf1 = build_step1_base(
        positive="masterpiece, best_quality, high_quality, anime coloring, 2people, 1girl, 1boy, standing, facing_viewer, looking_at_viewer, school_uniform, classroom, indoors, window, bright, daylight",
        negative="(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic, dark, from_behind, back",
        seed=777,
    )
    base_filename, _ = await queue_and_wait(wf1)
    if not base_filename:
        print("❌ Step 1 failed")
        return

    # 캐시된 경우 최신 파일 찾기
    import glob
    import shutil

    if base_filename == "__cached__":
        files = sorted(
            glob.glob(str(OUTPUT_DIR / "SP_2p_step1_base_*.png")), key=lambda f: Path(f).stat().st_mtime, reverse=True
        )
        base_filename = Path(files[0]).name if files else None
        if not base_filename:
            print("❌ No base file found")
            return
        print(f"  📂 Using cached: {base_filename}")

    # output → input 복사 (ComfyUI LoadImage는 input만 읽음)
    shutil.copy(OUTPUT_DIR / base_filename, INPUT_DIR / base_filename)

    # Step 2: 얼굴 감지 → 마스크 생성
    print(f"\n[Step 2] Face detection on {base_filename}")
    masks = detect_faces_and_create_masks(base_filename)

    # Step 3: 좌측 캐릭터 inpaint (재민 — 베이스에서 좌측이 남자)
    print("\n[Step 3] Inpaint LEFT face → 재민")
    wf3 = build_step_inpaint(
        base_image=base_filename,
        mask_image=masks[0],
        ref_image="ip_ref_jaemin_sq.png",
        positive="masterpiece, best_quality, anime coloring, 1boy, face, portrait, facing_viewer",
        negative="(worst quality, low quality:1.4), bad anatomy, 3d, realistic",
        seed=142,
        weight=0.85,
        end_at=1.0,
        denoise=0.65,
        prefix="SP_2p_step3_left",
    )
    left_filename, _ = await queue_and_wait(wf3)
    if not left_filename:
        print("❌ Step 3 failed")
        return
    if left_filename == "__cached__":
        files = sorted(
            glob.glob(str(OUTPUT_DIR / "SP_2p_step3_left_*.png")), key=lambda f: Path(f).stat().st_mtime, reverse=True
        )
        left_filename = Path(files[0]).name if files else None
        if not left_filename:
            print("❌ No left file found")
            return
        print(f"  📂 Using cached: {left_filename}")

    # output → input 복사
    shutil.copy(OUTPUT_DIR / left_filename, INPUT_DIR / left_filename)

    # Step 4: 우측 캐릭터 inpaint (하은 — 베이스에서 우측이 여자)
    print("\n[Step 4] Inpaint RIGHT face → 하은")
    wf4 = build_step_inpaint(
        base_image=left_filename,
        mask_image=masks[1],
        ref_image="ip_ref_haeun_sq.png",
        positive="masterpiece, best_quality, anime coloring, 1girl, face, portrait, facing_viewer",
        negative="(worst quality, low quality:1.4), bad anatomy, 3d, realistic",
        seed=242,
        weight=0.85,
        end_at=1.0,
        denoise=0.65,
        prefix="SP_2p_step4_final",
    )
    final_filename, _ = await queue_and_wait(wf4)

    print(f"\n{'=' * 60}")
    print(f"🎉 Final result: /home/tomo/ComfyUI/output/{final_filename}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
