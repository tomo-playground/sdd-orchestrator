---
id: SP-072
priority: P1
scope: backend
branch: feat/SP-072-narrator-scene-intelligence
created: 2026-03-23
approved_at: 2026-03-23
depends_on:
label: feat
---

## 무엇을 (What)
Narrator 씬의 `no_humans` 주입을 script 의미 기반으로 판단하여, 군중/활동이 암시되는 씬에서는 배경 인물이 표현되도록 개선한다.

## 왜 (Why)
현재 Narrator 씬 = "사람 없는 배경"으로 일괄 처리. "정신없는 사무실 풍경" 같이 불특정 다수가 필요한 씬에서도 `no_humans`가 주입되어 빈 공간만 생성된다. Narrator는 "주인공 캐릭터 태그를 주입하지 않는 씬"이지, "사람이 아예 없는 씬"이 아니다.

## 상세 설계 (How)

> [design.md](./design.md) 참조

## 완료 기준 (DoD)

### A. 백엔드 `_inject_narrator_defense()` 개선
- [x] `_PERSON_INDICATORS`에 군중 태그 추가: `crowd`, `many_others`, `6+girls`, `6+boys`
- [x] 군중 태그가 포함된 Narrator 씬에는 `no_humans` 주입하지 않는다
- [x] `_append_narrator_negative()`에서 군중 씬은 person-exclusion 태그 주입하지 않는다

### B. Finalize 노드 Narrator 처리 확인
- [x] Finalize에서 Narrator 씬에 `no_humans`를 강제하는 로직이 있으면 동일하게 군중 씬 예외 처리
- [x] `negative_prompt_extra`에 `1girl, 1boy, person`을 일괄 추가하는 로직에 군중 씬 예외 처리

### C. Cinematographer 프롬프트 업데이트
- [x] Compositor 프롬프트(v2 반영 확인): Narrator 씬 규칙이 script 의미 기반 판단으로 변경됨
- [x] 메인 프롬프트(v10): Narrator 규칙 동일 업데이트
- [x] Framing/Action/Atmosphere 서브에이전트: Narrator 씬에서 군중 여부에 따라 적절한 태그 생성

### D. 테스트
- [x] 군중 Narrator 씬 ("정신없는 사무실", "북적이는 거리") → `no_humans` 미주입 + `crowd` 태그 포함
- [x] 빈 공간 Narrator 씬 ("조용한 복도", "빈 교실") → `no_humans` 주입 (기존 동작 유지)
- [x] 기존 테스트 regression 없음
- [x] 린트 통과
