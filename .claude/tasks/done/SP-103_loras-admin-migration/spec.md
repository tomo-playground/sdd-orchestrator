---
id: SP-103
priority: P2
scope: frontend
branch: feat/SP-103-loras-admin-migration
created: 2026-03-26
approved_at: 2026-03-26
depends_on: SP-100
label: chore
---

## 무엇을 (What)
Library에서 LoRAs 탭 제거. `/dev` (Admin)에서만 관리.

## 왜 (Why)
LoRAs는 일반 사용자 기능이 아니라 Admin 전용. 화풍(Styles) 상세에서 LoRA 선택은 이미 존재.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase D — SP-061 항목

## 완료 기준 (DoD)
- [x] Library 탭에서 LoRAs 제거
- [x] `/library/loras` → `/dev/sd-models` redirect (기존 북마크 대응)
- [x] 화풍(Styles) 상세의 LoRA 선택 기능 정상 동작 확인
- [x] 빌드 에러 0개

## 힌트
- `LibraryShell.tsx` — LoRAs 탭 항목 제거
- `app/(service)/library/loras/page.tsx` — 삭제 또는 redirect
- `next.config.ts` — `/library/loras` → `/dev/sd-models` redirect
