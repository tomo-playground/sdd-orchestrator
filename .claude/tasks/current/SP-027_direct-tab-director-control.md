---
id: SP-027
priority: P2
scope: fullstack
branch: feat/SP-027-direct-tab-director-control
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Direct 탭 연출 컨트롤 — TTS 톤 조정 + BGM 프리셋 일괄 적용

## 왜
- TTS 음성 톤을 조정할 곳이 없음 — 생성 후 음성 감정을 바꿀 수 없음
- BGM/Voice 설정이 Stage + Publish에 산재 — 어디서 수정해야 할지 혼란
- 전체 톤 일괄 변경 불가 — 20씬이면 20번 개별 수정

## 완료 기준 (DoD)
- [ ] 전체 기본 음성 톤 설정 (밝게/긴장/차분 등)
- [ ] 씬별 음성 톤 오버라이드
- [ ] BGM 분위기 프리셋 일괄 적용
- [ ] Direct 탭 연출 패널 UI
- [ ] 기존 기능 regression 없음

## 제약
- 건드리면 안 되는 것: Publish 탭 렌더 파라미터 (audioDucking, bgmVolume 등)
- 원천 UI 수정 원칙: 연출 의도는 Direct 탭, 렌더 파라미터는 Publish 탭

## 힌트
- 명세: `docs/01_product/FEATURES/DIRECT_TAB_DIRECTOR_CONTROL.md`
- 관련 파일: `frontend/app/components/studio/DirectTab.tsx`, `backend/services/video/tts_postprocess.py`
