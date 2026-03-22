# IA Redesign — 정보 구조 개선

> **상태**: Draft (PM + Tech Lead 검토 반영 v2)
> **작성일**: 2026-03-22
> **Phase**: A(Quick Wins) → B(중규모) → C(Direct 3패널) → D(Library 통일)
> **선행 조건**: SP-028, SP-027, SP-040 PR 머지
> **총 태스크**: 17개 (SP-049~SP-061, SP-055는 a/b 분리)
> **예상 기간**: 6~10주 (낙관 8주, 현실 10주)

---

## 1. 배경 및 문제 정의

### 검증된 핵심 문제 (코드 grep/실제 파일 확인)

| # | 문제 | 근거 | 심각도 |
|---|------|------|--------|
| P0-1 | Studio ↔ Library 연결 부재 | Studio에서 `/library` 링크 0건 (grep 검증). Materials 팝오버에서 Missing 발견해도 이동 불가. Voice/Music만 link 있고 Characters/Style은 `action: "stage-tab"`만 존재 | Critical |
| P0-2 | 3계층 컨텍스트 32px 압축 | PersistentContextBar `h-8`에 3개 드롭다운. 경쟁사(InVideo 1단계, Fliki 2단계) 대비 진입 장벽 최고 | Critical |
| P0-3 | SceneCard props 과부하 | SceneCardProps top-level 필드 40개 (코드 검증). 이미 6개 서브컴포넌트로 분해되어 있으나 ScenesTab에서 props drilling으로 조립. SceneContext.tsx가 존재하나 미사용 | Critical |
| P1-1 | Library CRUD 패턴 4가지 혼재 | Characters(별도 /[id] 페이지), Styles(인라인 우측 패널), Voices/Music(상단 인라인 폼), LoRAs(읽기 전용) | High |
| P1-2 | Settings에 이질적 항목 | Trash(콘텐츠 복구), YouTube(퍼블리싱) — 설정이 아님 | High |
| P1-3 | ContextBar가 Library/Settings에서도 표시 | Library는 시리즈 컨텍스트와 무관한 전체 에셋 공간인데 채널/시리즈 드롭다운 노출 | High |
| P2-1 | Home이 허브 역할 부재 | HomeVideoFeed만 렌더링. 단, WelcomeBar/QuickStatsBar/ContinueWorkingSection은 이미 존재 — 개선 수준 | Medium |
| P2-2 | PipelineStatusDots 5개 vs 탭 4개 불일치 | Dots: Script/Stage/Images/Render/Video, 탭: Script/Stage/Direct/Publish | Medium |
| P2-3 | 전문 용어 노출 | LoRAs(Library 탭), Stage/Direct(Studio 탭), Dev(NavBar) | Medium |
| P2-4 | Ghost route/컴포넌트 잔존 | /scripts, /storyboards(page.tsx redirect), AppMobileTabBar(import 0건) | Low |

### 에이전트 크로스 리뷰 종합

**Frontend Dev 발견:**
- `SceneContext.tsx`가 이미 존재 (SceneDataContext 22필드 + SceneCallbacksContext 17필드) — 미사용 상태. Compound 패턴 신규 도입보다 기존 Context 활성화가 변경 범위 최소
- 한국어화 시 E2E/VRT 테스트 **13-15개 파일** 동시 수정 필요 (당초 8-10개 추정은 과소)
- `AppSidebar`는 Phase D Master-Detail에 재활용 가능 — 삭제 보류
- SceneContext에 **TTS 관련 4개 props 미정의** — Context 활성화 전 추가 필요

**UX Engineer 발견:**
- Characters는 편집 깊이(LoRA, 프롬프트, Gemini 편집, 5-step 위자드)가 커서 우측 패널로 불충분 → 전용 페이지 유지
- LoRAs는 "제거"가 아닌 "Admin 이전" — Service API에서 Admin으로 위치 변경
- Library/Settings에서 ContextBar 숨기기 추가 제안
- 채널/시리즈 1개일 때 ContextBar 자동 숨기기 (Progressive Disclosure)
- Stage 탭 토글 4개(자동 리라이트/안전 태그/고해상도/Veo)도 기본/고급 분리 대상

**Tech Lead 발견:**
- Phase 0 필요: SP-028, SP-027, SP-040 PR 머지가 선행 조건
- SP-021(Speaker 동적 역할)을 Phase B↔C 사이에 배치해야 SceneCard speaker props 설계 안정
- C-7 진짜 문제는 SceneCard 자체가 아니라 ScenesTab의 13개+ action handler glue code
- C-9에 feature flag(`use3PanelLayout`) 도입하여 즉시 롤백 가능하게
- B-5(Settings 재배치)는 Trash 이동 + YouTube 변경 2개로 분할

**PM 발견:**
- ROADMAP.md에 Phase 미등록 — Phase 39 등록 필요
- SP-055는 12파일 초과 — SP-055a/SP-055b로 분리 필수 (SDD 원칙)
- SP-049~061 backlog.md 미등록
- SP-021 지연 시 Phase C 전체 블로킹 — 크리티컬 패스 표시 필요

---

## 2. Phase 구조 및 의존성

```
Phase 0: PR 머지 (SP-028 #122, SP-027 #126, SP-040 #125)
    |
Phase A: Quick Wins ──── 3태스크 병렬 ──── 1~2일
    |
Phase B: 중규모 ──────── 4태스크 병렬 ──── 1~2주
    |                    + SP-021 (Speaker, 크리티컬 패스)
    |
Phase C: Direct 3패널 ── 5태스크 순차 ──── 2~3주
    |
Phase D: Library 통일 ── 5~6태스크 ─────── 1~2주
```

### 태스크 의존성 그래프

```
SP-028 머지 ─┐
SP-027 머지 ─┼──→ SP-050 (라벨 한국어화)
             └──→ SP-055a (SceneContext 도입)

SP-050 ─┐
SP-051 ─┼─ 병렬 (Phase A)
SP-052 ─┘

SP-053 ─┐
SP-054a ─┼─ 병렬 (Phase B)
SP-054b ─┤
SP-049  ─┘  (Home 개선)

SP-021 (Speaker, 크리티컬 패스) ──→ SP-055a (SceneContext 도입)

SP-058 (Direct E2E 보강) ← SP-055a 착수 전 완료

SP-055a ──→ SP-055b (Props→Context 전환) ──→ SP-056 (속성 패널) ──→ SP-057 (3패널 통합)

SP-059 (Master-Detail 공통) ──→ SP-060a (Styles)
                                SP-060b (Voices) ── 탭별 병렬
                                SP-060c (Music)
SP-061 (LoRAs Admin 이전) ← SP-060a 완료 후
```

**크리티컬 패스**: SP-021 → SP-055a → SP-055b → SP-056 → SP-057
SP-021 지연 시 Phase C 전체가 밀림. 완화: Phase B 기간 내 SP-021 완료 목표, 미완료 시 Phase C를 Phase D와 순서 교환 가능.

---

## 3. Phase A: Quick Wins

### SP-050 — UI 라벨 한국어화 + Dev 제거

**선행**: SP-028 + SP-027 머지 (같은 파일 `StudioWorkspaceTabs.tsx` 근처 터치)

**변경 파일 (13~15개):**

소스 코드:
- `ServiceShell.tsx` — NavBar 라벨 한국어화 + DEV_ITEM 블록 제거
- `StudioWorkspaceTabs.tsx` — TABS label: Script→대본, Stage→준비, Direct→이미지, Publish→게시
- `LibraryShell.tsx` — TABS label: Characters→캐릭터, Styles→화풍, Voices→음성, Music→BGM
- `SettingsShell.tsx` — TABS label: Render Presets→렌더 설정, YouTube→연동, Trash→휴지통
- `PipelineStatusDots.tsx` — STEPS label 한국어화 (Script→대본, Stage→준비, Images→이미지, Render→렌더, Video→영상)
- `PreflightModal.tsx` — STEP_LABELS 전체 한국어화 (Stage/Images/TTS/Render)
- `MaterialsPopover.tsx` — 항목 label 한국어화
- `ContinueWorkingSection.tsx` — STEP_META label 한국어화 (Script/Edit/Publish/Done)
- `QuickStatsBar.tsx` — 카테고리 label 한국어화 (Characters/Styles/Voices/Music)
- `constants/index.ts` — AUTO_RUN_STEPS label 한국어화 (Images/Render 등)

테스트:
- `e2e/smoke.spec.ts` — 버튼명 매칭 업데이트
- `e2e/qa-patrol.spec.ts` — 버튼명 매칭 업데이트
- `tests/vrt/studio-e2e.spec.ts` — 버튼명 매칭 업데이트 (11곳)
- `tests/vrt/home.spec.ts` — NavBar 링크명 업데이트
- `tests/vrt/warning-toast-e2e.spec.ts` — 버튼명 업데이트

**DoD:**
- [ ] NavBar: 홈, 스튜디오, 라이브러리, 설정 (Dev 항목 제거)
- [ ] Studio 탭: 대본, 준비, 이미지, 게시 (key 값 script/stage/direct/publish 유지, URI 딥링크 호환)
- [ ] Library 탭: 캐릭터, 화풍, 음성, BGM, LoRAs(Phase D에서 제거 예정)
- [ ] Settings 탭: 렌더 설정, 연동, 휴지통
- [ ] PipelineStatusDots label 전체 한국어화
- [ ] PreflightModal STEP_LABELS 전체 한국어화
- [ ] ContinueWorkingSection STEP_META 한국어화
- [ ] QuickStatsBar 카테고리 한국어화
- [ ] AUTO_RUN_STEPS 한국어화
- [ ] Dev는 NavBar에서 제거, `/dev` URL 직접 접근은 유지
- [ ] E2E 테스트: 영문 라벨 매칭 → 한국어 라벨 매칭으로 **수정** (테스트가 "통과 대상"이 아니라 "수정 대상")
- [ ] VRT 베이스라인 전체 갱신
- [ ] 빌드 에러 0개

**비고**: 파일 수 13-15개지만 변경 내용은 문자열 교체 위주. 로직 변경 없음.

---

### SP-051 — Ghost Route/컴포넌트 삭제

**변경 파일 (3~4개):**
- `app/(service)/scripts/page.tsx` — 삭제 (useRouter redirect → next.config redirect로 이전)
- `app/(service)/storyboards/page.tsx` — 삭제 (redirect → next.config redirect로 이전)
- `app/components/layout/AppMobileTabBar.tsx` — 삭제 (import 0건 확인)
- `next.config.ts` — redirect 규칙 추가

**next.config redirect 동작** (Tech Lead 검증):
- Next.js redirect에서 query string은 자동 전달됨
- `/scripts?id=123` → `/studio?id=123` 정상 동작
- 단, query 없는 `/scripts` 접근 시 `/studio`로 이동 (현재 page.tsx에서는 `/`로 이동)

**DoD:**
- [ ] `/scripts?id=X` → `/studio?id=X` 리다이렉트 정상 (next.config, query 자동 전달)
- [ ] `/scripts?new=true` → `/studio?new=true` 리다이렉트 정상
- [ ] `/scripts` (query 없음) → `/studio` 리다이렉트 (기존 `/`와 동작 변경 — Studio에서 Kanban 표시되므로 허용)
- [ ] `/storyboards` → `/` 리다이렉트 정상
- [ ] AppMobileTabBar.tsx 삭제됨
- [ ] redirect E2E 테스트 추가 (3경로 검증)
- [ ] 빌드 에러 0개, 기존 테스트 전체 통과

**보류 (Phase C/D 판단):**
- `AppSidebar.tsx` — Phase D Master-Detail에 재활용 가능성
- `AppThreeColumnLayout.tsx` — Phase C 3패널에 재활용 가능성

**Phase 31 중복 확인**: Phase 31(UX Navigation Overhaul) ARCHIVED 문서와 대조하여, /scripts, /storyboards, AppMobileTabBar가 이미 처리되지 않았음을 SP-051 착수 전 확인할 것.

---

### SP-052 — Materials 팝오버 Library 직접 링크

**변경 파일 (1~2개):**
- `MaterialsPopover.tsx` — Characters/Style 항목에 조건부 `link` 추가

**현재 상태 (코드 확인):**
- Voice: `link: "/library/voices"` — 이미 있음
- Music: `link: "/library/music"` — 이미 있음
- Characters: `action: "stage-tab"` — Library 링크 없음
- Style: `action: "stage-tab"` — Library 링크 없음

**구현 패턴**: ready 상태면 `action`(Stage 탭 이동), missing 상태면 `link`(Library 이동) 우선. 기존 `action`/`link` 프로퍼티 분기 구조를 활용하여 `missing` 시에만 `link`를 오버라이드.

**DoD:**
- [ ] Characters Missing 상태에서 클릭 → `/library/characters` 이동
- [ ] Style Missing 상태에서 클릭 → `/library/styles` 이동
- [ ] Ready 상태에서는 기존 동작(stage-tab) 유지
- [ ] Missing 상태 링크에 "만들기 →" 텍스트 표시
- [ ] 빌드 에러 0개

---

## 4. Phase B: 중규모

### SP-053 — ContextBar 개선

**변경 파일 (2~3개):**
- `PersistentContextBar.tsx` — h-8→h-10, 아이콘 추가, Library/Settings에서 숨기기
- CSS 변수 영향 확인 (Studio 작업 영역 높이)

**DoD:**
- [ ] ContextBar 높이: h-10 (40px)
- [ ] 채널/시리즈 아이콘 추가 (폴더 아이콘)
- [ ] Library 페이지(`/library/*`)에서 ContextBar 숨김 (`pathname.startsWith("/library")` 판정)
- [ ] Settings 페이지(`/settings/*`)에서 ContextBar 숨김
- [ ] 채널 1개 + 시리즈 1개인 경우 ContextBar 자동 숨김 — `useProjectGroups()` 훅의 `projects.length === 1 && groups.length === 1` 조건. **로딩 중에는 숨기지 않음** (로딩 완료 후 판정)
- [ ] Studio 작업 영역 높이 감소 체감 확인 (VRT)
- [ ] VRT 베이스라인 갱신

---

### SP-054a — Settings 재배치: Trash → Library 이동

**변경 파일 (5~6개):**
- `SettingsShell.tsx` — Trash 탭 제거
- `LibraryShell.tsx` — 하단에 Trash 링크 추가 (탭이 아닌 하단 독립 링크)
- `app/(service)/library/trash/page.tsx` — 신규 (기존 TrashTab 컴포넌트 재사용)
- `app/(service)/settings/trash/page.tsx` — redirect로 전환 (`/library/trash`)
- `next.config.ts` — `/settings/trash` → `/library/trash` redirect 추가 (북마크 대응)

**DoD:**
- [ ] `/library/trash` 경로에서 휴지통 정상 표시
- [ ] `/settings/trash` → `/library/trash` 리다이렉트
- [ ] Library 탭바 하단에 "휴지통" 링크 (별도 섹션, 탭과 시각적 구분)
- [ ] Settings 탭: 렌더 설정, 연동 (2개)
- [ ] 빌드 에러 0개

---

### SP-054b — Publish 탭에 YouTube 연동 진입점 추가

**주의**: Settings 탭 라벨 "연동"은 SP-050에서 이미 처리됨. 이 태스크는 **Publish 탭 진입점 추가만** 담당.

**변경 파일 (2~3개):**
- Publish 탭 컴포넌트 — YouTube 연동 상태 인라인 표시 추가
- YouTube OAuth 상태 확인: `useYouTubeTab()` 훅의 기존 `isConnected` 상태 활용

**DoD:**
- [ ] Publish 탭에 YouTube 연동 상태 배지 표시 (연결됨: 초록 배지 / 미연결: 회색 배지)
- [ ] 연동 상태는 `useYouTubeTab()` 훅의 `isConnected` 필드 사용 (신규 API 없음)
- [ ] 미연결 시 "설정 > 연동에서 연결 →" 링크 (`/settings/youtube`)
- [ ] 빌드 에러 0개

---

### SP-049 — Home 대시보드 개선

**현재 상태 (코드 확인):**
- `HomeVideoFeed.tsx`에 WelcomeBar, QuickStatsBar, ContinueWorkingSection, ShowcaseSection 이미 존재
- SetupWizard도 Home에서 트리거됨 (PersistentContextBar.tsx:117)

**변경 파일 (3~5개):**
- `WelcomeBar.tsx` — "빠른 시작" 입력 필드 추가
- `ContinueWorkingSection.tsx` — 진행 상태 5단계 dots 추가
- `QuickStatsBar.tsx` — 채널 개요 강화

**SetupWizard와의 관계**: WelcomeBar의 "빠른 시작"은 SetupWizard의 **간소화 버전**. 채널/시리즈가 없는 초기 사용자는 기존 SetupWizard 플로우 유지, 이미 채널/시리즈가 있는 사용자에게 "빠른 시작" 표시. 채널/시리즈 자동 생성은 기존 API 조합 사용: `POST /api/projects` → `POST /api/groups` → `POST /api/storyboards` → `/studio?id=X` redirect.

**DoD:**
- [ ] WelcomeBar에 주제 입력 필드 추가 (채널/시리즈가 이미 존재하는 경우에만 표시)
- [ ] 입력 시 기존 API 3개 순차 호출 (project 생성 → group 생성 → storyboard 생성) → `/studio?id=X` 이동
- [ ] SetupWizard 완료 후 ContextStore의 `projectId`/`groupId` 자동 설정 (`setProjectId()`, `setGroupId()` 호출)
- [ ] ContinueWorkingSection 각 카드에 진행 상태 표시 (대본/준비/이미지/렌더/완성)
- [ ] 기존 ShowcaseSection 유지
- [ ] 채널/시리즈가 없는 초기 사용자: 기존 SetupWizard 동작 유지 (변경 없음)
- [ ] VRT 베이스라인 갱신

---

## 5. Phase C: Direct 3패널

### SP-058 — Direct 탭 E2E 테스트 보강 (안전망, Phase C 선행)

**목적**: Phase C 리팩토링 전에 회귀 방지 안전망 구축

**DoD:**
- [ ] Direct 탭 핵심 플로우 E2E 시나리오 (SD WebUI 모킹 사용):
  - 씬 선택 → 이미지 생성 **트리거** 확인 (API 호출 발생, 실제 생성은 mock)
  - 씬 프롬프트 편집 → 저장 → DB 반영
  - 씬 삭제 → 목록 갱신
  - TTS 미리보기 버튼 클릭 → 오디오 플레이어 표시
- [ ] 기존 `studio-e2e.spec.ts` 확장 또는 별도 spec
- [ ] 모킹 전략: SD WebUI/TTS API는 `page.route()` 인터셉트로 fixture 응답

---

### SP-055a — SceneContext Provider 도입 (호환 레이어)

**선행**: SP-021 (Speaker 동적 역할) 머지 (크리티컬 패스)

**접근**: 기존 `SceneContext.tsx` 활성화. **기존 props는 유지하면서** Context를 병렬 제공.

**SceneContext 현재 상태 (코드 확인):**
- `SceneDataContext`: 22개 필드 정의됨
- `SceneCallbacksContext`: 17개 필드 정의됨
- `SceneProvider`, `useSceneContext()`: 구현 완료, 미사용

**전제조건**: SceneContext에 TTS 관련 4개 필드 추가 필요 (현재 미정의):
- `ttsState`, `onTTSPreview`, `onTTSRegenerate`, `audioPlayer`

**변경 파일 (5~7개):**
- `SceneContext.tsx` — TTS 4개 필드 추가 + Provider 활성화
- `ScenesTab.tsx` — SceneCard 호출부를 SceneProvider로 래핑
- `SceneCard.tsx` — 내부에서 useSceneContext() 접근 가능하도록 구조 변경 (기존 props도 유지)
- 단위 테스트 — SceneProvider 없이 useSceneContext() 호출 시 에러 발생 확인

**DoD:**
- [ ] SceneContext에 TTS 관련 4개 필드 추가됨
- [ ] ScenesTab에서 SceneProvider로 SceneCard를 래핑
- [ ] SceneCard 내부에서 `useSceneContext()` 접근 가능
- [ ] **기존 SceneCard props는 모두 유지** (호환성, 이 태스크에서 제거하지 않음)
- [ ] 기존 Direct 탭 모든 기능 동일하게 동작 (E2E 통과)
- [ ] 시각적 변경 없음 (VRT 차이 0)

---

### SP-055b — Props → Context 전환 (Props Drilling 해소)

**선행**: SP-055a

**변경 파일 (7~9개):**
- `SceneCard.tsx` — props 축소 (scene, sceneIndex + 최소 제어)
- `SceneImagePanel.tsx` — useSceneContext() 전환
- `SceneActionBar.tsx` — useSceneContext() 전환
- `SceneEssentialFields.tsx` — useSceneContext() 전환
- `ScenePromptFields.tsx` — useSceneContext() 전환
- `SceneSettingsFields.tsx` — useSceneContext() 전환
- `SceneGeminiModals.tsx` — useSceneContext() 전환
- `ScenesTab.tsx` — SceneCard 호출부에서 불필요해진 props 제거
- (검토) `SceneEditImageModal.tsx`, `SceneClothingModal.tsx` — SceneCard 내부에서 사용, Context 범위 내

**DoD:**
- [ ] SceneCard props: top-level 40개 → 5개 이하 (scene, sceneIndex + 최소 제어)
- [ ] 서브컴포넌트 6개 이상이 useSceneContext()로 데이터/콜백 소비
- [ ] ScenesTab의 action handler glue code가 SceneProvider 내부로 이동
- [ ] 기존 Direct 탭 모든 기능 동일하게 동작 (E2E 통과)
- [ ] 시각적 변경 없음 (VRT 차이 0)
- [ ] Context 전달 무결성 단위 테스트: SceneProvider 없이 useSceneContext() 호출 시 에러

---

### SP-056 — 속성 패널 컴포넌트 (기본/고급 분리)

**선행**: SP-055b

**변경 파일 (3~5개):**
- `ScenePropertyPanel.tsx` — 신규 컴포넌트
- SceneCard에서 Tier 2-4 (Customize, Scene Tags, Advanced) 섹션 추출
- 기본 탭: 프롬프트, 스피커, 태그
- 고급 탭: ControlNet, IP-Adapter, LoRA, 검증 (기본 접힘)

**DoD:**
- [ ] ScenePropertyPanel 컴포넌트 독립 렌더링 테스트 통과
- [ ] [기본] 탭: 프롬프트, 스피커, 태그 표시
- [ ] [고급] 탭: ControlNet, IP-Adapter, LoRA 설정 (기본 접힘 상태)
- [ ] useSceneContext() 소비 (SP-055b 의존)
- [ ] 아직 Direct 탭에 미통합 (독립 컴포넌트)

---

### SP-057 — Direct 3패널 레이아웃 통합

**선행**: SP-055b, SP-056

**변경 파일 (3~5개):**
- `ScenesTab.tsx` — 2컬럼 → 3컬럼 레이아웃
- `variants.ts` — STUDIO_3COL_LAYOUT 상수 추가
- feature flag: `use3PanelLayout` (롤백 안전장치)
- (검토) `AppThreeColumnLayout.tsx` 재활용 여부 결정 → 사용하면 삭제 보류 해제, 미사용이면 삭제

```
AS-IS: [SceneList 280px] [SceneCard flex-1]
TO-BE: [SceneList 240px] [SceneCard flex-1] [PropertyPanel 300px]
```

**DoD:**
- [ ] 3패널 레이아웃: 씬 목록 | 씬 카드(미리보기+텍스트+액션) | 속성 패널
- [ ] feature flag `use3PanelLayout`로 2패널/3패널 전환 가능
- [ ] SceneCard에서 설정 영역 제거 → PropertyPanel로 이동
- [ ] 모바일(< 1024px): "데스크톱에서 이용하세요" 안내 (Studio는 데스크톱 전용)
- [ ] AppThreeColumnLayout.tsx 처리 결정 (재활용 또는 삭제)
- [ ] Direct 탭 E2E 전체 통과 (SP-058 시나리오)
- [ ] VRT 베이스라인 갱신

---

## 6. Phase D: Library 통일

### SP-059 — Master-Detail 공통 레이아웃 컴포넌트

**변경 파일 (2~3개):**
- `LibraryMasterDetail.tsx` — 신규 공통 컴포넌트 (좌측 목록 | 우측 상세)
- `AppSidebar.tsx` 재활용 검토 (목록 패널 역할) → 재활용이면 보류 해제, 미사용이면 삭제

**DoD:**
- [ ] LibraryMasterDetail 컴포넌트: `items: T[]`, `selectedId: number | null`, `onSelect: (id) => void`, `renderDetail: (item: T) => ReactNode` props
- [ ] 좌측: 아이템 리스트 (검색, 필터, + 추가 버튼)
- [ ] 우측: 선택된 아이템 상세/편집
- [ ] 반응형: 모바일에서는 목록만 → 클릭 시 상세 전체화면
- [ ] AppSidebar.tsx 처리 결정 (재활용 또는 삭제)
- [ ] 독립 렌더링 테스트 통과

---

### SP-060a — Styles → Master-Detail 전환

**현재**: 카드 그리드 + 하단 인라인 에디터 (StyleProfileEditor)
**TO-BE**: LibraryMasterDetail 적용 (좌측 목록 | 우측 StyleProfileEditor)

**DoD:**
- [ ] Styles 페이지가 LibraryMasterDetail 사용
- [ ] 기존 CRUD 기능 동일 동작: 생성/편집/삭제/복제 각각 E2E 검증
- [ ] VRT 베이스라인 갱신

---

### SP-060b — Voices → Master-Detail 전환

**현재**: 상단 인라인 폼 + 카드 그리드
**TO-BE**: LibraryMasterDetail 적용 (좌측 목록 | 우측 편집 폼)

**DoD:**
- [ ] Voices 페이지가 LibraryMasterDetail 사용
- [ ] 기존 CRUD + TTS 미리보기 동일 동작: E2E 검증
- [ ] VRT 베이스라인 갱신

---

### SP-060c — Music → Master-Detail 전환

**현재**: 상단 인라인 폼 + 카드 그리드 (Voices와 동일 패턴)
**TO-BE**: LibraryMasterDetail 적용

**DoD:**
- [ ] Music 페이지가 LibraryMasterDetail 사용
- [ ] 기존 CRUD + BGM 미리보기 동일 동작: E2E 검증
- [ ] VRT 베이스라인 갱신

---

### SP-061 — LoRAs 탭 제거 + Admin 이전

**현재**: Library에 읽기 전용 탭, "Manage in Dev" 링크
**TO-BE**: Library에서 제거, `/dev` (Admin) 에서만 관리. 화풍(Styles) 상세에 LoRA 선택은 이미 존재.

**변경 파일 (2~3개):**
- `LibraryShell.tsx` — LoRAs 탭 항목 제거
- `app/(service)/library/loras/page.tsx` — 삭제 또는 `/dev/sd-models` redirect
- `next.config.ts` — `/library/loras` → `/dev/sd-models` redirect 추가

**DoD:**
- [ ] Library 탭에서 LoRAs 제거
- [ ] `/library/loras` → `/dev/sd-models` redirect (기존 북마크 대응)
- [ ] 화풍(Styles) 상세의 LoRA 선택 기능 정상 동작 확인
- [ ] 빌드 에러 0개

---

### Characters 전용 페이지 유지 (변경 없음)

**근거** (UX Engineer 검토):
- 편집 필드 20개+, 5-step 위자드, Gemini 편집 모달, LoRA/IP-Adapter 설정
- 300px 우측 패널에 수용 불가
- 현재 `/library/characters/[id]` 전용 페이지 패턴이 적합
- Master-Detail 통일 대상에서 제외

---

## 7. 리스크 및 완화

| Phase | 최대 리스크 | 완화 전략 |
|-------|-----------|-----------|
| A | SP-050 한국어화 시 테스트 13-15개 깨짐 | SP-028+SP-027 머지 후 진행, 테스트 동시 수정. 로직 변경 없으므로 리스크 낮음 |
| B | SP-021 지연 → Phase C 전체 블로킹 | **크리티컬 패스**. SP-021 미완료 시 Phase D를 먼저 진행 (순서 교환) |
| B | ContextBar 높이 변경 → Studio 작업 영역 감소 | VRT로 체감 확인, 필요시 롤백 |
| B | Settings URL 변경 → 북마크 깨짐 | next.config redirect 유지 |
| C | **Direct 탭 regression (최대 리스크)** | SP-058 E2E 안전망 선행, feature flag 도입, SP-055 2단계 분해 |
| C | SceneContext TTS 필드 미정의 | SP-055a에서 TTS 4개 필드 추가를 전제조건으로 명시 |
| D | Library 4페이지 동시 리팩토링 | 탭별 개별 PR: Styles → Voices → Music 순 |

---

## 8. 테스트 전략

| Phase | 주요 테스트 유형 | 구체적 전략 |
|-------|----------------|------------|
| A (라벨/삭제) | VRT + E2E | VRT 베이스라인 전체 갱신. E2E는 "수정 대상" (영문→한국어 매칭). SP-051에 redirect 검증 E2E 추가 |
| B (ContextBar/Home) | VRT + E2E | ContextBar 숨김 조건 E2E 검증. Home 컴포넌트 VRT |
| C (SceneCard/3패널) | **단위 테스트** + E2E | Context 전달 무결성 단위 테스트 (Provider 없이 호출 시 에러). Direct 탭 전체 플로우 E2E. SD/TTS API는 `page.route()` 모킹 |
| D (Library 통일) | VRT + E2E | 각 탭 CRUD E2E 검증 (생성/편집/삭제 각각). VRT 베이스라인 갱신 |

---

## 9. 전체 실행 타임라인

```
Week 1:   Phase 0 (PR 머지) + Phase A (3태스크 병렬)
Week 2-3: Phase B (4태스크 병렬) + SP-021 (Speaker, 크리티컬 패스)
Week 4:   SP-058 (E2E 보강) + SP-055a (Context 도입)
Week 5:   SP-055b (Props 전환)
Week 6:   SP-056 (속성 패널) + SP-057 (3패널 통합)
Week 7:   SP-059 (공통 컴포넌트) + SP-060a (Styles)
Week 8:   SP-060b (Voices) + SP-060c (Music) 병렬
Week 9:   SP-061 (LoRAs Admin 이전) + 정리
Buffer:   Week 10 (SP-021 지연 시 Phase C/D 순서 교환 대응)
```

**SP-021 지연 대응**: Phase B 완료 시점에 SP-021 미완료면, Phase D를 먼저 착수 (Phase C와 D는 상호 독립).

---

## 10. 미적용 판단 사항

| 제안 | 판단 | 이유 |
|------|------|------|
| Characters → Master-Detail 패널 | 미적용 | 편집 깊이가 패널로 불충분 (UX Engineer) |
| 모바일 3패널 스와이프 | 미적용 | 개발 비용 대비 효과 낮음, Studio는 데스크톱 전용 (UX Engineer) |
| PipelineStatusDots 4개로 축소 | Phase C에서 판단 | 3패널 전환 시 함께 검토 |
| Stage 토글 기본/고급 분리 | 별도 태스크 | IA 리디자인 범위 밖, 독립 UX 개선 |

---

## 11. 후속 작업 (명세 외)

- [ ] ROADMAP.md에 Phase 39(IA Redesign) 등록
- [ ] backlog.md에 SP-049~SP-061 등록
- [ ] SP-047, SP-048 공백 처리 (의도적 건너뜀 주석)
- [ ] Phase 31 ARCHIVED 문서와 SP-051 중복 대조 확인
