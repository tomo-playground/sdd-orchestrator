---
id: SP-104
priority: P2
scope: frontend
branch: feat/SP-104-ui-label-korean
created: 2026-03-26
status: design
depends_on:
label: feature
---

## 무엇을 (What)
NavBar, Studio 탭, Library 탭, Settings 탭, PipelineStatusDots 등 UI 전체 라벨 한국어화 + Dev 항목 제거.

## 왜 (Why)
서비스 기본 언어가 한국어인데 영문 라벨(Script, Stage, Direct, Publish 등)이 잔존. 전문 용어(LoRAs, Dev)도 사용자에게 노출.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase A — SP-050 항목
- 원래 ID SP-050 → SP-087로 재할당 (ID 충돌)

## 완료 기준 (DoD)
- [ ] NavBar: 홈, 스튜디오, 라이브러리, 설정 (Dev 항목 제거)
- [ ] Studio 탭: 대본, 준비, 이미지, 게시 (key 값 script/stage/direct/publish 유지)
- [ ] Library 탭: 캐릭터, 화풍, 음성, BGM, LoRAs(Phase D에서 제거 예정)
- [ ] Settings 탭: 렌더 설정, 연동, 휴지통
- [ ] PipelineStatusDots label 전체 한국어화
- [ ] PreflightModal STEP_LABELS 전체 한국어화
- [ ] ContinueWorkingSection STEP_META 한국어화
- [ ] QuickStatsBar 카테고리 한국어화
- [ ] AUTO_RUN_STEPS 한국어화
- [ ] Dev는 NavBar에서 제거, `/dev` URL 직접 접근은 유지
- [ ] E2E 테스트: 영문 라벨 매칭 → 한국어 라벨로 수정
- [ ] VRT 베이스라인 전체 갱신
- [ ] 빌드 에러 0개

## 힌트
- `ServiceShell.tsx` — NavBar 라벨 + DEV_ITEM 제거
- `StudioWorkspaceTabs.tsx` — Studio 탭 label
- `LibraryShell.tsx` — Library 탭 label
- `SettingsShell.tsx` — Settings 탭 label
- `PipelineStatusDots.tsx` — STEPS label
- `PreflightModal.tsx` — STEP_LABELS
- `MaterialsPopover.tsx` — 항목 label
- `ContinueWorkingSection.tsx` — STEP_META label
- `QuickStatsBar.tsx` — 카테고리 label
- `constants/index.ts` — AUTO_RUN_STEPS label
- 테스트: `e2e/smoke.spec.ts`, `e2e/qa-patrol.spec.ts`, `tests/vrt/studio-e2e.spec.ts`, `tests/vrt/home.spec.ts`, `tests/vrt/warning-toast-e2e.spec.ts`

## 주의
- 로직 변경 없음 — 문자열 교체 위주
- key/URI 값(script, stage, direct, publish) 변경 금지
- 파일 수 13~15개지만 변경 내용 단순

## 상세 설계 (How)
→ `design.md` 참조

**요약**: 15개 파일 변경 (소스 10 + 테스트 5). 로직 변경 0건. 순수 문자열 교체.

| 영역 | 파일 수 | 핵심 변경 |
|------|---------|----------|
| NavBar | 1 | 4개 라벨 한국어 + Dev 블록 제거 |
| Studio 탭 | 1 | 4개 label (key 유지) |
| Library 탭 | 1 | 5개 label (LoRAs 유지) |
| Settings 탭 | 1 | 3개 label |
| PipelineStatusDots | 1 | 5개 label + 15개 tooltip 문자열 |
| PreflightModal | 1 | 4개 STEP_LABELS |
| MaterialsPopover | 1 | 6개 label + 헤더/상태 텍스트 |
| ContinueWorkingSection | 1 | 4개 STEP_META label + 섹션 제목 |
| QuickStatsBar | 1 | 4개 카테고리 label |
| constants | 1 | AUTO_RUN_STEPS 2개 label |
| E2E/VRT 테스트 | 5 | 영문 매칭 → 한국어 매칭 |

**구현 순서**: 소스 변경 → 빌드 확인 → 테스트 매칭 수정 → VRT 갱신 → 전체 테스트
