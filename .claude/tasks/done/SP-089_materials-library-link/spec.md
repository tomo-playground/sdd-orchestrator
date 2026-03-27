---
id: SP-089
priority: P2
scope: frontend
branch: feat/SP-089-materials-library-link
created: 2026-03-26
status: done
approved_at: 2026-03-26
depends_on:
label: feature
---

## 무엇을 (What)
Materials 팝오버에서 Characters/Style이 Missing 상태일 때 Library 페이지로 직접 이동하는 링크 추가.

## 왜 (Why)
현재 Studio와 Library 연결이 부재. Voice/Music은 Library 링크가 있지만, Characters/Style은 `action: "stage-tab"`만 존재하여 Missing 발견 시 Library로 이동 불가.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase A — SP-052 항목

## 완료 기준 (DoD)
- [ ] Characters Missing 상태에서 클릭 → `/library/characters` 이동
- [ ] Style Missing 상태에서 클릭 → `/library/styles` 이동
- [ ] Ready 상태에서는 기존 동작(stage-tab) 유지
- [ ] Missing 상태 링크에 "만들기 →" 텍스트 표시
- [ ] 빌드 에러 0개

## 힌트
- `MaterialsPopover.tsx` — Characters/Style 항목에 조건부 `link` 추가
- 기존 패턴: Voice `link: "/library/voices"`, Music `link: "/library/music"` 이미 존재
- `missing` 시에만 `link` 오버라이드, `ready` 시 기존 `action` 유지
