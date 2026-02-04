# Sidebar Navigation + Context Switching Fix

**Phase**: 7-1 #15
**상태**: 미착수
**우선순위**: P0 (데이터 오염 버그 포함)

## 문제

### 컨텍스트 전환 버그 (6건)

| # | 버그 | 심각도 | 위치 |
|---|------|--------|------|
| 1 | 그룹 전환 시 씬/스토리보드 미초기화 — 이전 그룹 데이터 잔존, Generate 시 잘못된 그룹에 저장 | P0 | `useProjectGroups.ts:60-66` |
| 2 | 프로젝트 전환 시 동일 — groupId만 null, scenes/storyboard 유지 | P0 | `useProjectGroups.ts:54-57` |
| 3 | Cmd+K 스토리보드 선택 시 groupId/projectId 미갱신 — ContextBar 불일치 | P1 | `CommandPalette.tsx:102` |
| 4 | 스토리보드 로드 시 컨텍스트 검증 없음 — group_id 불일치 가능 | P1 | `useStudioInitialization.ts:146-191` |
| 5 | Home 그룹 필터가 전역 groupId와 분리 — local state로 관리 | P2 | `StoryboardsSection.tsx:54` |
| 6 | loadGroupDefaults 이중 호출 — selectGroup 직접 + useEffect | P2 | `useProjectGroups.ts:62-63` |

### 근본 원인

컨텍스트(Project/Group)와 콘텐츠(Storyboard/Scenes)가 독립적으로 변경 가능.
컨텍스트 전환 시 콘텐츠 정리/동기화 로직 부재.

### 네비게이션 문제

- 상단 NavBar만으로 Project → Group → Storyboard 계층 표현 한계
- ContextBar 드롭다운이 Studio에서만 존재 — Home/Manage에서는 컨텍스트 단절
- 스토리보드 목록이 Home에서만 보임 — Studio에서 다른 스토리보드로 전환 불편

## 목표

좌측 사이드바를 도입하여 계층 탐색과 컨텍스트 전환을 통합한다.

## 설계

### 레이아웃

```
┌──────────────────────────────────────────────────────┐
│  [Logo]  Shorts Producer                [Cmd+K] [⚙️] │
├───────────┬──────────────────────────────────────────┤
│           │                                          │
│ [Project▾]│  Page Content                            │
│           │  (Studio / Home / Manage)                │
│ GROUPS    │                                          │
│ ● 샘플    │                                          │
│   테스트  │                                          │
│ + New     │                                          │
│           │                                          │
│ ───────── │                                          │
│ STORIES   │                                          │
│ ● 처음 .. │                                          │
│   오늘 .. │                                          │
│ + New     │                                          │
│           │                                          │
│ ───────── │                                          │
│ 🏠 Home   │                                          │
│ 🎬 Studio │                                          │
│ ⚙️ Manage  │                                          │
│           │                                          │
└───────────┴──────────────────────────────────────────┘
```

### 사이드바 구성

| 섹션 | 내용 |
|------|------|
| Project Selector | 드롭다운. 프로젝트 변경 시 하위 전부 초기화 |
| Groups | 현재 프로젝트의 그룹 목록. 선택 시 스토리보드 목록 갱신 |
| Storyboards | 현재 그룹의 스토리보드 목록. 클릭 시 Studio로 이동 |
| Navigation | Home, Studio, Manage 링크 (현재 AppShell에서 이동) |

### 전환 규칙

| 동작 | 처리 |
|------|------|
| 프로젝트 변경 | groupId/storyboardId/scenes 전부 초기화 → Home으로 이동 |
| 그룹 변경 | storyboardId/scenes 초기화. 미저장 변경 있으면 확인 다이얼로그 |
| 스토리보드 클릭 | `/studio?id=X` + projectId/groupId 자동 동기화 |
| + New Storyboard | 현재 그룹에 새 스토리보드 생성 → Studio로 이동 |

## 구현 범위

### Phase A: 버그 수정 (사이드바 없이 선행 가능)

1. `selectGroup()`: storyboardId/scenes 초기화 추가
2. `selectProject()`: groupId/storyboardId/scenes 초기화
3. `CommandPalette`: 스토리보드 선택 시 group/project 컨텍스트 동기화
4. `useStudioInitialization`: 로드 시 storyboard.group_id로 컨텍스트 갱신
5. `StoryboardsSection`: filterGroupId를 전역 groupId와 동기화
6. `selectGroup()`: loadGroupDefaults 이중 호출 제거

### Phase B: 사이드바 구현

1. `Sidebar.tsx` 컴포넌트 생성
2. `AppShell.tsx` 레이아웃 변경 (상단 NavBar → 사이드바 + 최소 상단바)
3. `ContextBar` 제거 (사이드바로 대체)
4. 스토리보드 목록 API 연동 (groupId 변경 시 fetch)
5. 반응형: 모바일에서 아이콘 모드 또는 오버레이

### Phase C: Studio 서브헤더 정리

사이드바 도입 후 Studio 서브헤더 간소화:
- ContextBar breadcrumb 제거 (사이드바에서 보임)
- 스토리보드 제목 인라인 편집만 유지
- Actions bar (Generate/AutoRun/Save) 유지

## 관련 파일

| 파일 | 변경 |
|------|------|
| `components/shell/AppShell.tsx` | 레이아웃 변경 |
| `hooks/useProjectGroups.ts` | 전환 로직 수정 |
| `hooks/useStudioInitialization.ts` | 컨텍스트 검증 추가 |
| `components/context/ContextBar.tsx` | Phase C에서 제거 |
| `components/ui/CommandPalette.tsx` | 컨텍스트 동기화 |
| `components/home/StoryboardsSection.tsx` | 필터 동기화 |
| `store/actions/groupActions.ts` | 초기화 로직 추가 |
| `store/useStudioStore.ts` | resetScenes 액션 추가 |
