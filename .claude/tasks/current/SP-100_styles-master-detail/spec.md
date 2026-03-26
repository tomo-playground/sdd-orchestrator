---
id: SP-100
priority: P2
scope: frontend
branch: feat/SP-100-styles-master-detail
created: 2026-03-26
status: approved
approved_at: 2026-03-26
depends_on: SP-099
label: feature
---

## 무엇을 (What)
Styles 페이지를 LibraryMasterDetail로 전환.

## 왜 (Why)
현재 카드 그리드 + 하단 인라인 에디터 → 좌측 목록 | 우측 StyleProfileEditor 통일.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase D — SP-060a 항목

## 완료 기준 (DoD)
- [ ] Styles 페이지가 LibraryMasterDetail 사용
- [ ] 기존 CRUD 기능 동일 동작: 생성/편집/삭제/복제 각각 E2E 검증
- [ ] VRT 베이스라인 갱신
