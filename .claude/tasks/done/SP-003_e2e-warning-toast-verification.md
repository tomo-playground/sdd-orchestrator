---
id: SP-003
priority: P2
scope: fullstack
branch: feat/SP-003-e2e-warning-toast-verification
created: 2026-03-19
status: done
depends_on: SP-002
---

## 무엇을
PR Test Plan의 수동 확인 항목을 Playwright E2E 테스트로 자동화

## 왜
SP-002 PR에서 수동 확인 2건이 남음. SDD 워크플로우에서 Stop Hook이 자동 검증하려면
E2E 테스트가 있어야 함. 수동 확인 의존도를 줄여 완전 자율 실행에 가까워짐.

## 완료 기준 (DoD)
- [ ] Playwright 테스트: TTS Designer 실패 mock → warning 토스트 표시 확인
- [ ] Playwright 테스트: warnings 없을 때 기존 동작 변화 없음 확인
- [ ] 기존 테스트 regression 없음

## 제약
- 변경 파일 10개 이하
- Backend mock으로 Gemini API 실패 시뮬레이션 (실제 API 호출 금지)
- 서버 기동 상태에서만 실행 가능 (on-stop.sh E2E 조건과 동일)

## 힌트
- 기존 E2E: frontend/tests/vrt/ 또는 playwright.config.ts 확인
- warning 토스트: SP-002에서 추가한 handleStreamOutcome → toast 경로
- Backend mock: MSW 또는 Playwright route intercept 활용
