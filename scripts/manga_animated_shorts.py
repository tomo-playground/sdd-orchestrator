"""
4컷만화 애니메이션 쇼츠 — 만화 스타일 버전.

레퍼런스: 따뜻한 크림 배경 + 말풍선 + 둥근 패널.

연출 구조 (총 ~11초):
0-1.8초   HOOK: 전체 "?" + 내레이션
1.8-4.0초 패널1 공개 + 말풍선
4.0-6.2초 패널2 공개 + 말풍선
6.2-8.4초 패널3 공개 + 말풍선
8.4-10.6초 패널4 공개 + 말풍선 (반전)
10.6-12초 전체 + CTA
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
TEMP_DIR = OUTPUT_DIR / "manga_anim"
BGM_PATH = PROJECT_ROOT / "backend" / "assets" / "audio" / "cute-guitar-music-322164.mp3"

# === SD WebUI ===
SD_TXT2IMG_URL = "http://127.0.0.1:7860/sdapi/v1/txt2img"

# === 영상 설정 ===
W, H = 1080, 1920
FPS = 30
HOOK_DUR = 1.8
PANEL_DUR = 2.2
OUTRO_DUR = 2.0
TRANS_DUR = 0.6

# === 캐릭터 (Midoriya Izuku) ===
CHARACTER_LORA = "<lora:mha_midoriya-10:0.4>"
CHARACTER_TRIGGER = "Midoriya_Izuku"
CHARACTER_TRAITS = "1boy, solo, green_hair, short_hair, messy_hair, green_eyes, freckles"
CHARACTER_OUTFIT = "(white_shirt:1.2), (black_pants:1.1)"

REFERENCE_IMAGE_PATH = OUTPUT_DIR / "midoriya_reference.png"
REFERENCE_IMAGE_URL = (
    "http://localhost:9000/shorts-producer/characters/3/preview/character_3_preview_1c9977f7c6ddf1d9.png"
)

NEGATIVE_PROMPT = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, blurry, "
    "multiple views, multiple panels, easynegative, "
    "1girl, female, skirt, dress, ribbon, bodysuit, hero_costume, cape, mask, gloves"
)

PANELS = [
    {
        "prompt": (
            f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
            f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
            "kitchen, (looking_at_viewer:1.4), (excited:1.2), sparkle, "
            "(open_mouth:1.2), smile, fist_pump, upper_body, bright_lighting, warm_colors"
        ),
        "caption": "오늘은 풀코스 요리에\n도전이다!",
    },
    {
        "prompt": (
            f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
            f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
            "kitchen, (looking_at_viewer:1.4), (tired_eyes:1.2), sweating, "
            "(crying:0.6), holding_knife, onion, upper_body, warm_lighting"
        ),
        "caption": "양파만 벌써\n3시간째...",
    },
    {
        "prompt": (
            f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
            f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
            "kitchen, (looking_at_viewer:1.4), (panicking:1.3), (smoke:1.2), "
            "(fire:1.2), frying_pan, (open_mouth:1.3), scared, upper_body, dramatic_lighting"
        ),
        "caption": "으악!!\n주방이 불바다!!",
    },
    {
        "prompt": (
            f"masterpiece, best_quality, {CHARACTER_TRIGGER}, {CHARACTER_LORA}, "
            f"{CHARACTER_TRAITS}, {CHARACTER_OUTFIT}, "
            "kitchen, (looking_at_viewer:1.4), (smug:1.3), (holding_plate:1.3), "
            "(fried_egg:1.4), proud, closed_mouth, upper_body, bright_lighting"
        ),
        "caption": "완성!\n...계란프라이 1개",
    },
]


# ─── 유틸 ───────────────────────────────────────────


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "BlackHanSans-Regular.ttf" if bold else "NotoSansKR-VariableFont_wght.ttf"
    return ImageFont.truetype(str(FONTS_DIR / name), size)


def img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generate_sd(prompt: str, seed: int, ref: Image.Image) -> Image.Image:
    payload = {
        "prompt": prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "steps": 28,
        "cfg_scale": 7.0,
        "sampler_name": "DPM++ 2M Karras",
        "seed": seed,
        "width": 512,
        "height": 768,
        "batch_size": 1,
        "alwayson_scripts": {
            "controlnet": {
                "args": [
                    {
                        "enabled": True,
                        "image": img_to_b64(ref),
                        "module": "ip-adapter_clip_sd15",
                        "model": "ip-adapter-plus_sd15 [836b5c2e]",
                        "weight": 0.45,
                        "guidance_start": 0.0,
                        "guidance_end": 1.0,
                        "control_mode": "Balanced",
                        "resize_mode": "Crop and Resize",
                    }
                ]
            }
        },
    }
    print(f"    SD 생성 중 (seed={seed})...")
    with httpx.Client(timeout=180) as c:
        r = c.post(SD_TXT2IMG_URL, json=payload)
        r.raise_for_status()
    data = r.json()
    img = Image.open(io.BytesIO(base64.b64decode(data["images"][0])))
    info = json.loads(data.get("info", "{}"))
    print(f"    완료 (seed={info.get('seed', seed)})")
    return img


def smart_crop(img: Image.Image, tw: int, th: int) -> Image.Image:
    """이미지를 목표 비율로 크롭 후 리사이즈."""
    sw, sh = img.size
    tr = tw / th
    sr = sw / sh
    if sr > tr:
        nw = int(sh * tr)
        img = img.crop(((sw - nw) // 2, 0, (sw + nw) // 2, sh))
    else:
        nh = int(sw / tr)
        yo = int((sh - nh) * 0.3)
        img = img.crop((0, yo, sw, yo + nh))
    return img.resize((tw, th), Image.LANCZOS)


# ─── 만화 스타일 레이아웃 ──────────────────────────────

# 색상
BG_COLOR = (248, 243, 235)  # 따뜻한 크림
EMPTY_PANEL_BG = (238, 234, 226)  # 빈 패널
BORDER_COLOR = (55, 55, 55)  # 패널 테두리
BUBBLE_BG = (255, 255, 255)  # 말풍선
BUBBLE_OUTLINE = (55, 55, 55)  # 말풍선 테두리
TEXT_COLOR = (45, 45, 45)  # 텍스트

# 레이아웃
CORNER_R = 18
OUTER_PAD = 40
GRID_TOP = 100
GRID_BOTTOM = 70
GUTTER = 18
PANEL_W = (W - 2 * OUTER_PAD - GUTTER) // 2
PANEL_H = (H - GRID_TOP - GRID_BOTTOM - GUTTER) // 2

POSITIONS = [
    (OUTER_PAD, GRID_TOP),
    (OUTER_PAD + PANEL_W + GUTTER, GRID_TOP),
    (OUTER_PAD, GRID_TOP + PANEL_H + GUTTER),
    (OUTER_PAD + PANEL_W + GUTTER, GRID_TOP + PANEL_H + GUTTER),
]


# ─── 만화 그리기 함수 ─────────────────────────────────


def paste_rounded(canvas: Image.Image, img: Image.Image, x: int, y: int) -> None:
    """라운드 코너 마스크로 이미지 붙이기."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, w - 1, h - 1],
        radius=CORNER_R,
        fill=255,
    )
    canvas.paste(img, (x, y), mask)


def draw_empty_panel(draw: ImageDraw.Draw, idx: int) -> None:
    """빈 패널 — 아직 미공개."""
    px, py = POSITIONS[idx]
    draw.rounded_rectangle(
        [px, py, px + PANEL_W, py + PANEL_H],
        radius=CORNER_R,
        fill=EMPTY_PANEL_BG,
        outline=BORDER_COLOR,
        width=2,
    )
    font = load_font(72, bold=True)
    bbox = font.getbbox("?")
    qw, qh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (px + (PANEL_W - qw) // 2, py + (PANEL_H - qh) // 2 - 20),
        "?",
        fill=(205, 200, 190),
        font=font,
    )


def draw_speech_bubble(draw: ImageDraw.Draw, text: str, idx: int) -> None:
    """만화 스타일 말풍선 (패널 내부 상단)."""
    px, py = POSITIONS[idx]
    font = load_font(30, bold=True)
    lines = text.split("\n")
    line_h = 42

    # 텍스트 폭 측정
    line_widths = []
    for line in lines:
        bbox = font.getbbox(line)
        line_widths.append(bbox[2] - bbox[0])

    max_lw = max(line_widths)
    total_th = len(lines) * line_h

    # 말풍선 크기/위치
    pad_x, pad_y = 30, 18
    bw = max_lw + pad_x * 2
    bh = total_th + pad_y * 2
    bx = px + (PANEL_W - bw) // 2
    by = py + 22

    # 꼬리
    tail_cx = bx + bw // 2
    tail_top = by + bh
    tail_hw, tail_h = 14, 20

    # 1) 채우기 (본체 + 꼬리)
    draw.rounded_rectangle(
        [bx, by, bx + bw, by + bh],
        radius=16,
        fill=BUBBLE_BG,
    )
    draw.polygon(
        [(tail_cx - tail_hw, tail_top - 2), (tail_cx + tail_hw, tail_top - 2), (tail_cx, tail_top + tail_h)],
        fill=BUBBLE_BG,
    )

    # 2) 테두리 (본체)
    draw.rounded_rectangle(
        [bx, by, bx + bw, by + bh],
        radius=16,
        outline=BUBBLE_OUTLINE,
        width=2,
    )

    # 3) 꼬리 테두리 (좌우 선만)
    draw.line(
        [(tail_cx - tail_hw, tail_top), (tail_cx, tail_top + tail_h)],
        fill=BUBBLE_OUTLINE,
        width=2,
    )
    draw.line(
        [(tail_cx + tail_hw, tail_top), (tail_cx, tail_top + tail_h)],
        fill=BUBBLE_OUTLINE,
        width=2,
    )

    # 4) 연결부 덮기
    draw.line(
        [(tail_cx - tail_hw + 2, tail_top), (tail_cx + tail_hw - 2, tail_top)],
        fill=BUBBLE_BG,
        width=4,
    )

    # 5) 텍스트
    ty = by + pad_y
    for i, line in enumerate(lines):
        lw = line_widths[i]
        tx = bx + (bw - lw) // 2
        draw.text((tx, ty), line, fill=TEXT_COLOR, font=font)
        ty += line_h


def draw_narration_box(
    draw: ImageDraw.Draw,
    text: str,
    y: int,
    size: int = 38,
) -> None:
    """내레이션/후킹/CTA 박스 (상단 중앙)."""
    font = load_font(size, bold=True)
    lines = text.split("\n")
    line_h = int(size * 1.4)

    line_widths = [font.getbbox(l)[2] - font.getbbox(l)[0] for l in lines]
    max_lw = max(line_widths)
    total_th = len(lines) * line_h

    pad_x, pad_y = 40, 14
    bw = max_lw + pad_x * 2
    bh = total_th + pad_y * 2
    bx = (W - bw) // 2

    draw.rounded_rectangle(
        [bx, y, bx + bw, y + bh],
        radius=16,
        fill=(255, 250, 230),
        outline=(190, 150, 60),
        width=3,
    )

    ty = y + pad_y
    for i, line in enumerate(lines):
        lw = line_widths[i]
        tx = bx + (bw - lw) // 2
        draw.text((tx, ty), line, fill=(85, 65, 20), font=font)
        ty += line_h


# ─── 6단계 프레임 생성 ────────────────────────────────


def build_stages(sd_images: list[Image.Image]) -> list[Path]:
    """5개 스테이지 프레임 — 결말 선공개형 HOOK."""
    # 결말 선공개: 패널4 먼저 → 1→2→3 순차 공개 → CTA
    stage_config = [
        ({3}, "이게 대체 어떻게...?", 38),  # HOOK: 결말만
        ({0, 3}, None, 0),  # 패널1(기) 공개
        ({0, 1, 3}, None, 0),  # 패널2(승) 공개
        ({0, 1, 2, 3}, None, 0),  # 패널3(전) 공개 → 전체 완성
        ({0, 1, 2, 3}, "다음 도전이 궁금하다면?", 34),  # CTA
    ]
    paths = []

    for stage, (active, narration, nar_size) in enumerate(stage_config):
        canvas = Image.new("RGB", (W, H), BG_COLOR)
        draw = ImageDraw.Draw(canvas)

        for i in range(4):
            if i in active:
                panel = smart_crop(sd_images[i], PANEL_W, PANEL_H)
                px, py = POSITIONS[i]
                paste_rounded(canvas, panel, px, py)
            else:
                draw_empty_panel(draw, i)

        draw = ImageDraw.Draw(canvas)

        for i in range(4):
            if i in active:
                px, py = POSITIONS[i]
                draw.rounded_rectangle(
                    [px, py, px + PANEL_W, py + PANEL_H],
                    radius=CORNER_R,
                    outline=BORDER_COLOR,
                    width=2,
                )
                draw_speech_bubble(draw, PANELS[i]["caption"], i)

        if narration:
            draw_narration_box(draw, narration, y=18, size=nar_size)

        path = TEMP_DIR / f"stage_{stage}.png"
        canvas.save(str(path), quality=95)
        paths.append(path)

    return paths


# ─── FFmpeg ──────────────────────────────────────────


def build_ffmpeg_cmd(
    stage_paths: list[Path],
    bgm: Path | None,
    out: Path,
) -> list[str]:
    durations = [HOOK_DUR, PANEL_DUR, PANEL_DUR, PANEL_DUR + 0.5, OUTRO_DUR]
    num = len(stage_paths)

    inputs: list[str] = []
    for i, p in enumerate(stage_paths):
        inputs.extend(["-loop", "1", "-t", str(durations[i] + 1), "-i", str(p)])
    if bgm and bgm.exists():
        inputs.extend(["-i", str(bgm)])
        bgm_idx = num
    else:
        bgm_idx = None

    filters: list[str] = []

    # 각 스테이지: 미세 줌 + 트림
    for i in range(num):
        dur = durations[i]
        frames = int(dur * FPS)
        zs = 1.0 + 0.006 * i
        ze = zs + 0.012
        filters.append(
            f"[{i}:v]scale={W}x{H},"
            f"zoompan=z='({zs}+({ze}-{zs})*on/{frames})'"
            f":x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.5'"
            f":d={frames}:s={W}x{H}:fps={FPS},"
            f"trim=duration={dur},setpts=PTS-STARTPTS[v{i}]"
        )

    # xfade 체인 (누적 offset)
    curr = "[v0]"
    acc = durations[0]
    for i in range(1, num):
        offset = max(acc - TRANS_DUR, 0.1)
        out_label = f"[vx{i}]"
        filters.append(f"{curr}[v{i}]xfade=transition=dissolve:duration={TRANS_DUR}:offset={offset}{out_label}")
        curr = out_label
        acc += durations[i] - TRANS_DUR

    filters.append(f"{curr}format=yuv420p[vout]")

    # BGM
    if bgm_idx is not None:
        total = acc
        filters.append(
            f"[{bgm_idx}:a]afade=t=in:st=0:d=0.5,"
            f"afade=t=out:st={total - 1.5}:d=1.5,"
            f"atrim=duration={total},volume=0.35[aout]"
        )

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[vout]",
    ]
    if bgm_idx is not None:
        cmd.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    cmd.extend(
        [
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    return cmd


# ─── 메인 ───────────────────────────────────────────


def main():
    print("=== 4컷만화 쇼츠 (만화 스타일) ===\n")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # 레퍼런스
    if not REFERENCE_IMAGE_PATH.exists():
        with httpx.Client(timeout=30) as c:
            r = c.get(str(REFERENCE_IMAGE_URL))
            REFERENCE_IMAGE_PATH.write_bytes(r.content)
    ref = Image.open(str(REFERENCE_IMAGE_PATH))
    print(f"[레퍼런스] {ref.size}\n")

    # SD 이미지 생성
    sd_images = []
    for i, p in enumerate(PANELS):
        print(f"[패널 {i + 1}/4]")
        img = generate_sd(p["prompt"], seed=2024 + i, ref=ref)
        sd_images.append(img)
    print()

    # 6단계 프레임
    print("[프레임] 만화 스타일 6단계 합성 중...")
    stage_paths = build_stages(sd_images)
    print(f"  {len(stage_paths)}장 완료\n")

    # FFmpeg
    bgm = BGM_PATH if BGM_PATH.exists() else None
    output = OUTPUT_DIR / "manga_animated_shorts.mp4"
    print(f"[BGM] {bgm.name if bgm else '없음'}")
    print("[FFmpeg] 렌더링...")
    cmd = build_ffmpeg_cmd(stage_paths, bgm, output)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"  에러:\n{result.stderr[-600:]}")
        return

    size_mb = output.stat().st_size / (1024 * 1024)
    total = HOOK_DUR + PANEL_DUR * 2 + (PANEL_DUR + 0.5) + OUTRO_DUR - TRANS_DUR * 4
    print("\n=== 완료! ===")
    print(f"  출력: {output}")
    print(f"  크기: {size_mb:.1f} MB")
    print(f"  길이: ~{total:.0f}초 ({W}x{H} {FPS}fps)")
    print("  스타일: 만화 말풍선 + 크림 배경")


if __name__ == "__main__":
    main()
