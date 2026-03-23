# /sentry-patrol Command

Sentry 에러 배치 순찰 — 새 이슈 수집 후 GitHub Issue 자동 생성.

## 사용법

```
/sentry-patrol [--since HOURS]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--since` | 24 | 최근 N시간 내 새 이슈 조회 |

## 실행 내용

아래를 **순서대로 자동 수행**한다.

### 1. 환경변수 확인
- `SENTRY_AUTH_TOKEN` 존재 확인 (없으면 안내 후 중단)
- `backend/.env`에서 로드 시도

### 2. 스크립트 실행
```bash
# backend/.env에서 SENTRY_AUTH_TOKEN 로드 후 실행
source backend/.env 2>/dev/null
./scripts/sdd-sentry.sh --since ${HOURS:-24}
```

### 3. 결과 보고
- 새 이슈 수, 스킵(중복) 수, GitHub Issue 생성 수 요약

## 프로세스

```
Sentry API (3개 프로젝트 순회)
  → firstSeen 기준 새 이슈 필터링
  → GitHub Issues (label:sentry) 중복 체크
  → 최신 이벤트 스택트레이스 조회
  → gh issue create (label: sentry, bug)
```

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `SENTRY_AUTH_TOKEN` | Yes | Sentry API Bearer token |

## 관련 파일
- `scripts/sdd-sentry.sh` — 배치 순찰 스크립트
- `backend/.env` — SENTRY_AUTH_TOKEN 저장
