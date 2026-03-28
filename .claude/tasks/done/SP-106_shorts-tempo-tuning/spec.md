---
id: SP-106
priority: P0
scope: backend
branch: feat/SP-106-shorts-tempo-tuning
created: 2026-03-28
status: done
approved_at: 2026-03-28
depends_on:
label: enhancement
---

## 상세 설계 (How)

> [design.md](./design.md) 참조 (설계 승인 후 작성)

## 무엇을 (What)
쇼츠 영상의 전반적 템포를 높여 시청 유지율에 적합한 빠른 페이싱으로 개선.

## 왜 (Why)
2026-03-28 다수 시연에서 **"전반적으로 템포가 너무 느리다"** 공통 피드백.
쇼츠는 첫 2초에 이탈이 결정되는 포맷 — 현재 기본 설정이 일반 영상 수준의 느긋한 페이싱으로 되어 있어 쇼츠 특성에 맞지 않음.

## 근본 원인 분석

### C1. 한국어 읽기 속도 과소 추정
- **위치**: `config.py` — `READING_SPEED["korean"]["cps"] = 4.0`
- **현상**: 실제 쇼츠 나레이션은 6~8 cps가 일반적. 4.0은 강의/다큐 수준
- **영향**: TTS 기반 씬 듀레이션이 필요 이상으로 길어짐

### C2. 씬 간 여백(패딩)이 과다
- **위치**: `config.py` — `READING_DURATION_PADDING = 0.5`
- **위치**: `services/video/utils.py` — `tts_padding = 0.8 / speed`
- **현상**: 매 씬마다 0.5초 읽기 패딩 + 0.8초 TTS 패딩 = 1.3초 무음/여백
- **영향**: 10씬 기준 ~13초가 여백 — 30초 쇼츠의 43%

### C3. 씬 듀레이션 범위가 넓음
- **위치**: `config.py` — `SCENE_DURATION_RANGE = (2.0, 3.5)`, `SCENE_DEFAULT_DURATION = 3.0`
- **현상**: 상한 3.5초, 기본 3.0초는 쇼츠 평균(1.5~2.5초)보다 높음
- **영향**: 씬 전환이 느려 시청자 집중력 이탈

### C4. 트랜지션 듀레이션 여유
- **위치**: `services/video/utils.py` — `transition_dur = 0.5 / speed`
- **현상**: speed=1.0 기준 0.5초 크로스페이드
- **영향**: 장면 전환에 체감 지연

## 완료 기준 (DoD)

### Must (P0)
- [ ] `READING_SPEED["korean"]["cps"]` 상향: 4.0 → 6.0
- [ ] `READING_DURATION_PADDING` 하향: 0.5 → 0.2
- [ ] `tts_padding` 기본값 하향: 0.8 → 0.4 (in `calculate_speed_params`)
- [ ] `SCENE_DURATION_RANGE` 조정: (2.0, 3.5) → (1.5, 2.5)
- [ ] `SCENE_DEFAULT_DURATION` 하향: 3.0 → 2.0
- [ ] 기존 영상 1개 이상 재렌더링하여 체감 템포 개선 확인

### Should (P1)
- [ ] `transition_dur` 기본값 하향: 0.5 → 0.3 (in `calculate_speed_params`)
- [ ] 일본어 읽기 속도도 동기화 검토: `japanese cps` 5.0 → 7.0
- [ ] 영어 읽기 속도 검토: `english wps` 2.5 → 3.0

### Could (P2)
- [ ] speed_multiplier 기본값 1.0 → 1.2 검토
- [ ] 프롬프트 템포 규칙은 SP-107에서 별도 진행

## 참조
- `backend/config.py` — READING_SPEED, SCENE_DURATION_*, READING_DURATION_PADDING
- `backend/services/video/utils.py` — `calculate_speed_params()`, 씬 듀레이션 계산 로직
- `backend/constants/layout.py` — DEFAULT_XFADE_DURATION, XFADE_OFFSET

## 힌트
- P0은 순수 config 값 변경이라 사이드이펙트 최소. 단, 기존 영상의 타이밍이 바뀌므로 재렌더링 필요
- `calculate_speed_params()`의 상수를 config.py로 승격시키면 향후 튜닝이 편해짐
- 읽기 속도 변경은 AI가 생성하는 씬 텍스트 길이에도 간접 영향 (같은 duration 목표 → 더 많은 텍스트 허용)
