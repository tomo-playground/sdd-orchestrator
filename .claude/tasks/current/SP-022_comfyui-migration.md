---
id: SP-022
priority: P1
scope: backend
branch: feat/SP-022-comfyui-migration
created: 2026-03-21
status: pending
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
ForgeUI → ComfyUI 마이그레이션 + SD Client 추상화 계층 도입

## 왜
- 1-step 고정 파이프라인의 구조적 한계 (ControlNet + IP-Adapter 동시 투입 품질 저하)
- ComfyUI 네이티브 배치 생성/프롬프트 스케줄링 활용
- 캐릭터 일관성 V3의 선행 조건

## 완료 기준 (DoD)
- [ ] `SDClientBase` 인터페이스 + `WebUIClient` + `ComfyUIClient` 구현
- [ ] 4-Module 파이프라인 동작 (Identity → Context → Refinement → Upscale)
- [ ] 2-Step 생성(CN→IPA) 또는 FaceID+CN 1-Step 생성 지원
- [ ] 배치 4씬 일괄 생성 가능
- [ ] 기존 SD WebUI 직접 호출 지점 0건 (services/, routers/)
- [ ] pytest 전체 통과

## 제약
- Phase A~F, 대규모 작업 → 태스크 분할 필요
- 건드리면 안 되는 것: 프롬프트 엔진 (composition.py)
- ComfyUI 서버 별도 설치/설정 필요

## 힌트
- 명세: `docs/01_product/FEATURES/COMFYUI_MIGRATION.md`
- 실험 검증 4회 54장 완료 (명세 내 결과)
- 관련 파일: `backend/services/image.py`, `backend/services/generation_prompt.py`
