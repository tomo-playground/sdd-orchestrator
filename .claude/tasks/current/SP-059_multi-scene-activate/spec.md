---
id: SP-059
priority: P1
scope: backend
branch: feat/SP-059-multi-scene-activate
created: 2026-03-22
status: pending
depends_on:
label: feat
---

## 무엇을 (What)
dialogue/narrated_dialogue 구조에서 2인 동시 출연 씬(scene_mode="multi")을 실제로 작동하도록 활성화한다.

## 왜 (Why)
MultiCharacterComposer, Finalize 검증, 이미지 생성 분기 등 코드가 완전히 구현되어 있지만, DB에 scene_mode="multi" 씬이 0건이다. Cinematographer 프롬프트가 "multi"를 출력하도록 충분히 유도하지 않고, Finalize가 과도하게 multi→single로 보정하기 때문이다.

## 완료 기준 (DoD)

### 프롬프트 강화
- [ ] Cinematographer 프롬프트(LangFuse 또는 prompt_builders_c.py)에서 scene_mode="multi" 출력 지시를 강화
- [ ] 핵심 감정 장면에서 1-2씬은 multi로 지정하도록 명시적 규칙 추가
- [ ] multi 씬 예시를 JSON output format에 포함

### Finalize 보정 완화
- [ ] `_validate_scene_modes()`에서 multi → single 강제 전환 조건을 완화 (character_b_id 존재 시 multi 허용)
- [ ] multi 씬 상한을 2개로 유지하되, 0개 강제 전환은 제거

### 동작 검증
- [ ] dialogue 구조로 스토리보드 생성 시 scene_mode="multi" 씬이 1개 이상 생성됨
- [ ] multi 씬의 이미지가 MultiCharacterComposer 경로로 생성됨 (BREAK 토큰 구조)
- [ ] multi 씬에서 ControlNet/IP-Adapter가 정상적으로 비활성화됨 (기존 로직 유지)

### 품질 게이트
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석
- `backend/services/agent/prompt_builders_c.py` — build_multi_character_rules() 강화
- `backend/services/agent/nodes/finalize.py` — _validate_scene_modes() 완화
- LangFuse `creative/cinematographer` 프롬프트 — multi 씬 지시 강화

## 제약 (Boundaries)
- ControlNet/IP-Adapter 비활성화는 유지 (LoRA+BREAK만으로 생성)
- multi 씬 상한 2개 유지
- 캐릭터 일관성 품질 이슈는 ComfyUI 전환(SP-022/023) 후 개선
- monologue 구조에서는 multi 씬 불가 (기존 제약 유지)

## 상세 설계 (How)
> [design.md](./design.md) 참조 (착수 시 작성)
