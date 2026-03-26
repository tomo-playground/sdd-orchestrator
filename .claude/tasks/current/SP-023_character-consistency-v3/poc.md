# SP-023 PoC 결과: 캐릭터 일관성 V3

## 문제
한 장면에 2명 이상 등장 시 캐릭터 속성(머리색/의상/체형)이 교차 오염되고, 위치 제어가 불가.

## 성공 기준
4장 중 3장 이상에서 2P 캐릭터가 구분되고, 위치가 제어됨.

## 제약
- GPU: 16GB VRAM (RTX)
- 모델: NoobAI-XL V-Pred 1.0
- 백엔드: ComfyUI
- FLUX 불가 (24GB+ 필요)

---

## 실험 결과

| # | 전략 | 샘플 수 | 배경 | 위치 제어 | 캐릭터 구분 | 인원 정확도 | 판정 |
|---|------|:------:|:----:|:--------:|:---------:|:---------:|:----:|
| 베이스라인 | BREAK만 (기존) | 4 | ★★★ | ★ | ★★ | ★★★ | 기준 |
| 1 | StoryDiffusion (V-Pred) | 4 | - | - | - | - | **폐기** (V-Pred 비호환, 노이즈) |
| 2 | V-Pred Bridge (Animagine→NoobAI) | 4 | ★★★ | ★ | ★★ | ★★★ | **폐기** (기존 대비 차이 없음) |
| 3 | Regional (ConditioningSetArea) | 4 | ★ | ★★ | ★★ | ★★★ | **폐기** (배경 약화) |
| 4 | Regional (블러마스크) | 4 | ★★★★ | ★ | ★★ | ★★★ | **부분** (배경 OK, 포즈 랜덤) |
| **5** | **ControlNet Pose + BREAK** | **4** | **★★★** | **★★★** | **★★★** | **★★★** | **채택** |
| 6 | A+B 합체 (Pose+마스크) | 4 | ★★★★ | ★ | ★ | ★ | **폐기** (충돌, 3인 생성) |

## 부수 발견

| 발견 | 상세 |
|------|------|
| BREAK가 ComfyUI에서 작동 | CLIPTextEncode에서 크로스어텐션 분리 정상 동작 확인 |
| V-Pred + StoryDiffusion 비호환 | StoryDiffusion_KSampler가 V-Prediction을 처리 못 함 |
| V-Pred Bridge 패턴 유효 | Animagine(EPS) → NoobAI(V-Pred) img2img 파이프라인 동작 |
| Regional + ControlNet 충돌 | 블러마스크가 ControlNet 포즈 해석을 방해 |
| 포즈 스틱이 위치를 결정 | 프롬프트의 "on the left/right"보다 포즈 스틱 위치가 우선 |

## 채택 전략: ControlNet Pose + BREAK

### 구조
```
ControlNet OpenPose (2인 포즈 스틱)
  → 위치 + 체형 강제

BREAK 프롬프트
  → [공통] 배경, 구도, LoRA
  → BREAK [캐릭터A] 외형 태그
  → BREAK [캐릭터B] 외형 태그

DynamicThresholdingFull
  → V-Pred CFG Rescale
```

### 워크플로우
- `poc_artifacts/workflows/strategy_a_pose_break.json`

### 한계
- 씬마다 2인 포즈 스틱 이미지 필요 → 자동 생성 파이프라인 필요
- close-up 프롬프트와 충돌 → 2P 씬에서 wide_shot 강제 필요 (기존 `_enforce_wide_framing` 활용)
- 레퍼런스 이미지와 동일 얼굴 재현은 여전히 불가 (프롬프트 기반 한계)

### 미검증 (추후 테스트 후보)
- Inspire-Pack Regional Sampler
- ComfyUI-Attention-Couple
- FaceDetailer 후처리 (Impact Pack 업데이트 필요)

## 스토리보드 1188 전체 테스트

9씬 전략 A 적용 결과 (seed=42):

| 씬 | 유형 | 캐릭터 | 결과 |
|:--:|------|--------|------|
| 1 | 배경 | - | ✓ 밤거리 분위기 |
| 2 | solo | 하린 | ✓ 흰 가디건, 리본, 갈색 머리 |
| 3 | solo | 준서 | ✓ 네이비 가디건, 짧은 머리 |
| 4 | 배경 | - | ✓ 자전거 전조등 |
| 5 | **2P** | 하린+준서 | ✓ 캐릭터 구분, 위치 고정 |
| 6 | **2P** | 하린+준서 | △ close-up으로 1인만 나옴 |
| 7 | 배경 | - | ✓ 그림자 |
| 8 | solo | 하린 | ✓ 불안한 표정 |
| 9 | solo | 준서 | ✓ 차분한 미소 |

## 최종 결론

**전략 A (ControlNet Pose + BREAK) 조건부 채택.**

다음 단계:
1. SP-023 Phase B: 포즈 스틱 자동 생성 파이프라인
2. SP-023 Phase C: `scene_single.json` 워크플로우에 ControlNet Pose 통합
3. 2P 씬에서 wide_shot 강제 로직 확인/보완
