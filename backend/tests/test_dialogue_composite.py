"""대화형 쇼츠를 위한 캐릭터 분리 생성 + 합성 테스트.

테스트 항목:
1. 캐릭터 일관성: 같은 seed로 다른 표정 생성
2. 배경 제거: rembg로 투명 배경 추출
3. 레이아웃 합성: 좌/우 배치
4. 화자 강조: 밝기/테두리 효과

실행: python -m tests.test_dialogue_composite
"""

from __future__ import annotations

import base64
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

# rembg 설치 여부 확인
try:
    from rembg import remove as remove_bg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("⚠️  rembg 미설치. 배경 제거 테스트 스킵됨. (pip install rembg)")

# 설정
SD_BASE_URL = "http://127.0.0.1:7860"
SD_TXT2IMG_URL = f"{SD_BASE_URL}/sdapi/v1/txt2img"
OUTPUT_DIR = Path("outputs/dialogue_test")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 캐릭터 설정
CHARACTER_BASE = {
    "name": "A",
    "prompt_base": "1girl, solo, short brown hair, blue eyes, school uniform, white shirt, blue skirt",
    "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, multiple girls, 2girls",
}

EMOTIONS = [
    {"name": "happy", "tags": "smile, happy, open mouth, :D"},
    {"name": "surprised", "tags": "surprised, open mouth, wide eyes, :o"},
    {"name": "angry", "tags": "angry, frown, clenched teeth, glaring"},
    {"name": "sad", "tags": "sad, crying, tears, closed eyes"},
]

SD_PARAMS = {
    "width": 512,
    "height": 768,
    "steps": 20,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M",
    "seed": 12345,  # 일관성을 위한 고정 시드
}


def generate_character(emotion: dict, bg_type: str = "white") -> Image.Image | None:
    """SD API로 캐릭터 이미지 생성."""
    bg_prompt = "white background, simple background" if bg_type == "white" else "transparent background"

    prompt = f"{CHARACTER_BASE['prompt_base']}, {emotion['tags']}, {bg_prompt}, upper body, looking at viewer"

    payload = {
        "prompt": prompt,
        "negative_prompt": CHARACTER_BASE["negative"],
        **SD_PARAMS,
    }

    print(f"  📤 생성 중: {emotion['name']}...")

    try:
        with httpx.Client(timeout=120.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()

            if "images" not in data or not data["images"]:
                print(f"  ❌ 이미지 없음")
                return None

            img_b64 = data["images"][0]
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_bytes))
            print(f"  ✅ 생성 완료: {img.size}")
            return img
    except httpx.HTTPError as e:
        print(f"  ❌ SD 연결 실패: {e}")
        return None


def remove_background(img: Image.Image) -> Image.Image:
    """rembg로 배경 제거."""
    if not HAS_REMBG:
        print("  ⚠️  rembg 없음, 원본 반환")
        return img

    print("  🔄 배경 제거 중...")
    result = remove_bg(img)
    print("  ✅ 배경 제거 완료")
    return result


def create_dialogue_composite(
    char_a: Image.Image,
    char_b: Image.Image,
    speaker: str = "A",
    layout: str = "side_by_side",
) -> Image.Image:
    """두 캐릭터를 대화 레이아웃으로 합성.

    Args:
        char_a: 캐릭터 A 이미지
        char_b: 캐릭터 B 이미지
        speaker: 현재 화자 ("A" 또는 "B")
        layout: 레이아웃 타입 ("side_by_side", "overlap")
    """
    # 캔버스 크기 (9:16 세로형)
    canvas_w, canvas_h = 1080, 1920
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (30, 30, 30, 255))

    # 캐릭터 리사이즈 (캔버스의 45% 너비)
    char_w = int(canvas_w * 0.45)

    def resize_char(img: Image.Image) -> Image.Image:
        ratio = char_w / img.width
        new_h = int(img.height * ratio)
        return img.resize((char_w, new_h), Image.Resampling.LANCZOS)

    char_a_resized = resize_char(char_a)
    char_b_resized = resize_char(char_b)

    # 화자 강조 효과
    def apply_speaker_effect(img: Image.Image, is_speaking: bool) -> Image.Image:
        if is_speaking:
            # 밝기 증가
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)
            # 테두리 효과 (glow)
            return img
        else:
            # 어둡게
            enhancer = ImageEnhance.Brightness(img)
            return enhancer.enhance(0.6)

    char_a_final = apply_speaker_effect(char_a_resized, speaker == "A")
    char_b_final = apply_speaker_effect(char_b_resized, speaker == "B")

    # 배치 (좌우)
    y_pos = canvas_h // 2 - char_a_resized.height // 2

    # A는 왼쪽
    canvas.paste(char_a_final, (20, y_pos), char_a_final if char_a_final.mode == "RGBA" else None)
    # B는 오른쪽
    canvas.paste(char_b_final, (canvas_w - char_w - 20, y_pos), char_b_final if char_b_final.mode == "RGBA" else None)

    # 자막 영역
    draw = ImageDraw.Draw(canvas)
    subtitle_y = canvas_h - 200
    draw.rectangle([(0, subtitle_y), (canvas_w, canvas_h)], fill=(0, 0, 0, 180))

    # 화자 표시
    speaker_text = "A" if speaker == "A" else "B"
    draw.text((50, subtitle_y + 30), f"[{speaker_text}]", fill=(255, 255, 100))
    draw.text((50, subtitle_y + 80), "대사가 여기에 표시됩니다.", fill=(255, 255, 255))

    return canvas


def test_character_consistency():
    """테스트 1: 캐릭터 일관성 - 같은 seed로 다른 표정."""
    print("\n" + "=" * 50)
    print("🧪 테스트 1: 캐릭터 일관성")
    print("=" * 50)

    generated = []
    for emotion in EMOTIONS[:2]:  # happy, surprised만 테스트
        img = generate_character(emotion)
        if img:
            path = OUTPUT_DIR / f"char_{emotion['name']}.png"
            img.save(path)
            print(f"  💾 저장: {path}")
            generated.append((emotion["name"], img))

    return generated


def test_background_removal(images: list[tuple[str, Image.Image]]):
    """테스트 2: 배경 제거."""
    print("\n" + "=" * 50)
    print("🧪 테스트 2: 배경 제거")
    print("=" * 50)

    removed = []
    for name, img in images:
        result = remove_background(img)
        path = OUTPUT_DIR / f"char_{name}_nobg.png"
        result.save(path)
        print(f"  💾 저장: {path}")
        removed.append((name, result))

    return removed


def test_dialogue_layout(images: list[tuple[str, Image.Image]]):
    """테스트 3: 대화 레이아웃 합성."""
    print("\n" + "=" * 50)
    print("🧪 테스트 3: 대화 레이아웃 합성")
    print("=" * 50)

    if len(images) < 2:
        print("  ❌ 이미지 2개 필요")
        return

    char_a = images[0][1]
    char_b = images[1][1]

    # A가 말할 때
    composite_a = create_dialogue_composite(char_a, char_b, speaker="A")
    path_a = OUTPUT_DIR / "dialogue_speaker_A.png"
    composite_a.save(path_a)
    print(f"  💾 저장 (A 화자): {path_a}")

    # B가 말할 때
    composite_b = create_dialogue_composite(char_a, char_b, speaker="B")
    path_b = OUTPUT_DIR / "dialogue_speaker_B.png"
    composite_b.save(path_b)
    print(f"  💾 저장 (B 화자): {path_b}")


def test_second_character():
    """테스트 4: 두 번째 캐릭터 (다른 외모)."""
    print("\n" + "=" * 50)
    print("🧪 테스트 4: 두 번째 캐릭터 생성")
    print("=" * 50)

    # 다른 캐릭터 설정
    char_b_base = "1girl, solo, long black hair, red eyes, casual clothes, hoodie"

    payload = {
        "prompt": f"{char_b_base}, smile, white background, simple background, upper body, looking at viewer",
        "negative_prompt": CHARACTER_BASE["negative"],
        **SD_PARAMS,
        "seed": 54321,  # 다른 시드
    }

    print("  📤 캐릭터 B 생성 중...")

    try:
        with httpx.Client(timeout=120.0) as client:
            res = client.post(SD_TXT2IMG_URL, json=payload)
            res.raise_for_status()
            data = res.json()

            if "images" in data and data["images"]:
                img_b64 = data["images"][0]
                img_bytes = base64.b64decode(img_b64)
                img = Image.open(BytesIO(img_bytes))

                path = OUTPUT_DIR / "char_B_happy.png"
                img.save(path)
                print(f"  ✅ 저장: {path}")

                # 배경 제거
                if HAS_REMBG:
                    img_nobg = remove_background(img)
                    path_nobg = OUTPUT_DIR / "char_B_happy_nobg.png"
                    img_nobg.save(path_nobg)
                    print(f"  💾 저장 (배경 제거): {path_nobg}")
                    return img_nobg
                return img
    except httpx.HTTPError as e:
        print(f"  ❌ 실패: {e}")
        return None


def test_two_different_characters():
    """테스트 5: 서로 다른 두 캐릭터로 대화 장면."""
    print("\n" + "=" * 50)
    print("🧪 테스트 5: 서로 다른 캐릭터 대화 장면")
    print("=" * 50)

    # 캐릭터 A
    char_a_img = generate_character({"name": "neutral", "tags": "neutral expression"})
    if not char_a_img:
        print("  ❌ 캐릭터 A 생성 실패")
        return

    # 캐릭터 B (다른 외모)
    char_b_img = test_second_character()
    if not char_b_img:
        print("  ❌ 캐릭터 B 생성 실패")
        return

    # 배경 제거
    if HAS_REMBG:
        char_a_nobg = remove_background(char_a_img)
        char_b_nobg = char_b_img if char_b_img.mode == "RGBA" else remove_background(char_b_img)
    else:
        char_a_nobg = char_a_img
        char_b_nobg = char_b_img

    # 합성
    composite = create_dialogue_composite(char_a_nobg, char_b_nobg, speaker="A")
    path = OUTPUT_DIR / "dialogue_two_chars.png"
    composite.save(path)
    print(f"  ✅ 최종 합성 저장: {path}")


def check_sd_connection():
    """SD WebUI 연결 확인."""
    print("\n🔌 SD WebUI 연결 확인...")
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SD_BASE_URL}/sdapi/v1/options")
            res.raise_for_status()
            data = res.json()
            model = data.get("sd_model_checkpoint", "Unknown")
            print(f"  ✅ 연결됨 - 모델: {model}")
            return True
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        print("  💡 SD WebUI를 --api 옵션으로 실행하세요")
        return False


def main():
    print("🎬 대화형 쇼츠 캐릭터 합성 테스트")
    print("=" * 50)

    if not check_sd_connection():
        sys.exit(1)

    # 테스트 실행
    images = test_character_consistency()

    if images:
        nobg_images = test_background_removal(images)
        test_dialogue_layout(nobg_images)

    test_two_different_characters()

    print("\n" + "=" * 50)
    print(f"✅ 테스트 완료! 결과: {OUTPUT_DIR}/")
    print("=" * 50)


if __name__ == "__main__":
    main()
