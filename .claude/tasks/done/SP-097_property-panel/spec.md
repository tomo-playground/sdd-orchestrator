---
id: SP-097
priority: P2
scope: frontend
branch: feat/SP-097-property-panel
created: 2026-03-26
approved_at: 2026-03-26
depends_on: SP-096
label: feature
---

## 무엇을 (What)
ScenePropertyPanel 독립 컴포넌트 — SceneCard에서 기본/고급 설정 분리.

## 왜 (Why)
3패널 레이아웃 준비. 속성 패널이 독립 컴포넌트여야 우측 패널로 배치 가능.

## 참조
- IA Redesign 명세: `docs/01_product/FEATURES/IA_REDESIGN.md` Phase C — SP-056 항목

## 완료 기준 (DoD)
- [ ] ScenePropertyPanel 컴포넌트 독립 렌더링 테스트 통과
- [ ] [기본] 탭: 프롬프트, 스피커, 태그 표시
- [ ] [고급] 탭: ControlNet, IP-Adapter, LoRA 설정 (기본 접힘 상태)
- [ ] useSceneContext() 소비 (SP-096 의존)
- [ ] 아직 Direct 탭에 미통합 (독립 컴포넌트)

## 힌트
- SceneCard에서 Tier 2-4 (Customize, Scene Tags, Advanced) 섹션 추출
- 기본 탭: 프롬프트, 스피커, 태그
- 고급 탭: ControlNet, IP-Adapter, LoRA, 검증

## 상세 설계 (How)
→ `design.md` 참조
