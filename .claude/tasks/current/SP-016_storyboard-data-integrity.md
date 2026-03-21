---
id: SP-016
priority: P0
scope: full-stack
branch: feat/SP-016-storyboard-data-integrity
created: 2026-03-21
status: pending
depends_on:
label: bug
assignee: stopper2008
---

## 무엇을
씬 데이터 무결성 보장 — UI/DB 씬 불일치 + FK 위반 방지

## 왜
- SB 1128: UI에 7씬 표시되지만 DB에 0씬 (데이터 소실)
- FK 위반으로 orphan 씬 발생 가능
- 사용자가 작업한 씬이 저장 안 되는 치명적 데이터 손실 버그

## 참조
- 기능 명세: `docs/01_product/FEATURES/STORYBOARD_DATA_INTEGRITY.md`

## 완료 기준 (DoD)
- [ ] UI 씬 수와 DB 씬 수 일치 보장
- [ ] 저장 실패 시 사용자에게 명확한 에러 표시
- [ ] FK 위반 orphan 씬 방지
- [ ] 기존 테스트 통과
