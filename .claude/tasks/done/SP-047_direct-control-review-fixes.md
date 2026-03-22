---
id: SP-047
priority: P1
scope: frontend
branch: fix/SP-047-direct-control-review-fixes
created: 2026-03-22
status: done
depends_on:
label: bug
---

## 무엇을 (What)
PR #126 (SP-027 Direct 탭 연출 컨트롤) 리뷰에서 지적된 미수정 WARNING 4건 + INFO 3건 후속 수정

## 왜 (Why)
CodeRabbit + Claude 리뷰에서 CHANGES_REQUESTED 상태로 머지됨. 런타임 버그(null 가드, 토스트 집계)와 데이터 소실 위험(autoSave 주석 불일치)이 main에 존재.

## 완료 기준 (DoD)
> AI가 이 목록으로 실패 테스트를 작성(RED)하고, 구현(GREEN)한다.
> "must"는 필수, "should"는 권장. 모호한 표현 금지.

### WARNING (must)
- [ ] `ScenesTab.tsx` handleApplyAll에서 `storyboardId === null`이면 에러 토스트 표시 후 early return
- [ ] `ScenesTab.tsx` 성공 토스트에서 `status === "prebuilt"` 기준으로 성공/실패 건수 분리 표시
- [ ] `DirectorControlPanel.tsx` EMOTION_PRESETS/BGM_MOOD_PRESETS 하드코딩에 대해 백로그 태스크 등록 (Backend SSOT 전환)
- [ ] `useStoryboardStore.ts` setGlobalEmotion 주석 수정 — `tts_asset_id: null`이 autoSave 페이로드에 포함됨을 정확히 기술

### INFO (should)
- [ ] `ScenesTab.tsx` catch 블록에 `console.error` 추가
- [ ] `DirectorControlPanel.test.tsx` 전체 적용 버튼 클릭 시 `onApplyAll` 호출 검증 테스트 추가
- [ ] `DirectorControlPanel.test.tsx` BGM 프리셋 클릭 시 `selectedBgmPreset` 업데이트 검증 테스트 추가
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석
- 관련 함수/파일: `ScenesTab.tsx` (handleApplyAll), `DirectorControlPanel.tsx`, `useStoryboardStore.ts` (setGlobalEmotion), `useRenderStore.ts`
- 상호작용 가능성: autoSave 경로에서 tts_asset_id: null 전송 시 백엔드 동작 확인 필요
- 관련 Invariant: INV-2 (autoSave는 UPDATE만)

## 제약 (Boundaries)
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: 프리셋 데이터 구조 자체 (Backend SSOT 전환은 별도 태스크)
- 의존성 추가 금지

## 힌트 (선택)
- PR #126 리뷰 코멘트: https://github.com/tomo-playground/shorts-producer/pull/126
- 관련 파일: `frontend/app/components/studio/ScenesTab.tsx`, `frontend/app/components/studio/DirectorControlPanel.tsx`, `frontend/app/store/useStoryboardStore.ts`
