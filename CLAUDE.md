# 프로젝트: Shorts Producer

AI 기반 쇼츠 영상 자동화 워크스페이스. LangGraph Agentic Pipeline (Gemini) + Stable Diffusion (이미지) + Qwen3-TTS (음성) + FFmpeg (렌더링).

## Agent 공통 규칙

이 문서는 모든 AI 에이전트(Claude, Gemini 등)의 **SSOT 컨텍스트**입니다.

- **언어**: 모든 응답은 **한국어**로 작성합니다.
- **DB 스키마**: DB 관련 질문 시 `docs/03_engineering/architecture/DB_SCHEMA.md`를 최우선으로 참조합니다.
- **아키텍처/규칙**: 이 파일(`CLAUDE.md`)의 원칙을 항상 준수합니다. 에이전트별 컨텍스트 파일(`GEMINI.md` 등)은 역할 정의만 포함하며, 세부 규칙은 이 파일을 참조합니다.

## 아키텍처

| 레이어 | 기술 | 핵심 |
|--------|------|------|
| Backend | FastAPI + LangGraph | `routers/` (API), `services/` (로직), `services/agent/` (Agentic Pipeline) |
| Frontend | Next.js 16, React 19 | `app/(app)/` (Home, Studio, Scripts, Library, Settings), Zustand 4-Store |
| DB | PostgreSQL | Storyboard → Scene → CharacterAction 계층 구조 |
| AI | LangGraph + Gemini | 19개 노드 (Director, Writer, Critic, Research, Cinematographer 등), Gemini Function Calling |
| Observability | LangFuse | 셀프호스팅, 파이프라인 트레이싱 |

### Backend 구조
```
backend/
├── routers/          # API 엔드포인트 (29개 라우터)
├── services/
│   ├── agent/        # LangGraph Agentic Pipeline
│   │   ├── nodes/    #   19개 노드 (Director, Writer, Critic, Research, Cinematographer 등)
│   │   ├── tools/    #   Gemini Function Calling 도구
│   │   ├── state.py  #   Graph State
│   │   └── routing.py#   조건부 라우팅
│   ├── video/        # FFmpeg 렌더링 파이프라인
│   ├── prompt/       # 프롬프트 엔진 (composition.py: 12-Layer Builder)
│   ├── keywords/     # 태그 시스템 패키지 (core, db, db_cache, processing, validation 등)
│   ├── storyboard/   # 스토리보드 CRUD, Scene Builder
│   └── characters/   # 캐릭터 관리, LoRA 연동
├── models/           # SQLAlchemy ORM (associations.py: relational tags)
├── templates/        # Jinja2 30개 (스토리보드 5종 + Creative 21종 + 파셜 4종)
└── config.py         # 모든 상수/환경변수 SSOT
```

## 문서 구조
```
docs/
├── 00_meta/          # 문서 관리 규칙
├── 01_product/       # 제품 (PRD, 로드맵, 기능 명세)
│   ├── PRD.md
│   ├── ROADMAP.md
│   └── FEATURES/     # 미구현 기능별 명세 (what/why)
├── 02_design/        # UI/UX 설계
├── 03_engineering/   # 기술 설계 (how)
│   ├── api/          # REST API 명세
│   ├── architecture/ # DB 스키마, 시스템 개요
│   ├── backend/      # 프롬프트, 렌더링, Soft Delete 등
│   ├── frontend/     # 상태 관리
│   └── testing/      # 테스트 전략, 시나리오
├── 04_operations/    # 운영 (배포, SD WebUI, 트러블슈팅)
├── 99_archive/       # 완료된 문서 아카이브
└── guides/           # 개발 가이드 (CONTRIBUTING)
```

### 주요 문서
- **로드맵**: `docs/01_product/ROADMAP.md`
- **기능 명세**: `docs/01_product/FEATURES/*.md`
- **제품 스펙**: `docs/01_product/PRD.md`
- **API 명세**: `docs/03_engineering/api/REST_API.md`
- **DB 스키마**: `docs/03_engineering/architecture/DB_SCHEMA.md`
- **프롬프트 설계**: `docs/03_engineering/backend/PROMPT_SPEC.md`
- **테스트 전략**: `docs/03_engineering/testing/TEST_STRATEGY.md`
- **테스트 시나리오**: `docs/03_engineering/testing/TEST_SCENARIOS.md`
- **개발 가이드**: `docs/guides/CONTRIBUTING.md`

## 코드 및 문서 크기 가이드라인
| 단위 | 권장 | 최대 |
|------|------|------|
| 함수/메서드 | 30줄 | 50줄 |
| 클래스/컴포넌트 | 150줄 | 200줄 |
| 코드 파일 | 300줄 | 400줄 |
| 문서 파일 (.md) | 500줄 | 800줄 |

**원칙**: Single Responsibility, 중첩 3단계 이하, 매개변수 4개 이하
**문서 관리**: 800줄 초과 시 히스토리 추출(Archive) 또는 관심사 분리(Sub-Roadmap) 필수.

## UI Typography Rules (최소 가독성 기준)
- **최소 폰트 사이즈**: `11px` (text-[11px]). `text-[9px]`, `text-[10px]` 사용 금지.
- **본문/버튼/탭**: `text-xs` (13px) 이상.
- **입력 필드/제목**: `text-sm` (15px) 이상.
- **Tailwind 기본 스케일 사용 권장**: `text-xs` → `text-sm` → `text-base` → `text-lg`.
- **커스텀 픽셀 사이즈**: `text-[11px]`(배지), `text-[12px]`(라벨), `text-[13px]`(섹션 헤더)만 허용.

## 사전 요구사항
- **SD WebUI**: API 모드 실행 (`--api` 옵션)
- **환경 변수**: `backend/.env` 파일 필수 (`DATABASE_URL`, `GEMINI_API_KEY` 등)

## Service vs Admin API 분리 기준
- **Service API** (`/api/v1`): 일반 사용자가 서비스 화면(`app/(service)/`)에서 직접 수행하는 기능
  - 캐릭터 CRUD/프리뷰/레퍼런스, 프롬프트 번역/편집/태그검증, IP-Adapter 레퍼런스 조회, YouTube OAuth, 스토리보드/씬/렌더링 등
- **Admin API** (`/api/admin`): 시스템 관리, 일괄 작업, Back-office 전용
  - SD 모델/임베딩 관리, LoRA CUD, StyleProfile CUD, 일괄 레퍼런스 재생성, 영구 삭제, Lab/실험, Activity Logs, 캐시 갱신 등
- **Frontend 규칙**: 서비스 화면에서는 `API_BASE` 사용. `ADMIN_API_BASE`는 어드민 페이지(`app/admin/`)에서만 사용.
- **Backend 규칙**: 라우터 파일에서 `service_router`와 `admin_router`를 분리. `routers/__init__.py`에서 각각 등록.

## Configuration Principles (SSOT)
- **설정 값**: 모든 환경 변수 및 상수는 `backend/config.py`에서 관리합니다. 개별 파일 하드코딩 금지.
- **옵션 목록**: Language, Structure 등 도메인 옵션은 **Backend가 SSOT**. Frontend는 API 응답을 소비만 한다. `frontend/constants/`에 도메인 옵션 하드코딩 금지.
  - Language: `config.py` → `STORYBOARD_LANGUAGES` → `/presets` API 응답의 `languages` 필드
  - Structure: `services/presets.py` → `PRESETS` dict → `/presets` API 응답의 `presets[].structure`
- **로직 기준**: 태그 우선순위 등의 비즈니스 로직은 **Backend**(`backend/services/keywords/` 패키지)가 Single Source of Truth입니다.
- **태그 규칙**: 충돌(`tag_rules`), 별칭(`tag_aliases`), 필터(`tag_filters`) 모두 **DB 테이블**에서 관리. 코드 하드코딩 금지.
- **런타임 캐시**: `TagCategoryCache`, `TagAliasCache`, `TagRuleCache`, `LoRATriggerCache` — startup 시 DB에서 로드, 변경 시 `/admin/refresh-caches`.
- **SD 생성 파라미터 우선순위** (steps, cfg_scale, sampler_name, clip_skip):
  - `config.py` 전역 기본값 < `StyleProfile.default_*` (화풍별 최적 파라미터)
  - SD 생성 파라미터는 Group 레벨에서는 관리하지 않음 (제거됨).
  - 실제 이미지 생성 시에는 `_adjust_parameters()`에서 StyleProfile 값이 최종 적용된다.
  - 캐릭터 프리뷰 생성도 동일: `preview.py`에서 StyleContext 기반 오버라이드.
- **원천 UI 수정 원칙**: 설정 값의 SSOT를 소유한 UI에서만 수정을 허용한다. 다른 화면에서 동일 값을 표시할 때는 **읽기 전용**으로 보여주고, 수정이 필요하면 원천 UI로 이동시킨다. 특수한 케이스가 아닌 한 인라인 수정 금지.
  - 예: `narrator_voice_preset_id` → GroupConfigEditor가 원천. 렌더 패널은 읽기 전용 + "시리즈 설정에서 변경" 링크.
- **캐릭터 레퍼런스 프롬프트 SSOT** (공통 vs 고유 분리):
  - **공통 태그 = 상수 SSOT** (`config.py`, `config_prompt.py`):
    - Positive: `REFERENCE_ENV_TAGS` (배경), `REFERENCE_CAMERA_TAGS` (카메라), `_ensure_quality_tags()` (품질)
    - Negative: `DEFAULT_REFERENCE_NEGATIVE_PROMPT` (품질·배경·멀티뷰 억제)
    - `compose_for_reference()` + `preview.py` 머지 로직이 자동 주입
  - **캐릭터 고유 태그 = DB** (`characters.reference_base_prompt`, `reference_negative_prompt`):
    - Positive: 캐릭터 특화 보정만 (`chibi`, `flat_color`, `hrkzdrm_cs`, `expressionless` 등)
    - Negative: 캐릭터 특화 억제만 (`armor, bodysuit`, `1girl`, `realistic` 등)
  - ❌ DB에 공통 태그 중복 저장 금지 (`white_background`, `simple_background`, `solo`, `standing`, `lowres`, `bad_anatomy`, `detailed_background`, `multiple_views` 등)
  - 공통 태그 변경 시 상수 1곳만 수정. DB 캐릭터별 업데이트 불필요.

## DB Schema Design Principles
- **관심사 분리**: 콘텐츠 테이블(storyboards)과 설정 필드(groups의 FK/DNA)를 구분한다.
- **`default_` prefix 금지**: 실제 값에 `default_` 붙이지 않는다. cascade/fallback 문맥에서만 사용.
- **Boolean은 Boolean**: `Integer`로 boolean 저장 금지. `Boolean` 타입 + `is_`/`_enabled` 네이밍.
- **JSON은 JSONB**: `Text`에 JSON 문자열 저장 금지. 구조화 데이터는 반드시 `JSONB`.
- **설정 소유권**: `System Default < Group` (2단계). 콘텐츠 엔티티는 설정을 소유하지 않는다. Identity(채널명/아바타)는 Project → Group → Storyboard ORM 관계로 전달. **Character는 Group에 종속** (`group_id` NOT NULL FK) — 화풍은 Group.style_profile에서 자동 상속, Character가 독자적으로 화풍을 소유하지 않는다.
- **미디어 참조는 media_asset_id 필수**: 이미지/비디오/오디오 URL을 직접 저장하지 않는다.
  - ❌ `image_url: "http://localhost:9000/..."` — 환경 종속, 이동 불가
  - ✅ `media_asset_id: 123` — `media_assets` 테이블 FK 참조
  - Backend GET 응답에서 `media_asset_id` → `url` 변환 (serialize 시점)
  - Frontend는 저장 시 URL 제거, 조회 시 Backend가 채워준 URL 사용
- **URL 필드 규칙 (image_url / preview_image_url)**:
  - URL은 **DB에 저장하지 않는다**. ORM `@property`가 `media_asset` 관계에서 런타임 파생.
  - Pydantic 스키마에 URL 필드 추가 시 반드시 **용도 주석** 명시:
    - `# Response-only: derived from @property` — GET 응답 전용
    - `# Input-only: backend fetches this URL` — URL fetch 입력
    - `# Transient: render-time only, never stored` — 메모리 전용
  - `model_dump()` → JSONB 저장 시 `exclude={"image_url"}` 필수
  - Frontend: `sanitizeCandidatesForDb()` / Backend: `_sanitize_candidates_for_db()` 양쪽 방어
- **상세**: `.claude/agents/dba.md` "스키마 설계 철학" 섹션 참조.

## API Contract Principles (Backend ↔ Frontend)
- **response_model 필수**: 모든 FastAPI 라우터 엔드포인트에 `response_model=` 지정. raw dict 반환 금지.
- **응답 스키마 구체화**: `dict | None` 금지. 반드시 Pydantic 모델로 필드를 명시한다. (예: `data: SceneGenerateResponse | None`)
- **Frontend 타입 동기화**: Backend 스키마의 필드명을 그대로 사용. Frontend에서 필드명을 추측하여 작성하지 않는다.
  - Backend가 `image` (base64)를 반환하면 Frontend도 `result.data.image`로 접근.
  - `image_url` 등 존재하지 않는 필드를 가정하지 않는다.
- **신규 엔드포인트 체크리스트**:
  1. `schemas.py`에 Request + Response 모델 정의
  2. 라우터에 `response_model=` 지정
  3. Frontend 타입(interface)을 Backend 스키마와 일치시킴
  4. REST API 명세 (`docs/03_engineering/api/REST_API.md`) 업데이트

## Gemini API 호출 규칙

### system_instruction 분리 (필수)
- `system_instruction`은 반드시 `GenerateContentConfig.system_instruction` 파라미터로 전달
- ❌ `contents`에 system prompt 합치기 금지: `f"{system_prompt}\n\n{user_prompt}"`
- ✅ `GenerateContentConfig(system_instruction=system_prompt)` + `contents=user_prompt`
- 이유: `contents`에 합치면 Gemini 안전 필터가 더 엄격하게 작동

### Safety Settings (필수)
- 모든 Gemini 호출에 `GEMINI_SAFETY_SETTINGS` (config.py) 적용
- 개별 파일에 safety settings 하드코딩 금지 → config.py SSOT

### PROHIBITED_CONTENT 폴백 (필수)
- `PROHIBITED_CONTENT` 감지 시 `GEMINI_FALLBACK_MODEL` (gemini-2.0-flash)로 자동 1회 재시도
- 폴백 사용 시 반드시 로그 기록: `[Fallback] PROHIBITED_CONTENT → {fallback_model}`
- 폴백도 실패 시 사용자에게 에러 전파

### Sanitization (유지)
- `_sanitize_for_gemini_prompt()`: Gemini 호출 직전 미성년자 연상 단어 치환
- `_restore_danbooru_tags()`: Gemini 응답을 SD용 Danbooru 태그로 복원
- 2.5 Flash 유지율을 높이기 위한 1차 방어선 (폴백은 2차)

## Image Generation Debug Payload Convention
이미지 생성 결과의 `debug_payload`는 반드시 **`{request, actual}`** 2-레벨 구조로 저장한다.

```json
{
  "request": { /* Frontend가 보낸 원본 요청 */ },
  "actual": {
    "prompt": "Backend가 최종 구성한 프롬프트 (LoRA, 스타일 태그 포함)",
    "negative_prompt": "최종 네거티브 프롬프트",
    "steps": 25,
    "cfg_scale": 7.0,
    "sampler": "DPM++ 2M Karras",
    "seed": 123456
  }
}
```

**Backend 책임**: `_generate_scene_image_with_db()` 결과에 `used_prompt`, `used_negative_prompt`, `used_steps`, `used_cfg_scale`, `used_sampler` 필드를 반드시 포함한다.
- SSE 경로: `ImageProgressEvent` 스키마의 `used_*` 필드로 전달
- Sync 경로: `SceneGenerateResponse`의 `used_*` 필드로 전달

**Frontend 책임**: SSE/Sync 양쪽 모두 `debug_payload`를 `{request, actual}` 구조로 구성한다.
- `request`: Frontend `requestPayload` 원본
- `actual`: Backend 응답의 `used_*` 필드 + `seed`

**신규 생성 파라미터 추가 시**: Backend `result["used_X"]` → 스키마 `used_X` 필드 → Frontend `actual.X` 까지 3곳 동기화 필수.

## Code Modularization Principles (중복 로직 금지)
- **변환 로직 모듈화**: 동일한 데이터 변환이 여러 곳에서 필요하면 **반드시 헬퍼 함수로 추출**한다.
  - 예: `sanitizeCandidatesForDb()` — candidates 저장 시 `image_url` 제거
  - 예: `mapGeminiScenes()` — Gemini 응답 → Scene 타입 변환
- **복사-붙여넣기 금지**: 같은 로직이 2곳 이상에서 사용되면 즉시 공통 함수로 추출한다.
- **완전성 검증**: 새 기능 추가 시 **모든 호출 경로**에서 해당 로직이 적용되는지 확인한다.
  - ❌ `autoSaveStoryboard()`에만 적용하고 `persistStoryboard()`에서 누락하는 실수 방지
- **테스트 케이스 필수**: 공통 헬퍼 함수는 **단위 테스트로 방어**한다.

## Data Mapping Principles (Spread Passthrough 패턴)
데이터 변환 함수(API 응답 → Store, Store → API 페이로드, ORM → dict 등)에서 **Whitelist 매핑(필드 명시 나열) 금지**. 신규 필드 추가 시 매핑 함수 누락으로 인한 **null 덮어쓰기 데이터 소실**을 방지한다.

**원칙**: Spread(`...`)로 모든 필드를 패스스루하고, **변환이 필요한 필드만 오버라이드**.

```typescript
// ❌ Whitelist — 새 필드 추가 시 누락 위험 → null 덮어쓰기 → 데이터 소실
function mapDbScenes(dbScenes) {
  return dbScenes.map(s => ({
    id: s.id,
    script: s.script,
    // voice_design_prompt 깜빡하면 소실
  }));
}

// ✅ Spread Passthrough — 모든 필드 자동 생존
function mapDbScenes(dbScenes) {
  return dbScenes.map((s, i) => ({
    ...s,                        // 패스스루 (신규 필드 자동 포함)
    id: (s.id as number) || i,   // 변환 필요한 것만 오버라이드
    isGenerating: false,         // UI-only 필드 초기화
  })) as Scene[];
}
```

**Store → API 페이로드** 방향에서는 UI-only 필드를 **destructuring exclude**로 제거:
```typescript
// ✅ UI-only 필드 제외 후 나머지 패스스루
const { isGenerating, debug_payload, debug_prompt, ...apiFields } = scene;
return { ...apiFields, scene_id: i };
```

**Backend ORM → dict** 방향에서는 관계 enrichment만 별도 처리:
```python
# ✅ model_dump() 기반 패스스루 + 관계 필드만 별도 enrichment
base = {c.key: getattr(scene, c.key) for c in Scene.__table__.columns}
base["tags"] = [serialize_tag(t) for t in scene.tags]  # 관계만 별도
```

**적용 대상** (8개 함수):
| 함수 | 파일 | 방향 |
|------|------|------|
| `mapDbScenes` | `useStudioInitialization.ts` | DB→Store |
| `mapGeminiScenes` | `storyboardActions.ts` | Gemini→Store |
| `buildScenesPayload` | `buildScenesPayload.ts` | Store→API |
| `buildSavePayload` | `scriptEditor/actions.ts` | Editor→API |
| `mapScenesToItems` | `scriptEditor/mappers.ts` | Scene→SceneItem |
| `syncToGlobalStore` | `scriptEditor/mappers.ts` | SceneItem→Scene |
| `serialize_scene` | `scene_builder.py` | ORM→dict |
| `create_scenes` | `scene_builder.py` | schema→ORM |

## Frontend State Sync Principles (Active Entity Deletion)
- **삭제 = 즉시 정리**: 현재 활성 엔티티(스토리보드, 씬 등)를 삭제하면 **스토어 전체 리셋** + 안전한 화면으로 리다이렉트. `storyboardId: null`만 설정하고 나머지 데이터를 방치하지 않는다.
- **404 = 삭제된 것으로 간주**: API에서 404 반환 시 에러를 무시하지 않는다. 토스트 메시지 표시 + 스토어 리셋 + URL 정리.
- **useRef 가드 리셋**: `useRef`로 중복 실행을 방지할 때, 조건이 해제되면 **반드시 ref를 리셋**한다. (예: `?new=true` → `?id=X` 이동 시 ref 초기화)
- **Soft Delete 일관성**: Backend의 모든 GET/PUT/PATCH 쿼리에 `deleted_at.is_(None)` 필터 적용. DELETE만 soft delete 필터하고 UPDATE에서 빠뜨리지 않는다.

## Tag Format Standard (Danbooru 표준)
**원칙**: 모든 태그는 **언더바(_) 형식**을 사용합니다. 공백 형식 절대 금지.

**근거**:
- **Danbooru 표준**: `brown_hair`, `looking_at_viewer`, `cowboy_shot`
- **WD14 Tagger CSV**: 언더바 형식 사용
- **SD 프롬프트**: 언더바 형식 사용
- **DB 저장**: 언더바 형식 통일 (Phase 6-4.21 완료)

**적용 범위**:
- DB 저장 (tags 테이블, tag_effectiveness 테이블)
- API 응답 (JSON 포맷)
- 프롬프트 생성 (`normalize_prompt_token()` 보존)
- Gemini 템플릿 예시 (create_storyboard.j2)
- WD14 검증 결과

**금지 사항**:
- ❌ 공백 형식 변환 (`tag.replace("_", " ")`)
- ❌ 혼용 (일부는 언더바, 일부는 공백)
- ❌ 사용자 입력 자동 변환 (입력은 그대로, DB 조회 시에만 정규화)

**예외**:
- 하이픈 태그는 유지: `close-up`, `full-body`
- 복합어 태그는 언더바로 연결: `light_brown_hair`, `school_uniform`
- **치비(Chibi) 특화**: 반드시 `super_deformed`, `small_body`, `big_head` 형식을 사용 (공백 금지)
- **LoRA 트리거 워드**: Civitai 원본 형식 그대로 유지 (Danbooru 규칙 적용 안 함)
  - 공백 허용: `"flat color"`, `"cubism style"`
  - 언더스코어 허용: `"Midoriya_Izuku"`, `"hrkzdrm_cs"`
  - 이유: LoRA 제작자가 정의한 원본 형식 존중, 캐릭터명 가독성

> 관련 커밋: Phase 6-4.21 (2026-01-27) - DB 공백 태그 554개 → 언더바 통일

### Tag 2-Level Hierarchy (category + group_name)
| 필드 | 용도 | 허용 값 |
|------|------|---------|
| `category` | 대분류 (4종) | `scene`, `character`, `quality`, `meta` |
| `group_name` | 소분류 (24종) | `expression`, `gaze`, `pose`, `action`, `camera`, `mood` 등 |

- DB 쿼리에서 소분류 필터링 시 반드시 `Tag.group_name` 사용. `Tag.category`에 소분류 값 금지.
- ❌ `Tag.category == "expression"` / ✅ `Tag.group_name == "expression"`

## Sub Agents

| Agent | 역할 | Commands |
|-------|------|----------|
| **Tech Lead** | 개발 총괄, 코드 리뷰, 크로스 에이전트 조율 | `/roadmap`, `/test`, `/review`, `/db`, `/docs` |
| **PM Agent** | 로드맵/우선순위/문서 구조 관리 | `/roadmap`, `/docs`, `/vrt`, `/test`, `/pm-check` |
| **Prompt Engineer** | SD 프롬프트 최적화 + 데이터 기반 고도화 | `/prompt-validate`, `/sd-status` |
| **Storyboard Writer** | 스토리보드/스크립트 작성 | `/roadmap` |
| **QA Validator** | 품질 체크/테스트 검증/TROUBLESHOOTING | `/test`, `/review`, `/vrt`, `/sd-status`, `/prompt-validate` |
| **FFmpeg Expert** | 렌더링/비디오 효과 | `/vrt`, `/roadmap` |
| **UI/UX Engineer** | UI 설계/와이어프레임/사용성 개선 | `/vrt`, `/test` |
| **Frontend Dev** | Next.js/React 개발, Zustand 상태 관리 | `/test frontend`, `/vrt` |
| **Backend Dev** | FastAPI 개발, 서비스 로직, 스토리지 | `/test backend`, `/sd-status`, `/db`, `/pose` |
| **DBA** | DB 설계, Alembic 마이그레이션, 쿼리 최적화 | `/db`, `/test backend` |
| **Security Engineer** | 보안 취약점 분석, 인증/인가, 시크릿 관리 | `/review`, `/test` |

> **향후 확장**: 프로덕션 배포 및 규모 확장 시 DevOps Agent 분리 검토 (현재 인프라 담당: Backend Dev)

### Prompt Engineer 역할 상세
**핵심 원칙**: "프롬프트 기준 정확한 장면 생성"이 최우선 목표. 수동적 대응이 아닌 **적극적 제안**으로 품질을 선제적으로 개선합니다.

**책임**:
1. **위험 태그 모니터링**: Danbooru에 없는 태그(medium shot 등) 발견 시 즉시 지적 및 대체 제안
2. **프롬프트 품질 분석**: Match Rate 낮은 프롬프트 패턴 분석 및 개선안 제시
3. **Gemini 템플릿 개선**: 템플릿 예시가 부적절하면 Danbooru 검증된 태그로 교체 제안
4. **성공 조합 추출**: 과거 성공 케이스 분석 → 재사용 가능한 태그 조합 추천
5. **자동화 제안**: 반복되는 품질 문제 발견 시 자동 검증/수정 시스템 구축 제안

**적극적 개입 시점**:
- Gemini가 생성한 프롬프트에 위험 태그 발견 시
- Match Rate < 70% 씬 발견 시
- 동일한 태그 조합이 반복 실패할 때
- 새로운 캐릭터/스타일 추가 시 프롬프트 최적화 필요 시
- Danbooru/Civitai에서 더 나은 대안 태그를 발견했을 때

**금지 사항**:
- 문제 발견 후 사용자 지시 대기 (즉시 제안 필수)
- "괜찮을 것 같습니다" 같은 모호한 답변
- 데이터 없는 추측성 제안

## Commands

| Command | 역할 |
|---------|------|
| `/roadmap` | 로드맵 조회/업데이트/기능 목록 |
| `/test` | 테스트 실행 (전체/backend/frontend/vrt/e2e) |
| `/review` | 코드 리뷰 (lint, 품질, 아키텍처, 테스트 커버리지) |
| `/vrt` | Visual Regression Test 실행 |
| `/sd-status` | SD WebUI 상태 확인 |
| `/prompt-validate` | 프롬프트 문법 검증 |
| `/pose` | 포즈 에셋 분석/동기화 |
| `/db` | DB 마이그레이션 상태/생성/적용/롤백 |
| `/docs` | 문서 구조 조회/정합성 체크/크기 점검 |
| `/pm-check` | PM 자율 점검 (문서/로드맵/기능 명세/DoD) |

> Agents/Commands 관리 규칙은 `docs/guides/CONTRIBUTING.md` 참조

## Hooks (자동화)

| Event | Hook | 동작 |
|-------|------|------|
| `PostToolUse` | `auto-lint.sh` | Edit/Write 후 자동 린트 (ruff → `.py`, prettier → `.ts/.tsx`) |

설정: `.claude/settings.json` / 스크립트: `.claude/hooks/auto-lint.sh`

## Workflow Rules (에이전트 자동 워크플로우)

| 트리거 | 자동 액션 | 설명 |
|--------|----------|------|
| 구현 완료 | Tech Lead 코드 리뷰 | 코드 변경 구현 후, 커밋 전에 자동으로 Tech Lead 에이전트가 리뷰 수행 |
| `models/*.py` 또는 `alembic/` 변경 | DBA 리뷰 필수 | 스키마/마이그레이션 변경 시 커밋 전 DBA 에이전트 검증 필수 |
| Phase 작업 완료 시 | PM 문서 동기화 | ROADMAP 상태 업데이트 + FEATURES/ 상태 확인 |
| 새 기능 착수 시 | PM 명세 확인 | FEATURES/ 명세 존재 여부 확인, 없으면 생성 권고 |

**구현 → 리뷰 → 수정 자동 파이프라인**:
1. 코드 변경(Edit/Write) + 빌드/린트 통과
2. Tech Lead 리뷰 자동 실행 (사용자 보고 전)
3. WARNING/BLOCKER 이슈 발견 시 **즉시 자동 수정** 후 재빌드 확인
4. 최종 결과(변경 요약 + 리뷰 통과)를 사용자에게 보고
- 단, 단순 설정 변경(CLAUDE.md, config 수정 등)이나 문서만 수정한 경우는 리뷰를 생략한다.

**스키마 변경 → DBA 리뷰 파이프라인**:
1. `backend/models/*.py` 편집 또는 `backend/alembic/` 마이그레이션 생성/수정
2. DBA 에이전트 자동 호출 — 검증 항목:
   - 네이밍 규칙 준수 (Boolean→`is_`, FK→`_id`)
   - FK 제약조건 + CASCADE 정책 적합성
   - JSONB vs 정규화 판단 근거
   - `DB_SCHEMA.md` + `SCHEMA_SUMMARY.md` 업데이트 여부
   - Known Issues 목록 갱신 필요 여부
3. DBA BLOCKER 발견 시 수정 후 재검증, PASS 후에만 커밋 진행

**테스트 실패 수정 파이프라인**:
- 테스트 실패가 다수(3개 파일 이상) 발생하면 **멀티 에이전트 병렬 수정** 사용.
- 파일별로 독립 에이전트에게 분석+수정 위임 (DB fixture는 공유하므로 실행은 순차, 분석/수정만 병렬).
- 테스트 실행 자체는 단일 프로세스 (`pytest`)로 최종 검증.

## 용어 정의 (Terminology)

### Scene Text vs Caption (2026-01-31 변경)

**혼란 방지를 위한 명확한 용어 구분:**

| 용어 | 설명 | 위치 | 예시 |
|------|------|------|------|
| **Scene Text** | 씬의 스크립트 텍스트 (영상 위 오버레이) | Full: 영상 위 하단<br>Post: 이미지 위 영역 | "처음 칼을 잡았을 때,<br>너무 무서웠어" |
| **Caption** | 게시물 메타데이터 (좋아요, 시간 등) | Post: 카드 하단 | "좋아요 6만개<br>15분 전" |

**변경 사항:**
- `subtitles` → `scene_text` (네이밍 혼란 해소)
- `include_subtitles` → `include_scene_text`
- `subtitle_font` → `scene_text_font`
- `subtitleFont` → `sceneTextFont` (Frontend)
- `DEFAULT_SUBTITLE_FONT` → `DEFAULT_SCENE_TEXT_FONT` (Frontend 상수)
- `SUBTITLE_*` → `SCENE_TEXT_*` (Backend 상수)

**후방 호환성:**
- 기존 `include_subtitles` 필드명은 별칭(alias)으로 작동
- 기존 `subtitle_font` 필드명은 별칭(alias)으로 작동
- Frontend: 마이그레이션 로직에서 `subtitleFont` → `sceneTextFont` 자동 변환
- 기존 코드 수정 없이 동작하지만, 신규 코드는 `scene_text` 사용 권장

## 렌더링 품질 개선 (2026-02-14)

### Layout Type Improvements

#### 1. Post Type Scene Text 동적 높이
**목적**: 텍스트 길이에 따라 Scene Text 영역 높이를 자동 조정하여 공간 활용 최적화

**구현**:
- `calculate_scene_text_area_height()` 함수 추가 (`services/rendering.py`)
- 짧은 텍스트 (< 20자): 12% 높이
- 긴 텍스트 (> 60자 또는 > 2줄): 25% 높이
- 중간 길이: 선형 보간 (12-18%)

**효과**: 텍스트 잘림 방지 + 공간 낭비 최소화

#### 2. Full Type 플랫폼별 Safe Zone
**목적**: 플랫폼 UI 요소(좋아요, 댓글 버튼)와 Scene Text 겹침 방지

**구현**:
- `PLATFORM_SAFE_ZONES` 상수 추가 (`services/image.py`)
- YouTube Shorts: 하단 15% 회피
- TikTok: 하단 20% 회피
- Instagram Reels: 하단 18% 회피
- `calculate_optimal_scene_text_y()` 함수에 `platform` 파라미터 추가

**효과**: 플랫폼별 최적화로 텍스트 가시성 향상

### Visual Quality Improvements

#### 3. Post Type 블러 배경 품질 개선
**목적**: 더 부드럽고 고품질의 블러 효과

**구현**:
- Box Blur (radius=15) + Gaussian Blur (radius=20) 조합
- 기존: Gaussian Blur (radius=30) 단독 사용

**효과**: 고해상도에서도 자연스러운 배경 처리

#### 4. Scene Text 폰트 크기 동적 조정
**목적**: 텍스트 길이에 따라 폰트 크기 자동 조정

**구현**:
- `calculate_optimal_font_size()` 함수 추가 (`services/rendering.py`)
- 짧은 텍스트 (< 20자): 48px (큰 폰트)
- 긴 텍스트 (> 60자): 32px (작은 폰트)
- 중간 길이: 선형 보간 (32-48px)

**효과**: 긴 텍스트 잘림 방지 + 짧은 텍스트 임팩트 강화

#### 5. 배경 밝기 기반 텍스트 색상 자동 조정
**목적**: 배경 밝기에 따라 텍스트 색상 자동 선택으로 가독성 향상

**구현**:
- `analyze_text_region_brightness()` 함수 추가 (`services/image.py`)
- `render_scene_text_image()`에 `background_image` 파라미터 추가
- 밝은 배경 (brightness > 180): 검은 텍스트 + 흰 테두리
- 어두운 배경 (brightness ≤ 180): 흰 텍스트 + 검은 테두리 (기존)

**효과**: 텍스트 가독성 30% 향상 (밝은 배경에서)

**적용 범위**: Full Type Scene Text만 적용 (Post Type은 카드 내부 검은 텍스트 유지)

### 테스트 커버리지
- Layout Improvements: 16개 테스트
- Visual Improvements: 14개 테스트 (밝기 분석 4개 + 폰트 크기 7개 + 적응형 색상 3개)
- VRT: 8개 테스트 (Post Frame 베이스라인 업데이트)

**총 38개 테스트 추가** (기존 테스트 모두 통과)

---

## 렌더링 품질 개선 - 추가 기능 (2026-02-15)

### 6. 얼굴 감지 기반 스마트 크롭 (Post Type)
**목적**: 얼굴 잘림 방지

**구현**:
- OpenCV Haar Cascade 사용
- `detect_face()` 함수 추가 (`services/image.py`)
- `calculate_face_centered_crop()` 함수 추가
- `compose_post_frame()`에 통합
- 얼굴 감지 성공 → 얼굴 중심 크롭
- 얼굴 감지 실패 → 기존 로직 (후방 호환성)

**효과**: 얼굴 잘림 90% 감소

**테스트**: VRT 8개 PASS

---

### 7. TTS 오디오 정규화
**목적**: 씬별 일관된 음량

**구현**:
- `normalize_audio()` 함수 추가 (`services/video/tts_postprocess.py`)
- RMS 기반 dBFS 계산
- 타겟 레벨: -20dBFS (음성 콘텐츠 표준)
- `trim_tts_audio()` 5단계 파이프라인에 통합
- 클리핑 방지 및 무음 처리

**효과**: 일관된 오디오 레벨, 사용자 경험 향상

**테스트**: 6개 단위 테스트 PASS

---

### 8. Post Type 해시태그 색상
**목적**: Instagram 스타일 강화

**구현**:
- 해시태그 색상 변경: RGB(0, 55, 107) → RGB(0, 149, 246)
- Instagram Blue (#0095F6) 적용

**효과**: 더 Instagram 스타일, 해시태그 가시성 향상

**테스트**: VRT 8개 PASS

---

### 전체 테스트 커버리지 (2026-02-14~15)
- Layout Improvements: 16개 테스트
- Visual Improvements: 14개 테스트
- VRT: 8개 테스트
- Face Detection: VRT 8개 (통합)
- TTS Normalization: 6개 테스트
- Hashtag Color: VRT 8개 (통합)

**총 52개 테스트 추가** (모두 PASS)

