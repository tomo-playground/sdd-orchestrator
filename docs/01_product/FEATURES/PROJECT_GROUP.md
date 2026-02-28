# Project(Channel) & Group(Story Group) System

**상태**: Phase 0~1 완료, Phase 2~3 장기 백로그
**최종 갱신**: 2026-02-27

---

## 1. 구현 완료 현황

### Infrastructure (Phase 0) — 완료

| 항목 | 비고 |
|------|------|
| ORM 모델 | `Project`, `Group`, `RenderPreset` |
| DB 마이그레이션 | projects, groups, render_presets 테이블 + seed 데이터 |
| CRUD API | `routers/projects.py`, `routers/groups.py` (목록/상세/생성/수정/삭제) |
| Storyboard FK | `group_id` NOT NULL, CASCADE 정책, 복합 인덱스 |
| Seed 데이터 | Default Project(id=1) + Default Group(id=1) |
| Storage 경로 | `projects/{p_id}/groups/{g_id}/storyboards/{s_id}/` |

### Settings & Config (Phase 1) — 완료

| 항목 | 비고 |
|------|------|
| Cascading Config | `config_resolver.py` — System Default → Group 2단계 병합 |
| Group Config 필드 | render_preset_id, style_profile_id, narrator_voice_preset_id, channel_dna (JSONB) |
| Channel DNA | `channel_dna` JSONB — tone, target_audience, worldview, guidelines |
| Gemini 연동 | research_tools + gemini_generator에서 channel_dna 주입 |
| Effective Config API | `GET /groups/{id}/effective-config` |
| Render Preset | 시스템 프리셋 3종 + 커스텀 프리셋, CRUD API 완료 |

### Frontend UI (Phase 1) — 완료

| 항목 | 비고 |
|------|------|
| Context Bar | `ContextBar.tsx` — 브레드크럼 + 인라인 Popover 프로젝트/그룹 전환 |
| CRUD 모달 | `ProjectFormModal`, `GroupFormModal`, `GroupConfigEditor` |
| Setup Wizard | `SetupWizard` + ProjectStep + GroupStep + StepIndicator |
| Zustand Store | `useContextStore` — projectId/groupId/effectiveConfig 영속화 |
| Cmd+K Quick Switcher | `CommandPalette.tsx` — 프로젝트/그룹/스토리보드 fuzzy 검색 |
| Home 필터 | 프로젝트 드롭다운 + 그룹 필터 pill |
| 캐릭터 글로벌화 | `project_id` FK 제거, 글로벌 스코프 (v3.23) |

---

## 2. 잔여 작업 (미구현)

### 2-1. 폴리시 항목 (단독 착수 가능)

| # | 항목 | 설명 | 난이도 |
|---|------|------|--------|
| 1 | Empty State CTA | "첫 번째 시리즈를 만들어보세요" 빈 상태 UI | 낮음 |
| 2 | 프로젝트/그룹 색상 코딩 | 아이콘/컬러 차별화 | 낮음 |
| 3 | Render Preset 관리 UI | /manage 페이지에서 커스텀 프리셋 편집 | 중간 |
| 4 | SB 생성 시 effective_config 자동 주입 | 현재 수동, config_resolver 연동 필요 | 중간 |

### 2-2. Tag Intelligence — 장기 백로그

채널별 태그 정책 + 데이터 기반 추천. **Phase 9(Agentic) 인프라 위에 구축.**

| # | 항목 | 설명 |
|---|------|------|
| 1 | `tag_effectiveness`에 `project_id` 컬럼 추가 | 채널별 태그 성과 추적 |
| 2 | Project `allowed_tags[]`, `forbidden_tags[]` | 태그 화이트/블랙리스트 |
| 3 | 12-Layer Builder forbidden 태그 자동 제거 | 프롬프트 파이프라인 연동 |
| 4 | `GET /projects/{id}/tag-recommendations` | 프로젝트별 TOP 20 추천 |
| 5 | Gemini 템플릿 `recommended_tags` 자동 주입 | 생성 품질 향상 |

### 2-3. Series Intelligence — 장기 백로그

에피소드 연결 + 성공 패턴 학습. **Channel DNA 인프라 위에 확장.**

| # | 항목 | 설명 |
|---|------|------|
| 1 | `storyboards.episode_number`, `recap_text` 컬럼 | 에피소드 순서 관리 |
| 2 | `GET /groups/{id}/episode-context` | 이전 에피소드 요약 자동 생성 (Gemini) |
| 3 | Gemini `previous_episodes` 섹션 자동 주입 | 시리즈 연속성 |
| 4 | `GET /groups/{id}/success-patterns` | 그룹 내 Match Rate TOP 태그 조합 |
| 5 | Group 타임라인 에피소드 순서/연결 시각화 | Frontend |

### 2-4. Production Scale — 장기 백로그

대규모 콘텐츠 워크플로우.

| # | 항목 | 설명 |
|---|------|------|
| 1 | 배치 렌더링 + 큐 | Celery/Redis, 그룹 일괄 렌더, WebSocket 진행률 |
| 2 | 브랜딩 시스템 | 로고/워터마크, 인트로/아웃트로, 플랫폼별 출력 |
| 3 | 분석 대시보드 | Match Rate 추이, 프로젝트 간 비교, activity_logs 확장 |
| 4 | Jinja2 템플릿 오버라이드 | 그룹별 커스텀 Gemini 템플릿 |
| 5 | 프로젝트/그룹 템플릿 | 5종 Quick Start (명언/교육/요리/스토리/뉴스) |

---

## 3. 의존성

```
완료: Phase 0 (Foundation) → Phase 1 (Core + Config + UI)
           ↓
잔여: 2-1 폴리시 (단독 착수 가능)
           ↓
백로그: 2-2 Tag Intelligence ← tag_effectiveness 데이터 축적 필요
        2-3 Series Intelligence ← Channel DNA 활용 확장
        2-4 Production Scale ← 사용자 규모 확대 시
```

---

## 4. 기술 스택 현황

| 컴포넌트 | 파일 |
|---------|------|
| Project ORM | `backend/models/project.py` |
| Group ORM | `backend/models/group.py` |
| Group ORM (config 통합) | `backend/models/group.py` |
| RenderPreset ORM | `backend/models/render_preset.py` |
| Config Resolver | `backend/services/config_resolver.py` |
| Project Router | `backend/routers/projects.py` |
| Group Router | `backend/routers/groups.py` |
| Context Store | `frontend/app/store/useContextStore.ts` |
| Context UI (11파일) | `frontend/app/components/context/` |
| CommandPalette | `frontend/app/components/ui/CommandPalette.tsx` |
