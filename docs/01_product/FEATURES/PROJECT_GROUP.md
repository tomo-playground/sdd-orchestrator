# Project(Channel) & Group(Story Group) System

**상태**: Phase 0 완료, Phase 1 진행중 (1-2~1-5 완료, 1-1 미착수)
**우선순위**: P1 (Phase 6-7 이후, 7-1 병렬 가능)
**최종 갱신**: 2026-02-02

---

## 1. 현황 분석

### 존재하는 것 (Phase 0 완료 후 갱신)
| 항목 | 상태 | 비고 |
|------|------|------|
| ORM 모델 | `Project`, `Group` 정의 완료 | `backend/models/project.py`, `group.py` |
| Alembic 마이그레이션 | **구현 완료** | `f0a1b2c3d4e5` - projects, groups 테이블 + seed 데이터 |
| Frontend 상태 | `projectId`, `groupId` in metaSlice | `null` 초기값, `useProjectGroups` 훅이 자동 선택 |
| `?? 1` 하드코딩 | **제거 완료** | guard + early return 패턴으로 전환 (7개소) |
| Storage 경로 | `projects/{p_id}/groups/{g_id}/storyboards/{s_id}/` | `asset_service.py`에서 사용 중 |
| Storyboard 모델 | `group_id` FK **연결됨** | nullable, Phase 1-4에서 NOT NULL 전환 예정 |
| CRUD API | Project + Group CRUD 완료 | `routers/projects.py`, `routers/groups.py` |
| Context Bar | ContextBar + 드롭다운 완료 | `components/context/` 패키지 |
| Seed 데이터 | Default Project(id=1) + Default Group(id=1) | Alembic 마이그레이션 포함 |
| Activity Log | `project_id`, `group_id` **없음** | 분석 불가 (Phase 0-1.7 미착수) |

### 없는 것
- 설정 상속 체계 (Project -> Group -> Storyboard) — Phase 1-1
- Cmd+K Quick Switcher — Phase 1-2.3
- `activity_logs` project_id/group_id 컬럼 — Phase 0-1.7

---

## 2. 에이전트 아이디어 통합 분석

### 2.1 중복/유사 아이디어 그룹핑

53개 아이디어를 **12개 통합 테마**로 정리.

| # | 통합 테마 | 원본 아이디어 (에이전트) | 엣지 등급 |
|---|----------|------------------------|----------|
| T1 | **계층 CRUD + DB 정합성** | DBA-1(FK+CASCADE), DBA-2(JSONB settings), DBA-7(2단계 마이그레이션) | Foundation |
| T2 | **설정 상속 체인** | Backend-1(3단계 config 상속), Prompt-1(Style DNA), Prompt-5(Negative 프로필), FFmpeg-1(렌더링 프리셋), FFmpeg-2(BGM 프로필) | **Core Edge** |
| T3 | **Context Bar + Navigation** | Frontend-1(브레드크럼), UI/UX-1(계층 브레드크럼), UI/UX-2(Quick Switcher), Frontend-5(Cmd+K) | Core |
| T4 | **프로젝트/그룹 템플릿** | Backend-2(프로젝트 템플릿), Frontend-4(Smart Group Templates), Storyboard-3(Template Story) | **Core Edge** |
| T5 | **서사 톤 + 세계관 주입** | Storyboard-1(Narrative Tone), Storyboard-4(World Building), Storyboard-2(Recurring Character Pool) | **Top Edge** |
| T6 | **채널별 태그 정책 + 추천** | Backend-4(화이트/블랙리스트), Backend-9(계층형 추천), Prompt-3(Tag Effectiveness), Prompt-2(그룹별 프롬프트) | **Top Edge** |
| T7 | **에피소드 연결 + 학습** | Storyboard-5(Multi-Episode Arc), Storyboard-7(Success Pattern), Backend-7(교차 참조), Frontend-7(Context Suggestions) | **Top Edge** |
| T8 | **배치 렌더링 + 큐** | Backend-3(Redis/Celery 큐), FFmpeg-4(그룹 일괄 렌더), Frontend-8(Bulk Operations) | Advanced |
| T9 | **브랜딩 + 플랫폼 출력** | FFmpeg-3(인트로/아웃트로), FFmpeg-5(플랫폼별 프로필), FFmpeg-6(워터마크), FFmpeg-7(전환 스타일 통일) | Advanced |
| T10 | **분석 대시보드** | Frontend-6(Group Analytics), Prompt-6(그룹 간 비교), Backend-8(비용 관리), DBA-6(activity_log 확장) | Advanced |
| T11 | **UI/UX 세부** | UI/UX-3(Progressive Disclosure), UI/UX-4(Empty States), UI/UX-5(색상 코딩), UI/UX-6(D&D), UI/UX-7(Saved Views) | Polish |
| T12 | **스타일 전이 + A/B** | Backend-5(A/B 테스트), Backend-6(커스텀 레이어), Prompt-4(캐릭터 override), Prompt-7(스타일 전이), Frontend-3(Asset Library) | Future |

### 2.2 엣지 기준 평가

**"엣지"란**: 다른 쇼츠 제작 도구에 없는 차별화 + 제작 효율 극적 개선 + 지능적 자동화

| 등급 | 의미 | 선정 기준 |
|------|------|----------|
| **Top Edge** | 이 프로젝트만의 핵심 차별화 | 다른 영상 도구에 존재하지 않는 기능 |
| **Core Edge** | 강력한 생산성 향상 | 채널 운영 효율을 5배 이상 개선 |
| **Core** | 필수 기반 | 없으면 프로젝트/그룹이 무의미 |
| **Foundation** | DB/인프라 기초 | 모든 기능의 전제 조건 |
| **Advanced** | 고도화 | 있으면 좋지만 후순위 |
| **Future** | 미래 확장 | Phase 8+ 이후 |

---

## 3. Phase별 실행 계획

### Phase 0: Foundation (DB + CRUD Skeleton)

**목표**: Project/Group 테이블이 실제로 존재하고, Storyboard가 Group에 연결되며, 기본 CRUD가 동작하는 상태.
**기간**: 1주
**선행**: 없음 (6-7과 병렬 가능)

#### 0-1. DB 마이그레이션 (DBA)

| # | 작업 | 원본 아이디어 | 상태 |
|---|------|-------------|------|
| 1 | `f0a1b2c3d4e5` 마이그레이션 구현 (projects + groups 테이블 CREATE) | DBA-1 | [x] |
| 2 | `storyboards` 테이블에 `group_id` FK 추가 (nullable, Phase 1-4에서 NOT NULL) | DBA-1, DBA-7 | [x] |
| 3 | `groups` 테이블에 렌더 디폴트 컬럼 11개 추가 → `render_presets` 테이블로 분리 (1-5) | DBA-2 | [x] |
| 4 | `projects` 테이블 (name, description, handle, avatar_url) | DBA-2 | [x] |
| 5 | Seed 데이터: Default Project(id=1) + Default Group(id=1) 삽입 | DBA-7 | [x] |
| 6 | 기존 storyboards 전부 `group_id=1` 할당 (data migration) | DBA-7 | [x] |
| 7 | `activity_logs`에 `project_id`, `group_id` 컬럼 추가 (nullable) | DBA-6 | [ ] |
| 8 | 복합 인덱스: `(project_id, deleted_at)`, `(group_id, deleted_at)` | DBA-4 | [ ] |

**Settings JSONB 초기 스키마**:
```json
// Project.settings
{
  "default_sd_model_id": null,
  "default_style_profile_id": null,
  "default_negative_prompt": null,
  "default_voice": "ko-KR-SunHiNeural",
  "default_bgm_category": null,
  "rendering": {
    "resolution": "512x768",
    "fps": 30,
    "crf": 20,
    "include_scene_text": true
  },
  "narrative_tone": null,
  "world_building_context": null,
  "allowed_tags": [],
  "forbidden_tags": []
}

// Group.settings (동일 구조, null = 프로젝트 설정 상속)
{
  "default_sd_model_id": null,
  "default_style_profile_id": null,
  "default_narrative_tone": "dramatic",
  "jinja2_template_override": null
}
```

#### 0-2. Backend CRUD API (Backend Dev)

| # | 작업 | 상태 |
|---|------|------|
| 1 | `routers/projects.py` - Project CRUD (GET list, GET detail, POST, PUT, DELETE) | [x] |
| 2 | `routers/groups.py` - Group CRUD (nested under project) | [x] |
| 3 | `services/project_service.py` - 비즈니스 로직 분리 | — (라우터에 인라인) |
| 4 | Storyboard API에 `group_id` + `project_id` 필터 추가 | [x] |
| 5 | `asset_service.py`에서 hardcoded project_id/group_id 제거, 동적 조회 | [ ] |

**API 설계**:
```
GET    /projects                    # 프로젝트 목록
POST   /projects                    # 프로젝트 생성
GET    /projects/{id}               # 프로젝트 상세 (groups 포함)
PUT    /projects/{id}               # 프로젝트 수정
DELETE /projects/{id}               # 프로젝트 삭제

GET    /projects/{id}/groups        # 그룹 목록
POST   /projects/{id}/groups        # 그룹 생성
GET    /groups/{id}                 # 그룹 상세
PUT    /groups/{id}                 # 그룹 수정
DELETE /groups/{id}                 # 그룹 삭제

GET    /storyboards?group_id={id}   # 그룹별 스토리보드 필터
```

#### 0-3. Frontend 기초 연결 (Frontend Dev)

| # | 작업 | 상태 |
|---|------|------|
| 1 | `useProjectGroups` 훅 — projectId/groupId 초기 로드 + 자동 선택 | [x] |
| 2 | `?? 1` / `or 1` 하드코딩 7개소 제거 (guard + early return) | [x] |
| 3 | 프로젝트/그룹 선택 UI (Popover 드롭다운 + CRUD 모달) | [x] |

**DoD (Phase 0)**: ✅ 완료
- [x] `projects`, `groups` 테이블이 DB에 존재
- [x] Default Project(id=1), Default Group(id=1) seed 데이터 존재
- [x] 기존 storyboards 전부 group_id=1 할당
- [x] Project/Group CRUD API 동작
- [x] Frontend에서 `?? 1` 하드코딩 제거
- [x] 기존 테스트 전량 통과 (835 passed)

---

### Phase 1: Core + Settings Inheritance (차별화 시작)

**목표**: 설정 상속 체인이 동작하고, 채널/시리즈 전환이 자연스러운 상태.
**기간**: 2주
**선행**: Phase 0 완료

#### 1-1. 설정 상속 엔진 -- "Cascading Config" (Backend Dev + Prompt Eng)

> 원본: Backend-1, Prompt-1, Prompt-5, FFmpeg-1, FFmpeg-2

**핵심 차별화**: 3단계 설정 상속 (Project -> Group -> Storyboard). 개별 스토리보드에서 오버라이드하지 않는 한, 상위 설정이 자동 적용. **다른 쇼츠 도구에는 없는 기능.**

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `services/config_resolver.py` - 3단계 설정 병합 엔진 구현 | Backend | [ ] |
| 2 | `GET /projects/{id}/effective-config` - 프로젝트 유효 설정 반환 | Backend | [ ] |
| 3 | `GET /groups/{id}/effective-config` - 그룹 유효 설정 (프로젝트 + 그룹 병합) | Backend | [ ] |
| 4 | 스토리보드 생성 시 Group의 effective_config 자동 주입 | Backend | [ ] |
| 5 | **Style DNA**: Project `settings.default_sd_model_id`, `default_loras`, `quality_tags` | Prompt Eng | [ ] |
| 6 | **Negative Profile**: Project/Group 레벨 default_negative_prompt | Prompt Eng | [ ] |
| 7 | **Rendering Preset**: `render_presets` 테이블 도입 완료 (1-5), 상속 엔진 연동 미완 | FFmpeg | 부분 |
| 8 | **Audio Profile**: Group `settings.default_bgm_file`, `audio_ducking_level` | FFmpeg | [ ] |

**설정 병합 규칙**:
```python
def resolve_config(project_settings, group_settings, storyboard_overrides):
    """3단계 Cascading: Project < Group < Storyboard (가장 구체적인 것이 우선)"""
    base = DEFAULT_CONFIG.copy()
    # Level 1: Project 설정 덮어쓰기
    deep_merge(base, project_settings or {})
    # Level 2: Group 설정 덮어쓰기
    deep_merge(base, group_settings or {})
    # Level 3: Storyboard 개별 오버라이드
    deep_merge(base, storyboard_overrides or {})
    return base
```

#### 1-2. Context Bar + Navigation (Frontend Dev + UI/UX)

> 원본: Frontend-1, UI/UX-1, UI/UX-2, Frontend-5

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `ContextBar` 컴포넌트 - 브레드크럼 `[Project] > [Group] > [Storyboard]` | Frontend | [x] |
| 2 | 인라인 Popover 드롭다운으로 프로젝트/그룹 전환 (페이지 이동 없음) | Frontend | [x] |
| 3 | Home 페이지 그룹 필터 pill + 프로젝트 드롭다운 | Frontend | [x] |
| 4 | Project/Group CRUD 모달 (ProjectFormModal, GroupFormModal) | Frontend | [x] |
| 5 | Cmd+K Quick Switcher (프로젝트/그룹/스토리보드 fuzzy search) | Frontend | [ ] |
| 6 | 빈 상태(Empty State) CTA ("첫 번째 시리즈를 만들어보세요") | UI/UX | [ ] |
| 7 | 프로젝트/그룹별 색상 코딩 아이콘 | UI/UX | [ ] |

#### 1-3. 캐릭터 프로젝트 스코핑 (Backend + Frontend)

> 결정: A안 (프로젝트별 소속, `character.project_id` FK)

**배경**: 채널(프로젝트)별로 캐릭터가 다르므로 글로벌 공유 대신 프로젝트별 격리.
**영향도**: 60+ 파일 (모델, 라우터, 서비스 6개, 테스트 16개, 프론트 컴포넌트 15+)

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `characters` 테이블에 `project_id` FK 추가 (RESTRICT) + 복합 유니크 `(project_id, name)` | DBA | [x] |
| 2 | `GET /characters?project_id=X` 필터 추가 | Backend | [x] |
| 3 | `useCharacters(projectId)` 훅 파라미터 추가 | Frontend | [x] |
| 4 | Home 캐릭터 탭: 선택된 프로젝트 기준 필터링 | Frontend | [x] |
| 5 | Studio PlanTab: 캐릭터 선택기 프로젝트 스코핑 | Frontend | [x] |
| 6 | 기존 캐릭터 전부 `project_id=1` 데이터 마이그레이션 | DBA | [x] |

#### 1-4. Storyboard FK 강화 (DBA)

| # | 작업 | 상태 |
|---|------|------|
| 1 | `storyboards.group_id` NOT NULL 전환 (Phase 0에서 완료) | [x] |
| 2 | CASCADE 정책 설정: Group/Project 삭제 시 RESTRICT (삭제 방지) + 409 핸들링 | [x] |
| 3 | `storyboards` 복합 인덱스: `(group_id, created_at DESC)` | [x] |

#### 1-5. 렌더 프리셋 분리 (Backend + Frontend)

> Group의 `default_*` 11개 컬럼을 `render_presets` 테이블로 분리 (A안: 참조만, Override 없음)

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `render_presets` 테이블 + RenderPreset ORM 모델 | DBA | [x] |
| 2 | Group에서 default_* 11개 컬럼 제거, `render_preset_id` FK 추가 | DBA | [x] |
| 3 | Render Preset CRUD API (`GET/POST/PUT/DELETE`, 시스템 프리셋 수정/삭제 보호) | Backend | [x] |
| 4 | 시스템 프리셋 3종 시드 (Post 표준, Full 시네마틱, 빠른 초안) | Backend | [x] |
| 5 | GroupFormModal: 11개 입력 → 프리셋 라디오 선택 UI | Frontend | [x] |
| 6 | `loadGroupDefaults()` → `render_preset` nested 객체에서 값 추출 | Frontend | [x] |
| 7 | Render Preset 관리 UI (/manage 페이지) | Frontend | [ ] |

**DoD (Phase 1)**: 진행중
- [ ] Project 설정 변경 시 하위 Group/Storyboard에 자동 상속 (1-1)
- [ ] Group 설정에서 Project 설정 오버라이드 가능 (1-1)
- [x] ContextBar에서 프로젝트/그룹 전환 가능 (1-2)
- [x] Home 페이지 프로젝트 드롭다운 + 그룹 필터 pill (1-2)
- [ ] Cmd+K로 프로젝트/그룹/스토리보드 빠른 전환 (1-2)
- [x] `storyboards.group_id` NOT NULL, FK 관계 완전 (1-4)
- [x] 캐릭터가 프로젝트별로 격리 (`character.project_id`) (1-3)
- [x] 렌더 프리셋 테이블 분리 + CRUD API + GroupFormModal 연동 (1-5)

---

### Phase 2: Differentiation (이 프로젝트만의 엣지)

**목표**: "지능적 콘텐츠 제작 시스템"으로서의 차별화. 채널의 톤/세계관이 자동으로 콘텐츠에 반영되고, 과거 성공 데이터가 신규 제작에 활용되는 상태.
**기간**: 3주
**선행**: Phase 1 완료

#### 2-1. 서사 톤 + 세계관 자동 주입 -- "Channel DNA" (Storyboard Writer + Backend)

> 원본: Storyboard-1, Storyboard-4, Storyboard-2

**이것이 최고의 엣지**: 채널의 톤, 세계관, 등장인물 풀을 정의하면 모든 에피소드 생성 시 Gemini 프롬프트에 자동 주입. "채널의 인격"을 코드화하는 것.

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `Project.settings.narrative_tone` 스키마 정의 (톤, 타겟 연령, 말투 스타일) | Storyboard | [ ] |
| 2 | `Project.settings.world_building_context` 스키마 정의 (세계관 설정 텍스트) | Storyboard | [ ] |
| 3 | `Group.settings.recurring_characters` - 시리즈별 고정 캐릭터 풀 (character_id 배열) | Storyboard | [ ] |
| 4 | Gemini Jinja2 템플릿에 `narrative_tone`, `world_context` 변수 주입 | Backend | [ ] |
| 5 | `create_storyboard.j2` 수정: 톤/세계관 섹션 추가 | Backend | [ ] |
| 6 | Frontend: Project 설정에서 "채널 톤" 편집 UI | Frontend | [ ] |
| 7 | Frontend: Group 설정에서 "시리즈 세계관" 편집 UI | Frontend | [ ] |

**Gemini 프롬프트 주입 예시**:
```
[CHANNEL IDENTITY]
Tone: 극적이고 감성적인 일본 애니메이션 스타일. 독백 중심.
Target: 20-30대 여성, 감성 콘텐츠 선호층.
Voice: 부드럽고 차분한 여성 내레이터.

[SERIES CONTEXT]
World: 1990년대 도쿄. 오래된 카페가 배경.
Recurring Characters: 미카(주인공, 카페 직원), 하루(단골 손님)

[EPISODE REQUEST]
Topic: "첫 만남의 기억"
```

#### 2-2. 채널별 태그 정책 + 지능형 추천 -- "Tag Intelligence" (Prompt Eng + Backend)

> 원본: Backend-4, Backend-9, Prompt-3, Prompt-2

**엣지**: 채널별로 "이 채널에서 잘 먹히는 태그"를 데이터로 학습하고, Gemini에게 자동으로 추천. 수동 태그 관리를 넘어 **데이터 기반 자동 추천**.

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `tag_effectiveness`에 `project_id` 컬럼 추가 (채널별 추적) | DBA | [ ] |
| 2 | Project `settings.allowed_tags[]`, `forbidden_tags[]` 구현 | Backend | [ ] |
| 3 | 12-Layer PromptBuilder에 Project 태그 정책 적용 (forbidden 자동 제거) | Prompt Eng | [ ] |
| 4 | `GET /projects/{id}/tag-recommendations` - 프로젝트별 TOP 20 태그 추천 | Backend | [ ] |
| 5 | Gemini 템플릿에 `recommended_tags` 섹션 자동 주입 | Prompt Eng | [ ] |
| 6 | Frontend: Project 설정에서 태그 정책 편집 (whitelist/blacklist 토글) | Frontend | [ ] |

#### 2-3. 에피소드 연결 + 성공 패턴 학습 -- "Series Intelligence" (Storyboard Writer + Backend)

> 원본: Storyboard-5, Storyboard-7, Backend-7, Frontend-7

**엣지**: 시리즈의 이전 에피소드 맥락을 자동 요약하여 다음 에피소드 생성에 주입. 성공한 에피소드의 패턴(태그 조합, 씬 구조)을 자동 학습.

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `storyboards`에 `episode_number`, `recap_text` 컬럼 추가 | DBA | [ ] |
| 2 | `GET /groups/{id}/episode-context` - 이전 에피소드 요약 자동 생성 (Gemini) | Backend | [ ] |
| 3 | Gemini 템플릿에 `previous_episodes` 섹션 주입 | Storyboard | [ ] |
| 4 | `GET /groups/{id}/success-patterns` - 그룹 내 Match Rate TOP 태그 조합 추출 | Backend | [ ] |
| 5 | 성공 패턴을 Gemini "참고 예시"로 자동 주입 | Prompt Eng | [ ] |
| 6 | Frontend: Group 타임라인에서 에피소드 순서/연결 시각화 | Frontend | [ ] |

#### 2-4. 프로젝트/그룹 템플릿 -- "Quick Start" (Backend + Frontend)

> 원본: Backend-2, Frontend-4, Storyboard-3

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `project_templates` 시드 데이터 정의 (5종: 명언, 교육, 요리, 스토리, 뉴스) | Backend | [ ] |
| 2 | 템플릿 적용 API: `POST /projects?template=cooking_channel` | Backend | [ ] |
| 3 | Group 템플릿: 씬 구조 프리셋 (Hook -> 본문 -> CTA) | Storyboard | [ ] |
| 4 | Frontend: "새 프로젝트" 모달에 템플릿 카드 선택 UI | Frontend | [ ] |

**DoD (Phase 2)**:
- [ ] 프로젝트의 톤/세계관이 Gemini 생성에 자동 반영됨
- [ ] 시리즈 이전 에피소드 컨텍스트가 다음 에피소드에 주입됨
- [ ] 프로젝트별 태그 추천이 Match Rate 데이터 기반으로 동작
- [ ] 5종 프로젝트 템플릿으로 빠른 시작 가능
- [ ] 금지 태그가 프롬프트 파이프라인에서 자동 제거됨

---

### Phase 3: Advanced (Production Scale)

**목표**: 대규모 콘텐츠 제작 워크플로우. 배치 처리, 브랜딩, 분석.
**기간**: 4주+
**선행**: Phase 2 완료

#### 3-1. 배치 렌더링 + 큐 (Backend + FFmpeg)

> 원본: Backend-3, FFmpeg-4, Frontend-8

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | 백그라운드 작업 큐 인프라 (Celery + Redis or asyncio TaskGroup) | Backend | [ ] |
| 2 | `POST /groups/{id}/batch-render` - 그룹 내 전체 스토리보드 일괄 렌더 | Backend | [ ] |
| 3 | WebSocket 진행률 알림 (렌더링 상태 실시간 전달) | Backend | [ ] |
| 4 | Frontend: 배치 작업 진행 대시보드 | Frontend | [ ] |
| 5 | Frontend: 복수 스토리보드 선택 -> 일괄 작업 UI | Frontend | [ ] |

#### 3-2. 브랜딩 시스템 (FFmpeg + Frontend)

> 원본: FFmpeg-3, FFmpeg-5, FFmpeg-6, FFmpeg-7

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | Project `settings.branding` 스키마 (로고, 워터마크, 인트로/아웃트로) | Backend | [ ] |
| 2 | 인트로/아웃트로 비디오 클립 관리 API | FFmpeg | [ ] |
| 3 | 렌더링 파이프라인에 브랜딩 자동 적용 | FFmpeg | [ ] |
| 4 | 플랫폼별 출력 프로필 (Shorts 9:16, TikTok, Reels) | FFmpeg | [ ] |
| 5 | 시리즈별 전환 스타일 기본값 (`Group.settings.default_transition`) | FFmpeg | [ ] |
| 6 | Frontend: Project 브랜딩 설정 UI (로고 업로드, 프리뷰) | Frontend | [ ] |

#### 3-3. 분석 대시보드 (Frontend + Backend)

> 원본: Frontend-6, Prompt-6, Backend-8, DBA-6

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | `activity_logs` project_id/group_id 자동 기록 (Phase 0에서 컬럼 추가 후 활성화) | Backend | [ ] |
| 2 | `GET /projects/{id}/analytics` - Match Rate 추이, 비용 집계 | Backend | [ ] |
| 3 | `GET /groups/{id}/analytics` - 그룹별 태그 TOP 10, 성공률 | Backend | [ ] |
| 4 | Frontend: Group Analytics 탭 (차트, 추이, 비교) | Frontend | [ ] |
| 5 | 프로젝트 간 비교 뷰 ("A 채널 vs B 채널 성과") | Frontend | [ ] |

#### 3-4. 그룹별 Jinja2 템플릿 오버라이드 (Storyboard Writer)

> 원본: Storyboard-6

| # | 작업 | 상태 |
|---|------|------|
| 1 | `Group.settings.jinja2_template_override` - 커스텀 Gemini 템플릿 경로 | [ ] |
| 2 | 템플릿 선택 UI (기본 / 교육용 / 스토리용 / 요리용 등) | [ ] |
| 3 | 커스텀 템플릿 편집 기능 (고급 사용자용) | [ ] |

---

### Deferred (Phase 4+ / Backlog)

아래 아이디어는 Phase 3 이후 또는 별도 판단 시 착수.

| 아이디어 | 원본 | 연기 이유 |
|----------|------|----------|
| A/B 테스트 (동일 스토리보드 다른 스타일) | Backend-5 | Phase 2의 설정 상속이 선행 필요 |
| 커스텀 프롬프트 레이어 (Layer 13) | Backend-6 | 12-Layer 안정화 이후 |
| 비용/예산 관리 | Backend-8 | 분석 대시보드에 통합 (Phase 3-3) |
| 미디어 에셋 공유 풀 | Backend-10, Frontend-3 | MediaAsset 시스템 확장으로 별도 기획 |
| Group Timeline View | Frontend-2 | Phase 2-3의 에피소드 시각화에 통합 |
| 캐릭터 일관성 프로필 오버라이드 | Prompt-4 | Character Builder 기능과 통합 |
| 스타일 전이 마법사 | Prompt-7 | 템플릿 시스템(Phase 2-4)으로 대체 |
| Drag & Drop 재구성 | UI/UX-6 | 기존 Backlog "씬 순서 D&D"와 통합 |
| Smart Tags + Saved Views | UI/UX-7 | 분석 대시보드(Phase 3-3) 이후 |
| Progressive Disclosure 온보딩 | UI/UX-3 | 7-1의 Quick Start Flow와 통합 |

---

## 4. 의존성 그래프

```
Phase 0 (Foundation)
  ├── 0-1 DB Migration ─────────────────┐
  ├── 0-2 CRUD API ──── depends on 0-1 ─┤
  └── 0-3 Frontend ──── depends on 0-2 ─┘
                                         │
Phase 1 (Core)                           │ depends on Phase 0
  ├── 1-1 Config Resolver ───────────────┤
  ├── 1-2 Context Bar ──── depends on 0-3
  └── 1-3 FK Hardening ── depends on 0-1
                                         │
Phase 2 (Differentiation)               │ depends on Phase 1
  ├── 2-1 Channel DNA ──── depends on 1-1 (설정 상속 필요)
  ├── 2-2 Tag Intelligence ── depends on 1-1
  ├── 2-3 Series Intelligence ── depends on 2-1
  └── 2-4 Templates ──── depends on 0-2 (CRUD만 필요, 병렬 가능)
                                         │
Phase 3 (Advanced)                       │ depends on Phase 2
  ├── 3-1 Batch Rendering ── depends on 1-1
  ├── 3-2 Branding ──── depends on 1-1
  ├── 3-3 Analytics ──── depends on 2-2 (태그 데이터 필요)
  └── 3-4 Jinja2 Override ── depends on 2-1
```

---

## 5. 리스크 및 완화

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| 기존 storyboard 데이터 깨짐 | P0 | Phase 0에서 nullable FK + seed 데이터로 안전하게 이행 |
| Settings JSONB 스키마 파편화 | P1 | Pydantic 모델로 JSONB 검증, 마이그레이션 시 스키마 버전 관리 |
| Gemini 프롬프트 과부하 (톤+세계관+에피소드) | P2 | 토큰 한도 설정, 요약 자동 압축 |
| 설정 상속 순환 참조 | P1 | 3단계 고정 (Project->Group->Storyboard), 4단계 이상 금지 |
| 대량 데이터 성능 (1000+ 스토리보드) | P3 | 복합 인덱스, 페이지네이션, 캐싱 |

---

## 6. 성공 지표

| 지표 | Phase 0 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|---------|
| 프로젝트 전환 시간 | - | < 2초 | < 2초 | < 2초 |
| 새 시리즈 시작까지 클릭 수 | - | 5회 | 3회 (템플릿) | 2회 |
| 에피소드 간 톤 일관성 | 수동 | 수동 | 자동 (Gemini 주입) | 자동 + 검증 |
| 프로젝트별 Match Rate 추적 | 불가 | 불가 | 가능 | 대시보드 |
| 일괄 렌더링 | 불가 | 불가 | 불가 | 그룹 단위 |

---

## 7. 로드맵 배치

이 기능은 현재 로드맵의 **Phase 7-1 (UX & Feature Expansion)** 이후 또는 병렬로 배치합니다.

```
현재: Phase 6-7 (Infra/DX) → 7-1 (UX/Feature)
제안: Phase 6-7 (Infra/DX) → 7-1 (UX/Feature)
                             → 7-2 (Project/Group Phase 0-1) ← 병렬 가능
                                → 7-3 (Project/Group Phase 2-3)
```

Phase 0 (DB + CRUD)는 6-7의 CI 파이프라인 작업과 독립적이므로 **병렬 착수 가능**.
Phase 1-2는 7-1의 UX 개선 작업과 시너지가 크므로 7-1 완료 후 순차 진행 권장.
