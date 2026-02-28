# Style LoRA 선택 가이드 (숏폼 파이프라인)

**최종 업데이트**: 2026-02-28

숏폼 영상 파이프라인에서 Style LoRA를 선택·등록·조합하기 위한 실무 가이드.

---

## 1. LoRA 타입 구분

### 1-1. Offset LoRA vs 일반 LoRA

| 항목 | Offset LoRA | 일반 Style LoRA |
|------|:-----------:|:---------------:|
| 동작 원리 | UNet 출력 bias(잔차)만 시프트 | Cross-Attention 가중치 직접 수정 |
| 영향 범위 | 색감, 라이팅, 선 질감 | 구도, 포즈, 배경까지 변경 |
| 프롬프트 준수 | **높음** — 태그 어텐션 보존 | 중~낮음 — weight 높으면 태그 무시 |
| IP-Adapter 호환 | **우수** — 어텐션 간섭 최소 | weight 의존적 |
| 안전 weight 범위 | 0.5~1.0 | 0.3~0.6 |
| Civitai 수량 | 적음 | 풍부 |

**숏폼에서는 Offset LoRA가 압도적으로 유리합니다.**

- 10~30개 씬마다 다른 프롬프트(카메라, 포즈, 표정, 배경)가 정확히 반영되어야 함
- IP-Adapter로 캐릭터 일관성을 유지하면서 화풍도 통일해야 함
- Offset은 이 두 가지를 동시에 만족시킴

### 1-2. lora_type 분류

| lora_type | 용도 | Offset 관련성 |
|-----------|------|:------------:|
| `style` | 화풍/스타일 | Offset 여부 확인 필수 |
| `character` | 특정 캐릭터 외모 재현 | 해당 없음 |
| `detail` | 디테일 보정 (add_detail 등) | 해당 없음 |

---

## 2. 숏폼 LoRA 선택 3대 기준

### 2-1. 프롬프트 준수율 (Match Rate)

V3 PromptBuilder가 12-Layer로 정밀 배치한 태그가 실제 이미지에 반영되는 비율.

| Match Rate | 판정 | 조치 |
|:----------:|------|------|
| 80%+ | 우수 | 숏폼 즉시 사용 가능 |
| 70~80% | 보통 | weight 하향 조정 필요 |
| 70% 미만 | 위험 | 숏폼 부적합, weight 0.3 이하 또는 제외 |

캘리브레이션(`/api/admin/loras/{id}/calibrate`)을 실행하여 `optimal_weight`를 DB에 기록해야 합니다.

### 2-2. 씬 간 일관성

한 영상 내에서 화풍이 씬마다 달라지면 품질이 크게 저하됩니다.

- StyleProfile에 등록된 Style LoRA는 A/B/Narrator 모든 씬에 동일 적용 (Style LoRA Unification)
- LoRA가 특정 구도/배경을 강제하면 다양한 씬 연출이 불가 → **위험 신호**

### 2-3. IP-Adapter 호환성

캐릭터 일관성은 IP-Adapter `clip_face` (weight 0.35)로 유지합니다.

| Style LoRA 유형 | IP-Adapter 호환 |
|----------------|:--------------:|
| Offset (weight 0.5~0.8) | **우수** |
| 일반 (weight 0.3~0.5) | 양호 |
| 일반 (weight 0.6+) | **위험** — 캐릭터 얼굴 왜곡 |

---

## 3. 현재 등록 LoRA 적합도

### Tier S — 숏폼 최적

| ID | Name | Type | 적합도 | 추천 weight | 적합 장르 |
|----|------|------|:------:|:-----------:|----------|
| 14 | Makoto Shinkai | Offset | **A** | 0.6~0.8 | 감성 에세이, 로맨스, 일상 |
| 11 | Ghibli Style Offset | Offset | **A-** | 0.5~0.7 | 판타지, 힐링, 동화 |

### Tier A — 범용 추천

| ID | Name | Type | 적합도 | 추천 weight | 적합 장르 |
|----|------|------|:------:|:-----------:|----------|
| 5 | flat_color | 일반 | **A-** | 0.3~0.5 | 교육, 설명형, 깔끔한 비주얼 |
| 13 | add_detail | 일반 | **B+** | 0.3~0.5 | 모든 장르 (보조용, 조합 추천) |
| 10 | J_huiben (그림책) | 일반 | **B+** | 0.3~0.5 | 아동, 동화 |

### Tier B — 장르 제한

| ID | Name | Type | 적합도 | 추천 weight | 비고 |
|----|------|------|:------:|:-----------:|------|
| 7 | doremi-casual | 일반 | **B** | 0.3~0.5 | 가벼운 일상/코미디 |

### Tier C — 특수 목적 (전체 영상 비추천)

| ID | Name | 적합도 | 비고 |
|----|------|:------:|------|
| 2 | blindbox_v1_mix | **C+** | 포즈 다양성 심각 제한, 1~3씬만 사용 |
| 3 | chibi-laugh | **C** | IP-Adapter와 완전 충돌, 개별 씬만 |
| 6 | Gentle_Cubism | **C-** | Danbooru cubism 129건, SD 학습 부족 |

---

## 4. 추천 StyleProfile 조합

### 다중 LoRA weight 규칙

```
총 style LoRA weight 합 ≤ 1.0 (기본)
총 style LoRA weight 합 ≤ 0.9 (IP-Adapter 동시 사용 시)
```

### 조합 예시

**Shinkai + add_detail** (시네마틱)
```json
{ "loras": [
  { "lora_id": 14, "weight": 0.6 },
  { "lora_id": 13, "weight": 0.3 }
]}
// 총 0.90 — Shinkai 화풍 + 디테일 보정
```

**Ghibli 단독** (판타지/힐링)
```json
{ "loras": [
  { "lora_id": 11, "weight": 0.6 }
]}
```

**flat_color 단독** (교육/설명)
```json
{ "loras": [
  { "lora_id": 5, "weight": 0.4 }
]}
// 가장 안전. 프롬프트 준수율 최고
```

**J_huiben + add_detail** (아동/동화)
```json
{ "loras": [
  { "lora_id": 10, "weight": 0.35 },
  { "lora_id": 13, "weight": 0.25 }
]}
// 총 0.60 — 그림책 스타일 + 디테일 보완
```

---

## 5. Civitai에서 새 LoRA 선택 체크리스트

### 필수 확인 (MUST)

- [ ] **Base Model 일치**: LoRA의 base_model이 현재 체크포인트와 동일 (SD1.5 ↔ SD1.5)
- [ ] **Offset 타입 우선**: 설명에 "offset" 키워드가 있으면 우선 고려
- [ ] **트리거 워드 Danbooru 빈도**: 1,000+ posts → 안전 / 100 미만 → 위험
- [ ] **샘플 이미지 다양성**: 다양한 포즈/배경 샘플 확인 (정면만 있으면 mode collapse 위험)
- [ ] **권장 weight**: 제작자 권장 0.3~0.6이면 양호 / 1.0 고정이면 프롬프트 무시 가능성

### 등록 후 검증 (SHOULD)

- [ ] **캘리브레이션 실행**: `optimal_weight` DB 기록
- [ ] **IP-Adapter 동시 테스트**: clip_face 0.35 + Style LoRA 동시 적용, 캐릭터 유사도 확인
- [ ] **5씬 다양성 테스트**: standing / sitting / running / close-up / wide_shot
- [ ] **Expression 반응**: smile, crying, angry 등 주요 표정 반영 확인
- [ ] **Camera 반응**: cowboy_shot, from_above, from_behind 등 구도 반영 확인
- [ ] **배경 씬 테스트**: `no_humans`와 함께 생성, 인물이 나오지 않는지 확인

### 위험 신호 (RED FLAGS)

| 신호 | 위험도 | 이유 |
|------|:------:|------|
| Match Rate < 60% | 높음 | 어떤 weight에서도 프롬프트 무시 |
| 모든 테스트 이미지가 유사 | 높음 | Mode collapse — 구도/배경 강제 |
| 트리거 워드에 캐릭터명 포함 | 높음 | Narrator 배경 씬에서 캐릭터 출현 유발 |
| 트리거 워드에 `1girl`/`1boy` 포함 | 높음 | 인원수 태그 충돌 |
| Civitai 권장 weight > 0.8 | 중간 | 프롬프트 간섭 가능성 |
| Danbooru 트리거 워드 100건 미만 | 중간 | SD 모델 학습 부족 |

---

## 6. 레퍼런스 이미지 생성 시 주의사항

캐릭터 프리뷰(레퍼런스)는 `white_background` 강제 환경에서 생성됩니다.

| 항목 | 설정 |
|------|------|
| Style LoRA Scale | `REFERENCE_STYLE_LORA_SCALE = 0.45` |
| 환경 태그 | `(white_background:2.0), (simple_background:1.8)` 등 |
| 카메라 | `full_body, standing, looking_at_viewer` 고정 |

**Offset LoRA의 이점**: 흰 배경 환경에서도 색감/선 질감에서 화풍 힌트가 유지됩니다. 일반 LoRA는 white_background와 충돌하여 아티팩트가 발생할 수 있습니다.

**weight 조정**: 레퍼런스에서 화풍이 약하면 character.loras의 `weight`를 올려서 effective weight를 높일 수 있습니다.
```
effective_weight = character.loras.weight × REFERENCE_STYLE_LORA_SCALE
예: 1.6 × 0.45 = 0.72
```

---

## 7. Negative Prompt 설정

### StyleProfile 등록 시 필수

모든 StyleProfile의 `default_negative`에 공통 품질 방어 태그를 포함해야 합니다.

**공통 (모든 프로필)**:
```
(worst quality, low quality:1.4), normal quality, bad anatomy, bad hands,
bad proportions, blurry, watermark, text, error, signature, username,
artist name, jpeg artifacts, cropped
```

**스타일별 추가**:
| 스타일 | 추가 negative |
|--------|-------------|
| Anime 계열 | `ugly, extra fingers, mutated hands, poorly drawn face, deformed` |
| Realistic | `(cartoon:1.3), (anime:1.3), (illustration:1.3)` |
| Flat Color | `(3d:1.3), (realistic:1.3), (photorealistic:1.3)` |
| 아동/동화 | `(dark:1.3), (horror:1.5), (scary:1.5)` |
| Ghibli | `(3d:1.3), (photorealistic:1.3)` |

### Negative Embedding 필수 등록

모든 StyleProfile에 아래 6개 embedding을 `negative_embeddings`에 포함:

| ID | Name | 용도 |
|----|------|------|
| 1 | bad_prompt_version2 | 전반적 품질 방어 |
| 2 | badhandv4 | 손 품질 방어 |
| 3 | EasyNegative | 범용 품질 방어 |
| 4 | verybadimagenegative_v1.3 | 범용 품질 방어 |
| 5 | bad-artist | 아티스트 스타일 방어 |
| 6 | bad-artist-anime | 애니메 스타일 방어 |

---

## 관련 문서

- [Prompt System Specification](./PROMPT_SPEC_V2.md) — V3 12-Layer 프롬프트 전체 명세
- [RENDER_PIPELINE.md](./RENDER_PIPELINE.md) — FFmpeg 렌더링 파이프라인

## 관련 코드

| 파일 | 역할 |
|------|------|
| `services/prompt/v3_composition.py` | V3 12-Layer PromptBuilder, LoRA 주입 |
| `services/style_context.py` | StyleContext 해석, LoRA resolve |
| `services/lora_calibration.py` | LoRA 캘리브레이션 서비스 |
| `services/characters/preview.py` | 캐릭터 레퍼런스 생성 |
| `config.py` | `STYLE_LORA_WEIGHT_CAP`, `REFERENCE_STYLE_LORA_SCALE` |
