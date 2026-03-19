---
id: SP-002
priority: P1
scope: frontend
branch: feat/SP-002-tts-warning-frontend-toast
created: 2026-03-19
status: done
depends_on: SP-001
---

## 무엇을
Backend가 전달하는 warnings 필드를 프론트엔드에서 토스트로 표시

## 왜
PR #38에서 Backend가 warnings 배열을 SSE/Sync 양쪽으로 전달하지만,
프론트엔드에서 이를 소비하지 않아 사용자가 TTS Designer 실패를 인지할 수 없음.

## 완료 기준 (DoD)
- [x] SSE 응답의 warnings 필드 파싱
- [x] Sync 응답의 warnings 필드 파싱
- [x] warnings 존재 시 warning 토스트 표시 ("voice design 누락 씬 N개")
- [x] warnings 타입 정의 (string[])
- [x] 기존 기능 regression 없음

## 제약
- 변경 파일 10개 이하
- Backend 변경 없음
- 의존성 추가 금지

## 힌트
- SSE 경로: _scripts_sse.py → result.warnings
- Sync 경로: scripts.py → response.warnings
- 기존 토스트: useToast 또는 toast 유틸 확인
