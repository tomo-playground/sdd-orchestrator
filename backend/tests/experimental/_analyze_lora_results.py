"""LoRA 검증 결과 분석"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path("outputs/lora_emergency_check")

# 이미지 로드
images = [
    ("1. No LoRA (Baseline)", OUTPUT_DIR / "1_no_lora_seed12345.png"),
    ("2. LoRA + Random Seed", OUTPUT_DIR / "2_with_lora_random.png"),
    ("3. LoRA Weight 0.5", OUTPUT_DIR / "3_with_lora_weight05.png"),
    ("4. LoRA + Strong Negative", OUTPUT_DIR / "4_strong_negative.png"),
]

print("=" * 60)
print("📊 LoRA 검증 결과 분석")
print("=" * 60)

for title, path in images:
    if path.exists():
        img = Image.open(path)
        print(f"\n✅ {title}")
        print(f"   Path: {path}")
        print(f"   Size: {img.size}")
    else:
        print(f"\n❌ {title} - 파일 없음")

# 2x2 그리드 생성
print("\n" + "=" * 60)
print("🎨 2x2 비교 이미지 생성 중...")
print("=" * 60)

grid_width = 512 * 2
grid_height = (768 + 50) * 2  # 50px for title
grid = Image.new("RGB", (grid_width, grid_height), "white")
draw = ImageDraw.Draw(grid)

try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
except:
    font = ImageFont.load_default()

positions = [(0, 0), (512, 0), (0, 768 + 50), (512, 768 + 50)]

for (title, path), (x, y) in zip(images, positions):
    if path.exists():
        img = Image.open(path)
        # 제목 추가
        draw.text((x + 10, y + 10), title, fill="black", font=font)
        # 이미지 붙이기
        grid.paste(img, (x, y + 50))

output_path = OUTPUT_DIR / "COMPARISON.png"
grid.save(output_path)
print(f"✅ Saved: {output_path}")

print("\n" + "=" * 60)
print("🔍 분석 가이드")
print("=" * 60)
print("확인 포인트:")
print("  1. Test 1 (No LoRA): 1명만 나오는가?")
print("     → YES: SD 기본 설정은 정상")
print("     → NO: SD 설정 자체에 문제")
print()
print("  2. Test 2-4 (LoRA 사용): 2명이 계속 나오는가?")
print("     → YES: eureka_v9 LoRA 파일이 잘못됨")
print("     → NO: seed 12345의 우연한 문제")
print()
print("  3. 모든 테스트에서 2명이 나온다면:")
print("     → SD WebUI의 기본 설정 확인 필요")
print("     → (예: 'multiple girls' 태그가 기본 프롬프트에 있는지)")
print("=" * 60)
