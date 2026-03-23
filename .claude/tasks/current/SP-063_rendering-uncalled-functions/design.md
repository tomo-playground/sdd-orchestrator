# SP-063 상세 설계 (How)

> 작성: 2026-03-23 | status: design

## 코드 조사 결과 요약

grep으로 4개 함수의 정의 위치와 전체 호출 위치를 확인한 결과, **spec의 전제("미호출")와 실제 코드 상태가 다르다**. 대부분의 함수는 이미 호출되고 있으며, 실제 갭은 1건(platform 파라미터 미전달)뿐이다.

| 함수 | 정의 위치 | 렌더링 파이프라인 호출 | 상태 |
|------|----------|---------------------|------|
| `detect_face()` + `calculate_face_centered_crop()` | `backend/services/image.py` | `rendering.py:1151-1174` compose_post_frame 내부 | **이미 충족** |
| `analyze_text_region_brightness()` | `backend/services/image.py` | `rendering.py:411-415` + `filters.py:64-75` bg_img_for_color | **이미 충족** |
| `normalize_audio()` | `audio/services/tts_postprocess.py` | `trim_tts_audio()` Step 6에서 호출, `audio/main.py:153` | **이미 충족** |
| `calculate_optimal_scene_text_y(platform=)` | `backend/services/image.py` | `filters.py:99` 호출됨, 단 **platform 미전달** | **부분 미충족** |

---

## DoD-1: Face Detection 연결

### 판정: 이미 충족

**근거:**
- `compose_post_frame()` (rendering.py:1150-1174) 내부에서 `detect_face()` -> `calculate_face_centered_crop()` 호출 체인이 완전히 구현되어 있다.
- 얼굴 감지 실패 시 기존 `ImageOps.fit` 크롭으로 fallback한다 (rendering.py:1168-1174).
- `preview_frame.py:60`에서도 동일하게 호출된다.
- Video 렌더링 시 `scene_processing.py:219` -> `compose_post_frame()` 호출 경로에서 자동 적용된다.

**조치:** 없음. 테스트만 보강하여 회귀 방지.

### 테스트 전략
- 기존 호출 경로가 작동하는지 확인하는 단위 테스트 1건 작성
- `compose_post_frame()` + 얼굴 포함 이미지 -> 크롭 영역에 얼굴 중심이 포함되는지 검증
- `detect_face()` 실패(cv2 미설치 등) 시 fallback 크롭이 동작하는지 검증

### Out of Scope
- `detect_face()` 알고리즘 변경, cascade 파일 교체

---

## DoD-2: 배경 밝기 기반 텍스트 색상

### 판정: 이미 충족

**근거:**
- `render_scene_text_image()` (rendering.py:310-319) 시그니처에 `background_image: Image.Image | None = None` 파라미터가 존재한다.
- rendering.py:410-421에서 `background_image is not None`일 때 `analyze_text_region_brightness()` 호출 -> 밝기 > 180이면 검은 텍스트 + 흰 테두리 적용 로직이 구현되어 있다.
- Video 렌더링 파이프라인의 `_apply_subtitle_overlay` 호출 체인에서 `filters.py:64-75`:
  ```
  bg_img_for_color = scene_img if not builder.use_post_layout else None
  subtitle_img = builder._render_scene_text_image(..., bg_img_for_color)
  ```
  Full layout일 때 scene_img가 `background_image`로 전달된다.
- `preview_frame.py:73-84`에서도 동일하게 호출된다.

**조치:** 없음. 테스트만 보강하여 회귀 방지.

### 테스트 전략
- 밝은 배경 이미지(brightness > 180)로 `render_scene_text_image()` 호출 -> 텍스트 색상이 검정인지 검증
- 어두운 배경 이미지(brightness <= 180) -> 텍스트 색상이 흰색인지 검증
- `background_image=None` -> 기본 흰색 텍스트인지 검증

### Out of Scope
- 밝기 임계값(180) 변경, Post layout 적용 확장

---

## DoD-3: TTS 음량 정규화

### 판정: 이미 충족

**근거:**
- `normalize_audio()`는 **audio 서버** (`audio/services/tts_postprocess.py:127-154`)에 정의되어 있다. backend 서비스가 아니다.
- `trim_tts_audio()` 6단계 파이프라인의 Step 6 (tts_postprocess.py:180-182)에서 `normalize: bool = True` 기본값으로 호출된다.
- `audio/main.py:153`에서 TTS 합성 후 `trim_tts_audio(wavs[0], sr)` 호출 -> normalize 기본 True로 정규화가 적용된다.
- 타겟 레벨은 `-23.0 dBFS` (기본값), 피크 리미팅 `-1.0 dB`로 클리핑 방지.
- spec에 명시된 `-20 dBFS`와 실제 기본값 `-23.0 dBFS`에 차이가 있으나, 이는 CLAUDE.md의 명세가 오래된 것이고 현재 구현이 더 보수적인 값(-23)을 사용 중이다. 값 변경은 이 태스크 범위 밖이다.
- `audio/tests/test_tts_postprocess.py`에 이미 6개 테스트가 존재한다 (`test_normalize_audio_basic`, `test_normalize_audio_clipping`, `test_normalize_audio_silence`, `test_trim_tts_audio_with_normalization`, `test_trim_tts_audio_without_normalization`).

**조치:** 없음. 기존 테스트로 충분히 커버됨.

### Out of Scope
- target_dbfs 값 변경 (-23 -> -20), backend 측 추가 정규화 로직

---

## DoD-4: Platform Safe Zone

### 판정: 부분 미충족 -- 유일한 실제 작업 항목

**현황:**
- `calculate_optimal_scene_text_y()` (image.py:235-282)는 `platform` 파라미터를 받아 `PLATFORM_SAFE_ZONES` 딕셔너리에서 하단 마진을 결정한다.
- 그러나 호출 위치인 `filters.py:99`에서:
  ```python
  y_ratio = builder._calculate_optimal_scene_text_y(img, layout_style=builder.request.layout_style)
  ```
  `platform` 파라미터가 전달되지 않는다. 결과적으로 함수 시그니처의 기본값 `platform="default"`가 사용되고, `PLATFORM_SAFE_ZONES["default"] = 0.15`가 적용된다.
- `VideoRequest` 스키마에 `platform` 필드가 없다.
- `preview_frame.py`에서도 `platform` 미전달.

**실질적 영향:**
- `"default"` safe zone(15%)과 `"youtube_shorts"` safe zone(15%)이 동일한 값이다.
- `"tiktok"` (25%)과 `"instagram_reels"` (18%)만 다른 값을 가진다.
- 현재 서비스가 YouTube Shorts 전용이므로 실질적 차이는 없다. 그러나 향후 멀티 플랫폼 지원 시 필요하다.

### 구현 방법

1. **VideoRequest 스키마 확장** (`backend/schemas.py`):
   - `platform: str = "youtube_shorts"` 필드 추가 (기본값으로 현재 동작 유지)
   - 허용값: `"youtube_shorts"`, `"tiktok"`, `"instagram_reels"`, `"default"`

2. **filters.py:99 수정** (`backend/services/video/filters.py`):
   - `_calc_subtitle_y()` 내부에서 `builder.request.platform` 또는 `"youtube_shorts"`를 platform 인자로 전달
   - 변경 전: `builder._calculate_optimal_scene_text_y(img, layout_style=builder.request.layout_style)`
   - 변경 후: `builder._calculate_optimal_scene_text_y(img, layout_style=builder.request.layout_style, platform=getattr(builder.request, "platform", "youtube_shorts"))`

3. **preview_frame.py 동기화** (`backend/services/preview_frame.py`):
   - `SceneFramePreviewRequest`에도 `platform` 필드가 있으면 전달, 없으면 기본값 사용
   - 이 태스크에서는 `SceneFramePreviewRequest` 수정 없이 기본값 `"youtube_shorts"` 하드코딩으로 충분

### 동작 정의
- Before: platform 무관하게 항상 `default` (15%) safe zone 적용
- After: `VideoRequest.platform` 값에 따라 플랫폼별 safe zone 적용. 기본값 `youtube_shorts` = 15%이므로 기존 동작과 동일

### 엣지 케이스
- `platform` 필드가 `PLATFORM_SAFE_ZONES`에 없는 값이면 -> `dict.get(platform, 0.15)` fallback으로 안전
- `layout_style="post"`일 때 -> `calculate_optimal_scene_text_y`의 post 분기는 platform을 사용하지 않으므로 영향 없음
- 기존 API 호출에서 `platform` 미전달 -> 기본값 `"youtube_shorts"` 적용, 후방 호환 유지

### 영향 범위
- `schemas.py` VideoRequest 필드 추가 -> API 스펙 변경 (선택 필드, 후방 호환)
- `filters.py` _calc_subtitle_y 수정 -> 렌더링 파이프라인 Y좌표 계산에 영향
- Frontend는 변경 불필요 (기본값 사용)

### 테스트 전략
- `_calc_subtitle_y()`에 platform 인자가 전달되는지 mock 검증
- `calculate_optimal_scene_text_y(image, layout_style="full", platform="tiktok")` -> Y좌표가 0.75 이하인지 검증 (25% safe zone)
- `calculate_optimal_scene_text_y(image, layout_style="full", platform="youtube_shorts")` -> Y좌표가 0.85 이하인지 검증 (15% safe zone)
- 기본값(platform 미전달) -> `"default"` safe zone 적용 검증

### Out of Scope
- Frontend에서 platform 선택 UI 추가
- `SceneFramePreviewRequest`에 platform 필드 추가
- `PLATFORM_SAFE_ZONES` 값 자체 조정
- 다른 함수에 platform 파라미터 전파

---

## 통합 테스트 전략

| DoD | 테스트 유형 | 예상 테스트 수 |
|-----|-----------|--------------|
| 1. Face Detection | 단위 (compose_post_frame 회귀 검증) | 2건 |
| 2. 밝기 기반 텍스트 | 단위 (render_scene_text_image 색상 검증) | 3건 |
| 3. TTS 정규화 | 없음 (이미 audio 서버 테스트 존재) | 0건 |
| 4. Platform Safe Zone | 단위 (Y좌표 + platform 전달 검증) | 3건 |
| 통합 | 기존 테스트 regression 확인 | - |

**테스트 파일**: `backend/tests/test_rendering_quality.py` (신규) 또는 기존 테스트 파일에 추가

---

## 변경 파일 목록 (예상)

| 파일 | 변경 내용 |
|------|----------|
| `backend/schemas.py` | `VideoRequest.platform` 필드 추가 |
| `backend/services/video/filters.py` | `_calc_subtitle_y()`에 platform 전달 |
| `backend/tests/test_rendering_quality.py` | DoD 1,2,4 테스트 신규 작성 |

**변경 파일 3개** -- 제약(6개 이하) 충족.

---

## 설계 판단 요약

이 태스크의 원래 전제는 "4건의 품질 함수가 미호출"이었으나, 코드 조사 결과 **3건은 이미 올바르게 호출되고 있다**. 유일한 실제 갭은 DoD-4의 `platform` 파라미터 미전달 1건이며, 이마저도 현재 YouTube Shorts 전용이라 `default`(15%)와 `youtube_shorts`(15%)가 동일 값이므로 **실질적 영향은 없다**.

따라서 이 태스크의 실제 가치는:
1. **코드 정확성 보강**: platform 파라미터를 명시적으로 전달하여 향후 멀티 플랫폼 확장 대비
2. **테스트 보강**: 기존 호출 경로가 유지되는지 회귀 테스트로 방어
3. **CLAUDE.md 명세와 코드 실태의 불일치 해소**: 문서에 "미호출"로 기술된 부분을 "호출 확인됨"으로 정정

**권고**: spec의 DoD를 현실에 맞게 조정하여 진행하거나, 이미 충족된 항목(1-3)은 테스트 보강만 수행하고 실질 작업은 DoD-4에 집중하는 것이 효율적이다.
