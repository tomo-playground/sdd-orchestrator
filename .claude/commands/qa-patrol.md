# /qa-patrol Command

Playwright QA 순찰 — 핵심 플로우 자동 테스트 후 이상 감지 시 GitHub Issue 생성.

## 사용법

```
/qa-patrol
```

## 실행 내용

아래를 **순서대로 자동 수행**한다.

### 1. 서비스 상태 확인
- Backend (localhost:8000) + Frontend (localhost:3000) 헬스체크
- 서비스 다운 시 GitHub Issue 생성 후 중단

### 2. Playwright 테스트 실행
```bash
./scripts/qa-patrol.sh
```

### 3. 결과 보고
- 모든 테스트 통과: 정상 보고
- 테스트 실패: 실패 테스트 목록 + GitHub Issue 자동 생성

## 순찰 플로우

| 테스트 | 감지 항목 |
|--------|----------|
| 홈 접속 | 페이지 로드, 네비게이션, 콘솔 에러 |
| Studio 접속 | 칸반 로드, API 에러 |
| 새 영상 | 에디터 로드, 탭 렌더링 |
| Settings | 페이지 로드 |

## 감지 항목
- JS 콘솔 에러 (React 개발 경고 제외)
- API 5xx 응답
- DOM 요소 부재 (로딩 실패)
- 15초 timeout

## 관련 파일
- `scripts/qa-patrol.sh` — 순찰 래퍼 스크립트
- `frontend/e2e/qa-patrol.spec.ts` — Playwright 순찰 테스트
- `frontend/playwright.e2e.config.ts` — E2E 설정
