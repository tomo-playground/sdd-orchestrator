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

---

## 개선 실험 (Round 2)

베이스라인: 전략 A (Scene 5, seed=42). 변수 1개씩 변경.

| # | 개선 | 변경점 | 결과 | 판정 |
|---|------|--------|------|:----:|
| base | 전략 A 그대로 | - | 2P 구분 OK | 기준 |
| **#1** | **DWPose 포즈 추출** | 수동 스틱 → 실제 이미지에서 DWPose 추출 | **포즈 자연스러움 대폭 개선, 캐릭터 구분 최고** | **채택** |
| #2 | FaceDetailer 후처리 | UltralyticsDetectorProvider 필요 | Impact Pack 버전 문제로 실행 불가 | **보류** |
| #3 | close-up → medium_shot | 2P에서 close-up 금지 | 두 명 다 보임, 유효 | **유효** |
| #4a | ControlNet strength 0.4 | 0.7 → 0.4 | 포즈 약해짐, 자연스러움 | 기각 |
| #4b | ControlNet strength 0.9 | 0.7 → 0.9 | 포즈 강하지만 뻣뻣함 | 기각 |
| #5 | 의상 weight 강화 | `(tag:1.1)` → `(tag:1.35)` | **이미지 완전 파괴 (노이즈)** — V-Pred에서 과도한 weight 치명적 | **폐기** |
| #6 | Attention Couple + Pose | BREAK 대신 Attention 분리 | mask KeyError — 마스크 전달 방식 호환 안 됨 | **보류** |

### Round 2 핵심 발견

1. **DWPose (#1)가 가장 큰 개선** — 수동 스틱 대신 실제 이미지에서 추출한 포즈로 자연스러움 크게 향상
2. **V-Pred에서 weight 강화 절대 금지** — `(tag:1.35)` 수준에서 이미지 완전 파괴 (CFG Rescale로도 복구 불가)
3. **ControlNet strength 0.7이 최적** — 0.4는 너무 약하고 0.9는 뻣뻣함
4. **2P에서 close-up → medium_shot 자동 전환** 규칙 유효

### 최적 조합 (확정)

```
DWPose 포즈 추출 + ControlNet OpenPose (strength 0.7) + BREAK + medium_shot (2P)
```

### 미검증 (Impact Pack 업데이트 후 재시도)
- #2 FaceDetailer — UltralyticsDetectorProvider 필요
- #6 Attention Couple — mask 전달 디버깅 필요

---

## 최종 결론

**전략 A + DWPose 개선 채택.**

다음 단계:
1. SP-023 Phase B: DWPose 기반 2P 포즈 자동 추출 파이프라인
2. SP-023 Phase C: `scene_2p.json` 워크플로우 신규 생성 (ControlNet Pose + BREAK)
3. 2P 씬에서 close-up → medium_shot 자동 전환 로직
4. (후속) Impact Pack 업데이트 → FaceDetailer + Attention Couple 재도전

---

## Round 3: 추가 개선 실험

### B 전략: Gemini 태그 프로파일링

레퍼런스 이미지를 Gemini Pro로 분석 → 얼굴/눈/액세서리 Danbooru 태그 극한 추출.

| 항목 | 기존 태그 | Gemini 프로파일링 |
|------|----------|----------------|
| 리본 | hair_ribbon | **light_blue_ribbon, twin_ribbons** ✓ |
| 눈 | brown_eyes | **large_eyes, gradient_eyes, eyelashes** ✓ |
| 얼굴 | 없음 | **round_face, dot_nose, blush** ✓ |
| 머리 묶음 | long_hair | **two_side_up, parted_bangs, hair_between_eyes** ✓ |
| 의상 | white_cardigan | **beige_cardigan, open_cardigan, ribbon_tie** ✓ |

**판정: 채택** — 레퍼런스 재현도가 체감적으로 개선됨. 프롬프트만으로 달성 가능, 비용 0.

### StoryDiffusion 고급 모드 테스트

| 모드 | 결과 | 원인 |
|------|------|------|
| consistory | 실패 | CLIPTokenizer 호환성 (diffusers vs ComfyUI) |
| msdiffusion | 실패 | CLIP Vision G 모델 필요 + CLIPTokenizer 호환 |
| instant_character | 미테스트 | FLUX 전용 |
| story_maker | 미테스트 | InsightFace 필요 (애니 비호환) |

**결론: StoryDiffusion 고급 모드는 현재 ComfyUI + NoobAI V-Pred 환경에서 사용 불가.**

---

## 확정 최종 조합

```
1. Gemini Pro 태그 프로파일링 (캐릭터 등록 시 1회)
   → 레퍼런스에서 얼굴/눈/액세서리 태그 극한 추출

2. DWPose 포즈 추출 (2P 씬 생성 시)
   → 실제 이미지에서 자연스러운 2인 포즈 추출

3. ControlNet OpenPose + BREAK (생성)
   → 위치 제어 + 속성 분리

4. medium_shot 강제 (2P 씬)
   → close-up 충돌 방지
```

---

## Round 4: EPS Bridge LoRA (학습 데이터 생성)

### 문제
레퍼런스 이미지의 얼굴을 씬 이미지에서 재현할 수 없다 (프롬프트 기반 한계).

### 성공 기준
LoRA 적용 후 생성한 4장 중 3장 이상에서 레퍼런스와 동일인물로 인식 가능.

### 실험: Animagine(EPS) + IP-Adapter로 학습 데이터 생성

**핵심 발견: 닭과 달걀 문제 해결.**

Animagine XL 3.1(EPS 모델)에서는 IP-Adapter(PLUS FACE)가 정상 동작.
하린 레퍼런스 1장을 참조하여 다양한 포즈/표정의 학습 데이터 10장 생성 성공.

| 파라미터 | 값 |
|---------|-----|
| 모델 | Animagine XL 3.1 (EPS) |
| IP-Adapter | PLUS FACE (portraits), weight 0.6 |
| 프롬프트 | Gemini 프로파일링 태그 + 씬별 변화 |
| 시드 | 42~51 (10장) |
| 결과 | 10/10 일관된 캐릭터, 레퍼런스 얼굴 특징 유지 |

### 학습 데이터 품질 평가

| 항목 | 레퍼런스 | 학습 데이터 (10장) |
|------|---------|------------------|
| 얼굴형 | 둥근 얼굴 | ✓ 일관 |
| 눈 | 큰 갈색 그라데이션 | ✓ 일관 |
| 리본 | 파란색 양쪽 | ✓ 일관 |
| 의상 | 베이지 가디건 + 리본타이 블라우스 | ✓ 일관 |
| 포즈 다양성 | 정면 1장 | 정면/측면/독서/인사/상향 등 10가지 ✓ |

### 다음 단계 (미완료)

1. **kohya_ss 설치** — SDXL LoRA 학습 환경 구축
2. **LoRA 학습** — 10장 데이터, Rank 16, 500 steps (~10분)
3. **V-Pred에 LoRA 적용 테스트** — NoobAI V-Pred + 하린 LoRA로 씬 생성
4. **성공 기준 평가** — 4장 중 3장 이상 동일인물 여부

### 판정: **진행 중** — 학습 데이터 확보 성공, LoRA 학습 대기
