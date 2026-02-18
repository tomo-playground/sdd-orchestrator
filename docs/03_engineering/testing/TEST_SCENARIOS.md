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

---

## 9. AI BGM

### 9.1 음악 생성 캐시 키

| 항목 | 내용 |
|------|------|
| 사전조건 | - |
| 절차 | `_music_cache_key()` 호출 (다양한 파라미터 조합) |
| 기대결과 | 동일 입력 → 동일 키, 파라미터 변경 시 다른 키, 키 길이 16 |
| 테스트 파일 | `tests/test_music_generator.py` |

**테스트 케이스** (TestMusicCacheKey, 6개):
1. 동일 입력(prompt, duration, seed, steps)은 동일 캐시 키 반환
2. prompt 변경 시 다른 키
3. duration 변경 시 다른 키
4. seed 변경 시 다른 키
5. steps 변경 시 다른 키
6. 캐시 키 길이는 항상 16

### 9.2 음악 생성 캐시 히트

| 항목 | 내용 |
|------|------|
| 사전조건 | 캐시 파일 존재 |
| 절차 | `generate_music()` 호출 |
| 기대결과 | 모델 로드 없이 캐시된 바이트 반환, 음수 시드 → 양수 변환 |
| 테스트 파일 | `tests/test_music_generator.py` |

**테스트 케이스** (TestGenerateMusicCacheHit, 2개):
1. 캐시 히트 시 WAV 바이트 반환 + SR 44100 + 모델 호출 안 함
2. 음수 시드(-1) 입력 시 양수 시드로 자동 변환

### 9.3 Music Presets CRUD

| 항목 | 내용 |
|------|------|
| 사전조건 | DB 테이블 존재 |
| 절차 | `/music-presets` 엔드포인트 CRUD 호출 |
| 기대결과 | 생성/조회/수정/삭제 정상 동작, 404 에러 처리 |
| 테스트 파일 | `tests/test_router_music_presets.py` |

**테스트 케이스** (TestMusicPresetsRouter, 9개):
1. 빈 목록 조회 → `[]` 반환
2. 프리셋 생성 → name, prompt, duration, is_system 필드 검증
3. 단건 조회 → 생성된 프리셋 정상 반환
4. 존재하지 않는 ID 조회 → 404
5. 프리셋 수정 → name, prompt 변경 반영
6. 존재하지 않는 ID 수정 → 404
7. 프리셋 삭제 → `{"status": "deleted"}` 반환
8. 삭제된 프리셋 재조회 → 404
9. 복수 생성 후 목록 조회 → 모든 프리셋 포함

### 9.4 BGM 경로 해석 (AI / File 모드)

| 항목 | 내용 |
|------|------|
| 사전조건 | effects 모듈의 `_resolve_bgm_path()` |
| 절차 | bgm_mode별(ai, file) 경로 해석 |
| 기대결과 | AI 모드 → ai_bgm_path 반환, File 모드 → resolve_bgm_file 사용, 모드 간 fallthrough 방지 |
| 테스트 파일 | `tests/test_effects_ai_bgm.py` |

**테스트 케이스** (TestResolveBgmPath, 5개):
1. AI 모드 + 경로 존재 → AI BGM 경로 반환
2. AI 모드 + 경로 없음 → None 반환
3. AI 모드 + 경로 없음 → File 모드로 fallthrough 하지 않음 (resolve_bgm_file 미호출)
4. File 모드 → resolve_bgm_file 사용하여 스토리지 경로 반환
5. File 모드 + BGM 파일 없음 → None 반환

---

## 10. Creative Script Graph (Phase 10)

### 10.1 Script Graph 실행

| 항목 | 내용 |
|------|------|
| 사전조건 | LangGraph 노드 설정, Gemini Mock |
| 절차 | Script Graph 전체 실행 (Research → Write → Review → Produce) |
| 기대결과 | 각 노드 순차 실행, 상태 전이, 최종 스크립트 출력 |
| 테스트 파일 | `tests/test_script_graph.py` (19 tests) |

### 10.2 Creative Agents

| 항목 | 내용 |
|------|------|
| 사전조건 | Agent 초기화, Gemini Mock |
| 절차 | Director, Cinematographer, Critic 등 Agent 호출 |
| 기대결과 | 각 Agent가 역할에 맞는 출력 생성 |
| 테스트 파일 | `tests/test_creative_agents.py` (11), `tests/test_director_react.py` (13), `tests/test_critic_debate.py` (12) |

### 10.3 Tool Calling

| 항목 | 내용 |
|------|------|
| 사전조건 | Tool 정의, Agent Mock |
| 절차 | Agent의 tool calling 실행 |
| 기대결과 | Tool 호출 파라미터 정확, 결과 통합 |
| 테스트 파일 | `tests/test_tool_calling.py` (8), `tests/test_cinematographer_tool_calling.py` (13), `tests/test_research_tool_calling.py` (15) |

### 10.4 Graph Nodes

| 항목 | 내용 |
|------|------|
| 사전조건 | 개별 노드 함수 |
| 절차 | Research, Learn, Production, Review 노드 단위 실행 |
| 기대결과 | 노드별 상태 업데이트, 오류 처리, 스냅샷 저장 |
| 테스트 파일 | `tests/test_research_node.py` (32), `tests/test_learn_node.py` (5), `tests/test_production_nodes.py` (25) |

### 10.5 Narrative Review & Reflection

| 항목 | 내용 |
|------|------|
| 사전조건 | 생성된 스크립트 |
| 절차 | Review → Reflection → 수정 사이클 |
| 기대결과 | 품질 점수 산출, 수정 제안 생성, 반복 개선 |
| 테스트 파일 | `tests/test_narrative_review.py` (10), `tests/test_review_reflection.py` (7), `tests/test_review_empty_script.py` (11) |

### 10.6 Script Snapshots & State

| 항목 | 내용 |
|------|------|
| 사전조건 | Graph 실행 중 상태 |
| 절차 | 스냅샷 저장/복원, 상태 직렬화 |
| 기대결과 | 중간 상태 보존, 재개 가능 |
| 테스트 파일 | `tests/test_script_snapshots.py` (23), `tests/test_phase10a_state.py` (5) |

### 10.7 Agent Messaging

| 항목 | 내용 |
|------|------|
| 사전조건 | Agent 간 메시지 구조 |
| 절차 | 메시지 생성, 직렬화, 전달 |
| 기대결과 | 메시지 형식 검증, fallback 처리 |
| 테스트 파일 | `tests/test_agent_messages.py` (13), `tests/test_agent_messaging.py` (13) |

---

## 11. 렌더링 품질

### 11.1 Layout Improvements

| 항목 | 내용 |
|------|------|
| 사전조건 | 렌더링 모듈 |
| 절차 | Post Type 동적 높이, Full Type Safe Zone 계산 |
| 기대결과 | 텍스트 길이별 높이 조정, 플랫폼별 Safe Zone 적용 |
| 테스트 파일 | `tests/test_layout_improvements.py` (16 tests) |

### 11.2 Visual Improvements

| 항목 | 내용 |
|------|------|
| 사전조건 | 이미지 + 텍스트 렌더링 |
| 절차 | 배경 밝기 분석, 폰트 크기 동적 조정, 적응형 텍스트 색상 |
| 기대결과 | 밝기 기반 색상 선택, 텍스트 길이별 폰트 크기 조정 |
| 테스트 파일 | `tests/test_visual_improvements.py` (14 tests) |

---

## 12. TTS & 오디오

### 12.1 TTS Postprocessing

| 항목 | 내용 |
|------|------|
| 사전조건 | TTS 오디오 파일 |
| 절차 | 트리밍, 정규화, 포맷 변환 |
| 기대결과 | 무음 제거, -20dBFS 정규화, 클리핑 방지 |
| 테스트 파일 | `tests/test_tts_postprocess.py` (12), `tests/test_tts_normalization.py` (6) |

### 12.2 TTS Text Filter

| 항목 | 내용 |
|------|------|
| 사전조건 | 텍스트 입력 |
| 절차 | TTS 부적합 문자/패턴 필터링 |
| 기대결과 | 특수문자 제거, 발음 불가 텍스트 정리 |
| 테스트 파일 | `tests/test_tts_text_filter.py` (17 tests) |

---

## 13. 에러 응답 & 보안

### 13.1 사용자용/AI용 에러 분리

| 항목 | 내용 |
|------|------|
| 사전조건 | 에러 발생 상황 |
| 절차 | 에러 핸들링 → 응답 생성 |
| 기대결과 | user_message (사용자용) + detail (AI용) 분리 |
| 테스트 파일 | `tests/test_error_responses.py` |

### 13.2 경로 보안

| 항목 | 내용 |
|------|------|
| 사전조건 | 파일 경로 입력 |
| 절차 | Path Traversal 시도 (../, 절대경로 등) |
| 기대결과 | 악의적 경로 차단, 허용된 디렉토리만 접근 |
| 테스트 파일 | `tests/test_path_security.py` |

### 13.3 업로드 검증

| 항목 | 내용 |
|------|------|
| 사전조건 | 파일 업로드 요청 |
| 절차 | 파일 타입/크기/확장자 검증 |
| 기대결과 | 허용된 타입만 통과, 초과 크기 거부 |
| 테스트 파일 | `tests/test_upload_validation.py` |

---

## 14. 설정 & 캐시

### 14.1 Config SSOT

| 항목 | 내용 |
|------|------|
| 사전조건 | config.py 설정값 |
| 절차 | 설정값 참조 및 오버라이드 |
| 기대결과 | 모든 설정이 config.py에서만 관리됨 |
| 테스트 파일 | `tests/test_config_ssot.py`, `tests/test_config_validation.py`, `tests/test_config_resolver.py` |

### 14.2 DB Cache

| 항목 | 내용 |
|------|------|
| 사전조건 | DB에 tag_rules, tag_aliases, loras 데이터 |
| 절차 | 캐시 초기화, 조회, 갱신 |
| 기대결과 | 시작 시 DB 로드, 메모리 캐시 일관성, `/admin/refresh-caches` 동작 |
| 테스트 파일 | `tests/test_db_cache.py` |
