---
id: SP-024
priority: P2
scope: fullstack
branch: feat/SP-024-veo-clip
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Google VEO Video Generation API 통합 — 씬 단위 비디오 클립 생성

## 왜
- 현재 정지 이미지 + Ken Burns 효과만으로 영상 구성 → 역동성 부족
- AI Video Generation으로 더 몰입감 있는 쇼츠 제작 가능

## 완료 기준 (DoD)
- [ ] VEO API 호출 파이프라인 구현
- [ ] 씬별 이미지/비디오 선택 토글 UI
- [ ] 비디오 클립을 FFmpeg 렌더링 파이프라인에 통합
- [ ] 생성 실패 시 기존 이미지 + Ken Burns fallback
- [ ] 기존 기능 regression 없음

## 제약
- 건드리면 안 되는 것: 기존 이미지 기반 워크플로우
- VEO API 비용/할당량 확인 필요

## 힌트
- 명세: `docs/01_product/FEATURES/VEO_CLIP.md`
- 관련 파일: `backend/services/video/`, `frontend/app/components/scene/SceneCard.tsx`
