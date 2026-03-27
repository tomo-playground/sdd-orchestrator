---
id: SP-090
priority: P2
scope: frontend
branch: feat/SP-090-contextbar-improve
created: 2026-03-26
status: done
approved_at: 2026-03-26
depends_on:
label: feature
---

## 무엇을 (What)
PersistentContextBar 높이 확대, 아이콘 추가, Library/Settings에서 숨기기, 단일 채널 자동 숨기기.

## 왜 (Why)
3계층 컨텍스트가 32px에 압축. Library는 시리즈 컨텍스트와 무관한데 ContextBar 노출.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase B — SP-053 항목

## 완료 기준 (DoD)
- [ ] ContextBar 높이: h-10 (40px)
- [ ] 채널/시리즈 아이콘 추가 (폴더 아이콘)
- [ ] Library 페이지(`/library/*`)에서 ContextBar 숨김
- [ ] Settings 페이지(`/settings/*`)에서 ContextBar 숨김
- [ ] 채널 1개 + 시리즈 1개인 경우 ContextBar 자동 숨김 (로딩 완료 후 판정)
- [ ] Studio 작업 영역 높이 감소 체감 확인 (VRT)
- [ ] VRT 베이스라인 갱신

## 힌트
- `PersistentContextBar.tsx` — h-8→h-10, pathname 기반 숨기기
- `useProjectGroups()` 훅 — `projects.length === 1 && groups.length === 1` 조건
