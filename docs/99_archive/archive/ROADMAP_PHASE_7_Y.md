# Phase 7-Y: Layout Standardization & Navigation Simplification (Archived)

**기간**: 2026-02-15 완료
**커밋**: `8a8850f`
**목표**: Manage 페이지를 Library + Settings로 분리, 공유 레이아웃 시스템 도입, Home 페이지 리디자인.
**선행**: Phase 7-6, 7-X 완료.

## 주요 변경 요약

### 1. 네비게이션 재구조화
`[Home, Studio, Library, Lab, Manage]` → `[Home, Studio, Library, Settings]`
- Lab: 코멘트 아웃 (비활성화)
- Manage: **완전 삭제** → Library + Settings로 분리

### 2. `/manage` → `/library` + `/settings` 분리

| 페이지 | 탭 | 그룹 |
|--------|-----|------|
| `/library` (7개 탭) | Characters, Backgrounds, Styles \| Voices, Music \| Prompts, Tags | Visuals, Audio, Text & Meta |
| `/settings` (4개 탭) | General, Render Presets, YouTube \| Trash | General, Project + 시스템 |

### 3. 공유 레이아웃 시스템 신규

| 컴포넌트 | 역할 |
|----------|------|
| `AppThreeColumnLayout` | Left(사이드바) + Center(1fr 스크롤) + Right(300px 패널) |
| `AppSidebar` | 그룹 접기/펴기, localStorage 영속, 반응형(lg+) |
| `AppMobileTabBar` | 모바일 가로 스크롤 탭 바 (lg 미만) |

### 4. Home 페이지 리디자인
칸반 뷰 → `HomeVideoFeed` (`ShowcaseSection` + `QuickActionsWidget` + `QuickStatsWidget`)

### 5. 컴포넌트 정리

| 분류 | 파일 |
|------|------|
| 삭제 | CharacterEditModal, CharacterTagsEditor, GeminiPreviewEditModal 등 9개 |
| manage→library | StyleProfileEditor, TagsTab, StyleTab, PromptsTab 등 10개 |
| manage→settings | SettingsSecondaryPanel, GeneralSettingsTab, YouTubeConnectTab 등 9개 |

### 6. 경로 변경

| 기존 | 변경 후 |
|------|---------|
| `/manage` | 삭제 |
| `/manage?tab=settings` | `/settings?tab=general` |
| `/manage?tab=tags` | `/library?tab=tags` |
| `/characters/[id]` | `/library?tab=characters&id=X` |

### 7. 테스트 동기화
39개 테스트 실패 수정 (Badge/Button 7개, validation 19개, storyboardActions 3개, test_storyboard 2개, test_creative_pipeline 7개, subtitle 1개)

### 8. 추가 개선
Unified Setup Wizard: 프로젝트/그룹 생성 2-step 통합 위자드 (채널→시리즈→Studio), 5곳 트리거 연결

## 알려진 제한사항 (TODO)

| 항목 | 설명 |
|------|------|
| 캐릭터 편집 | Full Editor 삭제됨. 편집 기능 재구현 필요 |
| Lab 메뉴 | AppShell에서 코멘트 아웃. `showLabMenu` 플래그 제어 |
| 스토리보드 삭제 UI | Settings > Trash에서만 복원 가능 |
