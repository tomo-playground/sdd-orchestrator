# Service / Admin 분리 설계

> 작성: 2026-02-25 | 상태: **완료** (Phase 17, 02-28)

---

## 1. 배경

현재 Shorts Producer는 **단일 Backend(34개 라우터) + 단일 Frontend(6개 페이지)**로 구성되어 있다. "영상을 만드는 유저"와 "시스템을 세팅하는 백오피스 관리자"가 동일한 API와 UI를 공유하며, 이로 인해:

- 유저가 불필요한 관리 기능(LoRA, Tag 분류, 캐시 리프레시 등)에 노출
- 백오피스 기능과 생산 기능 간 권한 구분 없음
- 유저 UI의 정보 과부하 (Edit Tab의 30+ props SceneCard 등)

---

## 2. 사용자 페르소나

### 2.1 현재 문제

PRD에 명시적 페르소나 섹션이 없다. `DESIGN_PHILOSOPHY.md`에 "중급 1인 크리에이터" 1개만 정의되어 있으나, 실제로는 2가지 역할이 존재한다.

### 2.2 두 가지 역할

| 역할 | 설명 | 접근 경로 |
|------|------|----------|
| **유저 (Creator)** | 콘텐츠 크리에이터. 주제를 넣고 영상을 만드는 사람 | Service UI |
| **관리자 (Admin)** | 백오피스 운영자. SD 인프라, 캐릭터, 화풍, 태그 체계를 구축하고 튜닝하는 사람 | Admin UI |

**유저는 관리자가 세팅해둔 시스템 위에서 콘텐츠만 생산한다.**

- 유저: 캐릭터를 "선택"한다 / 관리자: 캐릭터를 "만든다"
- 유저: Style Profile을 "선택"한다 / 관리자: Style Profile을 "설계한다"
- 유저: Render 버튼을 누른다 / 관리자: Render Preset을 "정의한다"

---

## 3. API 분리 설계

### 3.1 구조

```
Backend (단일 FastAPI — 논리적 분리)
├── /api/v1/          ← Service API (유저)
└── /api/admin/       ← Admin API (백오피스)

Frontend (단일 Next.js — Route Group 분리)
├── app/(service)/    ← 유저 UI
└── app/(admin)/      ← 관리자 UI
```

### 3.2 정리 대상 (삭제/통합)

분리 전 먼저 불필요한 라우터/엔드포인트를 정리한다.

#### 라우터 전체 삭제 (2개)

| 라우터 | prefix | 사유 |
|--------|--------|------|
| `keywords.py` | `/keywords` | Frontend 호출 0건. `tags.py` + `services/keywords/`와 완전 중복 |
| `avatar.py` | `/avatar` | Frontend 호출 0건. `characters/{id}/regenerate-reference`가 대체 |

#### 엔드포인트 삭제 (5개)

| 라우터 | 엔드포인트 | 사유 |
|--------|-----------|------|
| `admin.py` | `POST /migrate-tag-rules` | One-time 마이그레이션 완료 |
| `tags.py` | `POST /migrate-patterns` | One-time 마이그레이션 완료 |
| `prompt.py` | `POST /validate` | Frontend 미사용. `/validate-tags`가 대체 |
| `prompt.py` | `POST /rewrite` | Frontend 미사용. Auto Compose가 내부 처리 |
| `prompt.py` | `POST /check-conflicts` | Frontend 미사용 |

#### 라우터 통합 (3건)

| 흡수되는 라우터 | 흡수 대상 | 사유 |
|----------------|----------|------|
| `analytics.py` (2개 EP) | `settings.py` | Gemini 비용 분석. Settings 페이지에서만 호출 |
| `cleanup.py` (3개 EP) | `admin.py` | 스토리지 정리. admin의 media GC와 동일 관심사 |
| `sd.py` (4개 EP) | `sd_models.py` | SD WebUI 직접 조회 + DB 모델 관리를 하나로 |

**결과: 34개 → 29개 라우터**

---

### 3.3 Service API (유저) — 12개 라우터

#### 워크스페이스

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `projects` | `/projects` | CRUD, effective-config | 프로젝트(채널) 관리 |
| `groups` | `/groups` | CRUD, config, effective-config | 그룹(시리즈) 관리 |
| `storyboard` | `/storyboards` | CRUD, materials, seed, restore, trash | 스토리보드 관리 |

#### 생산 파이프라인

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `scripts` | `/scripts` | generate, generate-stream, resume, feedback | AI 스크립트 생성 |
| `scene` | — | generate, generate-batch, validate, edit-with-gemini, edit-image, generate-async, cancel, progress | 이미지 생성/검증/편집 |
| `video` | `/video` | create, create-async, progress, delete, transitions, render-history, extract-caption/hashtags | 영상 렌더링 |
| `prompt` | `/prompt` | **compose만** | 프롬프트 자동 조합 (이미지 생성 시 호출) |

#### 퍼블리싱

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `youtube` | `/youtube` | **upload, upload-status만** | 유튜브 업로드 실행 |

#### 유저 라이브러리

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `prompt_histories` | `/prompt-histories` | CRUD, favorite, apply, update-score, trash, restore | 저장된 프롬프트 |

#### 리소스 조회 (읽기 전용 — Admin이 세팅한 것을 소비)

| 라우터 | prefix | Service에 노출할 엔드포인트 | 용도 |
|--------|--------|---------------------------|------|
| `presets` | `/presets` | GET list, GET /{id}, GET /{id}/topics | 프리셋 조회 (전체 읽기 전용) |
| `assets` | — | GET audio/list, fonts/list, overlay/list | 에셋 목록 |

#### 읽기 전용 프록시 (Admin 리소스 → Service 노출)

Admin이 관리하는 리소스 중 유저가 **선택**해야 하는 것들의 GET 엔드포인트:

| 원본 Admin 라우터 | Service 노출 엔드포인트 | 용도 |
|-------------------|------------------------|------|
| `characters` | `GET /characters`, `GET /characters/{id}` | 캐릭터 선택 |
| `style_profiles` | `GET /style-profiles`, `GET /style-profiles/default`, `GET /style-profiles/{id}` | 화풍 선택 |
| `voice_presets` | `GET /voice-presets`, `GET /voice-presets/{id}` | 음성 선택 |
| `music_presets` | `GET /music-presets`, `GET /music-presets/{id}` | 음악 선택 |
| `backgrounds` | `GET /backgrounds`, `GET /backgrounds/{id}`, `GET /backgrounds/categories` | 배경 선택 |
| `tags` | `GET /tags/search` | 태그 자동완성 |
| `quality` | `GET /quality/summary/{sb_id}`, `GET /quality/consistency/{sb_id}`, `GET /quality/alerts/{sb_id}` | 내 작업물 품질 확인 |
| `render_presets` | `GET /render-presets` | 렌더 프리셋 선택 |

---

### 3.4 Admin API (백오피스) — 17개 라우터

#### SD 인프라

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `sd_models` (통합) | — | SD models CRUD, embeddings CRUD, SD options 조회/변경, LoRA 목록 | SD WebUI + DB 모델 통합 관리 |
| `controlnet` | `/controlnet` | status, poses, detect-pose, suggest-pose, IP-Adapter CRUD, reference quality | ControlNet/IP-Adapter 관리 |
| `loras` | `/loras` | CRUD, Civitai 검색/임포트, calibrate | LoRA 등록/튜닝 |

#### 콘텐츠 에셋 구축

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `characters` | `/characters` | POST/PUT/DELETE, preview, builder, regenerate-reference, enhance, batch-regenerate | 캐릭터 구축 |
| `style_profiles` | `/style-profiles` | POST/PUT/DELETE | 화풍 프로필 관리 |
| `backgrounds` | `/backgrounds` | POST/PUT/DELETE, upload-image | 배경 관리 |

#### 프리셋 관리

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `render_presets` | `/render-presets` | CRUD | 렌더 프리셋 |
| `voice_presets` | `/voice-presets` | POST/PUT/DELETE, preview, attach-preview | 음성 프리셋 |
| `music_presets` | `/music-presets` | POST/PUT/DELETE, preview, attach-preview, warmup | 음악 프리셋 |
| `creative_presets` | `/lab/creative` | Agent 프리셋 CRUD | Agent 프리셋 |

#### 태그 시스템

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `tags` | `/tags` | CRUD, classify, approve, bulk-approve, groups, pending | 태그 관리 |
| `admin` (태그 관련) | `/admin` | tag deprecate/activate, tag-thumbnails/generate | 태그 폐기/썸네일 |

#### 프롬프트 도구

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `prompt` | `/prompt` | validate-tags, auto-replace, split, edit-prompt, translate-ko, negative-preview | 프롬프트 분석/변환 도구 |

#### 품질 모니터링

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `quality` | `/quality` | batch-validate | 시스템 전체 검증 |
| `lab` | `/lab` | experiments, tag-effectiveness, sync-effectiveness | 실험/분석 |
| `activity_logs` | `/activity-logs` | CRUD, analyze/patterns, suggest-conflict-rules, success-combinations | 활동 분석 |

#### 시스템 관리

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `admin` (시스템) | `/admin` | refresh-caches, media-assets GC/stats/orphans, image cache stats/clear, storage stats/cleanup | 캐시 + 스토리지 + 미디어 정리 (cleanup 통합 포함) |
| `settings` (통합) | — | auto-edit GET/PUT, cost-summary, gemini-edits analytics | 시스템 설정 + Gemini 비용 (analytics 통합 포함) |
| `memory` | `/memory` | stats, list/get/delete by namespace | AI 메모리 관리 |

#### 외부 연동 설정

| 라우터 | prefix | 엔드포인트 | 용도 |
|--------|--------|-----------|------|
| `youtube` | `/youtube` | authorize, callback, GET/DELETE credentials | 유튜브 채널 연결 설정 |

---

## 4. Frontend 분리 설계

### 4.1 구조

```
frontend/app/
├── (service)/              ← 유저 UI
│   ├── page.tsx            (Home — 대시보드, Continue Working)
│   ├── studio/page.tsx     (Studio — Script/Edit/Publish)
│   └── storyboards/        (스토리보드 목록, Kanban)
│
├── (admin)/                ← 관리자 UI
│   ├── characters/         (캐릭터 CRUD + Builder)
│   ├── styles/             (Style Profile + LoRA + Checkpoint + Embedding)
│   ├── tags/               (태그 관리 + 분류 + Deprecated)
│   ├── presets/             (Render/Voice/Music 프리셋)
│   ├── backgrounds/        (배경 관리)
│   ├── lab/                (Tag Lab, Scene Lab, Tag Browser, Analytics)
│   ├── quality/            (품질 모니터링, 일관성 분석)
│   └── system/             (캐시, 스토리지, 메모리, YouTube 연결, Gemini 설정)
│
└── (shared)/               ← 공유 레이아웃
    └── layout.tsx
```

### 4.2 유저 Studio 간소화

현재 Edit Tab 우측 패널의 기능을 유저/관리자 관점으로 분리:

**유저에게 보이는 것 (Service)**:
- 이미지 미리보기 + Generate / Auto Run
- Script Text 편집
- Quality 배지 (Match Rate — 숫자만, 해석은 시스템이 처리)
- Layout 선택 + Render 버튼

**관리자에게만 보이는 것 (Admin 또는 Advanced 토글)**:
- Positive/Negative Prompt 직접 편집
- Auto Compose / Auto Rewrite / Safe Tags / Hi-Res / Veo 토글
- ControlNet / IP-Adapter 설정
- 3x Candidates
- DriftHeatmap / Missing Tags / Tag Effectiveness

---

## 5. 분할이 필요한 라우터 상세

현재 하나의 라우터에 Service + Admin 엔드포인트가 혼재된 경우:

| 라우터 | Service (GET 읽기) | Admin (CUD 쓰기) |
|--------|-------------------|-----------------|
| `characters` | GET list, GET /{id} | POST, PUT, DELETE + preview/builder 전체 |
| `style_profiles` | GET list, default, /{id}, /{id}/full | POST, PUT, DELETE |
| `voice_presets` | GET list, GET /{id} | POST, PUT, DELETE, preview, attach |
| `music_presets` | GET list, GET /{id} | POST, PUT, DELETE, preview, attach, warmup |
| `backgrounds` | GET list, GET /{id}, categories | POST, PUT, DELETE, upload-image |
| `tags` | GET /search | CRUD, classify, approve, bulk-approve, pending, groups |
| `quality` | GET summary/consistency/alerts (per-SB) | POST batch-validate (시스템 전체) |
| `youtube` | POST upload, GET upload-status | GET authorize, POST callback, GET/DELETE credentials |
| `prompt` | POST compose | validate-tags, auto-replace, split, edit-prompt, translate-ko, negative-preview |

**구현 방식**: 라우터 파일 자체를 분리하거나, FastAPI `APIRouter` 태그로 구분.

---

## 6. 최초 접근 시 역할 식별

### 6.1 문제

서비스에 처음 접근할 때 "나는 유저인가, 관리자인가"를 시스템이 알아야 한다. 그래야 적절한 UI와 API 권한을 제공할 수 있다.

### 6.2 설계

```
첫 접근
  ├─ / (Service)     → 유저 UI (Home → Studio)
  └─ /admin (Admin)  → 백오피스 UI (로그인 필요)
```

| 항목 | Service (유저) | Admin (백오피스) |
|------|---------------|-----------------|
| 진입점 | `/` | `/admin` |
| 인증 | 없음 (로컬 실행) 또는 기본 인증 | 관리자 인증 필수 |
| 최초 접근 | 바로 Home 진입 | 관리자 로그인 → 대시보드 |
| URL 구분 | `app.example.com/` | `app.example.com/admin/` |

### 6.3 인증 전략 (단계별)

**Phase 1 — 로컬/단독 사용 (현재)**:
- 경로 기반 분리만 적용 (`/` vs `/admin`)
- 인증 없음 — 같은 사람이 두 역할을 겸하는 경우
- Admin UI 진입 시 "관리자 모드입니다" 배너로 시각적 구분

**Phase 2 — 멀티 유저**:
- 유저 계정 + 역할(role) 도입: `creator`, `admin`
- Admin API에 role 기반 미들웨어 적용
- 최초 가입 시 역할 선택 또는 관리자가 초대

**Phase 3 — 팀 운영**:
- 관리자가 유저를 초대하고 프로젝트/그룹에 할당
- 유저는 자기 프로젝트만 접근 가능
- Admin은 전체 시스템 + 모든 프로젝트 접근

### 6.4 Frontend 라우팅

```
frontend/app/
├── (service)/           ← / 로 접근
│   ├── layout.tsx       ← Service 전용 네비게이션 (Home, Studio)
│   └── ...
│
├── (admin)/             ← /admin 로 접근
│   ├── layout.tsx       ← Admin 전용 네비게이션 (사이드바 메뉴)
│   └── ...
│
└── middleware.ts        ← 경로 기반 역할 확인 (Phase 2부터 인증 체크)
```

---

## 7. 구현 단계

### Phase 1 — 정리 (선행) ✅ 02-25

- [x] `keywords.py` 라우터 삭제 + 테스트 정리
- [x] `avatar.py` 라우터 삭제 + 테스트 정리
- [x] `analytics.py` → `settings.py` 통합
- [x] `cleanup.py` → `admin.py` 통합
- [x] `sd.py` → `sd_models.py` 통합
- [x] One-time 마이그레이션 엔드포인트 3개 삭제
- [x] Frontend 미사용 prompt 엔드포인트 2개 삭제

### Phase 2 — Backend 논리적 분리 ✅ 02-28

- [x] Service 라우터를 `/api/v1/` prefix로 그룹핑
- [x] Admin 라우터를 `/api/admin/` prefix로 그룹핑
- [x] 분할 대상 라우터 10개의 엔드포인트 분리 (GET→Service, CUD→Admin)
- [x] OpenAPI docs 분리 (`/docs` → Service, `/admin/docs` → Admin)

### Phase 3 — Frontend Route Group 분리 ✅ 02-28

- [x] `(service)/` route group 생성 — Home, Studio, Storyboards
- [x] `admin/` route group 생성 — Characters, Styles, Tags, Lab, System
- [x] 현재 Library 페이지 해체 → Admin 하위로 재배치
- [x] 현재 Settings 페이지 해체 → Admin > System + Service > 유저 설정

### Phase 4 — 유저 UI 간소화 ✅ 02-28

- [x] Edit Tab: Advanced 토글로 관리자 기능 격리
- [x] Publish Tab: Quick Render (기본값 렌더) 추가
- [x] 전문 용어 Tooltip 시스템 추가 (10개 용어)

---

## 8. 최종 라우터 매핑 요약

```
정리 전: 34개 라우터
정리 후: 29개 라우터 (삭제 2 + 통합 3)

Service API:  12개 라우터 + 8개 읽기전용 프록시
Admin API:    17개 라우터

분할 필요:    9개 라우터 (GET → Service, CUD → Admin)
```
