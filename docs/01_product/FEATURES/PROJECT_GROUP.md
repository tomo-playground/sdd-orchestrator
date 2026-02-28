# Project(Channel) & Group(Story Group) System

**상태**: Phase 0~1 완료, Phase 2 (UX 개선) 신규 정의, 3-1~3-3 장기 백로그
**최종 갱신**: 2026-02-28

---

## 1. 구현 완료 현황

### Infrastructure (Phase 0) — 완료

| 항목 | 비고 |
|------|------|
| ORM 모델 | `Project`, `Group`, `RenderPreset` |
| DB 마이그레이션 | projects, groups, render_presets 테이블 + seed 데이터 |
| CRUD API | `routers/projects.py` (5개), `routers/groups.py` (6개) |
| Storyboard FK | `group_id` NOT NULL, RESTRICT 정책, 복합 인덱스 |
| Seed 데이터 | Default Project(id=1) + Default Group(id=1) |
| Storage 경로 | `projects/{p_id}/groups/{g_id}/storyboards/{s_id}/` |

### Settings & Config (Phase 1) — 완료

> **변경 이력**: GroupConfig 테이블 → Groups 테이블 병합 (02-28, commit 2d8c385)

| 항목 | 비고 |
|------|------|
| Cascading Config | `config_resolver.py` — Group → System Default 2단계 |
| Group 설정 필드 | `render_preset_id`, `style_profile_id`, `narrator_voice_preset_id` |
| Effective Config API | `GET /groups/{id}/effective-config` (sources 출처 표기 포함) |
| Render Preset | 시스템 프리셋 3종 + 커스텀 프리셋, CRUD API 완료 |
| Render Preset 관리 UI | Admin `RenderPresetsTab` + Settings `presets/page` |

### Frontend UI (Phase 1) — 완료

| 항목 | 비고 |
|------|------|
| Context Bar | `ContextBar.tsx` — 브레드크럼 + 인라인 Popover 프로젝트/그룹 전환 |
| CRUD 모달 | `ProjectFormModal`, `GroupFormModal`, `GroupConfigEditor` |
| Setup Wizard | `SetupWizard` + ProjectStep + GroupStep + StepIndicator |
| Zustand Store | `useContextStore` — projectId/groupId/effectiveConfig 영속화 |
| Cmd+K Quick Switcher | `CommandPalette.tsx` — 프로젝트/그룹/스토리보드 fuzzy 검색 (타입별 색상 아이콘) |
| Home 필터 | 프로젝트 드롭다운 + 그룹 필터 pill |
| 캐릭터 글로벌화 | `project_id` FK 제거, 글로벌 스코프 (v3.23) |

---

## 2. Phase 2: UX 개선

### 2-1. Zero-Config Start (P0) — 완료

신규 유저가 설정 없이 즉시 시작할 수 있는 환경 제공.

| # | 항목 | 설명 | 수정 파일 | 상태 |
|---|------|------|----------|------|
| 1 | 신규 유저 자동 프로비저닝 | projects=0일 때 "내 채널"/"기본 시리즈" 자동 생성 + 자동 선택 | `projectActions.ts` | 완료 |
| 2 | Home Empty State | 프로젝트 없을 때 SetupWizard CTA 버튼 표시 | `HomeVideoFeed.tsx` | 완료 |
| 3 | Studio Empty State | 채널/시리즈 미선택 시 빈 상태 UI + CTA | `StudioKanbanView.tsx` | 완료 |

> 기존 2-1 #1 (Empty State CTA) 흡수

### 2-2. 용어 통일 (P0) — 완료

UI 라벨만 변경. 코드 변수명(Project/Group/Storyboard)은 유지.

| # | 항목 | 설명 | 수정 파일 | 상태 |
|---|------|------|----------|------|
| 1 | UI 라벨 변경 | Project→채널, Group→시리즈, Storyboard→영상 (13개 파일) | Dropdown, Modal, ContextBar, CommandPalette, Actions 등 | 완료 |
| 2 | SetupWizard 일관성 확인 | 이미 "채널"/"시리즈" 사용 중 — 전체 UI 일관성 검증 완료 | `SetupWizardStepIndicator.tsx` | 완료 |

### 2-3. 설정 가시성 (P1)

Group 선택 시 어떤 설정이 적용되는지 한눈에 파악 가능하게.

| # | 항목 | 설명 | 수정 파일 |
|---|------|------|----------|
| 1 | GroupResponse에 프리셋 이름 추가 | `style_profile_name`, `voice_preset_name`, `render_preset_name` 필드 | `schemas.py`, `routers/groups.py` |
| 2 | GroupItem 타입 확장 | 위 3개 이름 필드 추가 | `types/index.ts` |
| 3 | GroupDropdown 설정 요약 뱃지 | 그룹명 옆에 화풍/보이스/렌더 이름 표시 | `GroupDropdown.tsx` |
| 4 | 색상 코딩 확대 | CommandPalette 아이콘 → 카드/리스트 UI 적용 | 관련 컴포넌트 |

> 기존 2-1 #2 (색상 코딩 확대) 흡수

### 2-4. 내비게이션 개선 (P2)

컨텍스트 전환 시 불필요한 리다이렉트 제거.

| # | 항목 | 설명 | 수정 파일 |
|---|------|------|----------|
| 1 | 프로젝트 전환 시 리다이렉트 제거 | Studio에서 프로젝트 변경해도 현재 페이지 유지, 데이터만 갱신 | `PersistentContextBar.tsx` |
| 2 | CommandPalette 전환 시 리다이렉트 제거 | `router.push("/")` → 현재 페이지 유지 | `CommandPalette.tsx` (L78, L99) |

---

## 3. 장기 백로그

### 3-1. Tag Intelligence

채널별 태그 정책 + 데이터 기반 추천. **Agentic Pipeline 인프라 위에 구축.**

| # | 항목 | 설명 |
|---|------|------|
| 1 | `tag_effectiveness`에 `project_id` 컬럼 추가 | 채널별 태그 성과 추적 |
| 2 | Project `allowed_tags[]`, `forbidden_tags[]` | 태그 화이트/블랙리스트 |
| 3 | 12-Layer Builder forbidden 태그 자동 제거 | 프롬프트 파이프라인 연동 |
| 4 | `GET /projects/{id}/tag-recommendations` | 프로젝트별 TOP 20 추천 |
| 5 | Gemini 템플릿 `recommended_tags` 자동 주입 | 생성 품질 향상 |

### 3-2. Series Intelligence

에피소드 연결 + 성공 패턴 학습.

| # | 항목 | 설명 |
|---|------|------|
| 1 | `storyboards.episode_number`, `recap_text` 컬럼 | 에피소드 순서 관리 |
| 2 | `GET /groups/{id}/episode-context` | 이전 에피소드 요약 자동 생성 (Gemini) |
| 3 | Gemini `previous_episodes` 섹션 자동 주입 | 시리즈 연속성 |
| 4 | `GET /groups/{id}/success-patterns` | 그룹 내 Match Rate TOP 태그 조합 |
| 5 | Group 타임라인 에피소드 순서/연결 시각화 | Frontend |

### 3-3. Production Scale

대규모 콘텐츠 워크플로우.

| # | 항목 | 설명 |
|---|------|------|
| 1 | 배치 렌더링 + 큐 | Celery/Redis, 그룹 일괄 렌더, WebSocket 진행률 |
| 2 | 브랜딩 시스템 | 로고/워터마크, 인트로/아웃트로, 플랫폼별 출력 |
| 3 | 분석 대시보드 | Match Rate 추이, 프로젝트 간 비교, activity_logs 확장 |
| 4 | Jinja2 템플릿 오버라이드 | 그룹별 커스텀 Gemini 템플릿 |
| 5 | 프로젝트/그룹 템플릿 | 5종 Quick Start (명언/교육/요리/스토리/뉴스) |

---

## 4. 의존성

```
완료: Phase 0 (Foundation) → Phase 1 (Core + Config + UI + Render Preset 관리)
           ↓
신규: Phase 2-1 Zero-Config (P0) → 2-2 용어 (P0) → 2-3 설정 가시성 (P1) → 2-4 내비게이션 (P2)
           ↓
백로그: 3-1 Tag Intelligence ← tag_effectiveness 데이터 축적 필요
        3-2 Series Intelligence ← 에피소드 데이터 축적 필요
        3-3 Production Scale ← 사용자 규모 확대 시
```

---

## 5. 설계 결정 기록

> 2026-02-28 — PM, UX, Creator, DBA, Backend Dev 크로스 리뷰 합의

| 결정 | 근거 |
|------|------|
| **Group 이중 역할 유지** (폴더 + 설정 번들) | 분리 시 가치 훼손. PM/UX/Creator 만장일치 |
| **Production Profile 미채택** | YAGNI. 6개 Group, 스토리보드 레벨 오버라이드 0건 (DBA/Backend 근거) |
| **channel_dna 제거** | 사용 빈도 0, YAGNI 원칙 적용 |
| **멀티유저 확장 방식** | `projects.user_id` FK 추가만으로 대응. `storyboards.group_id` NOT NULL 유지 |
| **코드 변수명 미변경** | Project/Group/Storyboard 영문 코드명 유지, UI 라벨만 한국어 변경 |

---

## 6. 기술 스택 현황

| 컴포넌트 | 파일 |
|---------|------|
| Project ORM | `backend/models/project.py` |
| Group ORM (config 통합) | `backend/models/group.py` |
| RenderPreset ORM | `backend/models/render_preset.py` |
| Config Resolver | `backend/services/config_resolver.py` |
| Project Router (5 EP) | `backend/routers/projects.py` |
| Group Router (6 EP) | `backend/routers/groups.py` |
| Context Store | `frontend/app/store/useContextStore.ts` |
| Context UI (11파일) | `frontend/app/components/context/` |
| CommandPalette | `frontend/app/components/ui/CommandPalette.tsx` |
| Render Preset Admin | `frontend/app/admin/system/tabs/RenderPresetsTab.tsx` |
| Render Preset Settings | `frontend/app/(service)/settings/presets/page.tsx` |
