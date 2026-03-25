# 렌더링 품질 개선 (2026-02-14~15)

> CLAUDE.md에서 분리된 구현 changelog. 코드가 SSOT.

## Layout Type Improvements

### 1. Post Type Scene Text 동적 높이
- `calculate_scene_text_area_height()` — 텍스트 길이별 영역 높이 자동 조정 (12~25%)

### 2. Full Type 플랫폼별 Safe Zone
- `PLATFORM_SAFE_ZONES` — YouTube(15%), TikTok(20%), Instagram(18%) 하단 회피

## Visual Quality Improvements

### 3. Post Type 블러 배경
- Box Blur(15) + Gaussian Blur(20) 조합

### 4. Scene Text 폰트 크기 동적 조정
- `calculate_optimal_font_size()` — 짧은 텍스트 48px, 긴 텍스트 32px, 선형 보간

### 5. 배경 밝기 기반 텍스트 색상
- `analyze_text_region_brightness()` — 밝은 배경: 검은 텍스트, 어두운 배경: 흰 텍스트

### 6. 얼굴 감지 기반 스마트 크롭 (Post Type)
- OpenCV Haar Cascade, `detect_face()` + `calculate_face_centered_crop()`

### 7. TTS 오디오 정규화
- `normalize_audio()` — RMS 기반, 타겟 -20dBFS

### 8. Post Type 해시태그 색상
- Instagram Blue (#0095F6)

## 테스트 커버리지
총 52개 테스트 추가 (Layout 16 + Visual 14 + VRT 8 + Face 8 + TTS 6 + Hashtag 8)
