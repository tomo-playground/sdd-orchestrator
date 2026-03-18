# Render Pipeline Specification

**최종 업데이트**: 2026-03-18

## 1. 개요

`backend/services/video/` 패키지의 `VideoBuilder` 클래스를 통해 수행되는 영상 렌더링 파이프라인 명세. FFmpeg 필터 구성, Ken Burns 효과, Scene Text 렌더링, TTS 후처리, 레이아웃 관리 로직을 포함한다.

---

## 2. Pipeline Workflow

영상 생성은 7단계 파이프라인을 거친다 (`VideoBuilder.build()` 메서드):

```
Step 1: Setup Avatars
  → 아바타 파일 준비 (Full/Post 레이아웃용)

Step 2: Process Scenes (씬 루프)
  → 이미지 로드 (MinIO/URL → Pillow)
  → Scene Text 줄바꿈 + 폰트 크기 계산
  → TTS 생성 + 후처리 (정규화, 무음 제거)
  → Post 레이아웃: compose_post_frame (얼굴 감지 크롭 포함)
  → Full 레이아웃: Scene Text 오버레이 이미지 생성

Step 3: Calculate Durations
  → 씬별 표시 시간 계산 (TTS 시간 기반)

Step 4: Prepare BGM
  → File Mode: 정적 파일 / random 선택
  → AI Mode: MusicGen 실시간 생성 (캐시 우선)

Step 5: Build FFmpeg Filters
  → Scale/Crop → Ken Burns → Transition → Scene Text Overlay → Audio

Step 6: Encode
  → FFmpeg 비동기 실행 → MP4 출력

Step 7: Upload
  → 결과 파일 MinIO 등록 + DB Asset 생성
```

---

## 3. 패키지 구조 (`services/video/`)

```
services/video/
├── __init__.py           # 공개 API re-export
├── builder.py            # VideoBuilder 메인 클래스 + create_video_task
├── scene_processing.py   # 씬별 이미지/TTS/오버레이 처리
├── filters.py            # FFmpeg 필터 체인 구성
├── effects.py            # Ken Burns, 전환 효과
├── encoding.py           # FFmpeg 인코딩 설정 + 비동기 실행
├── tts_helpers.py        # TTS 생성 유틸
├── tts_postprocess.py    # TTS 후처리 (정규화, 무음 제거)
├── progress.py           # SSE 진행률 (RenderStage, TaskProgress)
├── upload.py             # 결과 업로드 + DB Asset 등록
└── utils.py              # 유틸 (durations, speed, filename 등)
```

---

## 4. FFmpeg 필터 체인

각 씬의 비디오 트랙 필터링 순서:

```
Input Image → Scale/Crop → Zoompan(Ken Burns) → Trim/Fade → Subtitle Overlay
                                                                    ↓
                                                            Final Concatenation
                                                                    ↑
TTS Audio → Ducking ← BGM Track
```

- **Full Layout 크롭**: 2:3 이미지를 9:16으로 변환 시 상단 30% 지점 기준 크롭 (얼굴 보존)
- **Scene Text 오버레이**: 0.3초 Fade In/Out, Ken Burns 이후 합성 (모션 독립)
- **하단 Safe Zone**: 플랫폼 UI 가독성을 위해 약 70% 지점에 배치

---

## 5. 레이아웃 타입

### 5-1. Full Layout

전체 화면 이미지 + 하단 Scene Text 오버레이.

- **Safe Zone**: 플랫폼별 하단 회피 (YouTube 15%, TikTok 20%, Instagram 18%)
- **Scene Text 위치**: `calculate_optimal_scene_text_y()` — platform 파라미터 지원
- **배경 밝기 기반 텍스트 색상**: `analyze_text_region_brightness()` — 밝은 배경 시 검은 텍스트

#### Scene Text 사양 (1080×1920 기준)

| 항목 | 상수 | 값 | 1920h 환산 |
|------|------|----|-----------|
| 폰트 (base) | `SCENE_TEXT_FONT_RATIO` | 0.042 | 80px |
| 폰트 (min) | `SCENE_TEXT_MIN_FONT_RATIO` | 0.037 | 71px |
| 줄높이 | `SCENE_TEXT_LINE_HEIGHT_RATIO` | 1.35 | 108px (base) ~ 95px (min) |
| 최대 너비 | `SCENE_TEXT_MAX_WIDTH_RATIO` | 0.90 | 972px (화면 90%) |
| 최대 줄수 | `SCENE_TEXT_MAX_LINES` | 3 | — |
| 테두리 | `stroke_width` | 폰트 비례 `max(3, size//16)` | 80px→5, 72px→4 |
| 텍스트 색상 | `SCENE_TEXT_COLOR` | (255,255,255,255) | 흰색 (배경 밝기에 따라 반전) |
| 테두리 색상 | `SCENE_TEXT_STROKE_COLOR` | (0,0,0,255) | 검정 (배경 밝기에 따라 반전) |

> 상수 SSOT: `backend/constants/layout.py` → `FullLayout` 클래스

### 5-2. Post Layout

Instagram 카드 스타일. 이미지 + Scene Text 영역 + Caption 영역.

- **얼굴 감지 크롭**: OpenCV Haar Cascade → `detect_face()` → `calculate_face_centered_crop()`
- **Scene Text 영역 동적 높이**: 텍스트 길이별 12-25% 선형 보간
- **블러 배경**: Box Blur(15) + Gaussian Blur(20) 조합
- **해시태그 색상**: Instagram Blue (#0095F6)

### 5-3. Full vs Post 비교

| 항목 | Full (1080×1920) | Post (1080×1080) |
|------|-----------------|-----------------|
| 폰트 base | 80px (0.042) | 37px (0.034) |
| 폰트 min | 71px (0.037) | 26px (0.024) |
| 줄높이 비율 | 1.35 | 1.35 |
| 최대 너비 | 972px (화면 90%) | 카드 내부 92% |
| 최대 줄수 | 3 | 3 |
| 테두리 | 폰트 비례 `max(3, size//16)` | 0 (외곽선 없음) |
| 텍스트 색상 | 흰색 (배경 밝기 적응) | 검정 (40,40,40) |
| 배치 | 하단 Safe Zone (플랫폼별) | 카드 내 Scene Text 영역 |

---

## 6. TTS Pipeline

### 6-1. 생성

`tts_helpers.py` — Qwen-Audio 등 TTS 엔진으로 씬별 음성 생성.

### 6-2. 후처리 (`tts_postprocess.py`)

5단계 파이프라인:
1. 로드 + 포맷 검증
2. 선행 무음 제거
3. 후행 무음 제거
4. **오디오 정규화** — RMS 기반 dBFS 계산, 타겟 -20dBFS, 클리핑 방지
5. 최종 export

---

## 7. BGM Pipeline

### 7-1. Manual Mode (`bgm_mode="manual"`)

- `music_preset_id` → `MusicPreset` 조회 (우선)
- 캐시 확인: `audio_asset_id` 존재 + 로컬 파일 있으면 즉시 사용
- 없으면: MusicGen으로 실시간 생성 (캐시 우선)
- 폴백: preset 없으면 `bgm_file` 파일 사용 (`"random"` 시 무작위 선택)

### 7-2. Auto Mode (`bgm_mode="auto"`)

- Sound Designer가 생성한 `bgm_prompt`로 자동 BGM 생성
- Storyboard에 저장된 프롬프트 사용

### 7-3. Audio Ducking

TTS 구간에서 BGM 볼륨 자동 감소:
- Threshold: 0.01
- Ratio: `bgm_volume` 비례 (0.2-0.3 수준)
- Release: TTS 종료 후 즉시 복귀

---

## 8. Ken Burns 효과

`effects.py` — 씬별 줌/패닝 효과:

- **프리셋 시스템**: `resolve_preset_name()` → 랜덤/고정 프리셋
- **intensity 범위**: 0.5 ~ 2.0
- **zoompan 필터**: FFmpeg `zoompan` 파라미터로 구현

---

## 9. 진행률 추적

`progress.py`:

| Stage | 설명 |
|-------|------|
| `SETUP_AVATARS` | 아바타 준비 |
| `PROCESS_SCENES` | 씬 처리 (가장 오래 걸림) |
| `CALCULATE_DURATIONS` | 시간 계산 |
| `PREPARE_BGM` | BGM 준비 |
| `BUILD_FILTERS` | 필터 구성 |
| `ENCODE` | FFmpeg 인코딩 |
| `UPLOAD` | 업로드 |
| `COMPLETED` | 완료 |
| `FAILED` | 실패 |

SSE를 통해 Frontend에 실시간 진행률 전달.

---

## 10. 관련 서비스

| 서비스 | 파일 | 역할 |
|--------|------|------|
| `rendering.py` | `services/rendering.py` | Post frame 합성, 오버레이, Scene Text 렌더 |
| `image.py` | `services/image.py` | 이미지 로드, 얼굴 감지, 밝기 분석, Safe Zone |
| `motion.py` | `services/motion.py` | Ken Burns 프리셋 관리 |
| `avatar.py` | `services/avatar.py` | 아바타 파일 관리 |
