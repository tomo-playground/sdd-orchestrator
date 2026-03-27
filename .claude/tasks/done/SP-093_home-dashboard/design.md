# SP-093 설계

## 구현 방법

### 1. `WelcomeBar.tsx` — 빠른 시작 입력 필드 추가

**현재**: 인사말 + 스토리보드 수 표시 + "새 영상" 버튼.

**변경**:
- ContextStore에서 `projectId`, `groupId`를 구독. 둘 다 존재할 때만 빠른 시작 입력 필드를 렌더링.
- 입력 필드: `<input placeholder="어떤 영상을 만들까요?" />` + Enter/버튼으로 제출.
- 제출 핸들러 `handleQuickStart(topic: string)`:
  1. `POST /api/v1/storyboards/draft` (`{ title: topic, group_id }`) 호출 — 기존 `draftActions.ts`의 `ensureDraftStoryboard` 패턴과 유사하나, title에 사용자 입력 주제를 사용.
  2. 응답의 `storyboard_id`를 받아 `router.push(`/studio?id=${storyboardId}&topic=${encodeURIComponent(topic)}`)` 이동.
- 기존 "새 영상" 버튼은 유지 (`/studio?new=true`로 이동하는 기존 플로우).
- `projectId`/`groupId`가 null이면 입력 필드 숨기고 기존 UI만 표시 (SetupWizard 플로우 유지).
- 로딩 중 버튼 disable + spinner 표시.
- 에러 시 `showToast` 사용.

**변경 범위**: WelcomeBar.tsx 내부만 수정. 신규 파일 없음.

**참고**: spec DoD에 "기존 API 3개 순차 호출 (project→group→storyboard)"이라 되어 있으나, 채널/시리즈가 **이미 존재하는 경우에만** 빠른 시작이 표시되므로 project/group 생성은 불필요. draft API 1개 호출로 충분.

### 2. `ContinueWorkingSection.tsx` — 진행 상태 5단계 표시

**현재**: `kanban_status` 기반 4-step dots (draft/in_prod/rendered/published) + image_count/scene_count 진행률 바.

**변경**:
- 5단계 진행 상태로 확장: `Script` → `Stage` → `Images` → `Render` → `Done`
- `kanban_status`와 추가 필드를 조합하여 5단계 매핑:

| 조건 | 단계 | 의미 |
|------|------|------|
| `kanban_status === "draft"` | Script | 대본 작성 중 |
| `stage_status === "staged"` | Stage | 준비 완료 |
| `image_count > 0 && kanban_status === "in_prod"` | Images | 이미지 생성 중 |
| `kanban_status === "rendered"` | Render | 렌더 완료 |
| `kanban_status === "published"` | Done | 게시 완료 |

- `STEPS`와 `STEP_META` 상수를 5단계로 변경.
- `currentIdx` 산출 로직을 위 조건 기반으로 교체 (`deriveProgressStep()` 헬퍼 함수 추출).
- `RecentStoryboard` 타입에 `stage_status` 필드 추가 (Backend `StoryboardListItem` 스키마에 이미 존재).
- dots UI는 기존 패턴 유지 (색상/크기 동일).

**변경 범위**: ContinueWorkingSection.tsx 내부만 수정. 신규 파일 없음.

### 3. `StoryboardListItem` 타입 — `kanban_status` 추가

**현재**: `frontend/app/types/index.ts`의 `StoryboardListItem`에 `kanban_status` 필드 없음.

**변경**: Backend 스키마(`StoryboardListResponse`)에 이미 있는 `kanban_status` 필드를 프론트 타입에 추가.

```typescript
export type StoryboardListItem = {
  // ... 기존 필드
  kanban_status: "draft" | "in_prod" | "rendered" | "published";
};
```

**참고**: ContinueWorkingSection은 현재 자체 `RecentStoryboard` 로컬 타입을 사용 중. 이 타입에 `stage_status` 필드만 추가하면 됨 (이미 `kanban_status`가 있음).

### 4. Studio `page.tsx` — topic 쿼리 파라미터 처리

**현재**: `/studio?new=true` 또는 `/studio?id=X`만 처리.

**변경**: `/studio?id=X&topic=Y`로 진입 시, `topic` 파라미터를 StoryboardStore의 `topic` 필드에 설정. 이미 draft로 생성된 storyboard를 로드한 뒤, topic이 있으면 자동으로 Script 탭의 입력에 반영.

**변경 범위**: Studio page의 URL 파라미터 파싱 부분만 수정. 기존 흐름에 `topic` 읽기만 추가.

### 5. VRT 베이스라인 갱신

- `frontend/tests/vrt/home.spec.ts` 기존 테스트는 WelcomeBar에 입력 필드가 추가되므로 스냅샷 갱신 필요.
- 새 테스트 케이스 추가 (아래 테스트 전략 참조).

---

## 테스트 전략

### Vitest 단위 테스트 (신규)

**파일**: `frontend/app/components/__tests__/WelcomeBarQuickStart.test.tsx`

| 케이스 | 검증 내용 |
|--------|----------|
| 빠른 시작 표시 조건 | projectId + groupId 둘 다 있을 때만 입력 필드 렌더링 |
| 빠른 시작 숨김 | projectId 또는 groupId null이면 입력 필드 미렌더링 |
| 빈 입력 제출 방지 | topic이 빈 문자열이면 API 호출 안 함 |
| 제출 시 API 호출 | draft API 호출 + router.push 확인 |
| 에러 처리 | API 실패 시 toast 표시, 입력 필드 유지 |

**파일**: `frontend/app/components/__tests__/ContinueWorkingProgress.test.tsx`

| 케이스 | 검증 내용 |
|--------|----------|
| deriveProgressStep — draft | kanban_status "draft" → step 0 (Script) |
| deriveProgressStep — staged | stage_status "staged" → step 1 (Stage) |
| deriveProgressStep — in_prod | image_count > 0 → step 2 (Images) |
| deriveProgressStep — rendered | kanban_status "rendered" → step 3 (Render) |
| deriveProgressStep — published | kanban_status "published" → step 4 (Done) |
| 5-step dots 렌더링 | dots 5개 + 올바른 활성 색상 |

### Playwright VRT 테스트 (갱신)

**파일**: `frontend/tests/vrt/home.spec.ts`

| 케이스 | 검증 내용 |
|--------|----------|
| (기존) 초기 렌더 | 인사말 + 새 영상 버튼 + **빠른 시작 입력 필드** |
| (신규) 빠른 시작 미표시 | projectId 없는 상태에서 입력 필드 숨김 확인 |
| (신규) ContinueWorking 5-step dots | 5개 dots 렌더링 + 올바른 활성 상태 |
| (기존) 스토리보드 카드 클릭 | 기존 동작 유지 확인 |

### 수동 검증 체크리스트

- [ ] 채널/시리즈 있는 상태: 빠른 시작 입력 필드 표시 → 주제 입력 → Enter → Studio 이동 확인
- [ ] 채널/시리즈 없는 초기 상태: SetupWizard 동작 유지 (빠른 시작 미표시)
- [ ] ContinueWorking 카드: 5단계 dots가 kanban_status에 따라 올바르게 표시
- [ ] 에러 시나리오: API 실패 → toast 표시 + UI 정상 유지
