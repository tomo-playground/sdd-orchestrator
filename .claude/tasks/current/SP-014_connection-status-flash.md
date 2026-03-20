---
id: SP-014
priority: P0
scope: frontend
branch: feat/SP-014-connection-status-flash
created: 2026-03-21
status: pending
depends_on:
label: bug
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
페이지 전환마다 "연결 끊김" 오경고가 1~2초 플래시되는 문제 수정

## 왜
- 매 페이지 네비게이션마다 `useBackendHealth` hook이 리마운트되면서 초기값 `"disconnected"`로 리셋
- Backend는 정상(200 OK)인데 "Backend 서버와 연결이 끊어졌습니다" 알림 + 빨간 "연결 끊김" 표시가 깜빡임
- 사용자에게 불안감 유발, 서비스 신뢰도 저하

## 원인 분석
1. `useBackendHealth.ts`: `useState<ConnectionStatus>("disconnected")` — 초기값이 disconnected
2. `ServiceShell.tsx`가 페이지 전환 시 리렌더링 → hook 재마운트 → 상태 리셋
3. 첫 health check(`GET /health`) 응답 도착 전까지 disconnected 상태가 UI에 노출
4. `ConnectionGuard.tsx`가 disconnected일 때 전화면 오버레이 표시
5. `AppFooter.tsx`가 "연결 끊김" 텍스트 + 빨간 점 표시

## 완료 기준 (DoD)
- [ ] 페이지 전환 시 "연결 끊김" 플래시가 나타나지 않음
- [ ] 실제 Backend 다운 시에는 여전히 "연결 끊김" 정상 표시 (3회 실패 후)
- [ ] health check 주기(10초)/임계값(3회) 기존 동작 유지
- [ ] 기존 테스트 regression 없음
- [ ] 빌드(next build) 통과

## 수정 방향
**A안 (권장): 연결 상태를 모듈 레벨 싱글턴으로 전환**
- `useBackendHealth.ts` 내부에서 모듈 스코프 변수로 상태 관리 (또는 Zustand store)
- hook이 리마운트되어도 이전 상태를 유지
- health check 타이머도 싱글턴으로 유지 (중복 폴링 방지)

**B안: 초기값을 optimistic으로 변경**
- `useState("connected")` → 실제 실패 시에만 disconnected 전환
- 단점: 앱 최초 로드 시 Backend가 죽어있으면 false positive

## 제약
- 변경 파일 5개 이하 목표
- 건드리면 안 되는 것: health check 엔드포인트(`/health`), 폴링 주기/임계값
- 의존성 추가 금지

## 힌트
- 관련 파일:
  - `app/hooks/useBackendHealth.ts` — 핵심 수정 대상
  - `app/components/shell/ServiceShell.tsx` (L89) — hook 호출부
  - `app/components/shell/DevShell.tsx` (L18) — hook 호출부
  - `app/components/shell/ConnectionGuard.tsx` — disconnected 오버레이
  - `app/components/shell/AppFooter.tsx` — 상태바 "연결됨/연결 끊김"
- QA 스크린샷: `qa-screenshots/01-home.png` ~ `13-new-storyboard.png`
- 참고: health check는 `GET /health` (Next.js proxy → Backend 8000)
