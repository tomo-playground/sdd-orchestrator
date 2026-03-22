---
id: SP-055
priority: P1
scope: fullstack
branch: feat/SP-055-tts-bgm-param-unify
created: 2026-03-22
status: running
approved_at: 2026-03-22
depends_on:
label: fix
---

## 무엇을 (What)
오토런과 수동 실행에서 TTS/BGM 생성 파라미터를 통일하여, 동일 씬을 어떤 경로로 생성해도 같은 결과를 보장한다.

## 왜 (Why)
현재 오토런(tts_prebuild)과 수동(preview_tts)이 같은 중앙 함수(`generate_tts_audio`)를 호출하지만, 래퍼에서 파라미터를 제각각 조립한다:

1. **TTS `image_prompt_ko`**: prebuild는 전달, preview는 누락 → 수동 TTS에서 이미지 컨텍스트 없이 voice_design 생성 → 오토런과 다른 톤
2. **TTS `language`**: prebuild는 `None` 하드코딩, preview는 `req.language` 전달 → 같은 씬이 다른 언어 설정으로 생성 가능
3. **TTS `max_retries`**: prebuild=2, preview=1 → 수동 TTS도 `scene.tts_asset_id`에 영구 저장되는데 재시도가 적음
4. **BGM `duration`**: prebuild=항상 30초, render=영상 길이 반영 → prebuild BGM이 영상보다 짧을 수 있음

이미지는 `buildSceneRequest()` 단일 조립 함수로 경로 불일치가 없지만, TTS/BGM에는 이런 공통 레이어가 없음.

## 완료 기준 (DoD)

### TTS 파라미터 통일
- [x] Frontend에 `buildTtsRequest(scene, storyboardId)` 함수 추가 — Scene 객체에서 TTS 요청 파라미터를 조립하는 단일 진입점
- [x] `autopilotActions.ts`의 tts-prebuild 요청이 `buildTtsRequest()` 사용
- [x] `useTTSPreview.ts`의 preview/tts 요청이 `buildTtsRequest()` 사용
- [x] `ScenesTab.tsx`의 tts-prebuild 요청이 `buildTtsRequest()` 사용
- [x] `usePublishRender.ts`의 tts-prebuild 요청이 `buildTtsRequest()` 사용
- [x] Backend `SceneTTSPreviewRequest` 스키마에 `image_prompt_ko: str | None = None` 필드 추가
- [x] Backend `tts_core.generate_scene_tts()` 통합 래퍼 함수 추가 — 오토런/수동 모두 이 함수를 경유
- [x] `tts_prebuild._generate_audio()`가 `tts_core.generate_scene_tts()` 호출로 전환
- [x] `preview_tts._generate_scene_tts()`가 `tts_core.generate_scene_tts()` 호출로 전환
- [x] `max_retries` 값이 `config.py` SSOT 1곳에서 관리 — 경로별 하드코딩 제거
- [x] `language` 파라미터가 양쪽 경로에서 동일하게 전달 (Frontend에서 전달, Backend에서 fallback)
- [x] `voice_design` write-back이 양쪽 경로에서 동일하게 동작

### BGM duration 통일
- [x] `BgmPrebuildRequest` 스키마에 `total_duration: float | None = None` 필드 추가
- [x] `bgm_prebuild.prebuild_bgm()`이 `total_duration` 기반으로 duration 계산 — `min(max(30, total_duration or 30), MUSICGEN_MAX_DURATION)`
- [x] Frontend `autopilotActions.ts`의 bgm-prebuild 호출 시 씬 duration 합계 전달

### 품질 게이트
- [x] 기존 테스트 regression 없음 (41 passed)
- [x] 린트 통과 (ruff + prettier)
- [x] TTS 통합 래퍼 단위 테스트 추가 (5개 — 파라미터 전달 검증)

## 영향 분석

- 관련 함수/파일:
  - `backend/services/tts_prebuild.py` — `_generate_audio()`
  - `backend/services/preview_tts.py` — `_generate_scene_tts()`
  - `backend/services/video/tts_helpers.py` — `generate_tts_audio()` (SSOT, 변경 없음)
  - `backend/services/bgm_prebuild.py` — `prebuild_bgm()`, `_generate_bgm()`
  - `backend/schemas.py` — `SceneTTSPreviewRequest`, `BgmPrebuildRequest`
  - `frontend/app/hooks/useTTSPreview.ts` — TTS 수동 호출
  - `frontend/app/store/actions/autopilotActions.ts` — TTS/BGM 오토런 호출
  - `frontend/app/components/studio/ScenesTab.tsx` — TTS prebuild 호출
  - `frontend/app/hooks/usePublishRender.ts` — TTS prebuild 호출
- 상호작용 가능성: TTS 캐시 키가 `language` 포함하므로, prebuild의 language 변경 시 기존 캐시 미스 발생 가능 (의도된 동작)
- 관련 Invariant: INV-4 (config.py 상수 SSOT)

## 제약 (Boundaries)
- 변경 파일 10개 이하 목표
- `generate_tts_audio()` (tts_helpers.py) 시그니처 변경 금지 — 통합 래퍼가 감싸는 구조
- `generate_music()` (audio_client.py) 변경 금지
- 이미지 생성 경로는 이미 통일되어 있으므로 건드리지 않음

## 상세 설계 (How)
> [design.md](./design.md) 참조

## 힌트 (선택)
- 이미지의 `buildSceneRequest()` 패턴을 TTS에 그대로 적용하는 것이 핵심
- `tts_core.py` (신규) 또는 기존 `tts_helpers.py`에 통합 래퍼 추가 가능 — 파일 분리는 설계 단계에서 결정
- Frontend `buildTtsRequest()` 위치: `frontend/app/utils/buildTtsRequest.ts` 또는 `frontend/app/store/actions/` 하위
