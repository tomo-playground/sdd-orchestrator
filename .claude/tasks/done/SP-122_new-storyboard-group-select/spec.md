# SP-122: 새 영상 생성 시 시리즈 선택 UX 개선

- **approved_at**: 2026-03-31
- **branch**: feat/SP-122_new-storyboard-group-select
- **priority**: P1
- **scope**: frontend
- **assignee**: AI
- **created**: 2026-03-31

## 배경

홈에서 "새 영상" 클릭 → `/studio?new=true&tab=script` 이동 시, `ensureDraftStoryboard()`가 `groupId === ALL_GROUPS_ID(-1)` 또는 null로 인해 draft 생성 실패 → "시작하려면 시리즈를 생성하세요" 에러 토스트 → 칸반으로 복귀.

시리즈가 존재해도 에디터에 진입하지 못하는 버그.

### 재현

1. 홈 → "새 영상" 클릭
2. `/studio?new=true&tab=script` 이동
3. 시리즈 선택 화면(그룹 버튼)만 표시, 대본 에디터 미진입
4. "시작하려면 시리즈를 생성하세요" 토스트 출력

### 원인

- `resetAllStores()` 후 groupId가 `ALL_GROUPS_ID(-1)` 또는 보존된 값이 유효하지 않음
- `draftActions.ts:41` — `if (!groupId)` 체크에서 실패 → null 반환
- `useStudioInitialization.ts:77` — draftId null → URL 정리 → 칸반 복귀

## 목표

시리즈 개수에 따라 적절한 UX로 에디터 진입:
- 1개: 자동 선택 → 바로 에디터
- 2개+: 선택 팝업 → 선택 후 에디터
- 0개: "시리즈 만들기" 안내

## DoD (Definition of Done)

- [ ] 시리즈 1개일 때: 홈 "새 영상" → 자동 선택 → 대본 에디터 즉시 진입
- [ ] 시리즈 2개+일 때: 시리즈 선택 팝업 표시 → 선택 후 대본 에디터 진입
- [ ] 시리즈 0개일 때: "시리즈 만들기" 안내 (기존 동작 유지)
- [ ] 홈 Quick Start(텍스트 입력 + "시작")도 동일 흐름 적용
- [ ] 스튜디오 칸반의 "+ 새 영상" 버튼은 이미 그룹 선택된 상태이므로 영향 없음 확인

## 수정 대상 파일 (예상)

- `frontend/app/hooks/useStudioInitialization.ts` — draft 생성 전 groupId 유효성 체크
- `frontend/app/store/actions/draftActions.ts` — groupId fallback 로직
- `frontend/app/components/context/GroupSelectModal.tsx` (신규) — 시리즈 선택 팝업
- `frontend/app/components/home/WelcomeBar.tsx` — Quick Start 연동

## 참고

- `draftActions.ts:41`: `if (!groupId)` — ALL_GROUPS_ID(-1)도 falsy 아니므로 별도 처리 필요
- `resetAllStores.ts`: groupId는 보존되지만 ALL_GROUPS_ID일 수 있음
- `useProjectGroups.ts:70-78`: groups 로드 시 자동 선택 로직 존재 (재활용 가능)
