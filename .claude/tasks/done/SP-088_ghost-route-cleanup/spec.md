---
id: SP-088
priority: P2
scope: frontend
branch: feat/SP-088-ghost-route-cleanup
created: 2026-03-26
approved_at: 2026-03-26
depends_on:
label: chore
---

## 무엇을 (What)
사용하지 않는 Ghost Route(/scripts, /storyboards)와 미사용 컴포넌트(AppMobileTabBar) 삭제.

## 왜 (Why)
/scripts, /storyboards는 page.tsx에서 useRouter redirect만 하는 유령 라우트. AppMobileTabBar는 import 0건.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase A — SP-051 항목

## 완료 기준 (DoD)
- [ ] `/scripts?id=X` → `/studio?id=X` 리다이렉트 정상 (next.config, query 자동 전달)
- [ ] `/scripts?new=true` → `/studio?new=true` 리다이렉트 정상
- [ ] `/scripts` (query 없음) → `/studio` 리다이렉트
- [ ] `/storyboards` → `/` 리다이렉트 정상
- [ ] `AppMobileTabBar.tsx` 삭제됨
- [ ] redirect E2E 테스트 추가 (3경로 검증)
- [ ] 빌드 에러 0개, 기존 테스트 전체 통과

## 힌트
- `app/(service)/scripts/page.tsx` — 삭제 → next.config redirect
- `app/(service)/storyboards/page.tsx` — 삭제 → next.config redirect
- `app/components/layout/AppMobileTabBar.tsx` — 삭제 (import 0건)
- `next.config.ts` — redirect 규칙 추가

## 주의
- `AppSidebar.tsx` 삭제 보류 — Phase D Master-Detail에 재활용 가능
- `AppThreeColumnLayout.tsx` 삭제 보류 — Phase C 3패널에 재활용 가능
- next.config redirect에서 query string은 자동 전달됨
