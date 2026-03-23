"""ComfyUI vs ForgeUI 비교 테스트 스크립트.

동일 프롬프트로 양쪽에서 이미지를 생성하여 비교합니다.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY_URL = "http://localhost:8188"
FORGE_URL = "http://localhost:7860"
OUTPUT_DIR = Path("/tmp/comfy-test")
OUTPUT_DIR.mkdir(exist_ok=True)

# 테스트 프롬프트 (ForgeUI에서 실제 사용하는 스타일)
TEST_PROMPT = "1girl, solo, standing, school_uniform, blue_skirt, white_shirt, short_hair, brown_hair, smile, looking_at_viewer, upper_body, simple_background, masterpiece, best_quality"
TEST_NEGATIVE = (
    "lowres, bad_anatomy, bad_hands, text, error, worst_quality, low_quality, normal_quality, multiple_views"
)
CHECKPOINT = "noobaiXLNAIXL_vPred10Version.safetensors"
SEED = 42
STEPS = 25
CFG = 5.5
WIDTH = 832
HEIGHT = 1216


def test_comfyui():
    """ComfyUI API로 이미지 생성."""
    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": SEED,
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": CHECKPOINT},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": TEST_PROMPT, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": TEST_NEGATIVE, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "comfy_test", "images": ["8", 0]},
        },
    }

    prompt_data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=prompt_data,
        headers={"Content-Type": "application/json"},
    )

    print("[ComfyUI] 이미지 생성 요청...")
    start = time.time()
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        prompt_id = result["prompt_id"]
        print(f"[ComfyUI] prompt_id: {prompt_id}")
    except Exception as e:
        print(f"[ComfyUI] 요청 실패: {e}")
        return False

    # 완료 대기
    for _ in range(120):  # 최대 2분
        time.sleep(1)
        try:
            history_resp = urllib.request.urlopen(f"{COMFY_URL}/history/{prompt_id}")
            history = json.loads(history_resp.read())
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                if "9" in outputs:
                    images = outputs["9"]["images"]
                    elapsed = time.time() - start
                    print(f"[ComfyUI] 생성 완료 ({elapsed:.1f}초)")

                    # 이미지 다운로드
                    for img in images:
                        img_url = f"{COMFY_URL}/view?filename={urllib.parse.quote(img['filename'])}&subfolder={urllib.parse.quote(img.get('subfolder', ''))}&type={img['type']}"
                        img_data = urllib.request.urlopen(img_url).read()
                        out_path = OUTPUT_DIR / f"comfyui_{SEED}.png"
                        out_path.write_bytes(img_data)
                        print(f"[ComfyUI] 저장: {out_path} ({len(img_data) / 1024:.0f}KB)")
                    return True
        except Exception:
            pass

    print("[ComfyUI] 타임아웃 (2분)")
    return False


def test_forgeui():
    """ForgeUI API로 이미지 생성."""
    payload = {
        "prompt": TEST_PROMPT,
        "negative_prompt": TEST_NEGATIVE,
        "seed": SEED,
        "steps": STEPS,
        "cfg_scale": CFG,
        "width": WIDTH,
        "height": HEIGHT,
        "sampler_name": "DPM++ 2M",
        "scheduler": "Karras",
    }

    req = urllib.request.Request(
        f"{FORGE_URL}/sdapi/v1/txt2img",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    print("[ForgeUI] 이미지 생성 요청...")
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        elapsed = time.time() - start
        print(f"[ForgeUI] 생성 완료 ({elapsed:.1f}초)")

        import base64

        for i, img_b64 in enumerate(result.get("images", [])):
            img_data = base64.b64decode(img_b64)
            out_path = OUTPUT_DIR / f"forgeui_{SEED}.png"
            out_path.write_bytes(img_data)
            print(f"[ForgeUI] 저장: {out_path} ({len(img_data) / 1024:.0f}KB)")
        return True
    except Exception as e:
        print(f"[ForgeUI] 실패: {e}")
        return False


if __name__ == "__main__":
    print("=== ComfyUI vs ForgeUI 비교 테스트 ===")
    print(f"Prompt: {TEST_PROMPT[:60]}...")
    print(f"Seed: {SEED}, Steps: {STEPS}, CFG: {CFG}, Size: {WIDTH}x{HEIGHT}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    comfy_ok = test_comfyui()
    print()
    forge_ok = test_forgeui()

    print()
    print("=== 결과 ===")
    print(f"ComfyUI: {'성공' if comfy_ok else '실패'}")
    print(f"ForgeUI: {'성공' if forge_ok else '실패'}")
    if comfy_ok and forge_ok:
        print(f"\n비교: {OUTPUT_DIR}/comfyui_{SEED}.png vs {OUTPUT_DIR}/forgeui_{SEED}.png")
