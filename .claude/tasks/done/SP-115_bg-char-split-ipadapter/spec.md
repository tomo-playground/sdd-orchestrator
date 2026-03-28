---
id: SP-115
title: 배경/캐릭터 분리 IP-Adapter 파이프라인 통합
priority: P0
scope: backend
branch: feat/SP-115-bg-char-split-ipadapter
created: 2026-03-28
status: done
approved_at: 2026-03-28
label: feature
---

## 배경

SP-113에서 IP-Adapter ComfyUI 통합 완료. 2026-03-28 실험으로 **배경 + 캐릭터 분리 IP-Adapter (attn_mask)** 기법이 1인 씬에서 검증 완료.

- 배경 레퍼런스 → 배경 영역에만 적용 (attn_mask)
- 캐릭터 레퍼런스 → 인물 영역에만 적용 (attn_mask)
- 같은 배경 레퍼런스로 여러 씬 → 씬 간 배경 일관성

## DoD (Definition of Done)

### 1. scene_single.json 워크플로우 변경
- 현재: IP-Adapter 1개 (캐릭터만, 마스크 없음)
- 변경: IP-Adapter 2개 체이닝 (배경 + 캐릭터, 각각 attn_mask)
- 배경 마스크 / 인물 마스크를 변수로 주입 (`{{bg_mask}}`, `{{char_mask}}`)
- 배경 레퍼런스 이미지도 변수로 주입 (`{{bg_ref_image}}`)

### 2. ComfyUI 클라이언트 변경
- `_ip_adapter` payload에 `bg_ref_image_b64` 추가
- 인물/배경 마스크 생성 로직 (Python PIL)
- 마스크 이미지 업로드 → 변수 주입
- bypass 시 두 IP-Adapter 모두 bypass

### 3. generation_controlnet.py 변경
- `_apply_ip_adapter()`에서 배경 레퍼런스 정보도 payload에 포함
- 배경 레퍼런스 소스: `environment_reference` 또는 이전 씬 이미지

### 4. 배경 레퍼런스 소스 결정
- Option A: `environment_reference_id` (MediaAsset) — 기존 환경 레퍼런스 활용
- Option B: 같은 스토리보드의 이전 씬 이미지 자동 참조
- Option C: Group/Series 레벨 배경 레퍼런스 설정

### 5. 테스트
- 배경 + 캐릭터 분리 적용 시 각각 영역에만 반영 확인
- 배경 레퍼런스 없을 때 정상 동작 (캐릭터 IP-Adapter만)
- bypass 시 기존과 동일하게 동작
- 기존 1인 씬 테스트 통과

## 확정 파라미터

| 항목 | 값 |
|------|-----|
| IP-Adapter 모델 | NOOB-IPA-MARK1.safetensors |
| CLIP Vision | CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors |
| embeds_scaling | V only |
| 캐릭터 weight/end_at | 0.6 / 0.5 |
| 배경 weight/end_at | 0.3 / 0.7 |
| 레퍼런스 크기 | 1024x1024 정사각형 크롭 |

## 참조

- 실험 스크립트: `backend/scripts/experiment_scene_ref.py`
- 실험 결과 메모리: `project_ip_adapter_experiment_results.md`
- SP-113 PR #312 (IP-Adapter 기본 통합)
