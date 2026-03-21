---
id: SP-026
priority: P2
scope: fullstack
branch: feat/SP-026-storyboard-version-history
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
스토리보드 버전 히스토리 — 저장 시점별 스냅샷 조회/복원

## 왜
- 현재 스토리보드 수정 시 이전 상태 복원 불가
- 실수로 씬 삭제/변경 시 되돌릴 방법 없음
- 자동 저장과 결합하면 안전망 역할

## 완료 기준 (DoD)
- [ ] 저장 시 스토리보드 스냅샷 생성 (JSONB)
- [ ] 버전 목록 조회 API + UI
- [ ] 특정 버전으로 복원 기능
- [ ] 버전 수 상한 (예: 최근 20개) + 자동 정리
- [ ] 기존 기능 regression 없음

## 제약
- DB 스키마 변경 포함 → DBA 리뷰 필수
- 건드리면 안 되는 것: 기존 저장/로드 로직 (추가만)
- 스토리지 비용 고려 (JSONB 스냅샷 크기)

## 힌트
- 관련 파일: `backend/services/storyboard/crud.py`, `backend/models/storyboard.py`
- 기존 `storyboards.version` 컬럼 활용 가능
