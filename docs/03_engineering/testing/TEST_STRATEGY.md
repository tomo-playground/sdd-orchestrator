# Test Strategy

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
| **VRT** | pytest + SSIM | 이미지 렌더링 (자막, 오버레이, 프레임) | Golden Master 비교 |
| **E2E** | Playwright | Studio/Manage 페이지 유저 플로우 | Mock API 응답 |

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

**주요 개선사항 (Phase 6-5)**:
- DB Foreign Key 제약 정규화 (CASCADE 전략)
- validation.py DI 패턴 적용 (conftest.py 통합)
- Scene Text 네이밍 통일 (`subtitles` → `scene_text`)
- TagRuleCache 추가 (tag_rules 테이블 캐싱)
- LoRATriggerCache 추가 (loras 테이블 트리거 워드 캐싱)

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
- Max diff pixels: 100, threshold: 0.2
- Retry: CI 2회, 로컬 0회

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
```

---

## 4. 커버리지 목표

| 영역 | 현재 | 목표 |
|------|------|------|
| Backend Unit + Integration | 830 tests (60 files) | 80% line coverage |
| Frontend Unit | 118 tests (10 files) | 70% line coverage |
| VRT | 36 tests (4 files) | 주요 레이아웃 100% |
| E2E | 3 specs | 핵심 플로우 커버 |

**총 테스트**: 948개 (Backend 830 + Frontend 118)

**Backend 구성**:
- Unit: 429 tests (29 files, `tests/test_*.py`)
- Integration: 77 tests (7 files, `tests/api/`)
- Router: 288 tests (20 files, `tests/test_router_*.py`)
- VRT: 36 tests (4 files, `tests/vrt/`)

**최근 추가된 주요 테스트** (2026-02-01):
- `test_evaluation.py` - Evaluation 서비스 단위 테스트 (47 tests)
- `test_router_*.py` - 20개 라우터 통합 테스트 (288 tests, Phase 1-4)
- `test_v3_composition.py` - V3 Prompt Engine 12-Layer 검증 (41 tests)
- `test_generation_pipeline.py` - 이미지 생성 파이프라인 통합 테스트
- `test_image_storage_key.py` - image_storage_key 정규화 검증
- `test_db_cache.py` - TagRuleCache, LoRATriggerCache 검증

**Router 커버리지**: 20/24 라우터 (83%) - DoD 달성
- 테스트 있음 (20): storyboard, characters, style_profiles, loras, prompt, keywords, evaluation, video, settings, presets, admin, quality, tags, analytics, activity_logs, controlnet, avatar, sd, scene, assets
- 테스트 없음 (4): cleanup, prompt_histories, sd_models, generation

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
