"""
4컷만화 → 유튜브 쇼츠 영상 변환 스크립트.

SD WebUI로 생성한 4컷 이미지를 9:16 쇼츠 영상으로 렌더링합니다.
- Ken Burns 줌 효과
- 씬 텍스트 오버레이
- 페이드 트랜지션
- 배경음악 (선택)
"""

import base64
import io
import json
import subprocess
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

# === 경로 ===
PROJECT_ROOT = Path(__file__).parent.parent
FONTS_DIR = PROJECT_ROOT / "backend" / "assets" / "fonts"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMP_DIR = OUTPUT_DIR / "manga_frames"

# === SD WebUI ===
SD_BASE_URL = "http://127.0.0.1:7860"
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"

# === 영상 설정 ===
WIDTH = 1080
HEIGHT = 1920
FPS = 30
SCENE_DURATION = 4.0  # 씬당 초
TRANSITION_DURATION = 0.5  # 트랜지션 초
CRF = 20

# === 캐릭터 (Harukaze Doremi) ===
CHARACTER_LORA = "<lora:harukaze-doremi-casual:0.61>"
CHARACTER_TRIGGER = "hrkzdrm_cs"
CHARACTER_TRAITS = "1girl, solo, red_hair, double_bun, purple_eyes"
CHARACTER_OUTFIT = "(white_shirt:1.2), (short_sleeves:1.1), (black_pinafore_dress:1.3)"

REFERENCE_IMAGE_PATH = OUTPUT_DIR / "doremi_reference.png"
REFERENCE_IMAGE_URL = (
    "http://localhost:9000/shorts-producer/characters/9/preview/character_9_preview_c2758c59d041a709.png"
)

# === 스토리 ===
STORY = {
    "title": "첫 요리 도전기",
    "negative_prompt": (
        "lowres, bad anatomy, bad hands, text, error, missing fingers, "
        "extra digit, fewer digits, cropped, worst quality, low quality, "
        "normal quality, jpeg artifacts, signature, watermark, username, blurry, "
        "multiple views, multiple panels, "
        "apron, hoodie, jacket, coat, tank_top, bare_shoulders, strapless"
    ),
    "panels": [
        {
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, smiling, excited, holding_cookbook, "
                "looking_at_viewer, cowboy_shot, bright_lighting, warm_colors"
            ),
            "scene_text": "오늘은 처음으로\n요리에 도전해볼 거야!",
            "ken_burns": "zoom_in_center",
        },
        {
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, crying, cutting_onion, knife, "
                "chopping_board, vegetables, tears, cowboy_shot, warm_lighting"
            ),
            "scene_text": "레시피대로 재료를\n준비했는데...",
            "ken_burns": "pan_up_vertical",
        },
        {
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, panicking, smoke, fire, frying_pan, "
                "open_mouth, scared, cowboy_shot, dramatic_lighting"
            ),
            "scene_text": "불 조절을 잘못해서\n연기가 나기 시작했다",
            "ken_burns": "zoom_in_bottom",
        },
        {
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, sitting, eating, fried_chicken, "
                "happy, relaxed, cowboy_shot, warm_lighting, cozy"
            ),
            "scene_text": "결국 배달앱을\n켜게 되었다...",
            "ken_burns": "zoom_out_center",
        },
    ],
}

# === Ken Burns 프리셋 ===
KEN_BURNS_PRESETS = {
    "zoom_in_center": {
        "z_start": 1.0,
        "z_end": 1.15,
        "x_start": 0.5,
        "x_end": 0.5,
        "y_start": 0.5,
        "y_end": 0.5,
    },
    "zoom_out_center": {
        "z_start": 1.15,
        "z_end": 1.0,
        "x_start": 0.5,
        "x_end": 0.5,
        "y_start": 0.5,
        "y_end": 0.5,
    },
    "pan_up_vertical": {
        "z_start": 1.05,
        "z_end": 1.05,
        "x_start": 0.5,
        "x_end": 0.5,
        "y_start": 0.65,
        "y_end": 0.35,
    },
    "zoom_in_bottom": {
        "z_start": 1.0,
        "z_end": 1.2,
        "x_start": 0.5,
        "x_end": 0.5,
        "y_start": 0.6,
        "y_end": 0.5,
    },
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """한글 폰트 로드."""
    if bold:
        font_path = FONTS_DIR / "BlackHanSans-Regular.ttf"
    else:
        font_path = FONTS_DIR / "NotoSansKR-VariableFont_wght.ttf"
    return ImageFont.truetype(str(font_path), size)


def image_to_b64(img: Image.Image) -> str:
    """PIL Image → base64."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generate_sd_image(
    prompt: str,
    negative_prompt: str,
    seed: int = -1,
    reference_image: Image.Image | None = None,
) -> Image.Image:
    """SD WebUI txt2img (IP-Adapter FaceID 지원)."""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": 28,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": seed,
        "width": 512,
        "height": 768,  # 2:3 비율 (9:16에 적합)
        "batch_size": 1,
    }

    if reference_image is not None:
        ref_b64 = image_to_b64(reference_image)
        payload["alwayson_scripts"] = {
            "controlnet": {
                "args": [
                    {
                        "enabled": True,
                        "input_image": ref_b64,
                        "module": "ip-adapter_face_id_plus",
                        "model": "ip-adapter-faceid-plusv2_sd15 [6e14fc1a]",
                        "weight": 1.1,
                        "guidance_start": 0.0,
                        "guidance_end": 1.0,
                        "control_mode": "Balanced",
                        "resize_mode": "Crop and Resize",
                    }
                ]
            }
        }

    label = "IP-Adapter" if reference_image else "기본"
    print(f"  생성 중... (seed={seed}, {label})")

    with httpx.Client(timeout=180) as client:
        res = client.post(SD_TXT2IMG_URL, json=payload)
        res.raise_for_status()

    data = res.json()
    img_b64 = data["images"][0]
    img = Image.open(io.BytesIO(base64.b64decode(img_b64)))
    info = json.loads(data.get("info", "{}"))
    print(f"  완료! (seed={info.get('seed', seed)})")
    return img


def scale_image_to_frame(img: Image.Image) -> Image.Image:
    """이미지를 1080x1920에 맞게 스케일 (cover 모드, 상단 30% 크롭)."""
    src_w, src_h = img.size
    target_ratio = WIDTH / HEIGHT

    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        x_off = (src_w - new_w) // 2
        img = img.crop((x_off, 0, x_off + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        y_off = int((src_h - new_h) * 0.3)
        img = img.crop((0, y_off, src_w, y_off + new_h))

    return img.resize((WIDTH, HEIGHT), Image.LANCZOS)


def render_scene_text_overlay(text: str) -> Image.Image:
    """씬 텍스트 오버레이 이미지 (투명 배경)."""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(72, bold=True)

    lines = text.split("\n")
    line_height = 90
    total_h = len(lines) * line_height
    y_start = int(HEIGHT * 0.72) - total_h // 2

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (WIDTH - lw) // 2
        y = y_start + i * line_height

        # 반투명 배경 바
        bar_pad = 20
        draw.rounded_rectangle(
            [x - bar_pad, y - 8, x + lw + bar_pad, y + line_height - 12],
            radius=12,
            fill=(0, 0, 0, 140),
        )

        # 외곽선 + 텍스트
        stroke_w = 4
        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if abs(dx) + abs(dy) > 0:
                    draw.text((x + dx, y + dy), line, fill=(0, 0, 0, 255), font=font)
        draw.text((x, y), line, fill=(255, 255, 255, 255), font=font)

    return overlay


def build_zoompan_filter(preset_name: str, frames: int) -> str:
    """Ken Burns zoompan 필터 생성."""
    p = KEN_BURNS_PRESETS[preset_name]
    zs, ze = p["z_start"], p["z_end"]
    xs, xe = p["x_start"], p["x_end"]
    ys, ye = p["y_start"], p["y_end"]

    z_expr = f"({zs}+({ze}-{zs})*on/{frames})"
    x_expr = f"(iw-iw/zoom)*({xs}+({xe}-{xs})*on/{frames})"
    y_expr = f"(ih-ih/zoom)*({ys}+({ye}-{ys})*on/{frames})"

    return f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"


def build_ffmpeg_command(frame_paths: list[Path], output_path: Path) -> list[str]:
    """FFmpeg 명령어 생성 (4씬 + Ken Burns + 트랜지션)."""
    num_scenes = len(frame_paths)
    scene_frames = int(SCENE_DURATION * FPS)

    # 입력 파일
    inputs = []
    for path in frame_paths:
        inputs.extend(["-loop", "1", "-t", str(SCENE_DURATION + 1), "-i", str(path)])

    # 필터 그래프
    filters = []

    # 각 씬: scale → zoompan → trim
    for i, panel in enumerate(STORY["panels"]):
        kb = build_zoompan_filter(panel["ken_burns"], scene_frames)
        filters.append(
            f"[{i}:v]scale={WIDTH}x{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"{kb},"
            f"trim=duration={SCENE_DURATION},setpts=PTS-STARTPTS"
            f"[v{i}]"
        )

    # 트랜지션 체인 (xfade)
    transitions = ["fade", "wipeleft", "circleopen", "dissolve"]
    curr = "[v0]"
    for i in range(1, num_scenes):
        offset = SCENE_DURATION - TRANSITION_DURATION
        t_type = transitions[i - 1]
        out_label = f"[vt{i}]"
        filters.append(
            f"{curr}[v{i}]xfade=transition={t_type}:duration={TRANSITION_DURATION}:offset={offset}{out_label}"
        )
        curr = out_label

    # 최종 비디오에 format 적용
    filters.append(f"{curr}format=yuv420p[vout]")

    filter_complex = ";".join(filters)

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(CRF),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    return cmd


def main():
    """메인 파이프라인."""
    print("=== 4컷만화 → 유튜브 쇼츠 영상 ===\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 레퍼런스 이미지 로드
    if not REFERENCE_IMAGE_PATH.exists():
        print("[레퍼런스] 다운로드 중...")
        with httpx.Client(timeout=30) as client:
            res = client.get(str(REFERENCE_IMAGE_URL))
            res.raise_for_status()
            REFERENCE_IMAGE_PATH.write_bytes(res.content)

    ref_image = Image.open(str(REFERENCE_IMAGE_PATH))
    print(f"[레퍼런스] 로드 완료: {ref_image.size}\n")

    # 2) SD 이미지 생성 + 프레임 합성
    base_seed = 52
    frame_paths = []

    for i, panel in enumerate(STORY["panels"]):
        print(f"[씬 {i + 1}/4] 이미지 생성...")
        sd_img = generate_sd_image(
            prompt=panel["prompt"],
            negative_prompt=STORY["negative_prompt"],
            seed=base_seed + i,
            reference_image=ref_image,
        )

        # 9:16 프레임으로 스케일
        frame = scale_image_to_frame(sd_img)

        # 씬 텍스트 오버레이 합성
        text_overlay = render_scene_text_overlay(panel["scene_text"])
        frame_rgba = frame.convert("RGBA")
        frame_with_text = Image.alpha_composite(frame_rgba, text_overlay)
        frame_final = frame_with_text.convert("RGB")

        # 저장
        frame_path = TEMP_DIR / f"frame_{i}.png"
        frame_final.save(str(frame_path), quality=95)
        frame_paths.append(frame_path)
        print(f"  프레임 저장: {frame_path}\n")

    # 3) FFmpeg로 영상 생성
    output_path = OUTPUT_DIR / "manga_shorts.mp4"
    print("[영상] FFmpeg 렌더링 시작...")

    cmd = build_ffmpeg_command(frame_paths, output_path)
    print(f"  명령어 길이: {len(' '.join(cmd))} chars")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"  FFmpeg 에러:\n{result.stderr[-500:]}")
        return

    # 파일 크기 확인
    size_mb = output_path.stat().st_size / (1024 * 1024)
    total_dur = SCENE_DURATION * 4 - TRANSITION_DURATION * 3
    print("\n=== 완료! ===")
    print(f"  출력: {output_path}")
    print(f"  크기: {size_mb:.1f} MB")
    print(f"  길이: {total_dur:.1f}초")
    print(f"  해상도: {WIDTH}x{HEIGHT} ({FPS}fps)")


if __name__ == "__main__":
    main()
