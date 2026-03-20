---
id: SP-008
priority: P2
scope: frontend
branch: feat/SP-008-background-delete-ui
created: 2026-03-20
status: running
depends_on:
---

## 무엇을
배경 이미지 삭제 UI 추가

## 왜
Backend에 배경 삭제 API가 있지만 프론트엔드에서 삭제할 방법이 없음.
사용하지 않는 배경이 쌓여서 목록이 지저분해짐.

## 완료 기준 (DoD)
- [ ] 배경 목록/카드에 삭제 버튼
- [ ] 삭제 확인 다이얼로그
- [ ] `DELETE /api/v1/backgrounds/{id}` 호출
- [ ] 삭제 후 목록 갱신 + 토스트
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 5개 이하
- Backend 변경 없음

## 힌트
- Backend: routers/backgrounds.py DELETE 엔드포인트
- 배경 페이지: frontend/app/(service)/backgrounds/page.tsx
