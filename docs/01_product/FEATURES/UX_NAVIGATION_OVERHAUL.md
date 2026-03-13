# Phase 31: UX Navigation Overhaul (동선 일관성 개편)

**상태**: A~D 완료, E~F 미착수
**목적**: 채널 → 그룹 → LoRA → 캐릭터 → 장면 생성 동선의 일관성 확보, 죽은 코드 정리, 상태 관리 누수 수정
**분석 근거**: 6-에이전트 병렬 분석 (UI/UX Engineer, Backend Dev, Frontend Dev, Explore x3) — 2026-03-13
**기존 감사**: `docs/02_design/UI_UX_AUDIT_2026_03_01.md` (42건 중 미해결 항목 포함)

---

## 문제 정의

### 1. CRUD 패턴 비일관성
사용자가 "이걸 편집하려면 어디로 가야 하지?"의 답이 도메인마다 전부 다름.

| 도메인 | 패턴 | 생성 | 편집 | 위치 |
|--------|------|------|------|------|
| Character | Multi-page | Wizard 5단계 | /[id] 상세 페이지 | Library |
| StyleProfile | Single-page | 인라인 "+ New" | 인라인 에디터 패널 | Library |
| Voice/Music | Single-page | 인라인 폼 | 같은 폼 | Library |
| LoRA | Dev 전용 | Civitai 다운로드 | EditLoraModal | Dev |
| Group 설정 | 모달 | SetupWizard Step 2 | GroupConfigEditor 모달 | ContextBar |
| Render Preset | Settings 탭 | 인라인 | 인라인 | Settings |

### 2. LoRA 관리 동선 분산 + API 제약
- LoRA 원본 관리: `/dev/sd-models` (Dev 영역에 숨어있음)
- StyleProfile LoRA 연결: `/library/styles`
- 캐릭터 LoRA 연결: `/library/characters/[id]`
- **API 문제**: LoRA CRUD 전부 `/api/admin/loras`에만 등록. Service API에 GET조차 없음

### 3. Admin 라우트 전체가 유령 코드
6개 페이지 + AdminShell + AdminSidebar = 모두 redirect만 수행 (9개 파일)

### 4. Lab 컴포넌트 18개 고아 코드
`components/lab/` 디렉토리에 18개 파일 잔류, 어디서도 import하지 않음

### 5. Settings가 admin/ 디렉토리 컴포넌트를 역참조
`/settings/presets` → `admin/system/tabs/RenderPresetsTab` (의존 방향 역전)

### 6. 상태 관리 누수 3건
- handleDismiss: ContextStore만 리셋, StoryboardStore/RenderStore 잔류
- 삭제 핸들러: selectProject/selectGroup과 달리 불완전 정리
- 스토리보드 전환: RenderStore 불완전 초기화 (videoUrl만 null, 나머지 잔류)

### 7. Backend API 비일관성
- Scene URL: `/scene/validate_image` vs `/scene/generate-batch` vs `/scenes/{id}/edit-image`
- 삭제 응답 스키마 4종류
- Storyboard permanent delete가 Service API에 노출
- response_model 누락 4건

---

## Sub-Phase 구성

### Sub-Phase A: 죽은 코드 정리 (P0)

**목표**: 유령 라우트, 고아 컴포넌트, 역참조 의존 해소

| # | 작업 | 파일 수 | 유형 |
|---|------|--------|------|
| A-1 | Admin 라우트 그룹 제거 | 9 | 삭제 |
| | - `admin/layout.tsx`, `admin/page.tsx` | | |
| | - `admin/characters/page.tsx`, `admin/characters/[id]/page.tsx`, `admin/characters/new/page.tsx` | | |
| | - `admin/styles/page.tsx`, `admin/voices/page.tsx`, `admin/music/page.tsx` | | |
| | - `admin/system/page.tsx` | | |
| | - `components/shell/AdminShell.tsx`, `components/shell/AdminSidebar.tsx` | | |
| A-2 | `admin/system/tabs/` 3개 컴포넌트를 `components/settings/`로 이동 | 3+3 | 이동+import 수정 |
| | - `RenderPresetsTab` → `components/settings/RenderPresetsTab.tsx` | | |
| | - `YouTubeConnectTab` → `components/settings/YouTubeConnectTab.tsx` | | |
| | - `TrashTab` → `components/settings/TrashTab.tsx` | | |
| | - `admin/system/hooks/` 하위 훅도 함께 이동 | | |
| A-3 | Lab 컴포넌트 18개 삭제 | 18 | 삭제 |
| | - `components/lab/` 디렉토리 전체 | | |
| A-4 | 미사용 컴포넌트 확인 및 정리 | TBD | 삭제 |
| | - `components/analytics/`, `components/quality/` 실사용 여부 확인 | | |
| | - `components/manage/` 실사용 여부 확인 | | |

**검증**: 빌드 성공 + 기존 테스트 전체 PASS

### Sub-Phase B: 상태 관리 누수 수정 (P0)

**목표**: 컨텍스트 전환 시 stale 데이터 완전 제거

| # | 작업 | 파일 | 상세 |
|---|------|------|------|
| B-1 | handleDismiss 완전 리셋 | PersistentContextBar.tsx | `resetContext()` 후 `StoryboardStore.reset()` + `RenderStore.reset()` 추가 |
| B-2 | 삭제 핸들러 완전 리셋 | PersistentContextBar.tsx | `handleDeleteProject`/`handleDeleteGroup`에 `StoryboardStore.reset()` + `RenderStore.reset()` 추가 |
| B-3 | 스토리보드 전환 시 RenderStore 완전 리셋 | useStudioInitialization.ts | `prevStoryboardIdRef !== currentId` 감지 시 `RenderStore.reset()` 먼저 실행 후 DB 로드 |

**검증**: 수동 시나리오 테스트 (스토리보드 X → 새 스토리보드, 그룹 삭제 → 새 그룹 선택)

### Sub-Phase C: Backend API 정리 (P1)

**목표**: API 일관성 확보, Service/Admin 경계 명확화

| # | 작업 | 파일 | 상세 |
|---|------|------|------|
| C-1 | LoRA GET을 Service API에 노출 | routers/loras.py, routers/__init__.py | `GET /api/v1/loras` (읽기 전용 목록+상세) 추가. CUD는 Admin 유지 |
| C-2 | response_model 누락 4건 수정 | routers/render_presets.py, routers/voice_presets.py | DELETE, POST /preview, POST /attach-preview에 response_model 지정 |
| C-3 | Storyboard permanent delete를 Admin으로 이동 | routers/storyboard.py, routers/__init__.py | `DELETE /{id}/permanent`를 admin_router로 이동 |
| C-4 | Scene URL 패턴 통일 | routers/scene.py | `validate_image` → `validate-image`, prefix를 `/scenes`(복수형)으로 통일. 기존 URL은 deprecated alias 유지 (3개월) |
| C-5 | 삭제 응답 스키마 통일 | schemas 관련 파일 | `StatusResponse` 1종으로 통일. 기존 `OkDeletedResponse`, `DeleteStatusResponse` deprecated |

**검증**: Backend 테스트 전체 PASS + Frontend API 호출 경로 확인

### Sub-Phase D: 네비게이션 구조 개선 (P1)

**목표**: Shell/SubNav 중복 제거, 진입점 일관성

| # | 작업 | 파일 | 상세 |
|---|------|------|------|
| D-1 | LibraryShell/SettingsShell → SubNavShell 통합 | shell/ | 범용 `SubNavShell` 활용, 각 Shell은 tabs 설정만 전달 |
| D-2 | Library에 LoRA 탭 추가 | library/loras/ (신규) | `/library/loras` 페이지 신규. 기존 `/dev/sd-models`의 LoRA 섹션을 여기로 이동. Dev에는 Checkpoint/Embedding만 남김 |
| D-3 | DevSidebar 단순화 | components/shell/DevSidebar.tsx | LoRA 이동 후 Dev에는 SD Models(Checkpoint+Embedding) + System만 |

**검증**: 빌드 성공 + 네비게이션 동선 수동 테스트

### Sub-Phase E: 온보딩 개선 (P2)

**목표**: 신규 사용자 첫 영상 생성까지의 마찰 감소

| # | 작업 | 파일 | 상세 |
|---|------|------|------|
| E-1 | Quick-Start API | routers/projects.py (또는 신규) | `POST /api/v1/quick-start` — Project + Group + 기본 StyleProfile 연결을 한 번에 생성. 응답에 생성된 group_id 포함 |
| E-2 | SetupWizard Quick-Start 모드 | components/setup/ | Quick-Start API 호출로 2단계(채널명+시리즈명 입력)만으로 시작 |
| E-3 | Home 미사용 컴포넌트 활성화 여부 검토 | components/home/ | `ContinueWorkingSection`, `QuickStatsBar` 등 현재 Home에서 사용 중인지 확인 후, 미사용이면 활성화 또는 삭제 결정 |

**검증**: 새 DB에서 처음부터 온보딩 → 첫 영상 생성 E2E 테스트

### Sub-Phase F: Soft Delete 및 삭제 보호 통일 (P2)

**목표**: 삭제 정책 일관성

| # | 작업 | 파일 | 상세 |
|---|------|------|------|
| F-1 | Group Soft Delete 추가 | models/, routers/groups.py, crud | `deleted_at` 컬럼 추가, DELETE → soft delete, `POST /restore` 추가. Trash 탭에 Groups 표시 |
| F-2 | 프리셋 삭제 시 FK 참조 체크 | routers/style_profiles.py, render_presets.py, voice_presets.py | 삭제 전 Group 참조 여부 확인, 참조 중이면 409 반환 |

**검증**: Backend 테스트 + Trash 페이지에서 Group 복원 확인

---

## 작업 순서 및 의존 관계

```
Sub-Phase A (죽은 코드 정리)
  ↓
Sub-Phase B (상태 관리 수정)     ← 독립, A와 병렬 가능
  ↓
Sub-Phase C (Backend API 정리)   ← A 완료 후 (admin 구조 변경 영향)
  ↓
Sub-Phase D (네비게이션 개선)     ← C-1 완료 후 (LoRA Service API 필요)
  ↓
Sub-Phase E (온보딩 개선)         ← D 완료 후 (네비게이션 안정화 필요)
  ↓
Sub-Phase F (Soft Delete 통일)   ← 독립, E와 병렬 가능
```

**병렬 가능 조합**:
- A + B (독립)
- E + F (독립)

---

## 영향 범위

### Frontend
- 삭제: ~30개 파일 (Admin 9 + Lab 18 + 기타)
- 이동: 3~6개 파일 (admin/system/tabs → components/settings)
- 수정: ~10개 파일 (Shell, ContextBar, Studio hooks)
- 신규: 2~3개 파일 (Library/LoRA 페이지, SubNavShell 리팩터)

### Backend
- 수정: ~8개 파일 (라우터, 스키마)
- 신규: 1~2개 파일 (Quick-Start API, LoRA Service 라우터)

### DB
- 마이그레이션: 1건 (Group soft delete — `deleted_at` 컬럼 추가)

---

## DoD (Definition of Done)

- [x] Admin 라우트 그룹 완전 제거 (빌드 성공) — Sub-Phase A
- [x] Lab 컴포넌트 18개 삭제 (빌드 성공) — Sub-Phase A
- [x] Settings 탭 컴포넌트 위치 정상화 (service → admin 역참조 제거) — Sub-Phase A
- [x] 상태 관리 누수 3건 수정 (수동 시나리오 검증) — Sub-Phase B
- [x] LoRA GET API Service 노출 — Sub-Phase C
- [x] response_model 누락 수정 — Sub-Phase C
- [x] Scene URL 패턴 통일 — Sub-Phase C
- [x] Storyboard permanent delete Admin 이동 — Sub-Phase C
- [x] Library에 LoRA 탭 추가 (읽기 전용) — Sub-Phase D
- [x] LibraryShell/SettingsShell → SubNavShell 통합 — Sub-Phase D
- [ ] Quick-Start API (E2E 온보딩 검증) — Sub-Phase E
- [ ] Group Soft Delete (Trash 복원 검증) — Sub-Phase F
- [ ] 기존 테스트 전체 PASS (Backend + Frontend + E2E)
