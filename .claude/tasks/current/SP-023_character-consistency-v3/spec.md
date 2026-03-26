---
id: SP-023
priority: P1
scope: backend
branch: feat/SP-023-character-consistency-v3
created: 2026-03-26
status: poc
depends_on:
label: feature
---

## 무엇을 (What)
씬 이미지 생성 시 멀티 캐릭터(2P) 구분 + 캐릭터 외형 일관성을 보장하는 ComfyUI 네이티브 파이프라인 구축.

## 왜 (Why)
2P 씬에서 캐릭터 속성(머리색/의상/체형)이 교차 오염되고, 위치 제어가 불가. 프롬프트만으로는 "비슷한 다른 사람"이 나옴.

## 전제 조건
- ~~SP-084 (ComfyUI 네이티브 정리)~~ ✅ 완료
- ComfyUI 서버 실행 중 (localhost:8188)

## PoC 결과 (3라운드, 12가지 전략 테스트)

> [poc.md](./poc.md) 상세 참조

### 확정된 최적 조합

```
1. Gemini Pro 태그 프로파일링 (캐릭터 등록 시 1회)
   → 레퍼런스에서 얼굴/눈/액세서리 Danbooru 태그 극한 추출
   → 기존 9개 태그 → 26개 태그로 확장 (round_face, large_eyes, gradient_eyes, two_side_up 등)

2. DWPose 포즈 추출 (2P 씬 생성 시)
   → 실제 이미지에서 자연스러운 2인 포즈 추출 (수동 스틱 대체)

3. ControlNet OpenPose (strength 0.7) + BREAK (생성)
   → 위치 제어 + 속성 분리

4. medium_shot 강제 (2P 씬)
   → close-up 충돌 방지 (기존 _enforce_wide_framing 활용)
```

### 테스트 완료 전략 (폐기/보류)

| 전략 | 판정 | 사유 |
|------|:----:|------|
| StoryDiffusion | 폐기 | V-Pred 비호환 (노이즈) |
| V-Pred Bridge (Animagine→NoobAI) | 폐기 | 기존 대비 차이 없음 |
| Regional (ConditioningSetArea) | 폐기 | 배경 약화 |
| Regional (블러마스크) | 폐기 | 포즈 랜덤 |
| Pose + 마스크 합체 | 폐기 | 충돌, 3인 생성 |
| 의상 weight 강화 | 폐기 | V-Pred에서 이미지 파괴 |
| ConsiStory | 보류 | CLIPTokenizer 호환성 문제 |
| MS-Diffusion | 보류 | CLIP Vision G 필요 + CLIPTokenizer 호환 |
| Attention Couple | 보류 | mask 전달 디버깅 필요 |
| FaceDetailer 후처리 | 보류 | Impact Pack UltralyticsDetectorProvider 필요 |

### 미해결 (추가 PoC 필요)

- **레퍼런스와 100% 동일한 얼굴 재현** — 프롬프트 기반 한계. 해결 후보:
  - EPS Bridge LoRA (Animagine EPS + IP-Adapter로 학습 데이터 생성 → V-Pred LoRA)
  - FaceDetailer + 레퍼런스 Inpaint (Impact Pack 업데이트 후)
  - 클라우드 GPU → FLUX 경로

## 완료 기준 (DoD)

### Phase A: PoC (리서치) — ✅ 진행 중
- [x] BREAK가 ComfyUI에서 작동하는지 검증
- [x] 2P 캐릭터 구분 전략 비교 (12가지)
- [x] 최적 조합 확정 (DWPose + Pose + BREAK + Gemini 프로파일링)
- [x] 스토리보드 1188 전체 9씬 테스트
- [ ] 추가 PoC: EPS Bridge LoRA 실험 (얼굴 동일성)
- [ ] 추가 PoC: FaceDetailer 후처리 (Impact Pack 업데이트 후)

### Phase B: 파이프라인 구현 (Phase A 완료 후)
- [ ] `scene_2p.json` ComfyUI 워크플로우 신규 생성 (ControlNet Pose + BREAK)
- [ ] Gemini Pro 태그 프로파일링 자동화 (캐릭터 등록/수정 시)
- [ ] DWPose 2P 포즈 라이브러리 구축 + 자동 선택
- [ ] `comfyui/__init__.py`에 2P 워크플로우 분기 추가
- [ ] 2P 씬에서 close-up → medium_shot 자동 전환

### Phase C: 통합 + 검증
- [ ] `generation.py` / `generation_controlnet.py`에서 2P 감지 → scene_2p 워크플로우 자동 선택
- [ ] `multi_character.py`의 BREAK 프롬프트와 ControlNet Pose 연동
- [ ] 동일 캐릭터 5씬 생성 → 일관성 수동 검증
- [ ] 기존 1P 씬 regression 없음

### 공통
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 힌트
- ComfyUI 워크플로우: `backend/services/sd_client/comfyui/workflows/`
- 2P 프롬프트 합성: `backend/services/prompt/multi_character.py`
- ControlNet: `backend/services/controlnet.py` (noobaiXLControlnet_openposeModel)
- DWPose: comfyui_controlnet_aux의 DWPreprocessor 노드
- DynamicThresholding 필수: mimic_scale=5.0, cfg_mode="Half Cosine Down"
- Gemini 태그 프로파일링: `mcp__gemini__gemini-analyze-image` (pro 모델)

## 참고
- PoC 상세: `poc.md` (3라운드, 12전략)
- PoC 워크플로우: `poc_artifacts/workflows/`
- ComfyUI 전환: `memory/project_comfyui_migration.md`

## 주의
- Phase A 추가 PoC가 남아있으므로 바로 구현으로 넘어가지 않는다
- V-Pred에서 weight 강화 (`(tag:1.35)` 이상) 절대 금지 — 이미지 파괴
- StoryDiffusion 고급 모드(consistory, msdiffusion 등)는 ComfyUI 호환 불가 확인됨
