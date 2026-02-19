# Test Strategy

**최종 업데이트**: 2026-02-19

---

## 1. 테스트 레벨

```
E2E (Playwright)          ← 유저 플로우 검증
  Integration (API)       ← 라우터 + DB + 서비스 통합
    Unit (pytest/vitest)  ← 개별 함수/훅 로직
      VRT (SSIM)          ← 렌더링 결과 시각 비교
```

| 레벨 | 도구 | 대상 | 격리 방식 |
|------|------|------|----------|
| **Unit** | pytest / vitest | 서비스 함수, 유틸, 훅 | Mock, 인메모리 |
| **Integration** | pytest + TestClient | API 라우터 + DB | SQLite 인메모리 |
| **VRT (Backend)** | pytest + SSIM | 이미지 렌더링 (자막, 오버레이, 프레임, 결정적 렌더링) | Golden Master 비교 |
| **VRT (Frontend)** | Playwright `toHaveScreenshot()` | 페이지별 스크린샷 (8 페이지, 24장) | Mock API + baseline PNG |
| **E2E** | Playwright | Studio/Manage/Home 유저 플로우 | Mock API 응답 |

---

## 2. 도구 및 설정

### Backend (pytest)

| 항목 | 값 |
|------|-----|
| 프레임워크 | `pytest >= 8.0.0` |
| 비동기 | `pytest-asyncio` (auto mode) |
| 커버리지 | `pytest-cov` |
| 설정 | `backend/pyproject.toml` → `testpaths = ["tests"]` |
| DB | SQLite 인메모리 (`StaticPool`, 테스트별 격리) |
| 시드 | `seed_random` fixture (seed=42) |

**핵심 Fixture** (`backend/tests/conftest.py`):

| Fixture | 역할 |
|---------|------|
| `db_session` | SQLite 인메모리 세션 (테스트별 생성/삭제) |
| `client` | FastAPI TestClient (`get_db` 의존성 오버라이드) |
| `init_tag_caches` | autouse. TagFilter/Rule/Alias/Category/LoRA 캐시 초기화 |
| `seed_random` | 난수 시드 고정 (결정적 테스트) |

**주요 개선사항 (Phase 6-5 ~ 10)**:
- DB Foreign Key 제약 정규화 (CASCADE 전략)
- validation.py DI 패턴 적용 (conftest.py 통합)
- Scene Text 네이밍 통일 (`subtitles` → `scene_text`)
- TagRuleCache 추가 (tag_rules 테이블 캐싱)
- LoRATriggerCache 추가 (loras 테이블 트리거 워드 캐싱)
- Phase 10: Creative Script Graph 테스트 94개 추가 (agent, tool calling, graph nodes)

### Frontend (vitest + Playwright)

| 항목 | 값 |
|------|-----|
| Unit/Integration | `vitest` (jsdom 환경) |
| 컴포넌트 | React Testing Library |
| E2E | Playwright (Chromium) |
| 설정 | `frontend/vitest.config.ts`, `frontend/playwright.config.ts` |
| Mock | `vi.mock()`, `tests/helpers/mockApi.ts` |

**Playwright 설정**:
- Snapshot: `tests/vrt/__snapshots__/`
- Max diff pixels: 100, threshold: 0.2, animations: disabled
- Retry: CI 2회, 로컬 0회

**Frontend VRT** (상세: `VRT_GUIDE.md`):
- 8개 스펙 파일, 24개 스크린샷 (list + empty 상태)
- Mock: `tests/helpers/mockApi.ts` (페이지별 API 인터셉터)
- Fixtures: `tests/helpers/fixtures/` (Mock 데이터 분리)
- Utils: `tests/helpers/vrtUtils.ts` (waitForPageReady, hideAnimations, clearLocalStorage)

---

## 3. 실행 방법

### 전체 실행

```bash
./run_tests.sh
```

순서: Backend (pytest) → Frontend (vitest) → VRT (pytest). 결과 요약 출력.

### 개별 실행

```bash
# Backend 전체
cd backend && uv run pytest

# Backend 특정 파일
uv run pytest tests/test_motion.py -v

# Backend VRT만
uv run pytest tests/vrt/ -v

# Frontend Unit
cd frontend && npm test

# Frontend E2E
npx playwright test

# Frontend VRT (baseline 비교)
cd frontend && npm run test:vrt

# Frontend VRT (baseline 갱신)
npm run test:vrt:update

# Frontend VRT (UI 모드)
npm run test:vrt:ui
```

---

## 4. 커버리지 현황

| 영역 | 현재 | 목표 |
|------|------|------|
| Backend Unit | 1,334 tests (103 files) | 80% line coverage |
| Backend Router | 368 tests (25 files) | 주요 라우터 100% |
| Backend Integration | 108 tests (9 files) | 핵심 API 100% |
| Backend VRT | 36 tests (4 files) | 주요 레이아웃 100% |
| Backend Benchmark | 18 tests | 성능 기준선 |
| Frontend Unit | 352 tests (31 files) | 70% line coverage |
| Frontend VRT | 24 screenshots (8 specs) | 전체 페이지 커버 |
| Frontend E2E | 3 specs | 핵심 플로우 커버 |

**총 테스트**: **2,214개** (Backend 1,862 + Frontend 352)

### Backend 구성 (1,862 tests, 143 files)

| 유형 | 테스트 수 | 파일 수 | 위치 |
|------|----------|---------|------|
| Unit | 1,334 | 103 | `tests/test_*.py` (router 제외) |
| Router | 368 | 25 | `tests/test_router_*.py` |
| Integration | 108 | 9 | `tests/api/` |
| VRT | 36 | 4 | `tests/vrt/` |
| Benchmark | 18 | 1 | `tests/benchmark/` |

### Frontend 구성 (352 tests, 31 files)

| 카테고리 | 주요 테스트 | 테스트 수 |
|----------|-----------|----------|
| Hooks | useAutopilot(27), useCharacters(13), useFocusTrap(5) | 45+ |
| Store Actions | storyboardActions(33), groupActions(12), narratorGeneration(11) | 63+ |
| Components | Button(15), Modal(13), Badge(9), ConfirmDialog(8), Skeleton(7) | 73+ |
| Utils | validation(34), speakerResolver(24), sceneSettingsResolver(14), autoPin(11), format(10) | 161+ |
| Store | resetAllStores(6) | 6 |

### Router 커버리지: 25/33 라우터 (76%)

**테스트 있음 (25)**: storyboard, characters, style_profiles, loras, prompt, keywords, video, video_async, settings, presets, admin, quality, tags, analytics, activity_logs, controlnet, avatar, sd, scene, assets, music_presets, groups, projects, render_presets, voice_presets

**테스트 없음 (8)**: cleanup, prompt_histories, sd_models, backgrounds, lab, memory, scripts, creative_presets, youtube

> `tests/api/` 통합 테스트가 일부 라우터(lab, render_presets, quality, activity_logs)를 추가 커버

---

## 5. 테스트 작성 규칙

### 네이밍

```python
# Backend: test_{동작}_{조건}_{기대결과}
def test_compose_prompt_with_empty_tags_returns_base_only():

# Frontend: describe > it 패턴
describe("useAutopilot", () => {
  it("should pause when cancel is triggered", () => {
```

### 새 기능 추가 시

1. Unit 테스트 먼저 (TDD 권장)
2. API 라우터 변경 시 Integration 테스트 추가
3. 렌더링 변경 시 VRT Golden Master 갱신
4. UI 플로우 변경 시 E2E 시나리오 검토

### Mock 원칙

- 외부 서비스(SD WebUI, Gemini API)는 항상 Mock
- DB는 SQLite 인메모리 (프로덕션 DB 접근 금지)
- 파일 I/O는 tmp 디렉토리 사용
