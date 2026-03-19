---
id: SP-004
priority: P1
scope: frontend
branch: feat/SP-004-e2e-smoke-tests
created: 2026-03-20
status: pending
depends_on:
---

## 무엇을
Playwright E2E smoke 테스트 3개 + 기본 인프라 (서버 자동 기동 포함)

## 왜
현재 E2E 테스트가 없어 PR Test Plan의 수동 확인 항목을 자동화할 수 없음.
가장 기본적인 smoke 테스트부터 시작하여 점진적으로 확장.

## 완료 기준 (DoD)
- [ ] `frontend/e2e/` 디렉토리 생성
- [ ] playwright.config.ts에 E2E 프로젝트 추가 (기존 VRT와 분리)
- [ ] webServer 설정으로 Backend+Frontend 자동 기동/종료
- [ ] Smoke 테스트 3개 작성
  - Home 페이지 로딩 + 기본 요소 확인
  - Studio 페이지 접근 + 탭 전환
  - 스토리보드 목록 페이지 로딩
- [ ] `npm run test:e2e` 스크립트 추가
- [ ] 기존 VRT 테스트 regression 없음

## 제약
- 변경 파일 10개 이하
- 외부 API 호출 없음 (페이지 로딩만 확인)
- DB는 기존 개발 DB 사용
- 의존성 추가 금지 (Playwright 이미 설치됨)

## 힌트
- 기존 VRT: frontend/tests/vrt/ + playwright.config.ts
- Playwright webServer: https://playwright.dev/docs/test-webserver
- Backend: uv run uvicorn main:app --port 8000
- Frontend: npm run dev -- --port 3000
