---
id: SP-091
priority: P2
scope: frontend
branch: feat/SP-091-trash-to-library
created: 2026-03-26
status: pending
depends_on:
label: feature
---

## 무엇을 (What)
Settings에서 Trash 탭 제거 → Library 하단에 휴지통 링크로 이동.

## 왜 (Why)
Trash(콘텐츠 복구)는 설정이 아니라 콘텐츠 관리. Library에 위치하는 것이 자연스러움.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase B — SP-054a 항목

## 완료 기준 (DoD)
- [ ] `/library/trash` 경로에서 휴지통 정상 표시
- [ ] `/settings/trash` → `/library/trash` 리다이렉트
- [ ] Library 탭바 하단에 "휴지통" 링크 (별도 섹션, 탭과 시각적 구분)
- [ ] Settings 탭: 렌더 설정, 연동 (2개)
- [ ] 빌드 에러 0개

## 힌트
- `SettingsShell.tsx` — Trash 탭 제거
- `LibraryShell.tsx` — 하단에 Trash 링크 추가
- `app/(service)/library/trash/page.tsx` — 신규 (기존 TrashTab 컴포넌트 재사용)
- `next.config.ts` — `/settings/trash` → `/library/trash` redirect
