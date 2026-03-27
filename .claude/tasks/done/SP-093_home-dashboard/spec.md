---
id: SP-093
priority: P2
scope: frontend
branch: feat/SP-093-home-dashboard
created: 2026-03-26
status: done
approved_at: 2026-03-26
depends_on:
label: feature
---

## 무엇을 (What)
Home 대시보드 개선 — WelcomeBar에 빠른 시작 입력 필드, ContinueWorkingSection에 진행 상태 표시.

## 왜 (Why)
Home이 허브 역할을 못 함. HomeVideoFeed만 렌더링되고 있으나 WelcomeBar/QuickStatsBar/ContinueWorkingSection은 이미 존재 — 개선 수준.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase B — SP-049 항목

## 완료 기준 (DoD)
- [ ] WelcomeBar에 주제 입력 필드 추가 (채널/시리즈가 이미 존재하는 경우에만 표시)
- [ ] 입력 시 기존 API 3개 순차 호출 (project→group→storyboard) → `/studio?id=X` 이동
- [ ] ContinueWorkingSection 각 카드에 진행 상태 표시 (대본/준비/이미지/렌더/완성)
- [ ] 채널/시리즈가 없는 초기 사용자: 기존 SetupWizard 동작 유지
- [ ] VRT 베이스라인 갱신

## 힌트
- `WelcomeBar.tsx` — 빠른 시작 입력 필드
- `ContinueWorkingSection.tsx` — 진행 상태 5단계 dots
- `QuickStatsBar.tsx` — 채널 개요 강화
- SetupWizard 완료 후 ContextStore `setProjectId()`/`setGroupId()` 호출

## 상세 설계 (How)

→ `design.md` 참조.

**핵심 결정:**
1. **빠른 시작 API**: spec DoD에 "API 3개 순차 호출"이라 되어 있으나, 채널/시리즈가 이미 존재할 때만 표시되므로 `POST /storyboards/draft` 1개 호출로 충분. draft 생성 후 `/studio?id=X&topic=Y`로 이동.
2. **5단계 진행 상태**: 기존 `kanban_status` 4단계 + `stage_status` 필드 조합으로 5단계 파생. Backend 스키마 변경 불필요 (이미 `stage_status` 포함).
3. **QuickStatsBar**: 현재 충분히 기능하고 있어 이번 스코프에서 변경 없음. DoD에도 명시되지 않음.
4. **변경 파일**: WelcomeBar.tsx, ContinueWorkingSection.tsx, home.spec.ts (VRT). Studio page에 topic 쿼리 파라미터 처리 추가.
