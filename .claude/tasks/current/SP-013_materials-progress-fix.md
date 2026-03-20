---
id: SP-013
priority: P0
scope: fullstack
branch: feat/SP-013-materials-progress-fix
created: 2026-03-21
status: pending
depends_on:
label: bug
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
Materials 진행률 및 Stage 사전 준비 진행률이 실제 데이터와 불일치하는 버그 수정

## 왜
E2E 테스트(SB #1120)에서 발견:
- Materials 팝오버: 1/6 표시 (실제 6/6 — 모든 항목 준비 완료)
- Stage 탭: 2/5 완료 표시 (실제 5/5)
- 사용자가 진행 상태를 오인하여 불필요한 재작업 유발

### 근본 원인
1. **Frontend 매핑 누락**: Backend API가 `is_ready`를 반환하지만, Frontend `MaterialStatus` 타입은 `ready`를 기대. `useMaterialsCheck.ts`에서 raw API 데이터를 그대로 spread하여 `is_ready` → `ready` 변환 없음.
2. **TTS 검증 목록 미갱신**: "전체 TTS 확인" 후 상단은 "11/11 캐시됨"이지만 하단 검증 목록은 여전히 "TTS 캐시 없음" 표시.
3. **폐기 용어**: 채팅 모드 버튼에 "Hands-on" (폐기됨, CLAUDE.md 기준) 표시.

## 완료 기준 (DoD)
- [ ] `useMaterialsCheck.ts`에서 API 응답 `is_ready` → `ready` 매핑 적용
- [ ] Materials 팝오버가 API 상태를 정확히 반영 (6/6)
- [ ] Stage 탭 진행률이 API 상태를 정확히 반영 (5/5)
- [ ] "전체 TTS 확인" 후 검증 목록(PreRenderReport)도 갱신되도록 수정
- [ ] "Hands-on" → 제거 또는 유효한 모드명으로 교체
- [ ] 기존 테스트 regression 없음
- [ ] `npm run build` 통과

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: Backend API 응답 구조 (`is_ready` 필드명은 Python 컨벤션이므로 유지)
- 의존성 추가 금지

## 힌트
- **BUG-1 핵심 수정 파일**: `frontend/app/hooks/useMaterialsCheck.ts` (L56)
  - `if (apiData) return { ...apiData, style: styleReady }` → API 각 항목의 `is_ready`를 `ready`로 변환 필요
  - 소비처: `MaterialsPopover.tsx` (L38, L69), `StageTab.tsx` (L124-126)
- **BUG-2 TTS 검증**: `frontend/app/components/video/PreRenderReport.tsx` — TTS 확인 결과 반영 로직 확인
- **BUG-4 Hands-on**: 채팅 모드 버튼 컴포넌트에서 `Hands-on` 제거. CLAUDE.md 유효 모드: `auto`, `guided`, `FastTrack`
- **QA 스크린샷**: `qa-screenshots/08_materials_progress_bug.png`
- **API 검증 결과**: `curl localhost:8000/api/v1/storyboards/1120/materials` → 모든 항목 `is_ready: true`
