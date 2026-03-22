---
id: SP-060
priority: P1
scope: frontend
branch: feat/SP-060-voice-preset-cache-stale
created: 2026-03-22
status: approved
depends_on:
label: bug
---

## 무엇을 (What)
캐릭터 편집 페이지의 Voice Preset 드롭다운이 Voices 관리 페이지의 최신 데이터와 싱크되지 않음 — 프리뷰 생성/수정 후에도 이전 데이터 표시.

## 왜 (Why)
`useRenderStore.voicePresetsLoaded` 플래그가 세션 내 1회만 fetch하는 방식이라, Voices 페이지에서 프리셋을 추가/수정/프리뷰 생성해도 캐릭터 편집 드롭다운에 반영되지 않는다.

**재현 시나리오:**
1. 캐릭터 편집 페이지 진입 → voice presets 로드 (`voicePresetsLoaded = true`)
2. Voices 관리 페이지에서 프리셋 추가 또는 기존 프리셋에 프리뷰 음성 생성
3. 캐릭터 편집 페이지로 복귀 → 드롭다운에 이전 목록 표시, 새 프리셋 미표시, 프리뷰 재생 불가

**데이터 확인:**
- DB에 15개 voice preset 존재 (id 9~32)
- API(`GET /api/v1/voice-presets`) 응답 정상 (15개, audio_url 포함)
- 진우(id=28)만 `audio_asset_id=None` (프리뷰 미생성)
- `VoicePresetSelector`는 `useRenderStore.voicePresets` 캐시 사용
- Voices 관리 페이지는 `useVoicePresets` hook으로 매번 fresh fetch

## 완료 기준 (DoD)
- [x] `VoicePresetSelector` 컴포넌트 마운트 시 항상 최신 voice presets를 가져온다 (stale 캐시 사용 금지)
- [x] Voices 관리 페이지에서 프리셋 추가/수정/삭제 후 캐릭터 편집 드롭다운에 즉시 반영된다
- [x] 기존 voice preset 선택/저장/재생 기능 regression 없음
- [x] 린트 통과

## 영향 분석
- 관련 파일:
  - `frontend/app/store/useRenderStore.ts` (voicePresets, voicePresetsLoaded, fetchVoicePresets)
  - `frontend/app/components/voice/VoicePresetSelector.tsx` (useEffect로 fetch 호출)
  - `frontend/app/hooks/useVoicePresets.ts` (Voices 관리 페이지용 — 참고용)
- 상호작용: `StageVoiceSection`, `StageCharacterCard`, `GroupConfigEditor` 등에서도 `voicePresets` 사용
- `voicePresetsLoaded`는 `fetchVoicePresets` 중복 호출 방지 용도 — 캐시 전략 변경 시 불필요한 네트워크 요청 최소화 고려 필요

## 제약 (Boundaries)
- 변경 파일 3개 이하 목표
- 건드리면 안 되는 것: Backend API, DB 스키마, Voices 관리 페이지 로직
- 의존성 추가 금지

## 힌트
- 가장 간단한 해결: `voicePresetsLoaded` 플래그 제거하고 컴포넌트 마운트 시 항상 fetch
- 또는: `voicePresetsLoaded`를 timestamp 기반 TTL로 전환 (예: 30초)
- 또는: Voices 관리 페이지에서 변경 시 `voicePresetsLoaded = false`로 리셋 (cross-store 이벤트)
