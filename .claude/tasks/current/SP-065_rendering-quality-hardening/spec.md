---
id: SP-065
priority: P2
scope: backend
branch: feat/SP-065-rendering-quality-hardening
created: 2026-03-23
status: running
depends_on:
label: feat
---

## 무엇을 (What)
렌더링 파이프라인의 Ken Burns, BGM Ducking, Voice Pacing, 전환 효과 4개 영역에서 엣지 케이스 방어와 fallback을 추가한다.

## 왜 (Why)
- Ken Burns 무효 preset → None → 렌더링 시 효과 먹통 (fallback 없음)
- BGM Ducking 타이밍이 scene_durations와 어긋나면 음성에 BGM이 겹치거나 완전히 사라짐
- TTS Designer가 생성한 pacing(head/tail_padding)이 실제 렌더링에 적용되는지 불명확
- 전환 효과(slideL/slideR)와 Ken Burns(pan_left/pan_right)가 같은 방향으로 겹치면 어지러움

## 완료 기준 (DoD)

### Ken Burns Fallback

- [x] `resolve_preset_name()`에서 무효한 값 반환 시 emotion 기반 자동 배정을 fallback으로 적용한다 (Finalize의 감정 기반 배정 로직 재사용)
- [x] 무효 preset 입력에 대해 fallback이 작동하는 테스트를 작성한다

### BGM Ducking 검증

- [x] `apply_music_effects()`에서 ducking offset이 scene_durations 합계를 초과하면 마지막 씬 끝으로 클램프한다
- [x] BGM 길이가 전체 영상보다 짧으면 루핑 또는 fade-out 처리가 적용되는지 확인하고, 미적용이면 추가한다
- [x] ducking 타이밍 정확도 테스트를 작성한다

### Voice Pacing 적용 확인

- [x] TTS Designer가 생성한 `head_padding`/`tail_padding` 값이 렌더링 시 실제로 적용되는 경로를 확인한다
- [x] 미적용이면 scene_processing에서 TTS 오디오에 padding을 추가하는 로직을 연결한다

### 전환 효과 충돌 방지

- [x] `resolve_scene_transition()`에서 선택된 전환 효과의 방향이 해당 씬의 ken_burns_preset 방향과 동일하면 (예: slideL + pan_left) 다른 전환으로 대체한다
- [x] 방향 충돌 케이스에 대한 테스트를 작성한다

### 통합

- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 영향 분석
- 관련 파일: `backend/services/video/effects.py`, `backend/services/video/scene_processing.py`, `backend/services/video/builder.py`, `backend/services/motion.py`
- 상호작용: FFmpeg 필터 체인 — 전환/모션/오디오 타이밍 전반
- Ken Burns와 전환 효과 모두 최종 FFmpeg 명령어에 영향

## 제약
- 변경 파일 6개 이하
- FFmpeg 필터 체인의 기본 구조는 변경하지 않음 — 파라미터/fallback만 추가
- BGM 생성 로직(MusicGen)은 건드리지 않음 — 후처리만

## 힌트
- `VALID_PRESET_NAMES` (config.py)와 `resolve_preset_name()` (motion.py) 확인
- `apply_music_effects()` 위치: `backend/services/video/effects.py` 또는 `builder.py`
- pacing 적용은 `trim_tts_audio()` 5단계 파이프라인 내부 확인
