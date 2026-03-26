---
id: SP-094
priority: P2
scope: frontend
branch: feat/SP-094-direct-e2e-safety
created: 2026-03-26
status: pending
depends_on:
label: chore
---

## 무엇을 (What)
Direct 탭 E2E 테스트 보강 — Phase C 리팩토링 전 회귀 방지 안전망.

## 왜 (Why)
Phase C에서 SceneCard/3패널 대규모 리팩토링 예정. 사전 E2E 없으면 regression 감지 불가.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase C — SP-058 항목

## 완료 기준 (DoD)
- [ ] Direct 탭 핵심 플로우 E2E 시나리오 (SD WebUI 모킹):
  - 씬 선택 → 이미지 생성 트리거 확인 (API 호출 발생, 실제 생성은 mock)
  - 씬 프롬프트 편집 → 저장 → DB 반영
  - 씬 삭제 → 목록 갱신
  - TTS 미리보기 버튼 클릭 → 오디오 플레이어 표시
- [ ] 기존 `studio-e2e.spec.ts` 확장 또는 별도 spec
- [ ] 모킹 전략: SD WebUI/TTS API는 `page.route()` 인터셉트로 fixture 응답

## 힌트
- 기존 `tests/vrt/studio-e2e.spec.ts` 확장
- SD/TTS API `page.route()` 모킹 패턴
