---
id: SP-099
priority: P2
scope: frontend
branch: feat/SP-099-master-detail-layout
created: 2026-03-26
status: pending
depends_on:
label: feature
---

## 무엇을 (What)
LibraryMasterDetail 공통 레이아웃 컴포넌트 신규 생성.

## 왜 (Why)
Library 4페이지(Styles/Voices/Music/LoRAs)의 CRUD 패턴이 모두 다름. 공통 Master-Detail로 통일.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase D — SP-059 항목

## 완료 기준 (DoD)
- [ ] LibraryMasterDetail 컴포넌트: `items`, `selectedId`, `onSelect`, `renderDetail` props
- [ ] 좌측: 아이템 리스트 (검색, 필터, + 추가 버튼)
- [ ] 우측: 선택된 아이템 상세/편집
- [ ] 반응형: 모바일에서는 목록만 → 클릭 시 상세 전체화면
- [ ] AppSidebar.tsx 처리 결정 (재활용 또는 삭제)
- [ ] 독립 렌더링 테스트 통과
