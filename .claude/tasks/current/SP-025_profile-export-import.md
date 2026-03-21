---
id: SP-025
priority: P2
scope: fullstack
branch: feat/SP-025-profile-export-import
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Style Profile JSON Export/Import — 화풍 프로필 공유 기능

## 왜
- Style Profile(Model + LoRA + Embeddings 세트)을 다른 환경이나 사용자와 공유 불가
- 환경 이전 시 수동 재설정 필요

## 완료 기준 (DoD)
- [ ] Profile → JSON Export (Model, LoRA, Embedding 메타데이터)
- [ ] JSON → Profile Import + 누락 에셋 경고
- [ ] Import 시 모델/LoRA 존재 여부 검증
- [ ] Settings > Style 탭에 Export/Import 버튼 UI
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: StyleProfile ORM 모델 구조

## 힌트
- 명세: `docs/01_product/FEATURES/PROFILE_EXPORT_IMPORT.md`
- 관련 파일: `backend/models/style_profile.py`, `backend/routers/style_profiles.py`
