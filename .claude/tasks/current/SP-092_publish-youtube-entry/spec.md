---
id: SP-092
priority: P2
scope: frontend
branch: feat/SP-092-publish-youtube-entry
created: 2026-03-26
status: approved
approved_at: 2026-03-26
depends_on:
label: feature
---

## 무엇을 (What)
Publish 탭에 YouTube 연동 상태 인라인 표시 + Settings 링크 추가.

## 왜 (Why)
YouTube 연동이 Settings에만 있어서 Publish 탭에서 연동 상태를 확인할 수 없음.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase B — SP-054b 항목

## 완료 기준 (DoD)
- [ ] Publish 탭에 YouTube 연동 상태 배지 표시 (연결됨: 초록 / 미연결: 회색)
- [ ] 연동 상태는 `useYouTubeTab()` 훅의 `isConnected` 필드 사용
- [ ] 미연결 시 "설정 > 연동에서 연결 →" 링크 (`/settings/youtube`)
- [ ] 빌드 에러 0개

## 힌트
- Publish 탭 컴포넌트에 YouTube 상태 인라인 표시
- `useYouTubeTab()` 훅 — 기존 `isConnected` 상태 활용 (신규 API 없음)
