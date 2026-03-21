---
id: SP-023
priority: P1
scope: backend
branch: feat/SP-023-character-consistency-v3
created: 2026-03-21
status: pending
depends_on: SP-022
label: enhancement
assignee: stopper2008
---

## 무엇을
캐릭터 일관성 V3 — 다단계 모듈 파이프라인 (ComfyUI 기반)

## 왜
- V2(Phase 30)에서 1회 SD 호출에 모든 도구 동시 투입 → 구조적 한계
- 캐릭터 일관성 + 포즈 다양성 + 의상 가변성 동시 확보 불가
- 실험 검증으로 2-Step(CN→IPA) + FaceID 도입 효과 확인됨

## 완료 기준 (DoD)
- [ ] 4-Module 파이프라인 (Identity → Context → Refinement → Upscale)
- [ ] Identity Module: FaceID + LoRA 캐릭터 인식
- [ ] Context Module: ControlNet 포즈 + 씬 컨텍스트
- [ ] Refinement Module: IP-Adapter 디테일 보정
- [ ] 동일 캐릭터 씬간 일관성 70%+ (Match Rate 기준)
- [ ] 기존 기능 regression 없음

## 제약
- ComfyUI 마이그레이션(SP-022) 선행 필수
- 건드리면 안 되는 것: 프롬프트 빌더 로직
- GPU VRAM 한도 고려 필요

## 힌트
- 명세: `docs/01_product/FEATURES/CHARACTER_CONSISTENCY_V3.md`
- V2 명세: `docs/99_archive/features/CHARACTER_CONSISTENCY_V2.md`
- 실험 결과: 씬 컨셉 레퍼런스 > 흰배경 레퍼런스 (명세 내 실험 섹션)
