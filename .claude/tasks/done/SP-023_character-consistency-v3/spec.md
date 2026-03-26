---
id: SP-023
priority: P1
scope: backend
branch: feat/SP-023-character-consistency-v3
created: 2026-03-26
status: done
approved_at: 2026-03-26
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

## PoC 결과 요약

> [poc.md](./poc.md) 상세 참조 (4라운드, 12가지 전략 테스트)

### 확정된 최적 조합

```
1. Gemini Pro 태그 프로파일링 (캐릭터 등록 시 1회)
   → 레퍼런스에서 얼굴/눈/액세서리 Danbooru 태그 극한 추출
   → 기존 9개 태그 → 26개 태그로 확장

2. DWPose 포즈 추출 (2P 씬 생성 시)
   → 실제 이미지에서 자연스러운 2인 포즈 추출

3. ControlNet OpenPose (strength 0.7) + BREAK (생성)
   → 위치 제어 + 속성 분리

4. medium_shot 강제 (2P 씬)
   → close-up 충돌 방지 (기존 _enforce_wide_framing 활용)
```

### 보류 항목 (후속 태스크)
- EPS Bridge LoRA (얼굴 동일성) — 학습 데이터 10장 확보 완료, LoRA 학습 미실행
- FaceDetailer 후처리 — Impact Pack 업데이트 후 재시도

## 상세 설계 (How)

> [design.md](./design.md) 참조

## 현재 코드 상태 (갭 분석)

| 항목 | 현재 | 목표 |
|------|------|------|
| ComfyUI 워크플로우 | `scene_single.json` (1P만) | `scene_2p.json` 신규 (ControlNet Pose + BREAK) |
| ControlNet × ComfyUI | SD WebUI 형식 (`alwayson_scripts`) → ComfyUI 무시 | 워크플로우 노드로 네이티브 통합 |
| 2P ControlNet | `apply_controlnet`에서 multi-char **스킵** | 2P Pose ControlNet 활성화 |
| 포즈 이미지 전달 | `load_pose_reference` → base64 (WebUI용) | ComfyUI `LoadImage` 노드 → 파일명 참조 |
| DWPose 포즈 | 없음 (수동 스틱만) | 2P 포즈 라이브러리 + 자동 선택 |
| Gemini 프로파일링 | 없음 (수동 태깅) | 레퍼런스 분석 → 자동 태그 추출 |
| wide framing | `_enforce_wide_framing` 존재 (프롬프트만) | 그대로 유지 (이미 동작) |

## 완료 기준 (DoD)

### Phase A: PoC (리서치) — ✅ 완료
- [x] BREAK가 ComfyUI에서 작동하는지 검증
- [x] 2P 캐릭터 구분 전략 비교 (12가지)
- [x] 최적 조합 확정 (DWPose + Pose + BREAK + Gemini 프로파일링)
- [x] 스토리보드 1188 전체 9씬 테스트
- [x] EPS Bridge LoRA 학습 데이터 생성 (10장 확보)

### Phase B: 파이프라인 구현
- [ ] B-1. `scene_2p.json` ComfyUI 워크플로우 신규 생성
  - PoC `strategy_a_pose_break.json` 기반 템플릿화
  - `{{positive}}`, `{{negative}}`, `{{pose_image}}`, `{{controlnet_strength}}` 등 변수 주입
  - 3 LoRA 슬롯 + DynamicThresholding + ControlNetLoader + ControlNetApply
- [ ] B-2. ComfyUI client에 포즈 이미지 업로드 기능 추가
  - `txt2img` 전에 pose 이미지를 ComfyUI `/upload/image` API로 전송
  - 워크플로우 `LoadImage` 노드에 업로드된 파일명 주입
- [ ] B-3. DWPose 2P 포즈 라이브러리 구축
  - 기본 2P 포즈 세트 (walking, standing, sitting, facing 등 6~8종)
  - `shared/poses/2p/` 경로에 저장 (StorageService)
  - `POSE_2P_MAPPING` 매핑 테이블 추가 (config.py)
- ~~B-4. Gemini Pro 태그 프로파일링~~ → 별도 태스크로 분리 (1P에도 독립적 가치)

### Phase C: 통합 + 검증
- [ ] C-1. `generation.py`에서 2P 자동 감지 → `scene_2p` 워크플로우 선택
  - `character_b_id` 존재 시 `_comfy_workflow = "scene_2p"` 자동 설정
- [ ] C-2. `generation_controlnet.py` multi-char 스킵 제거 → 2P Pose 적용
  - 2P 전용 포즈 자동 선택 로직 (context_tags 기반)
  - `apply_controlnet` → payload에 `_pose_image` 키로 파일명 전달
- [ ] C-3. `comfyui/__init__.py`에서 `_pose_image` 처리
  - pose 이미지 업로드 + 워크플로우 변수 주입 통합
- [ ] C-4. 동일 캐릭터 5씬 생성 → 일관성 수동 검증
- [ ] C-5. 기존 1P 씬 regression 없음

### 공통
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 힌트
- ComfyUI 워크플로우: `backend/services/sd_client/comfyui/workflows/`
- PoC 워크플로우 (템플릿 기반): `poc_artifacts/workflows/strategy_a_pose_break.json`
- 2P 프롬프트 합성: `backend/services/prompt/multi_character.py` (BREAK 토큰, `_enforce_wide_framing`)
- ComfyUI client: `backend/services/sd_client/comfyui/__init__.py` (`txt2img`, `_payload_to_variables`)
- ControlNet 현재: `backend/services/controlnet.py` + `generation_controlnet.py`
- DWPose: comfyui_controlnet_aux의 DWPreprocessor 노드
- DynamicThresholding 필수: mimic_scale=5.0, cfg_mode="Half Cosine Down"
- Gemini 프로파일링: `mcp__gemini__gemini-analyze-image` (pro 모델)
- 포즈 업로드 API: ComfyUI `POST /upload/image` (multipart/form-data)
- ComfyUI `LoadImage` 노드: `{"image": "filename.png"}` (input 폴더 기준)

## 참고
- PoC 상세: `poc.md` (4라운드)
- PoC 워크플로우: `poc_artifacts/workflows/`
- ComfyUI 전환: `memory/project_comfyui_migration.md`

## 주의
- V-Pred에서 weight 강화 (`(tag:1.35)` 이상) 절대 금지 — 이미지 파괴
- ControlNet strength 0.7 최적 (0.4 너무 약, 0.9 뻣뻣)
- ComfyUI ControlNet은 `alwayson_scripts` 아님 — 워크플로우 노드로 직접 통합
- 기존 1P `scene_single.json` 워크플로우 절대 수정 금지
