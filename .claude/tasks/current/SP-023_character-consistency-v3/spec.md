---
id: SP-023
priority: P1
scope: backend
branch: feat/SP-023-character-consistency-v3
created: 2026-03-26
status: pending
depends_on:
label: feature
---

## 무엇을 (What)
씬 이미지 생성 시 캐릭터 일관성을 보장하는 ComfyUI 네이티브 파이프라인 구축. 동일 캐릭터가 여러 씬에서 동일한 얼굴/의상/체형으로 렌더링되도록 한다.

## 왜 (Why)
현재 캐릭터 레퍼런스 이미지를 생성할 수 있지만, 씬 이미지에서 캐릭터 일관성이 유지되지 않음. PoC 결과 SDXL IP-Adapter(NOOB-IPA-MARK1)는 스타일 전이만 가능하고 얼굴 동일성은 불가. ComfyUI 전환(SP-084) 완료로 워크플로우 기반 파이프라인 구축 가능.

## 전제 조건
- ~~SP-084 (ComfyUI 네이티브 정리)~~ ✅ 완료
- ComfyUI 서버 실행 중 (localhost:8188)

## PoC 결과 요약 (memory/project_character_consistency_poc.md)
- NOOB-IPA-MARK1: 스타일만 전이, 얼굴 동일성 없음
- FaceID: 애니 얼굴 미감지 (InsightFace 한계)
- ip-adapter-plus_sdxl_vit-h: NoobAI-XL V-Pred 비호환
- **미탐색**: FLUX + PuLID/Kontext, 캐릭터 LoRA, ACE++

## 완료 기준 (DoD)

### Phase A: 접근법 결정 (리서치)
- [ ] FLUX + PuLID/Kontext 실현 가능성 조사 — ComfyUI 커스텀 노드 존재 여부, VRAM 요구량, NoobAI와 병행 가능 여부
- [ ] 캐릭터 LoRA 미니 학습 테스트 — 레퍼런스 이미지 5장으로 kohya_ss 학습, 일관성 효과 확인
- [ ] 최종 접근법 선택 + 사용자 승인

### Phase B: 씬 워크플로우 확장
- [ ] `scene_single.json` 워크플로우에 캐릭터 일관성 모듈 추가 (선택된 접근법 기반)
- [ ] `comfyui/__init__.py`의 `_payload_to_variables()`에 캐릭터 레퍼런스 이미지 전달 경로 추가
- [ ] `generation.py` → `comfyui/txt2img()`에 캐릭터 레퍼런스 이미지 주입 파라미터 추가

### Phase C: 파이프라인 통합
- [ ] `generation_controlnet.py`에서 씬 생성 시 캐릭터 레퍼런스 자동 로드
- [ ] 캐릭터별 레퍼런스 이미지를 storage에서 가져와 payload에 포함
- [ ] 멀티 캐릭터 씬 (2P) 지원 — Regional Prompting + 캐릭터별 IP-Adapter/LoRA

### Phase D: 품질 검증
- [ ] 동일 캐릭터 5씬 생성 → 얼굴/의상 일관성 수동 검증
- [ ] 일관성 점수 기준 정의 (주관적 5점 척도 or WD14 태그 일치율)
- [ ] 기존 레퍼런스 생성 기능 regression 없음

### 공통
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 힌트
- ComfyUI 워크플로우: `backend/services/sd_client/comfyui/workflows/`
- ComfyUI 클라이언트: `backend/services/sd_client/comfyui/__init__.py`
- 레퍼런스 생성: `backend/services/characters/reference.py`
- 씬 생성: `backend/services/generation.py`, `backend/services/generation_controlnet.py`
- ControlNet/IP-Adapter: `backend/services/controlnet.py`
- 설치된 ComfyUI 노드: IPAdapter Plus (35노드), Impact-Pack, controlnet_aux, sd-dynamic-thresholding
- DynamicThresholding 필수: mimic_scale=5.0, cfg_mode="Half Cosine Down"

## 참고
- PoC 결과: `memory/project_character_consistency_poc.md`
- ComfyUI 전환: `memory/project_comfyui_migration.md`
- 씬 이미지 품질: `memory/project_scene_image_quality.md`

## 주의
- Phase A는 리서치 단계 — 코드 변경 없이 접근법 결정 후 설계 진행
- FLUX 모델은 ~17GB, VRAM 24GB+ 필요 — 현재 환경에서 실행 가능한지 먼저 확인
- 캐릭터 LoRA 학습은 데이터 확보가 선결 — 레퍼런스 이미지 품질에 의존
