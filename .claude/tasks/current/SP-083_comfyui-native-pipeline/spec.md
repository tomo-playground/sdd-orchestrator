---
id: SP-083
priority: P1
scope: backend
branch: feat/SP-083-comfyui-native-pipeline
created: 2026-03-25
status: pending
depends_on: SP-022
label: feat
---

## 무엇을 (What)
2P(멀티캐릭터) 씬에서 Regional Conditioning + 영역별 IP-Adapter를 적용하여 캐릭터 분리 품질을 개선하고, ForgeUI 잔여 로직을 제거한다.

## 왜 (Why)
현재 2P 씬은 BREAK 프롬프트 방식으로 생성하여 Match Rate 12~16%로 낮음. 캐릭터가 섞이거나 한쪽만 생성되는 문제 빈발. Regional Conditioning 프로토타입(scene_2p.json)으로 캐릭터 좌/우 분리가 검증됨 — 이를 파이프라인에 통합해야 함.

## 완료 기준 (DoD)

### Phase A: 2P 워크플로우 통합
- [ ] `scene_2p.json` 워크플로우가 `ComfyUIClient.txt2img()`에서 `_comfy_workflow=scene_2p`로 호출 가능
- [ ] `_payload_to_variables()`가 2P payload (`positive_bg`, `positive_a`, `positive_b`)를 워크플로우 변수로 변환
- [ ] 2P 씬 감지 시 자동으로 `scene_2p` 워크플로우 선택 (BREAK 프롬프트 포함 여부 기준)
- [ ] LoRA 태그가 2P 워크플로우에서도 정상 파싱/적용됨

### Phase B: 프롬프트 분리
- [ ] Cinematographer 노드가 2P 씬에 대해 `positive_bg` / `positive_a` / `positive_b` 3분할 프롬프트 생성
- [ ] 기존 BREAK 구문 프롬프트를 3분할 프롬프트로 변환하는 `split_2p_prompt()` 유틸 제공
- [ ] 1P 씬은 기존 `scene_single.json` 경로 그대로 유지 (회귀 없음)

### Phase C: IP-Adapter 영역별 적용 (선택)
- [ ] ComfyUI IPAdapter Plus 커스텀 노드 설치
- [ ] 캐릭터A 레퍼런스 → 좌측 영역, 캐릭터B 레퍼런스 → 우측 영역에 독립 적용
- [ ] IP-Adapter 미설치 환경에서도 Regional Conditioning만으로 정상 동작 (graceful fallback)

### 공통
- [ ] 기존 1P 씬 테스트 regression 없음
- [ ] 2P Regional Conditioning 단위 테스트 추가 (워크플로우 변수 주입, 프롬프트 분리)
- [ ] 린트 통과

## 검증 기준
- 2P 씬 생성 시 좌/우 캐릭터가 프롬프트대로 분리되어 생성됨
- 기존 스토리보드(#1185)의 2P 씬(4번, 8번)을 Regional Conditioning으로 재생성하여 품질 비교

## 참고
- 프로토타입 워크플로우: `backend/services/sd_client/comfyui/workflows/scene_2p.json`
- 프로토타입 결과: `/tmp/test_2p_regional.png` — 캐릭터 좌/우 분리 확인됨
- ComfyUI 노드: `ConditioningSetArea` + `ConditioningCombine` (네이티브)
- 영역 설정: A=좌측(x:0, w:448), B=우측(x:384, w:448), 64px 오버랩
