---
id: SP-039
priority: P0
scope: fullstack
branch: fix/SP-039-draft-resurrection
created: 2026-03-21
status: pending
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
삭제한 Draft 스토리보드가 autoSave에 의해 부활하는 버그 수정

## 왜
- 사용자가 칸반에서 Draft 삭제 → 시간이 지나면 다시 나타남
- 원인: `persistStoryboard()` 404 catch → POST 재생성 로직이 "삭제"와 "DB 초기화"를 구분 못 함
- 근본: `5629d1f2` (Sonnet)이 404→재생성을 넣었고, `5b180d72` (Opus)가 삭제 기능을 만들면서 충돌 미인지

## 재현 경로
1. "새 영상" 클릭 → Draft 생성
2. 채팅 없이 다른 영상으로 이동
3. 칸반에서 해당 Draft 삭제 (soft delete)
4. autoSave 2초 후 PUT → 404 → POST 재생성 → Draft 부활

## 수정 범위

### 1. persistStoryboard 404 재생성 제거
- `frontend/app/store/actions/storyboardActions.ts` Line 234-242
- 404 시 POST 재생성 대신: 스토어 정리 + 토스트 알림 + `return false`
- CLAUDE.md Invariant: "404 = 삭제, 자동 재생성 금지"

### 2. autoSave 삭제 방어
- `frontend/app/store/effects/autoSave.ts`
- `scheduleSave()` 내 storyboardId 유효성 검증 추가
- storyboardId가 null이면 저장 스킵 (새 생성은 사용자 명시적 액션으로만)

### 3. 비활성 Draft 삭제 시 방어
- `frontend/app/components/studio/StudioKanbanView.tsx`
- 비활성 삭제 후에도 `cancelPendingSave()` 호출 (타이밍 방어)

## 완료 기준 (DoD)
- [ ] Draft 삭제 후 부활하지 않음 (활성/비활성 양쪽)
- [ ] 404 시 autoSave가 새 스토리보드를 생성하지 않음
- [ ] 기존 정상 저장 흐름 regression 없음 (기존 영상 PUT 정상)
- [ ] "새 영상" → 첫 메시지 → 저장 정상 (PR #68 로직과 공존)

## 제약
- 변경 파일 3개 이하
- PR #68 (`fix/draft-pre-create-v2`) 머지 후 착수 (충돌 방지)
- 건드리면 안 되는 것: `deleteStoryboard()` 함수, `ensureDraftStoryboard()` 함수

## 힌트
- 원인 커밋: `5629d1f2` (404 → POST 재생성)
- 삭제 커밋: `5b180d72` (PR #46, 칸반 삭제 UI)
- Draft 선생성: `a392186e` → `024d0911` (PR #68)
