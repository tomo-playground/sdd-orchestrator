# Test Scenarios

기능별 테스트 시나리오. 각 시나리오는 **사전조건 → 절차 → 기대결과** 형식.

---

## 1. Storyboard

### 1.1 생성

| 항목 | 내용 |
|------|------|
| 사전조건 | Topic, Character 선택됨 |
| 절차 | `POST /storyboard` 호출 |
| 기대결과 | Storyboard + Scene[] 생성, DB 저장 |
| 테스트 파일 | `tests/api/test_storyboard.py` |

### 1.2 조회

| 항목 | 내용 |
|------|------|
| 사전조건 | DB에 Storyboard 존재 |
| 절차 | `GET /storyboards/{id}` |
| 기대결과 | Scenes, CharacterActions, context_tags 포함 응답 |

### 1.3 삭제

| 항목 | 내용 |
|------|------|
| 사전조건 | DB에 Storyboard + Scene + Asset 존재 |
| 절차 | `DELETE /storyboards/{id}` |
| 기대결과 | CASCADE 삭제, Asset 정리 |

---

## 2. 이미지 생성

### 2.1 단일 씬 생성

| 항목 | 내용 |
|------|------|
| 사전조건 | Scene에 image_prompt 존재, SD WebUI 가동 |
| 절차 | `POST /generate_image` (scene_index, prompt 등) |
| 기대결과 | 이미지 생성, Asset 저장, URL 반환 |
| 테스트 파일 | `tests/api/test_prompt.py` |

### 2.2 ControlNet + IP-Adapter

| 항목 | 내용 |
|------|------|
| 사전조건 | Character에 reference image 존재, ControlNet 활성 |
| 절차 | `POST /generate_image` (controlnet + ip_adapter 파라미터) |
| 기대결과 | 페이로드에 controlnet_units 포함, 이미지 반환 |
| 테스트 파일 | `tests/api/test_controlnet.py` |

### 2.3 Environment Pinning

| 항목 | 내용 |
|------|------|
| 사전조건 | 연속 씬이 같은 environment context_tag |
| 절차 | 이미지 생성 성공 후 자동 핀 로직 |
| 기대결과 | 이전 씬 이미지 참조 자동 설정 |
| 테스트 파일 | `frontend/app/utils/__tests__/autoPin.test.ts`, `applyAutoPin.test.ts`, `pinIntegration.test.ts` |

---

## 3. 프롬프트 엔진

### 3.1 V3 Composition (12-Layer)

| 항목 | 내용 |
|------|------|
| 사전조건 | Character + Scene 태그 존재 |
| 절차 | `POST /prompt/compose` |
| 기대결과 | 12개 레이어 순서대로 합성, 중복 제거(intra-layer) |
| 테스트 파일 | `tests/test_prompt_compose_error.py`, `tests/test_prompt_quality.py` |

### 3.2 태그 정규화

| 항목 | 내용 |
|------|------|
| 사전조건 | 다양한 형식의 태그 입력 (공백, 하이픈, 대소문자) |
| 절차 | `normalize_prompt_token()` 호출 |
| 기대결과 | Danbooru 언더바 표준 유지, LoRA 트리거 원본 보존 |
| 테스트 파일 | `tests/test_tag_normalization.py` (504 LOC) |

### 3.3 태그 충돌/의존성

| 항목 | 내용 |
|------|------|
| 사전조건 | 충돌 태그 쌍 (e.g., standing + sitting) |
| 절차 | 프롬프트 합성 시 태그 필터링 |
| 기대결과 | 우선순위 높은 태그만 유지, 충돌 태그 제거 |
| 테스트 파일 | `tests/test_filter_prompt_tokens_effectiveness.py` |

---

## 4. 캐릭터

### 4.1 CRUD

| 항목 | 내용 |
|------|------|
| 사전조건 | - |
| 절차 | Character 생성/조회/수정/삭제 API |
| 기대결과 | DB 반영, 연관 태그/LoRA 연동 |

### 4.2 Style Profile 적용

| 항목 | 내용 |
|------|------|
| 사전조건 | Character에 StyleProfile 연결 |
| 절차 | 이미지 생성 시 캐릭터 선택 |
| 기대결과 | Model, LoRA, Embedding이 StyleProfile에 따라 적용 |
| 테스트 파일 | `tests/test_style_lora_integration.py`, `tests/test_scene_generation_with_style_profile.py` |

### 4.3 Style LoRA Unification (v4.2)

| 항목 | 내용 |
|------|------|
| 사전조건 | Dialogue/Narrated Dialogue 구조, StyleProfile 설정됨 |
| 절차 | A, B, Narrator 씬 이미지 생성 |
| 기대결과 | 모든 씬이 동일한 StyleProfile.loras 적용, Character별 character LoRA만 구분 |
| 테스트 파일 | `tests/test_style_lora_unification.py`, `frontend/app/utils/__tests__/speakerResolver.test.ts` |

**테스트 케이스**:
1. StyleProfile LoRA → Speaker A 적용
2. StyleProfile LoRA → Speaker B 적용 (동일 style)
3. StyleProfile LoRA → Narrator 적용 (배경씬)
4. Character style LoRA 무시 (StyleProfile 우선)
5. 중복 LoRA 제거 (StyleProfile weight 우선)
6. StyleProfile 없을 때 Fallback
7. 모든 씬 동일 Style 검증

### 4.4 Character Tags → Prompt

| 항목 | 내용 |
|------|------|
| 사전조건 | Character에 identity/clothing 태그 연결 |
| 절차 | `POST /prompt/compose` |
| 기대결과 | 캐릭터 태그가 Layer 2(Identity), 5(Clothing)에 반영 |
| 테스트 파일 | `frontend/app/hooks/__tests__/useCharacters.test.ts` |

---

## 5. 렌더링 (VRT)

### 5.1 Scene Text 렌더링

| 항목 | 내용 |
|------|------|
| 사전조건 | 폰트 파일 존재, 텍스트 입력 |
| 절차 | 씬 텍스트 이미지 생성 |
| 기대결과 | Golden Master와 SSIM >= 0.95 |
| 테스트 파일 | `tests/vrt/test_subtitle_rendering.py` |

### 5.2 오버레이 렌더링

| 항목 | 내용 |
|------|------|
| 사전조건 | 헤더/푸터 오버레이 에셋 |
| 절차 | Post Layout 프레임 합성 |
| 기대결과 | Golden Master와 SSIM >= 0.95 |
| 테스트 파일 | `tests/vrt/test_overlay_rendering.py` |

### 5.3 Post Frame 합성

| 항목 | 내용 |
|------|------|
| 사전조건 | 이미지 + 오버레이 + 씬 텍스트 |
| 절차 | `compose_post_frame()` |
| 기대결과 | 완성 프레임 Golden Master 일치 |
| 테스트 파일 | `tests/vrt/test_post_frame.py` |

### 5.4 결정적 렌더링

| 항목 | 내용 |
|------|------|
| 사전조건 | 동일 입력, 시드 고정 |
| 절차 | 동일 파라미터로 2회 렌더링 |
| 기대결과 | 결과 완전 일치 (SSIM = 1.0) |
| 테스트 파일 | `tests/vrt/test_deterministic.py` |

---

## 6. 프론트엔드 핵심 플로우

### 6.1 Autopilot

| 항목 | 내용 |
|------|------|
| 사전조건 | Topic + Character 설정 완료 |
| 절차 | Autopilot 시작 → Storyboard → Images → Render |
| 기대결과 | 상태 전이 정상, 취소/재개 동작, 체크포인트 저장 |
| 테스트 파일 | `frontend/app/hooks/__tests__/useAutopilot.test.ts` (27개) |

### 6.2 Validation

| 항목 | 내용 |
|------|------|
| 사전조건 | 생성된 이미지 존재 |
| 절차 | WD14 태그 비교, match rate 계산 |
| 기대결과 | 씬별 match rate 산출, 수정 제안 생성 |
| 테스트 파일 | `frontend/app/utils/__tests__/validation.test.ts` (30개) |

### 6.3 E2E: Studio 페이지

| 항목 | 내용 |
|------|------|
| 사전조건 | Frontend 서버 가동 |
| 절차 | Studio 페이지 접근, 스토리보드 로드, 씬 확인 |
| 기대결과 | 페이지 정상 렌더링, 주요 요소 표시 |
| 테스트 파일 | `frontend/tests/vrt/studio-e2e.spec.ts` |

---

## 7. 품질 & 분석

### 7.1 Quality Dashboard

| 항목 | 내용 |
|------|------|
| 사전조건 | Activity logs 데이터 존재 |
| 절차 | `/api/quality/summary` 호출 |
| 기대결과 | 요약 통계 (성공률, 평균 match rate) 반환 |
| 테스트 파일 | `tests/api/test_quality.py`, `frontend/.../QualityDashboard.test.tsx` |

### 7.2 Activity Logs

| 항목 | 내용 |
|------|------|
| 사전조건 | 이미지 생성 완료 |
| 절차 | 로그 CRUD, 패턴 분석 |
| 기대결과 | 로그 저장, 성공 조합 추출 |
| 테스트 파일 | `tests/api/test_activity_logs.py` (461 LOC) |

---

## 8. 인프라

### 8.1 Asset Storage (MinIO)

| 항목 | 내용 |
|------|------|
| 사전조건 | MinIO 서비스 가동 |
| 절차 | 에셋 업로드/다운로드/삭제 |
| 기대결과 | 3계층 스토리지 (permanent/storyboard/temp) 정상 동작 |
| 테스트 파일 | `tests/test_storage.py`, `tests/test_asset_service.py` |

### 8.2 DB 격리

| 항목 | 내용 |
|------|------|
| 사전조건 | 테스트 환경 |
| 절차 | 여러 테스트 병렬 실행 |
| 기대결과 | 테스트 간 DB 상태 간섭 없음 |
| 테스트 파일 | `tests/test_db_isolation.py` |
