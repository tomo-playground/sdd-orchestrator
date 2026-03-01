# Shorts Producer V3 — 종합 감사 보고서

**일시**: 2026-02-28
**감사 에이전트**: Backend Dev, Frontend Dev, DBA, Security Engineer, Tech Lead, QA Validator
**범위**: Backend + Frontend + DB + 보안 + 아키텍처 전체

---

## 요약 대시보드

| Severity | 건수 | 설명 |
|----------|------|------|
| **P0 - Critical** | 7 | 즉시 수정 필요 |
| **P1 - High** | 22 | 1~2주 내 수정 권장 |
| **P2 - Medium** | 38 | 기술 부채, 스프린트 내 개선 |
| **P3 - Low** | 25 | 개선 권장, 백로그 등록 |
| **총합** | **92** | |

---

## P0 — Critical (5건)

### P0-1. Admin API 인증/인가 완전 부재 [Security]
- **위치**: `backend/main.py:157-158`, `backend/routers/__init__.py:12,40-62`
- **내용**: 29개 라우터 전체 무인증. `DELETE /characters/{id}/permanent`, `POST /storage/cleanup`, `POST /youtube/callback` 등 위험 엔드포인트 포함.
- **영향**: 네트워크 접근 가능한 누구나 데이터 삭제, 과금 API 호출, 서비스 장애 유발 가능.
- **조치**: API Key 또는 Session 기반 인증 미들웨어 추가.

### P0-2. asyncio.create_task 결과 미보관 (Fire-and-Forget) [Backend]
- **위치**: `backend/routers/scene.py:563`, `backend/routers/video.py:104`
- **내용**: 백그라운드 Task 결과를 변수에 저장하지 않아 GC가 수집하면 예외가 침묵됨. Python 3.12+에서 경고 발생.
- **영향**: 이미지/비디오 생성 작업이 조용히 실패할 수 있음.
- **조치**: 모듈 레벨 `set[asyncio.Task]`에 보관, 완료 시 콜백으로 제거.

### P0-3. ImageTaskProgress / VideoTaskProgress Race Condition [Backend]
- **위치**: `backend/services/image_progress.py:60-74`, `backend/services/video/progress.py:106-122`
- **내용**: 다수 SSE 클라이언트가 동일 task polling 시 `_event.clear()` 경합. 빠른 연속 notify 시 이벤트 누락 가능.
- **조치**: `asyncio.Condition` 사용 또는 클라이언트별 독립 이벤트 구조로 변경.

### P0-4. CORS `allow_credentials=True` + `allow_origins` 설정 위험 [Security]
- **위치**: `backend/main.py:136-142`, `backend/config.py:220-222`
- **내용**: `CORS_ORIGINS` 환경변수를 `*`로 설정하면 CSRF 공격에 완전 노출. 현재 기본값(`localhost:3000`)은 안전하나 배포 시 위험.
- **조치**: startup 시 `allow_credentials=True` + `*` 조합 감지 → 에러로 차단.

### P0-5. V3PromptBuilder 1,252줄 단일 클래스 [Tech Lead]
- **위치**: `backend/services/prompt/v3_composition.py` (1,361줄)
- **내용**: CLAUDE.md 클래스 최대 200줄 기준 6.3배 초과. 유지보수성 심각.
- **조치**: Background/Character/Reference 컴포저를 별도 클래스로 분리 (Strategy/Mixin 패턴).

---

## P1 — High (18건)

### Backend

| ID | 제목 | 위치 | 내용 |
|----|------|------|------|
| P1-1 | response_model 누락 (~60개) | `routers/*.py` 전반 | CLAUDE.md "response_model 필수" 위반. characters(5), activity_logs(3), admin(6), settings(5), controlnet(10), loras(4), tags(2), assets(5) 등 |
| P1-2 | SSE 스트림 에러 미전달 | `routers/scene.py:646`, `routers/video.py:206` | 예외 발생 시 로깅만, 클라이언트에 error 이벤트 미전송 → 무한 대기 |
| P1-3 | In-memory task store 무한 증가 | `services/image_progress.py:78`, `video/progress.py:126` | cleanup이 create 시에만 동작. base64 이미지(수 MB)가 누적 가능 |
| P1-4 | Rate Limiting 완전 부재 | `main.py` 전체 | Gemini API/SD WebUI/FFmpeg 무제한 호출 가능 → 과금 폭증, GPU 고갈 |
| P1-5 | 에러 응답에 내부 예외 메시지 직접 노출 | `admin.py:235`, `activity_logs.py:144` 등 15+곳 | `str(e)` → DB 정보, 파일 경로 등 노출. `raise_user_error()` 패턴 통일 필요 |
| P1-6 | SSRF DNS Rebinding 취약 | `services/image.py:56-86`, `agent/nodes/research.py:72-91` | 도메인의 DNS 해석 결과 미검증. 내부 네트워크 접근 가능 |
| P1-7 | asyncio.run() in BackgroundTasks | `routers/admin.py:111` | 이벤트 루프 충돌 가능성 (RuntimeError) |

### Frontend

| ID | 제목 | 위치 | 내용 |
|----|------|------|------|
| P1-8 | SSE EventSource cleanup 누락 | `utils/renderWithProgress.ts` | 렌더링 시작 후 페이지 이탈해도 EventSource가 계속 열림 |
| P1-9 | autoSave isDirty 구독 경합 | `store/effects/autoSave.ts:52-54` | `isDirty`가 `true→true`일 때 트리거 안 됨. isGenerating 중 변경 누락 가능 |
| P1-10 | handleImageUpload FileReader 에러 미처리 | `store/actions/imageActions.ts:72-117` | `reader.onerror` 미설정. Promise 미반환으로 완료 추적 불가 |
| P1-11 | useStudioInitialization unmount 방어 없음 | `hooks/useStudioInitialization.ts:137-236` | async 작업 중 unmount 시 setState 경고 |
| P1-12 | batchActions SD 파라미터 하드코딩 | `store/actions/batchActions.ts:54-60` | `steps:27, cfg_scale:7` 등 Frontend 하드코딩. Backend SSOT 위반 |

### DB

| ID | 제목 | 위치 | 내용 |
|----|------|------|------|
| P1-13 | Soft Delete 필터 누락 16건 | `generation_controlnet.py:234`, `image_gen_pipeline.py:65`, `prompt.py:131,238,293` 등 | 삭제된 Scene/Character에 대해 이미지 생성 시도 가능 |
| P1-14 | N+1 쿼리 (TagRule 개별 조회) | `routers/activity_logs.py:516-517,689-690` | TagRule 순회마다 Tag 2건씩 개별 쿼리. joinedload 적용 필요 |

### Security (추가)

| ID | 제목 | 위치 | 내용 |
|----|------|------|------|
| P1-15 | debug_db_status.py DB URL 콘솔 출력 | `backend/debug_db_status.py:7` | `engine.url` (패스워드 포함 가능) 노출 |
| P1-16 | subprocess argument injection | `services/video/effects.py:186-199` | storage key가 `-`로 시작하면 ffmpeg 옵션으로 해석 가능 |

### Architecture (추가)

| ID | 제목 | 위치 | 내용 |
|----|------|------|------|
| P1-17 | rendering.py ↔ layout.py 이중 관리 | `services/rendering.py` vs `constants/layout.py` | rendering.py가 layout.py를 import하지 않고 매직 넘버 20+회 하드코딩. SSOT 위반 |
| P1-18 | schemas.py 2,253줄 단일 파일 | `backend/schemas.py` | 210개 Pydantic 클래스. 가이드라인 5.6배 초과 |

---

## P2 — Medium (33건)

### 코드 크기 위반 (13건)

| 파일 | 줄 수 | 비고 |
|------|------|------|
| `backend/services/rendering.py` | 1,266 | layout.py 미사용 |
| `backend/services/keywords/patterns.py` | 981 | |
| `backend/routers/activity_logs.py` | 886 | 분석 로직이 라우터에 위치 |
| `backend/services/prompt/prompt.py` | 782 | |
| `backend/services/controlnet.py` | 746 | |
| `backend/config.py` | 744 | SSOT이므로 구조적 불가피 |
| `backend/routers/scene.py` | 647 | validate_and_auto_edit 164줄 |
| `backend/services/imagen_edit.py` | 607 | cost_usd 11회 하드코딩 |
| `backend/routers/scripts.py` | 588 | |
| `frontend/app/(service)/pipeline-demo/page.tsx` | 1,320 | 단일 컴포넌트 |
| `frontend/app/types/index.ts` | 977 | 80개 타입, 분할 필요 |
| `frontend/app/admin/lab/tabs/SceneLabTab.tsx` | 553 | |
| `frontend/app/admin/system/tabs/GeneralSettingsTab.tsx` | 528 | |

### Backend 이슈 (6건)

| ID | 제목 | 위치 |
|----|------|------|
| P2-1 | DB 세션 점유 상태 SD WebUI 호출 | `services/generation.py:56`, `services/lab.py:80` |
| P2-2 | storage.py 전역 변수 thread-safety | `services/storage.py:260` |
| P2-3 | hashlib.sha1 사용 (deprecated) | 9곳 (scene.py, asset_service.py 등) |
| P2-4 | Tag 전체 테이블 로드 | `routers/activity_logs.py:631` |
| P2-5 | Gemini 동기 호출 in async 함수 | `routers/video.py:432,467` |
| P2-6 | imagen_edit.py 비용 상수 하드코딩 | `services/imagen_edit.py` (11회) |

### Frontend 이슈 (6건)

| ID | 제목 | 위치 |
|----|------|------|
| P2-7 | 빈 catch 핸들러 6곳 | useCharacterAutoLoad, usePublishRender, sceneActions 등 |
| P2-8 | IP-Adapter 참조 API 중복 호출 | useCharacterAutoLoad + useSceneActions |
| P2-9 | useShortsSession stale closure | `components/lab/useShortsSession.ts:24` |
| P2-10 | useProjectGroups fetchGroups 이중 호출 | `hooks/useProjectGroups.ts:54-66` |
| P2-11 | persistStoryboard 에러 시 사일런트 실패 | `store/actions/storyboardActions.ts:306` |
| P2-12 | generateSceneCandidates 3회 실패 시 피드백 없음 | `store/actions/imageGeneration.ts:251` |

### DB 이슈 (4건)

| ID | 제목 | 위치 |
|----|------|------|
| P2-13 | FK 인덱스 누락 (자주 조회 테이블 8개) | scenes.image_asset_id, groups.render_preset_id 등 |
| P2-14 | Soft Delete 관계 필터링 (앱 레벨) | `services/storyboard/crud.py:154` |
| P2-15 | scene.py db.close() 후 재사용 | `routers/scene.py:419-460` |
| P2-16 | DB_SCHEMA.md 불일치 4건 | valence, thumbnail_asset_id, style_profile_id, bgm_audio_asset_id 미기재 |

### Security 이슈 (4건)

| ID | 제목 | 위치 |
|----|------|------|
| P2-17 | /outputs 디렉토리 무인증 정적 서빙 | `main.py:146-147` |
| P2-18 | Admin Swagger UI 무인증 노출 | `main.py:195-207` |
| P2-19 | setattr() Mass Assignment 위험 | groups.py, projects.py, loras.py 등 10+곳 |
| P2-20 | YOUTUBE_TOKEN_ENCRYPTION_KEY 형식 미검증 | `config_pipelines.py:15` |

---

## P3 — Low (22건)

### Backend (9건)
- 불필요한 noqa 주석 과다
- 함수 내부 import 패턴 (순환 의존성 우회 5곳)
- video/create SessionLocal 수동 관리
- f-string 로깅 (성능)
- `_strip_quotes` 불완전
- image_cache TOCTOU
- scripts.py preflight `except: pass`
- projects.py 페이지네이션 없음
- group delete 시 FK 참조 명시적 체크 없음

### Frontend (7건)
- Pre-hydration SSR 패턴
- CATEGORY_DESCRIPTIONS 하드코딩
- language "Korean" 기본값 하드코딩 (3곳)
- resetContext 중복 로직
- buildScenesPayload 경로별 미세 차이
- toast ID 비결정적 생성
- useStoryboards 에러 시 빈 배열

### DB (3건)
- `default_` prefix (허용 범위)
- `_thumbnail_asset` 비표준 관계명
- render_presets music_preset relationship 미정의

### Security (2건)
- Git에 디버그/관리 스크립트 포함 (4개)
- `allow_methods=["*"]`, `allow_headers=["*"]`

### Architecture (1건)
- REST_API.md에 엔드포인트 ~94개 미반영

---

## 테스트 커버리지 감사 [QA Validator]

### 현황 요약

| 영역 | 테스트 수 | 비고 |
|------|----------|------|
| Backend 단위 | 2,670 | 프롬프트 엔진 183개 등 핵심 양호 |
| Backend 통합 (API) | 98 | 8개 라우터만 커버, 30개 중 7개 라우터 미테스트 |
| Frontend 단위 | ~435 | 컴포넌트 커버리지 **9.5%** (179개 중 17개) |
| E2E | 2 스펙 | 핵심 시나리오 부족 |
| VRT | 24 스크린샷 | 기준선 2/12, **16일 미갱신** |

### P0 — 테스트 없는 핵심 모듈

| 모듈 | 줄 수 | 위험도 | 이유 |
|------|------|--------|------|
| `routers/scripts.py` | 588줄 / 21EP | **CRITICAL** | LangGraph 파이프라인 핵심 진입점, 테스트 0개 |
| `services/rendering.py` | 1,266줄 | **CRITICAL** | 프로젝트 최대 파일, 렌더링 핵심, 테스트 0개 |

### P1 — 커버리지 갭

| 대상 | 규모 | 이슈 |
|------|------|------|
| 미테스트 라우터 7개 | scripts, prompt_histories, sd_models, youtube, stage, memory, creative_presets | 문서는 "27/30" 주장, 실제 23/30 |
| `routers/scene.py` | 647줄 | 테스트 **1개**만 존재 |
| `storyboard/crud.py` | 604줄 | 핵심 CRUD, 테스트 0개 |
| `keywords/patterns.py` | 981줄 | 태그 패턴 핵심, 테스트 0개 |
| `imagen_edit.py` | 607줄 | Gemini 편집, 테스트 0개 |
| `video/scene_processing.py` + `builder.py` | 888줄 합계 | 렌더링 파이프라인 |
| Frontend Hooks 커버리지 | 31개 중 5개 (16.1%) | useStudioInit(340줄), useMusic(258줄) 등 미테스트 |
| Frontend Actions 커버리지 | 13개 중 6개 (46.2%) | imageGeneration(307줄), styleProfileActions(252줄) 미테스트 |
| Agent 노드 유틸 | 14개 미테스트 | _context_tag_utils, _debate_utils 등 |

### P2 — 테스트 품질

| 이슈 | 상세 |
|------|------|
| 빈 테스트 3개 | `test_validate_tags_with_danbooru` 등 본문 없음 |
| Mock 과다 | `test_tool_calling.py` Mock:Test = 6:1, `test_cinematographer_tags.py` 8:1 |
| 하드코딩 경로 8개 | `/tmp/` 경로 → `tmp_path` fixture 교체 필요 |
| 시간 의존 테스트 | `test_soft_delete.py` time.sleep(), `test_progress.py` asyncio.sleep() |
| VRT 기준선 미갱신 | Frontend 2/12, Backend 2/15 이후 UI/렌더링 변경 미반영 |
| TEST_STRATEGY.md 불일치 | "27/30 라우터" 주장 vs 실제 23/30 |

### 통합 테스트 미커버 핵심 플로우

1. Scripts/LangGraph 전체 파이프라인 (generate → SSE → 노드실행 → 결과)
2. 이미지 생성 전체 (Scene → 프롬프트 → SD → Asset 저장)
3. 비디오 렌더링 전체 (Storyboard → 씬 처리 → FFmpeg → 업로드)
4. YouTube 업로드 (인증 → 업로드 → 상태 추적)
5. Stage 파이프라인 (캐스팅 → 확정 → 연출)
6. 캐릭터 CRUD (생성 → LoRA → 프리뷰 → 삭제 cascade)

---

## 긍정적 평가 (잘 구현된 부분)

| 영역 | 내용 |
|------|------|
| **Path Security** | `safe_resolve_path()`, `safe_storage_path()` — `is_relative_to()` 검증 |
| **Upload Validation** | MIME whitelist + 파일 크기 + magic bytes 3중 검증 |
| **YouTube OAuth** | HMAC-signed state + `hmac.compare_digest()` |
| **토큰 암호화** | Fernet 암호화로 DB 저장 |
| **SQLAlchemy ORM** | raw SQL 없음 (일회용 스크립트 제외), 파라미터 바인딩 자동 적용 |
| **Frontend XSS** | `dangerouslySetInnerHTML` 0건 |
| **Frontend 상태 관리** | Zustand 4-Store 아키텍처 일관성, TRANSIENT_KEYS persistence 필터링 |
| **Frontend 타입 안전성** | `any` 사용 2건만 (양호) |
| **폰트 사이즈 규칙** | `text-[9px]`, `text-[10px]` 사용 0건 |
| **.gitignore** | `.env`, `.key`, `.pem` 모두 포함. Git 히스토리에도 민감 파일 없음 |
| **테스트** | Backend 2,667 + Frontend 435 = 총 3,102개 |
| **TODO/FIXME** | Backend 2건, Frontend 0건 (양호) |

---

## 우선순위별 조치 로드맵

### Sprint A — 즉시 (P0 해소)
1. Admin API 인증 미들웨어 추가 (P0-1)
2. `asyncio.create_task` 결과 보관 패턴 적용 (P0-2)
3. SSE Progress Race Condition 수정 (P0-3)
4. CORS startup 검증 추가 (P0-4)
5. V3PromptBuilder 분할 착수 (P0-5)

### Sprint B — 1~2주 (P1 핵심)
6. response_model 일괄 추가 (~60개)
7. SSE 에러 이벤트 전달
8. Rate Limiting 도입 (slowapi)
9. `raise_user_error()` 패턴 통일
10. Soft Delete 필터 16건 보강
11. Frontend SSE cleanup + autoSave 경합 수정
12. batchActions SD 파라미터 Backend 위임

### Sprint C — 2~4주 (P2 기술 부채)
13. schemas.py 도메인별 분할
14. rendering.py → layout.py 통합
15. activity_logs 서비스 계층 추출
16. FK 인덱스 일괄 추가 마이그레이션
17. DB_SCHEMA.md 동기화
18. Frontend 빈 catch 핸들러 + 에러 UX 개선

### Sprint C-2 — 테스트 커버리지 (P0~P1)
13-a. `routers/scripts.py` 통합 테스트 신규 작성 (~15개)
13-b. `services/rendering.py` 단위 테스트 신규 작성 (~25개)
13-c. `services/storyboard/crud.py` 단위/통합 테스트 (~15개)
13-d. `routers/scene.py` 라우터 테스트 보강 (~15개)
13-e. Frontend `imageGeneration.ts` + `imageActions.ts` 테스트 (~15개)
13-f. VRT 기준선 갱신 (2/12 이후 UI 변경 반영)
13-g. TEST_STRATEGY.md 문서 동기화 (27/30 → 실제 23/30 수정)

### Backlog (P3)
19. scripts/ 디렉토리 정리
20. REST_API.md 동기화
21. 순환 의존성 리팩토링
22. types/index.ts 분할
23. Frontend 컴포넌트 커버리지 9.5% → 30% 목표
24. E2E 시나리오 2개 → 5개 확대
25. 하드코딩된 `/tmp/` 경로 → `tmp_path` fixture 교체 (8개 파일)
