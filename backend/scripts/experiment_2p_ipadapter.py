"""실험: 2P IP-Adapter with attention masks.

좌/우 반분할 마스크 + 듀얼 IP-Adapter 체이닝 테스트.
ComfyUI API에 직접 워크플로우를 큐잉한다.
"""

import asyncio
import json
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

COMFYUI_URL = "http://localhost:8188"
OUTPUT_DIR = Path("/home/tomo/ComfyUI/output")
INPUT_DIR = Path("/home/tomo/ComfyUI/input")


def create_mask_images(width: int = 832, height: int = 1216, feather: int = 64):
    """좌/우 반분할 마스크 생성 (feathered edges)."""
    # 좌측 마스크: 왼쪽 흰색 → 중앙 페더 → 오른쪽 검정
    mask_left = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask_left)
    # 좌측 절반 + feather 영역까지 흰색
    half = width // 2
    draw.rectangle([0, 0, half + feather // 2, height], fill=255)
    # Gaussian blur로 부드러운 경계
    mask_left = mask_left.filter(ImageFilter.GaussianBlur(radius=feather))

    # 우측 마스크: 좌측의 반전
    from PIL import ImageOps

    mask_right = ImageOps.invert(mask_left)

    # 저장
    mask_left.save(INPUT_DIR / "mask_2p_left.png")
    mask_right.save(INPUT_DIR / "mask_2p_right.png")
    print(f"✅ Masks saved: {width}x{height}, feather={feather}px")
    return "mask_2p_left.png", "mask_2p_right.png"


def build_workflow(
    ref_image_a: str,
    ref_image_b: str,
    mask_left: str,
    mask_right: str,
    positive_a: str = "1girl, brown_hair, ponytail, brown_eyes, school_uniform",
    positive_b: str = "1boy, black_hair, glasses, white_shirt",
    positive_common: str = "masterpiece, best_quality, anime coloring, 2people, classroom, indoors, window",
    negative: str = "(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic",
    weight: float = 0.6,
    end_at: float = 0.6,
    seed: int = 42,
) -> dict:
    """Attention Couple + 듀얼 IP-Adapter + 마스크 워크플로우."""
    return {
        "1_checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "noobaiXLNAIXL_vPred10Version.safetensors"},
        },
        "2_lora_style": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "noobai_vpred_1_flat_color_v2.safetensors",
                "strength_model": 0.6,
                "strength_clip": 0.6,
                "model": ["1_checkpoint", 0],
                "clip": ["1_checkpoint", 1],
            },
        },
        "5_dynthres": {
            "class_type": "DynamicThresholdingFull",
            "inputs": {
                "model": ["2_lora_style", 0],
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
        # ── 마스크 로드 ──
        "mask_left_img": {
            "class_type": "LoadImage",
            "inputs": {"image": mask_left},
        },
        "mask_left": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["mask_left_img", 0], "channel": "red"},
        },
        "mask_right_img": {
            "class_type": "LoadImage",
            "inputs": {"image": mask_right},
        },
        "mask_right": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["mask_right_img", 0], "channel": "red"},
        },
        # ── Attention Couple: 캐릭터별 프롬프트 분리 ──
        "6a_prompt_a": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": f"{positive_common}, {positive_a}", "clip": ["2_lora_style", 1]},
        },
        "6b_prompt_b": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": f"{positive_common}, {positive_b}", "clip": ["2_lora_style", 1]},
        },
        "6c_cond_a_masked": {
            "class_type": "ConditioningSetMask",
            "inputs": {
                "conditioning": ["6a_prompt_a", 0],
                "mask": ["mask_left", 0],
                "strength": 1.0,
                "set_cond_area": "default",
            },
        },
        "6d_cond_b_masked": {
            "class_type": "ConditioningSetMask",
            "inputs": {
                "conditioning": ["6b_prompt_b", 0],
                "mask": ["mask_right", 0],
                "strength": 1.0,
                "set_cond_area": "default",
            },
        },
        "6e_cond_combined": {
            "class_type": "ConditioningCombine",
            "inputs": {
                "conditioning_1": ["6c_cond_a_masked", 0],
                "conditioning_2": ["6d_cond_b_masked", 0],
            },
        },
        "7_negative": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2_lora_style", 1]},
        },
        # ── Attention Couple 적용 (IP-Adapter 후) ──
        "ac_couple": {
            "class_type": "Attention couple",
            "inputs": {
                "model": ["14b_ip_apply", 0],
                "positive": ["6e_cond_combined", 0],
                "negative": ["7_negative", 0],
                "mode": "Attention",
            },
        },
        # ── ControlNet Pose (2인 위치 고정) ──
        "cn_loader": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "noobaiXLControlnet_openposeModel.safetensors"},
        },
        "cn_pose_img": {
            "class_type": "LoadImage",
            "inputs": {"image": "pose_2p_standing.png"},
        },
        "cn_apply": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["ac_couple", 1],
                "negative": ["ac_couple", 2],
                "control_net": ["cn_loader", 0],
                "image": ["cn_pose_img", 0],
                "strength": 0.7,
                "start_percent": 0.0,
                "end_percent": 1.0,
            },
        },
        "8_latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 832, "height": 1216, "batch_size": 1},
        },
        # ── IP-Adapter 공통 로더 ──
        "12_ip_model": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"},
        },
        "12b_clip_vision": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
        },
        # ── IP-Adapter A: 하은 (좌측) ──
        "13a_ref_image": {
            "class_type": "LoadImage",
            "inputs": {"image": ref_image_a},
        },
        "14a_ip_apply": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["5_dynthres", 0],
                "ipadapter": ["12_ip_model", 0],
                "clip_vision": ["12b_clip_vision", 0],
                "image": ["13a_ref_image", 0],
                "attn_mask": ["mask_left", 0],
                "weight": weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── IP-Adapter B: 재민 (우측) ──
        "13b_ref_image": {
            "class_type": "LoadImage",
            "inputs": {"image": ref_image_b},
        },
        "14b_ip_apply": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["14a_ip_apply", 0],
                "ipadapter": ["12_ip_model", 0],
                "clip_vision": ["12b_clip_vision", 0],
                "image": ["13b_ref_image", 0],
                "attn_mask": ["mask_right", 0],
                "weight": weight,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": end_at,
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
            },
        },
        # ── Sampler ──
        "9_sampler": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["ac_couple", 0],
                "positive": ["cn_apply", 0],
                "negative": ["cn_apply", 1],
                "latent_image": ["8_latent", 0],
            },
        },
        "10_decode": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["9_sampler", 0], "vae": ["1_checkpoint", 2]},
        },
        "11_save": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "SP_2p_couple_test", "images": ["10_decode", 0]},
        },
    }


def build_workflow_regional(
    ref_image_a: str,
    ref_image_b: str,
    mask_left: str,
    mask_right: str,
    positive_a: str = "1girl, brown_hair, brown_eyes",
    positive_b: str = "1boy, black_hair, glasses",
    negative: str = "(worst quality, low quality:1.4), bad anatomy, bad hands, 3d, realistic",
    weight: float = 0.6,
    end_at: float = 0.6,
    seed: int = 42,
) -> dict:
    """IPAdapterRegionalConditioning + CombineParams + FromParams.

    공식 Regional IP-Adapter 파이프라인 — 프롬프트 분리 + IP-Adapter 마스크를 단일 패스로 처리.
    """
    return {
        "1_checkpoint": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "noobaiXLNAIXL_vPred10Version.safetensors"},
        },
        "2_lora_style": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "noobai_vpred_1_flat_color_v2.safetensors",
                "strength_model": 0.6,
                "strength_clip": 0.6,
                "model": ["1_checkpoint", 0],
                "clip": ["1_checkpoint", 1],
            },
        },
        "5_dynthres": {
            "class_type": "DynamicThresholdingFull",
            "inputs": {
                "model": ["2_lora_style", 0],
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
        "mask_left_img": {
            "class_type": "LoadImage",
            "inputs": {"image": mask_left},
        },
        "mask_left": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["mask_left_img", 0], "channel": "red"},
        },
        "mask_right_img": {
            "class_type": "LoadImage",
            "inputs": {"image": mask_right},
        },
        "mask_right": {
            "class_type": "ImageToMask",
            "inputs": {"image": ["mask_right_img", 0], "channel": "red"},
        },
        # ── 레퍼런스 이미지 ──
        "ref_a": {
            "class_type": "LoadImage",
            "inputs": {"image": ref_image_a},
        },
        "ref_b": {
            "class_type": "LoadImage",
            "inputs": {"image": ref_image_b},
        },
        # ── 프롬프트 ──
        "prompt_a": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive_a, "clip": ["2_lora_style", 1]},
        },
        "prompt_b": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive_b, "clip": ["2_lora_style", 1]},
        },
        "neg": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2_lora_style", 1]},
        },
        # ── Regional Conditioning A (하은) ──
        "rc_a": {
            "class_type": "IPAdapterRegionalConditioning",
            "inputs": {
                "image": ["ref_a", 0],
                "image_weight": weight,
                "prompt_weight": 1.0,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": end_at,
                "mask": ["mask_left", 0],
                "positive": ["prompt_a", 0],
                "negative": ["neg", 0],
            },
        },
        # ── Regional Conditioning B (재민) ──
        "rc_b": {
            "class_type": "IPAdapterRegionalConditioning",
            "inputs": {
                "image": ["ref_b", 0],
                "image_weight": weight,
                "prompt_weight": 1.0,
                "weight_type": "linear",
                "start_at": 0.0,
                "end_at": end_at,
                "mask": ["mask_right", 0],
                "positive": ["rc_a", 1],  # 체이닝: A의 positive 출력
                "negative": ["rc_a", 2],  # 체이닝: A의 negative 출력
            },
        },
        # ── Combine Params ──
        "params_combined": {
            "class_type": "IPAdapterCombineParams",
            "inputs": {
                "params_1": ["rc_a", 0],
                "params_2": ["rc_b", 0],
            },
        },
        # ── IP-Adapter 로더 ──
        "ip_model": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "NOOB-IPA-MARK1.safetensors"},
        },
        "clip_vision": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"},
        },
        # ── FromParams: 단일 패스 적용 ──
        "ip_apply": {
            "class_type": "IPAdapterFromParams",
            "inputs": {
                "model": ["5_dynthres", 0],
                "ipadapter": ["ip_model", 0],
                "ipadapter_params": ["params_combined", 0],
                "combine_embeds": "concat",
                "embeds_scaling": "V only",
                "clip_vision": ["clip_vision", 0],
            },
        },
        # ── Sampler ──
        "8_latent": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 832, "height": 1216, "batch_size": 1},
        },
        "9_sampler": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 28,
                "cfg": 4.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["ip_apply", 0],
                "positive": ["rc_b", 1],
                "negative": ["rc_b", 2],
                "latent_image": ["8_latent", 0],
            },
        },
        "10_decode": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["9_sampler", 0], "vae": ["1_checkpoint", 2]},
        },
        "11_save": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "SP_2p_regional_test", "images": ["10_decode", 0]},
        },
    }


async def queue_workflow(workflow: dict) -> str:
    """ComfyUI에 워크플로우 큐잉."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow},
        )
        resp.raise_for_status()
        data = resp.json()
        prompt_id = data["prompt_id"]
        print(f"📤 Queued: {prompt_id}")
        return prompt_id


async def wait_for_result(prompt_id: str, timeout: float = 120):
    """결과 대기."""
    import time

    start = time.time()
    async with httpx.AsyncClient(timeout=10) as client:
        while time.time() - start < timeout:
            resp = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            data = resp.json()
            if prompt_id in data:
                history = data[prompt_id]
                status = history.get("status", {})
                if status.get("completed"):
                    outputs = history.get("outputs", {})
                    for node_id, output in outputs.items():
                        if "images" in output:
                            for img in output["images"]:
                                print(f"✅ Result: {img['subfolder']}/{img['filename']}")
                    return history
                if status.get("status_str") == "error":
                    print(f"❌ Error: {json.dumps(status, indent=2, ensure_ascii=False)[:500]}")
                    return history
            await asyncio.sleep(2)
    print("⏱️ Timeout")
    return None


async def main():
    # 1. 마스크 생성
    mask_left, mask_right = create_mask_images()

    # 2. 레퍼런스 이미지
    ref_a = "ip_ref_haeun_sq.png"  # 하은 1024x1024 (좌측)
    ref_b = "ip_ref_jaemin_sq.png"  # 재민 1024x1024 (우측)

    # 3. Attention Couple + 듀얼 IP-Adapter (프롬프트 최소화, IP-Adapter 의존)
    workflow = build_workflow(
        ref_image_a=ref_a,
        ref_image_b=ref_b,
        mask_left=mask_left,
        mask_right=mask_right,
        positive_a="1girl, (brown_eyes:1.2), (dark_brown_hair:1.2), (medium_hair:1.1), (ponytail:1.2), (young_woman:1.15), (navy_cardigan:1.1), (white_blouse:1.2), (id_card:1.1), (lanyard:1.05)",
        positive_b="1boy, (black_hair:1.2), (short_hair:1.1), (glasses:1.3), (white_shirt:1.2), (necktie:1.1), (young_man:1.15)",
        positive_common="masterpiece, best_quality, anime coloring, 2people, standing, classroom, indoors, window, school_uniform",
        weight=0.6,
        end_at=0.6,
        seed=42,
    )

    # 4. 큐잉 & 대기
    prompt_id = await queue_workflow(workflow)
    result = await wait_for_result(prompt_id)

    if result:
        print("\n🎉 실험 완료! ComfyUI output 폴더에서 결과 확인.")


if __name__ == "__main__":
    asyncio.run(main())
