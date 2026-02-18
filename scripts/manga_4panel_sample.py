"""
4컷만화 샘플 생성 스크립트 (SD WebUI 이미지 포함).

SD WebUI API로 4장의 이미지를 생성한 후
2x2 그리드 4컷만화로 합성합니다.
"""

import base64
import io
import json
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

# 프로젝트 루트 기준 경로
PROJECT_ROOT = Path(__file__).parent.parent
FONTS_DIR = PROJECT_ROOT / "backend" / "assets" / "fonts"
OUTPUT_DIR = PROJECT_ROOT / "output"

# SD WebUI 설정
SD_BASE_URL = "http://127.0.0.1:7860"
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"

# 캔버스 설정
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# 색상
BG_COLOR = (15, 15, 20)
PANEL_BORDER_COLOR = (255, 255, 255)
TITLE_COLOR = (255, 255, 255)
TEXT_COLOR = (255, 255, 255)
TEXT_STROKE_COLOR = (0, 0, 0)
PANEL_NUMBER_COLOR = (255, 220, 100)

# LoRA 설정 (캐릭터 9: Harukaze Doremi)
CHARACTER_LORA = "<lora:harukaze-doremi-casual:0.61>"
CHARACTER_TRIGGER = "hrkzdrm_cs"
CHARACTER_TRAITS = "1girl, solo, red_hair, double_bun, purple_eyes"
CHARACTER_OUTFIT = "(white_shirt:1.2), (short_sleeves:1.1), (black_pinafore_dress:1.3)"

# 레퍼런스 이미지 경로 (캐릭터 프리뷰에서 다운로드)
REFERENCE_IMAGE_PATH = OUTPUT_DIR / "doremi_reference.png"
REFERENCE_IMAGE_URL = (
    "http://localhost:9000/shorts-producer/characters/9/preview/character_9_preview_c2758c59d041a709.png"
)

# 4컷 스토리 정의
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
            "number": 1,
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, smiling, excited, holding_cookbook, "
                "looking_at_viewer, cowboy_shot, bright_lighting, warm_colors"
            ),
            "bubble_text": "유튜브 보면\n쉬워 보이던데...",
            "scene_text": "오늘은 처음으로\n요리에 도전해볼 거야!",
        },
        {
            "number": 2,
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, crying, cutting_onion, knife, "
                "chopping_board, vegetables, tears, cowboy_shot, warm_lighting"
            ),
            "bubble_text": "양파를 왜\n이렇게 많이 썰어야 해?",
            "scene_text": "레시피대로 재료를\n준비했는데...",
        },
        {
            "number": 3,
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, panicking, smoke, fire, frying_pan, "
                "open_mouth, scared, cowboy_shot, dramatic_lighting"
            ),
            "bubble_text": "으악!\n불이야!!!!",
            "scene_text": "불 조절을 잘못해서\n연기가 나기 시작했다",
        },
        {
            "number": 4,
            "prompt": (
                f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
                f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
                "kitchen, sitting, eating, fried_chicken, "
                "happy, relaxed, cowboy_shot, warm_lighting, cozy"
            ),
            "bubble_text": "역시 치킨이\n최고야... ㅎㅎ",
            "scene_text": "결국 배달앱을\n켜게 되었다...",
        },
    ],
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """한글 폰트 로드."""
    if bold:
        font_path = FONTS_DIR / "BlackHanSans-Regular.ttf"
    else:
        font_path = FONTS_DIR / "NotoSansKR-VariableFont_wght.ttf"
    return ImageFont.truetype(str(font_path), size)


def image_to_b64(img: Image.Image) -> str:
    """PIL Image → base64 문자열."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generate_sd_image(
    prompt: str,
    negative_prompt: str,
    seed: int = -1,
    reference_image: Image.Image | None = None,
) -> Image.Image:
    """SD WebUI API로 이미지 생성. reference_image가 있으면 IP-Adapter FaceID 사용."""
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": 28,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": seed,
        "width": 512,
        "height": 512,
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
        print(f"  이미지 생성 중... (seed={seed}, IP-Adapter FaceID)")
    else:
        print(f"  레퍼런스 이미지 생성 중... (seed={seed})")

    with httpx.Client(timeout=180) as client:
        res = client.post(SD_TXT2IMG_URL, json=payload)
        res.raise_for_status()

    data = res.json()
    img_b64 = data["images"][0]
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_bytes))

    info = json.loads(data.get("info", "{}"))
    actual_seed = info.get("seed", seed)
    print(f"  완료! (실제 seed={actual_seed})")
    return img


def smart_crop_panel(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """패널 크기에 맞게 스마트 크롭 (중앙 기준, 상단 약간 우선)."""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # 소스가 더 넓음 → 좌우 크롭
        new_w = int(src_h * target_ratio)
        x_offset = (src_w - new_w) // 2
        img = img.crop((x_offset, 0, x_offset + new_w, src_h))
    else:
        # 소스가 더 높음 → 상하 크롭 (상단 30% 기준)
        new_h = int(src_w / target_ratio)
        y_offset = int((src_h - new_h) * 0.3)
        img = img.crop((0, y_offset, src_w, y_offset + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """텍스트 줄바꿈."""
    lines = []
    for raw_line in text.split("\n"):
        current_line = ""
        for char in raw_line:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] > max_width:
                if current_line:
                    lines.append(current_line)
                current_line = char
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
    return lines


def draw_speech_bubble(
    draw: ImageDraw.Draw,
    text: str,
    center_x: int,
    center_y: int,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> None:
    """말풍선 렌더링."""
    lines = wrap_text(text, font, max_width - 40)
    line_height = font.size + 8
    text_height = len(lines) * line_height
    text_widths = [font.getbbox(line)[2] - font.getbbox(line)[0] for line in lines]
    max_text_width = max(text_widths) if text_widths else 0

    bubble_w = max_text_width + 44
    bubble_h = text_height + 32
    bx = center_x - bubble_w // 2
    by = center_y - bubble_h // 2

    # 말풍선 그림자
    draw.rounded_rectangle(
        [bx + 3, by + 3, bx + bubble_w + 3, by + bubble_h + 3],
        radius=16,
        fill=(0, 0, 0, 80),
    )
    # 말풍선 배경
    draw.rounded_rectangle(
        [bx, by, bx + bubble_w, by + bubble_h],
        radius=16,
        fill=(255, 255, 255, 245),
        outline=(80, 80, 80),
        width=2,
    )
    # 꼬리
    tail_y = by + bubble_h
    draw.polygon(
        [(center_x - 8, tail_y - 2), (center_x + 8, tail_y - 2), (center_x + 4, tail_y + 16)],
        fill=(255, 255, 255, 245),
        outline=(80, 80, 80),
    )
    # 텍스트
    text_y = by + 16
    for line in lines:
        lw = font.getbbox(line)[2] - font.getbbox(line)[0]
        draw.text((center_x - lw // 2, text_y), line, fill=(30, 30, 30), font=font)
        text_y += line_height


def draw_scene_text(
    draw: ImageDraw.Draw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> None:
    """하단 씬 텍스트 (외곽선 포함)."""
    lines = wrap_text(text, font, max_width)
    line_height = font.size + 6

    for i, line in enumerate(lines):
        lw = font.getbbox(line)[2] - font.getbbox(line)[0]
        tx = x + (max_width - lw) // 2
        ty = y + i * line_height
        # 외곽선 (stroke)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text((tx + dx, ty + dy), line, fill=TEXT_STROKE_COLOR, font=font)
        draw.text((tx, ty), line, fill=TEXT_COLOR, font=font)


def create_manga_with_sd() -> str:
    """SD 이미지로 4컷만화 생성."""
    print("=== 4컷만화 생성 시작 ===\n")

    # 1) 캐릭터 레퍼런스 이미지 로드
    base_seed = 42
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not REFERENCE_IMAGE_PATH.exists():
        print("[레퍼런스] 캐릭터 프리뷰 다운로드 중...")
        with httpx.Client(timeout=30) as client:
            res = client.get(str(REFERENCE_IMAGE_URL))
            res.raise_for_status()
            REFERENCE_IMAGE_PATH.write_bytes(res.content)

    ref_image = Image.open(str(REFERENCE_IMAGE_PATH))
    print(f"[레퍼런스] 캐릭터 프리뷰 로드: {ref_image.size}\n")

    # 2) IP-Adapter FaceID로 4장 생성 (얼굴 고정)
    images = []
    for i, panel in enumerate(STORY["panels"]):
        print(f"[패널 {panel['number']}] {panel['prompt'][:50]}...")
        img = generate_sd_image(
            prompt=panel["prompt"],
            negative_prompt=STORY["negative_prompt"],
            seed=base_seed + i + 10,
            reference_image=ref_image,
        )
        images.append(img)
    print()

    # 2) 캔버스 생성
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR + (255,))
    draw = ImageDraw.Draw(canvas)

    # 폰트
    title_font = load_font(56, bold=True)
    panel_num_font = load_font(32, bold=True)
    scene_font = load_font(30)
    bubble_font = load_font(26)

    # 3) 타이틀
    title_text = STORY["title"]
    bbox = title_font.getbbox(title_text)
    title_w = bbox[2] - bbox[0]
    title_x = (CANVAS_WIDTH - title_w) // 2
    title_y = 55

    draw.rounded_rectangle(
        [title_x - 30, title_y - 12, title_x + title_w + 30, title_y + 72],
        radius=14,
        fill=(30, 30, 40, 220),
        outline=PANEL_NUMBER_COLOR,
        width=2,
    )
    draw.text((title_x, title_y), title_text, fill=TITLE_COLOR, font=title_font)

    # 4) 패널 그리드
    grid_top = 160
    grid_bottom = CANVAS_HEIGHT - 50
    grid_left = 30
    grid_right = CANVAS_WIDTH - 30
    gutter = 14

    total_w = grid_right - grid_left
    total_h = grid_bottom - grid_top
    panel_w = (total_w - gutter) // 2
    panel_h = (total_h - gutter) // 2

    positions = [
        (grid_left, grid_top),
        (grid_left + panel_w + gutter, grid_top),
        (grid_left, grid_top + panel_h + gutter),
        (grid_left + panel_w + gutter, grid_top + panel_h + gutter),
    ]

    for i, panel_data in enumerate(STORY["panels"]):
        px, py = positions[i]

        # SD 이미지를 패널 크기로 크롭 & 리사이즈
        panel_img = smart_crop_panel(images[i], panel_w, panel_h)

        # 하단 그라데이션 오버레이 (텍스트 가독성)
        gradient_overlay = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(gradient_overlay)
        gradient_start = int(panel_h * 0.6)
        for y in range(gradient_start, panel_h):
            alpha = int(180 * ((y - gradient_start) / (panel_h - gradient_start)))
            g_draw.line([(0, y), (panel_w, y)], fill=(0, 0, 0, alpha))

        panel_rgba = panel_img.convert("RGBA")
        panel_rgba = Image.alpha_composite(panel_rgba, gradient_overlay)

        # 캔버스에 붙이기
        canvas.paste(panel_rgba, (px, py), panel_rgba)

        # 패널 테두리
        draw.rounded_rectangle(
            [px, py, px + panel_w, py + panel_h],
            radius=10,
            outline=PANEL_BORDER_COLOR,
            width=3,
        )

        # 패널 번호 뱃지
        num_text = str(panel_data["number"])
        draw.rounded_rectangle(
            [px + 10, py + 10, px + 48, py + 46],
            radius=8,
            fill=(0, 0, 0, 200),
            outline=PANEL_NUMBER_COLOR,
            width=2,
        )
        nbbox = panel_num_font.getbbox(num_text)
        nw = nbbox[2] - nbbox[0]
        draw.text((px + 29 - nw // 2, py + 12), num_text, fill=PANEL_NUMBER_COLOR, font=panel_num_font)

        # 말풍선 (상단 1/4 지점)
        draw_speech_bubble(
            draw,
            panel_data["bubble_text"],
            px + panel_w // 2,
            py + panel_h // 4,
            bubble_font,
            panel_w - 60,
        )

        # 씬 텍스트 (하단)
        draw_scene_text(
            draw,
            panel_data["scene_text"],
            px + 20,
            py + panel_h - 100,
            scene_font,
            panel_w - 40,
        )

    # 5) 워터마크
    wm_font = load_font(18)
    wm = "Shorts Producer - 4컷만화"
    wm_bbox = wm_font.getbbox(wm)
    wm_w = wm_bbox[2] - wm_bbox[0]
    draw.text(((CANVAS_WIDTH - wm_w) // 2, CANVAS_HEIGHT - 38), wm, fill=(100, 100, 100), font=wm_font)

    # 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "manga_4panel_sd.png"
    canvas.convert("RGB").save(str(output_path), quality=95)

    print(f"4컷만화 저장 완료: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    create_manga_with_sd()
