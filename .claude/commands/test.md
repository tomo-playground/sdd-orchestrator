# /test Command

프로젝트 테스트를 실행하는 원자적 명령입니다.

## 사용법

```
/test [scope]
```

### Scopes

| Scope | 설명 |
|-------|------|
| (없음) | 전체 테스트 실행 (Backend + Frontend) |
| `backend` | Backend pytest만 실행 |
| `frontend` | Frontend vitest만 실행 |
| `vrt` | Visual Regression Test만 실행 |
| `e2e` | Playwright E2E 테스트만 실행 |
| `changed` | 변경 코드에 영향받는 테스트만 (testmon) |
| `failed` | 마지막 실패 테스트만 재실행 (--lf) |
| `parallel` | 전체 테스트 병렬 실행 (xdist) |
| `watch` | Watch 모드 + testmon (파일 저장 시 자동 실행) |

## 실행 내용

### 전체 테스트
```bash
./run_tests.sh
```

### Backend
```bash
cd backend && uv run pytest -v
```

### Frontend Unit
```bash
cd frontend && npm test
```

### VRT (Backend)
```bash
cd backend && uv run pytest tests/vrt/ -v
```

### E2E (Playwright)
```bash
cd frontend && npx playwright test
```

### Changed (testmon)
```bash
cd backend && uv run pytest --testmon -v
```

### Failed (--lf)
```bash
cd backend && uv run pytest --lf -v
```

### Parallel (xdist)
```bash
cd backend && uv run pytest -n auto -v
```

### Watch (ptw + testmon)
```bash
cd backend && uv run ptw -- --testmon -x -v
```

## 출력 형식

```markdown
## 테스트 결과

### Backend
✅ 335 passed, 5 skipped

### Frontend
✅ 67 passed

### VRT
✅ 36/36 passed

### 요약
총 438개 테스트 | ✅ 전체 통과
```

## 관련 파일
- `docs/03_engineering/testing/TEST_STRATEGY.md` - 테스트 전략
- `docs/03_engineering/testing/TEST_SCENARIOS.md` - 테스트 시나리오
- `backend/tests/conftest.py` - Backend 테스트 Fixtures
- `frontend/vitest.config.ts` - Frontend 테스트 설정
- `frontend/playwright.config.ts` - E2E 테스트 설정
- `run_tests.sh` - 통합 테스트 스크립트
