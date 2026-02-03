# /review Command

코드 변경사항을 종합 리뷰하는 워크플로우입니다.

## 사용법

```
/review [scope]
```

### Scopes

| Scope | 설명 |
|-------|------|
| (없음) | 현재 브랜치의 전체 unstaged+staged 변경사항 리뷰 |
| `backend` | Backend 변경사항만 리뷰 |
| `frontend` | Frontend 변경사항만 리뷰 |
| `staged` | git staged 변경사항만 리뷰 |
| `branch` | 현재 브랜치의 main 대비 전체 diff 리뷰 |

## 리뷰 워크플로우

$ARGUMENTS 값에 따라 scope를 결정하세요.

### Step 1: 변경 범위 파악

scope에 따라 적절한 diff를 확인하세요:

- **(없음)**: `git diff --stat && git diff --staged --stat`
- **staged**: `git diff --staged --stat`
- **branch**: `git diff main...HEAD --stat`
- **backend/frontend**: 해당 디렉토리 필터링

변경된 파일 목록과 변경 규모를 먼저 파악합니다.

### Step 2: 린트 검사

**Backend (Python):**
```bash
cd backend && uv run ruff check --diff .
```

**Frontend (TypeScript):**
```bash
cd frontend && npx eslint --max-warnings 0 .
```

린트 에러가 있으면 파일:라인 형태로 리포트하세요.

### Step 3: 코드 품질 가이드라인 검증

CLAUDE.md 기준에 따라 변경된 파일을 검증하세요:

| 단위 | 권장 | 최대 |
|------|------|------|
| 함수/메서드 | 30줄 | 50줄 |
| 클래스/컴포넌트 | 150줄 | 200줄 |
| 코드 파일 | 300줄 | 400줄 |

변경된 파일 중 기준 초과 항목을 리포트하세요.

### Step 4: 아키텍처 리뷰

변경된 코드를 읽고 다음을 검토하세요:

- **Single Responsibility**: 하나의 함수/클래스가 하나의 책임만 갖는지
- **중첩 깊이**: 3단계 이하인지
- **매개변수 수**: 4개 이하인지
- **보안**: SQL injection, XSS, 하드코딩된 credential 등
- **설정 SSOT**: `backend/config.py` 외에 하드코딩된 상수가 없는지
- **태그 포맷**: Danbooru 언더바 표준 준수 여부 (태그 관련 변경 시)

### Step 5: 테스트 커버리지

변경된 코드에 대한 테스트가 존재하는지 확인하세요:

- Backend: `backend/tests/` 내 관련 테스트 파일 확인
- Frontend: 컴포넌트/훅에 대한 `.test.ts(x)` 확인
- 새 기능이 추가된 경우 테스트가 함께 있는지 확인

## 출력 형식

```markdown
## Code Review Report

### 변경 요약
- 변경 파일: N개
- 추가: +N줄 / 삭제: -N줄
- 영향 범위: backend/frontend/both

### Lint 결과
- Backend (ruff): PASS/FAIL
- Frontend (eslint): PASS/FAIL
- (실패 시 상세 내용 포함)

### 코드 품질
- 파일 크기 초과: (있으면 목록)
- 함수 크기 초과: (있으면 목록)
- 중첩 깊이 초과: (있으면 목록)

### 아키텍처 이슈
- 🔴 Blocker: (머지 전 반드시 수정)
- 🟡 Warning: (머지 전 수정 권장)
- 🔵 Suggestion: (개선 제안)

### 테스트 커버리지
- 테스트 존재 여부
- 누락된 테스트 케이스 제안

### 최종 판정
✅ APPROVE / ⚠️ APPROVE with comments / ❌ REQUEST CHANGES
```

## 관련 파일
- `CLAUDE.md` - 코드 가이드라인 (SSOT)
- `docs/03_engineering/testing/TEST_STRATEGY.md` - 테스트 전략
- `backend/pyproject.toml` - Ruff 설정
- `frontend/eslint.config.mjs` - ESLint 설정
