---
id: SP-099
priority: P2
scope: frontend
branch: feat/SP-099-master-detail-layout
created: 2026-03-26
status: approved
approved_at: 2026-03-26
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

## 상세 설계 (How)

`design.md` 참조. 요약:

**신규 파일 1개:**
- `frontend/app/components/layout/LibraryMasterDetail.tsx` — 제네릭 Master-Detail 레이아웃 (~150줄)

**핵심 결정:**
- 제네릭 `T extends { id: number }` 타입으로 Styles/Voices/Music 공통 사용
- 반응형: `md:` 브레이크포인트 기준 2패널(데스크톱) / 조건부 1패널(모바일)
- AppSidebar.tsx: 삭제하지 않고 보류 (미사용이나 용도가 다르고 향후 활용 가능)
- 마스터 패널 `w-80` 고정, 디테일 패널 `flex-1`

**테스트:**
- `LibraryMasterDetail.test.tsx` — vitest 단위 테스트 7개 (렌더링, 선택, 검색, 로딩, 빈 상태)
- VRT/E2E는 후속 SP-060a/b/c에서 수행
