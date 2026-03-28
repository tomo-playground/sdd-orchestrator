---
id: SP-101
priority: P2
scope: frontend
branch: feat/SP-101-voices-master-detail
created: 2026-03-26
status: running
approved_at: 2026-03-26
depends_on: SP-099
label: feature
---

## 무엇을 (What)
Voices 페이지를 LibraryMasterDetail로 전환.

## 왜 (Why)
현재 상단 인라인 폼 + 카드 그리드 → 좌측 목록 | 우측 편집 폼 통일.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase D — SP-060b 항목

## 완료 기준 (DoD)
- [ ] Voices 페이지가 LibraryMasterDetail 사용
- [ ] 기존 CRUD + TTS 미리보기 동일 동작: E2E 검증
- [ ] VRT 베이스라인 갱신
