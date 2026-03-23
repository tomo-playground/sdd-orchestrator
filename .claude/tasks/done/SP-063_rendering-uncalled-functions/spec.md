---
id: SP-063
priority: P1
scope: backend
branch: feat/SP-063-rendering-uncalled-functions
created: 2026-03-23
status: done
depends_on:
label: bug
---

## 무엇을 (What)
CLAUDE.md에 명세되고 함수도 구현되었지만 렌더링 파이프라인에서 실제로 호출되지 않는 4건의 품질 함수를 연결한다.

## 왜 (Why)
Phase 2026-02-14~15에 렌더링 품질 개선으로 함수가 정의되었으나 통합 호출이 누락된 상태다. 결과적으로:
- Post Type에서 얼굴이 잘리는 문제 (detect_face 미호출)
- 밝은 배경에 흰 텍스트가 읽히지 않는 문제 (analyze_text_region_brightness 미호출)
- 씬마다 TTS 음량 편차가 큰 문제 (normalize_audio 호출 불명확)
- 플랫폼 UI와 Scene Text가 겹치는 문제 (platform safe zone 미적용)

## 완료 기준 (DoD)

### 1. Face Detection 연결

- [x] Post Type 렌더링 시 `detect_face()` → `calculate_face_centered_crop()` 호출을 `compose_post_frame()` 또는 해당 scene_processing 경로에 연결한다
- [x] 얼굴 감지 실패 시 기존 크롭 로직(후방 호환)으로 fallback한다
- [x] Post Type 이미지에서 얼굴이 포함된 경우 얼굴 중심 크롭이 적용되는 테스트를 작성한다

### 2. 배경 밝기 기반 텍스트 색상

- [x] Full Type Scene Text 렌더링 시 `analyze_text_region_brightness()`를 호출하여 밝기 > 180이면 검은 텍스트 + 흰 테두리를 적용한다
- [x] `render_scene_text_image()` 호출 시 `background_image` 파라미터가 전달되는지 확인하고, 누락 시 연결한다
- [x] 밝은 배경 이미지에서 텍스트 색상이 자동 전환되는 테스트를 작성한다

### 3. TTS 음량 정규화

- [x] `normalize_audio()` 호출 위치를 확인한다. 미호출이면 TTS 생성 후 `trim_tts_audio()` 파이프라인에 통합한다
- [x] 타겟 레벨 -20dBFS 기준 정규화가 실행되는 테스트를 작성한다

### 4. Platform Safe Zone

- [x] Full Type Scene Text Y좌표 계산 시 `calculate_optimal_scene_text_y(platform)` 호출을 연결한다
- [x] platform 파라미터가 없으면 요청 context에서 추론하거나 기본값("youtube_shorts")을 적용한다
- [x] YouTube Shorts (하단 15% 회피) 기준 Scene Text 위치가 조정되는 테스트를 작성한다

### 통합

- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 영향 분석
- 관련 파일: `backend/services/video/scene_processing.py`, `backend/services/rendering.py`, `backend/services/image.py`, `backend/services/video/tts_postprocess.py`
- 상호작용: 렌더링 파이프라인 전반 — 이미지 크롭, 텍스트 오버레이, 오디오 후처리
- 기존 함수 시그니처 변경 없음 — 호출 추가만

## 제약
- 변경 파일 6개 이하
- 함수 로직 자체는 수정하지 않음 — 호출 연결만
- OpenCV(haar cascade)는 이미 의존성에 포함되어 있음

## 힌트
- `grep -r "detect_face\|analyze_text_region_brightness\|normalize_audio\|calculate_optimal_scene_text_y" backend/services/` 로 현재 호출 위치 확인
- CLAUDE.md "렌더링 품질 개선" 섹션에 각 함수의 명세가 상세히 기술되어 있음
