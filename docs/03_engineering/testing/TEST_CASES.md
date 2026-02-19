# Test Cases (TC) - 전체 매트릭스

**최종 업데이트**: 2026-02-19

---

## TC 요약

| 영역 | TC 수 | 테스트 파일 수 | 상태 |
|------|-------|--------------|------|
| Backend Unit | 1,334 | 103 | Active |
| Backend Router | 368 | 25 | Active |
| Backend Integration | 108 | 9 | Active |
| Backend VRT | 36 | 4 | Active |
| Backend Benchmark | 18 | 1 | Active |
| Frontend Unit | 352 | 31 | Active |
| Frontend VRT/E2E | 24+ | 11 | Active |
| **합계** | **2,214+** | **184** | - |

---

## 1. Storyboard (핵심 도메인)

### TC-1.1 AI 스토리보드 생성

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-1.1.1 | POST /storyboards/create — Gemini 호출 → Scene[] 반환 | Integration | `api/test_storyboard.py` |
| TC-1.1.2 | 생성 시 structure/language/duration 파라미터 전달 | Integration | `api/test_storyboard.py` |
| TC-1.1.3 | 생성 실패 시 에러 응답 (Gemini API 오류) | Unit | `test_router_storyboard.py` |

### TC-1.2 CRUD

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-1.2.1 | POST /storyboards — DB 저장, version=1 | Integration | `api/test_storyboard.py` |
| TC-1.2.2 | GET /storyboards — 목록 조회 (페이지네이션) | Router | `test_router_storyboard.py` |
| TC-1.2.3 | GET /storyboards/{id} — 상세 조회 (Scene/Character 포함) | Router | `test_router_storyboard.py` |
| TC-1.2.4 | PUT /storyboards/{id} — 전체 업데이트 (씬 재생성) | Router | `test_router_storyboard.py` |
| TC-1.2.5 | PATCH /storyboards/{id}/metadata — 부분 업데이트 (Optimistic Locking) | Router | `test_router_storyboard.py` |
| TC-1.2.6 | DELETE /storyboards/{id} — Soft Delete (deleted_at 설정) | Router | `test_router_storyboard.py` |
| TC-1.2.7 | GET /storyboards/trash — 삭제된 스토리보드 조회 | Router | `test_router_storyboard.py` |
| TC-1.2.8 | POST /storyboards/{id}/restore — 복원 | Router | `test_router_storyboard.py` |
| TC-1.2.9 | DELETE /storyboards/{id}/permanent — 영구 삭제 | Router | `test_router_storyboard.py` |

### TC-1.3 데이터 무결성

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-1.3.1 | Optimistic Locking — version 불일치 시 409 반환 | Unit | `test_router_storyboard.py` |
| TC-1.3.2 | CASCADE 삭제 — Scene + CharacterAction + Asset 정리 | Unit | `test_soft_delete.py` |
| TC-1.3.3 | Orphaned Media 정리 — PUT 시 이전 Asset 삭제 | Unit | `test_router_storyboard.py` |
| TC-1.3.4 | Storyboard 파싱 검증 | Unit | `test_storyboard_parsing.py` |
| TC-1.3.5 | Storyboard 제약 조건 검증 | Unit | `test_storyboard_constraints.py` |
| TC-1.3.6 | Candidates 영속화 | Unit | `test_candidates_persistence.py` |
| TC-1.3.7 | Candidates 포맷 검증 | Unit | `test_candidates_format.py` |

---

## 2. 이미지 생성 (Scene)

### TC-2.1 동기 생성

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-2.1.1 | POST /scene/generate — SD WebUI 호출 → Base64 이미지 반환 | Router | `test_router_scene.py` |
| TC-2.1.2 | 배치 생성 — Semaphore 기반 동시성 제어 | Router | `test_router_scene.py` |
| TC-2.1.3 | 이미지 저장 — POST /image/store → MediaAsset 생성 | Router | `test_router_scene.py` |

### TC-2.2 비동기 생성

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-2.2.1 | POST /scene/generate-async → task_id 반환 | Router | `test_router_scene.py` |
| TC-2.2.2 | GET /scene/progress/{task_id} — SSE 스트림 | Router | `test_router_scene.py` |
| TC-2.2.3 | 진행률 추적 — ImageProgress 상태 관리 | Unit | `test_image_progress.py` |

### TC-2.3 검증 & 편집

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-2.3.1 | POST /scene/validate-and-auto-edit — WD14 검증 + Gemini 편집 | Router | `test_router_scene.py` |
| TC-2.3.2 | POST /scene/edit-with-gemini — 수동 프롬프트 편집 | Router | `test_router_scene.py` |
| TC-2.3.3 | POST /scene/suggest-edit — 개선안 자동 제안 | Router | `test_router_scene.py` |
| TC-2.3.4 | 이미지 품질 검증 (WD14 score, match rate) | Unit | `test_validation.py` |

### TC-2.4 생성 파이프라인

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-2.4.1 | Generation Pipeline 전체 흐름 | Unit | `test_generation_pipeline.py` |
| TC-2.4.2 | SD WebUI 코어 통합 | Unit | `test_image_generation_core.py` |
| TC-2.4.3 | 이미지 스토리지 키 생성 | Unit | `test_image_storage_key.py` |
| TC-2.4.4 | Data URL 로드 | Unit | `test_load_as_data_url.py` |
| TC-2.4.5 | SD 진행률 폴링 | Unit | `test_image_progress.py` |

### TC-2.5 ControlNet & IP-Adapter

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-2.5.1 | ControlNet 참조 이미지 적용 | Unit | `test_controlnet_reference.py` |
| TC-2.5.2 | ControlNet API 통합 | Integration | `api/test_controlnet.py` |
| TC-2.5.3 | IP-Adapter 캐릭터 일관성 | Unit | `test_character_consistency.py` |

---

## 3. 프롬프트 엔진

### TC-3.1 V3 Composition (12-Layer)

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-3.1.1 | 12개 레이어 순서대로 합성 | Unit | `test_v3_composition.py` |
| TC-3.1.2 | Intra-layer 중복 제거 | Unit | `test_v3_composition.py` |
| TC-3.1.3 | 빈 태그 → base prompt만 반환 | Unit | `test_prompt_compose_error.py` |
| TC-3.1.4 | V3 Reference 테스트 | Unit | `test_v3_reference.py` |

### TC-3.2 태그 처리

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-3.2.1 | Danbooru 언더바 표준 정규화 | Unit | `test_tag_normalization.py` |
| TC-3.2.2 | LoRA 트리거 워드 원본 보존 | Unit | `test_tag_normalization.py` |
| TC-3.2.3 | 태그 충돌 필터링 (standing vs sitting) | Unit | `test_filter_prompt_tokens_effectiveness.py` |
| TC-3.2.4 | 태그 별칭 해석 (medium_shot → cowboy_shot) | Unit | `test_tag_normalization.py` |
| TC-3.2.5 | 키워드 컨텍스트 포매팅 | Unit | `test_format_keyword_context.py` |
| TC-3.2.6 | 키워드 카테고리 분류 | Unit | `test_keyword_categories.py` |

### TC-3.3 프롬프트 생성 & 품질

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-3.3.1 | 프롬프트 생성 서비스 | Unit | `test_generation_prompt.py` |
| TC-3.3.2 | 프롬프트 유틸리티 | Unit | `test_prompt_utils.py` |
| TC-3.3.3 | 프롬프트 품질 분석 | Unit | `test_prompt_quality.py` |
| TC-3.3.4 | 프롬프트 수정 패치 | Unit | `test_prompt_fixes.py` |
| TC-3.3.5 | 프롬프트 API 통합 | Integration | `api/test_prompt.py` |
| TC-3.3.6 | 태그 효과도 자동 분석 | Unit | `test_tag_effectiveness_auto.py` |

---

## 4. 캐릭터 & 스타일

### TC-4.1 캐릭터 CRUD

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-4.1.1 | 캐릭터 생성/조회/수정/삭제 API | Router | `test_router_characters.py` |
| TC-4.1.2 | 캐릭터 액션 해석 | Unit | `test_character_action_resolver.py` |
| TC-4.1.3 | 캐릭터 컨텍스트 빌드 | Unit | `test_character_context.py` |
| TC-4.1.4 | 다중 캐릭터 프롬프트 | Unit | `test_multi_character.py` |
| TC-4.1.5 | Speaker 매핑 동기화 | Unit | `test_sync_speaker_mappings.py` |
| TC-4.1.6 | Speaker 해석 | Unit | `test_speaker_resolver.py` |

### TC-4.2 스타일 & LoRA

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-4.2.1 | StyleProfile 적용 | Unit | `test_style_lora_integration.py` |
| TC-4.2.2 | Style LoRA Unification (전 씬 통일) | Unit | `test_style_lora_unification.py` |
| TC-4.2.3 | Style LoRA 해석 | Unit | `test_style_lora_resolution.py` |
| TC-4.2.4 | Style Context 빌드 | Unit | `test_style_context.py` |
| TC-4.2.5 | Scene Generation + StyleProfile | Unit | `test_scene_generation_with_style_profile.py` |
| TC-4.2.6 | StyleProfile CRUD API | Router | `test_router_style_profiles.py` |

### TC-4.3 아바타

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-4.3.1 | 아바타 생성 서비스 | Unit | `test_avatar_service.py` |
| TC-4.3.2 | 아바타 API | Router | `test_router_avatar.py` |

---

## 5. 비디오 렌더링

### TC-5.1 동기/비동기 렌더링

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-5.1.1 | POST /video/create — FFmpeg 동기 렌더링 | Router | `test_router_video.py` |
| TC-5.1.2 | POST /video/create-async → task_id 반환 | Router | `test_router_video_async.py` |
| TC-5.1.3 | GET /video/progress/{task_id} — SSE 8단계 | Router | `test_router_video_async.py` |
| TC-5.1.4 | 렌더 히스토리 조회 | Router | `test_router_video.py` |
| TC-5.1.5 | 비디오 모듈 검증 | Unit | `test_video_modules.py` |
| TC-5.1.6 | 비디오 스토리지 서비스 | Unit | `test_video_service_storage.py` |

### TC-5.2 효과 & BGM

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-5.2.1 | Ken Burns 효과 | Unit | `test_video_modules.py` |
| TC-5.2.2 | AI BGM 경로 해석 | Unit | `test_effects_ai_bgm.py` |
| TC-5.2.3 | BGM 모드 (AI/File) 전환 | Unit | `test_bgm.py` |
| TC-5.2.4 | Motion 이펙트 | Unit | `test_motion.py` |
| TC-5.2.5 | 진행률 추적 | Unit | `test_progress.py` |

---

## 6. 렌더링 품질 (VRT)

### TC-6.1 레이아웃

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-6.1.1 | Post Type Scene Text 동적 높이 | Unit | `test_layout_improvements.py` |
| TC-6.1.2 | Full Type 플랫폼별 Safe Zone | Unit | `test_layout_improvements.py` |
| TC-6.1.3 | 텍스트 길이별 폰트 크기 동적 조정 | Unit | `test_visual_improvements.py` |
| TC-6.1.4 | 배경 밝기 기반 텍스트 색상 자동 조정 | Unit | `test_visual_improvements.py` |

### TC-6.2 VRT Golden Master

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-6.2.1 | Scene Text 렌더링 (SSIM >= 0.95) | VRT | `vrt/test_subtitle_rendering.py` |
| TC-6.2.2 | 오버레이 렌더링 (SSIM >= 0.95) | VRT | `vrt/test_overlay_rendering.py` |
| TC-6.2.3 | Post Frame 합성 (SSIM >= 0.95) | VRT | `vrt/test_post_frame.py` |
| TC-6.2.4 | 결정적 렌더링 (SSIM = 1.0) | VRT | `vrt/test_deterministic.py` |

---

## 7. TTS & 오디오

### TC-7.1 TTS 후처리

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-7.1.1 | 트리밍 (무음 제거) | Unit | `test_tts_postprocess.py` |
| TC-7.1.2 | 정규화 (-20dBFS 타겟) | Unit | `test_tts_normalization.py` |
| TC-7.1.3 | 클리핑 방지 | Unit | `test_tts_normalization.py` |
| TC-7.1.4 | TTS 텍스트 필터 (특수문자 제거) | Unit | `test_tts_text_filter.py` |
| TC-7.1.5 | TTS 컨텍스트 빌드 | Unit | `test_tts_context.py` |

### TC-7.2 음성/음악 프리셋

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-7.2.1 | Voice Presets 검증 | Unit | `test_voice_presets.py` |
| TC-7.2.2 | Music Presets CRUD | Router | `test_router_music_presets.py` |
| TC-7.2.3 | Music Generator (캐시 키/히트) | Unit | `test_music_generator.py` |

---

## 8. Creative Script Graph (Agentic Pipeline)

### TC-8.1 Graph 실행

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-8.1.1 | Script Graph 전체 실행 (19 tests) | Unit | `test_script_graph.py` |
| TC-8.1.2 | Graph State 직렬화 | Unit | `test_phase10a_state.py` |
| TC-8.1.3 | Script Snapshots (23 tests) | Unit | `test_script_snapshots.py` |
| TC-8.1.4 | Checkpointer | Unit | `test_checkpointer.py` |

### TC-8.2 Agents

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-8.2.1 | Creative Agents (11 tests) | Unit | `test_creative_agents.py` |
| TC-8.2.2 | Director React (13 tests) | Unit | `test_director_react.py` |
| TC-8.2.3 | Critic Debate (12 tests) | Unit | `test_critic_debate.py` |
| TC-8.2.4 | Creative QC Music | Unit | `test_creative_qc_music.py` |

### TC-8.3 Nodes

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-8.3.1 | Research Node (32 tests) | Unit | `test_research_node.py` |
| TC-8.3.2 | Learn Node (5 tests) | Unit | `test_learn_node.py` |
| TC-8.3.3 | Production Nodes (25 tests) | Unit | `test_production_nodes.py` |
| TC-8.3.4 | Cinematographer | Unit | `test_cinematographer.py` |
| TC-8.3.5 | Concept Gate | Unit | `test_concept_gate.py` |

### TC-8.4 Tool Calling

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-8.4.1 | Tool Calling 기본 (8 tests) | Unit | `test_tool_calling.py` |
| TC-8.4.2 | Cinematographer Tool Calling (13 tests) | Unit | `test_cinematographer_tool_calling.py` |
| TC-8.4.3 | Research Tool Calling (15 tests) | Unit | `test_research_tool_calling.py` |

### TC-8.5 Review & Reflection

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-8.5.1 | Narrative Review (10 tests) | Unit | `test_narrative_review.py` |
| TC-8.5.2 | Review Reflection (7 tests) | Unit | `test_review_reflection.py` |
| TC-8.5.3 | Review Empty Script (11 tests) | Unit | `test_review_empty_script.py` |
| TC-8.5.4 | Revise & Expand | Unit | `test_revise_expand.py` |
| TC-8.5.5 | Writer Planning | Unit | `test_writer_planning.py` |
| TC-8.5.6 | Script Feedback | Unit | `test_script_feedback.py` |

### TC-8.6 Messaging

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-8.6.1 | Agent Messages (13 tests) | Unit | `test_agent_messages.py` |
| TC-8.6.2 | Agent Messaging (13 tests) | Unit | `test_agent_messaging.py` |
| TC-8.6.3 | Memory API | Unit | `test_memory_api.py` |

---

## 9. Project / Group 계층 구조

### TC-9.1 라우터

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-9.1.1 | Projects CRUD API | Router | `test_router_projects.py` |
| TC-9.1.2 | Groups CRUD API | Router | `test_router_groups.py` |
| TC-9.1.3 | Cascading Config 해석 | Unit | `test_config_resolver.py` |

### TC-9.2 설정 상속

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-9.2.1 | Config SSOT 검증 | Unit | `test_config_ssot.py` |
| TC-9.2.2 | Config Validation | Unit | `test_config_validation.py` |
| TC-9.2.3 | Config Resolver (System < Group) | Unit | `test_config_resolver.py` |
| TC-9.2.4 | Groups 통합 테스트 | Unit | `test_groups.py` |

---

## 10. 태그 & 키워드 시스템

### TC-10.1 태그 CRUD

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-10.1.1 | Tags API (생성/조회/검색) | Router | `test_router_tags.py` |
| TC-10.1.2 | Keywords API (제안/규칙/우선순위) | Router | `test_router_keywords.py` |
| TC-10.1.3 | Keywords 통합 | Integration | `api/test_keywords.py` |

### TC-10.2 캐시 시스템

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-10.2.1 | DB Cache (Tag/Rule/Alias/LoRA) | Unit | `test_db_cache.py` |
| TC-10.2.2 | Admin — /refresh-caches 동작 | Router | `test_router_admin.py` |

---

## 11. 프리셋 시스템

### TC-11.1 Presets

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-11.1.1 | Storyboard Presets API | Router | `test_router_presets.py` |
| TC-11.1.2 | Presets 통합 | Integration | `api/test_presets.py` |
| TC-11.1.3 | Render Presets CRUD | Integration | `api/test_render_presets.py` |
| TC-11.1.4 | Feedback Presets | Unit | `test_feedback_presets.py` |

### TC-11.2 프리셋 라우터

| ID | 테스트 케이스 | 유형 | 파일/상태 |
|----|-------------|------|----------|
| TC-11.2.1 | Voice Presets CRUD Router | Router | `test_router_voice_presets.py` |
| TC-11.2.2 | Render Presets Router 단위 | Router | `test_router_render_presets.py` |
| TC-11.2.3 | Creative Presets CRUD Router | Router | **미구현** |

---

## 12. 저장소 & 에셋

### TC-12.1 Storage

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-12.1.1 | 3계층 스토리지 (permanent/storyboard/temp) | Unit | `test_storage.py` |
| TC-12.1.2 | Asset 서비스 CRUD | Unit | `test_asset_service.py` |
| TC-12.1.3 | Assets API | Router | `test_router_assets.py` |
| TC-12.1.4 | Media GC (가비지 컬렉션) | Unit | `test_media_gc.py` |

### TC-12.2 커버리지 갭

| ID | 테스트 케이스 | 유형 | 상태 |
|----|-------------|------|------|
| TC-12.2.1 | Cleanup API Router | Router | **미구현** |
| TC-12.2.2 | Backgrounds CRUD Router | Router | **미구현** |

---

## 13. 보안 & 에러

### TC-13.1 보안

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-13.1.1 | Path Traversal 방지 | Unit | `test_path_security.py` |
| TC-13.1.2 | 업로드 파일 검증 (타입/크기) | Unit | `test_upload_validation.py` |

### TC-13.2 에러 응답

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-13.2.1 | 사용자용/AI용 에러 분리 | Unit | `test_error_responses.py` |
| TC-13.2.2 | 스키마 검증 실패 | Unit | `test_schema_validation.py` |

---

## 14. 분석 & 관리

### TC-14.1 분석

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-14.1.1 | Analytics API (Gemini Edits) | Router | `test_router_analytics.py` |
| TC-14.1.2 | Quality API | Router | `test_router_quality.py` |
| TC-14.1.3 | Quality 통합 | Integration | `api/test_quality.py` |
| TC-14.1.4 | Activity Logs API | Router | `test_router_activity_logs.py` |
| TC-14.1.5 | Activity Logs 통합 | Integration | `api/test_activity_logs.py` |

### TC-14.2 관리

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-14.2.1 | Admin 캐시 리프레시 | Router | `test_router_admin.py` |
| TC-14.2.2 | Settings (자동 편집) | Router | `test_router_settings.py` |

### TC-14.3 커버리지 갭

| ID | 테스트 케이스 | 유형 | 상태 |
|----|-------------|------|------|
| TC-14.3.1 | Prompt Histories CRUD Router | Router | **미구현** |
| TC-14.3.2 | SD Models Router | Router | **미구현** |
| TC-14.3.3 | Scripts Router | Router | **미구현** |
| TC-14.3.4 | Lab Router 단위 | Router | **미구현** |
| TC-14.3.5 | Memory Router | Router | **미구현** |
| TC-14.3.6 | YouTube Router | Router | **미구현** |

---

## 15. SD WebUI 통합

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-15.1 | SD 상태 확인 API | Router | `test_router_sd.py` |
| TC-15.2 | txt2img / img2img | Router | `test_router_sd.py` |
| TC-15.3 | LoRA 검색/관리 | Router | `test_router_loras.py` |

---

## 16. 인프라 & DB

### TC-16.1 DB 격리

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-16.1.1 | 테스트 간 DB 상태 간섭 없음 | Unit | `test_db_isolation.py` |
| TC-16.1.2 | Soft Delete 일관성 | Unit | `test_soft_delete.py` |
| TC-16.1.3 | Shared Assets 통합 | Unit | `test_shared_assets_integration.py` |

### TC-16.2 기타

| ID | 테스트 케이스 | 유형 | 파일 |
|----|-------------|------|------|
| TC-16.2.1 | Scene ID 순서 보장 | Unit | `test_scene_ids_ordering.py` |
| TC-16.2.2 | Scene Text 네이밍 통일 | Unit | `test_scene_text_naming.py` |
| TC-16.2.3 | Auto Pin 계산 | Unit | `test_auto_pin_calculation.py` |
| TC-16.2.4 | Dialogue 스토리보드 | Unit | `test_dialogue_storyboard.py` |
| TC-16.2.5 | Backgrounds 관리 | Unit | `test_backgrounds.py` |
| TC-16.2.6 | Lab 서비스 | Unit | `test_lab.py` |
| TC-16.2.7 | Lab 통합 | Integration | `api/test_lab_router.py` |
| TC-16.2.8 | Lab Compose & Run | Unit | `test_lab_compose_and_run.py` |
| TC-16.2.9 | P0 핫픽스 검증 | Unit | `test_p0_fixes.py` |
| TC-16.2.10 | Resolution 전략 | Unit | `test_resolution_strategy.py` |

---

## 17. Frontend Unit 테스트

### TC-17.1 컴포넌트

| ID | 테스트 케이스 | 테스트 수 | 파일 |
|----|-------------|---------|------|
| TC-17.1.1 | Button (15 tests) | 15 | `components/__tests__/Button.test.tsx` |
| TC-17.1.2 | Modal (13 tests) | 13 | `components/__tests__/Modal.test.tsx` |
| TC-17.1.3 | Badge (9 tests) | 9 | `components/__tests__/Badge.test.tsx` |
| TC-17.1.4 | ConfirmDialog (8 tests) | 8 | `components/__tests__/ConfirmDialog.test.tsx` |
| TC-17.1.5 | Skeleton (7 tests) | 7 | `components/__tests__/Skeleton.test.tsx` |
| TC-17.1.6 | Toast (3 tests) | 3 | `components/__tests__/Toast.test.tsx` |
| TC-17.1.7 | LoadingSpinner (3 tests) | 3 | `components/__tests__/LoadingSpinner.test.tsx` |
| TC-17.1.8 | AnalyticsDashboard (8 tests) | 8 | `analytics/__tests__/AnalyticsDashboard.test.tsx` |
| TC-17.1.9 | TagAutocomplete | - | `tests/components/TagAutocomplete.test.tsx` |

### TC-17.2 Hooks

| ID | 테스트 케이스 | 테스트 수 | 파일 |
|----|-------------|---------|------|
| TC-17.2.1 | useAutopilot (상태 전이, 취소/재개) | 27 | `hooks/__tests__/useAutopilot.test.ts` |
| TC-17.2.2 | useCharacters (캐릭터 데이터 관리) | 13 | `hooks/__tests__/useCharacters.test.ts` |
| TC-17.2.3 | useFocusTrap (포커스 트랩) | 5 | `hooks/__tests__/useFocusTrap.test.tsx` |
| TC-17.2.4 | useScriptEditor | - | `hooks/__tests__/useScriptEditor.test.ts` |

### TC-17.3 Store Actions

| ID | 테스트 케이스 | 테스트 수 | 파일 |
|----|-------------|---------|------|
| TC-17.3.1 | storyboardActions (CRUD, 동기화) | 33 | `store/actions/__tests__/storyboardActions.test.ts` |
| TC-17.3.2 | groupActions (그룹 관리) | 12 | `store/actions/__tests__/groupActions.test.ts` |
| TC-17.3.3 | narratorGeneration (나레이터 음성) | 11 | `store/actions/__tests__/narratorGeneration.test.ts` |
| TC-17.3.4 | batchActions (배치 처리) | 3 | `store/actions/__tests__/batchActions.test.ts` |
| TC-17.3.5 | autopilotActions | 2 | `store/actions/__tests__/autopilotActions.test.ts` |
| TC-17.3.6 | resetAllStores (스토어 리셋) | 6 | `store/__tests__/resetAllStores.test.ts` |

### TC-17.4 Utils

| ID | 테스트 케이스 | 테스트 수 | 파일 |
|----|-------------|---------|------|
| TC-17.4.1 | validation (씬 검증) | 34 | `utils/__tests__/validation.test.ts` |
| TC-17.4.2 | speakerResolver (화자 해석) | 24 | `utils/__tests__/speakerResolver.test.ts` |
| TC-17.4.3 | sceneSettingsResolver | 14 | `utils/__tests__/sceneSettingsResolver.test.ts` |
| TC-17.4.4 | autoPin (자동 핀) | 11 | `utils/__tests__/autoPin.test.ts` |
| TC-17.4.5 | format (포맷팅) | 10 | `utils/__tests__/format.test.ts` |
| TC-17.4.6 | pipelineSteps | 10 | `utils/__tests__/pipelineSteps.test.ts` |
| TC-17.4.7 | applyAutoPin | 8 | `utils/__tests__/applyAutoPin.test.ts` |
| TC-17.4.8 | pinIntegration | 8 | `utils/__tests__/pinIntegration.test.ts` |
| TC-17.4.9 | url (URL 유틸) | 7 | `utils/__tests__/url.test.ts` |
| TC-17.4.10 | pinnedSceneOrder | 6 | `utils/__tests__/pinnedSceneOrder.test.ts` |
| TC-17.4.11 | videoRestore | 5 | `utils/__tests__/videoRestore.test.ts` |

---

## 18. Frontend VRT / E2E

### TC-18.1 VRT (스크린샷 비교)

| ID | 테스트 케이스 | 파일 |
|----|-------------|------|
| TC-18.1.1 | Studio 페이지 스크린샷 | `studio.vrt.spec.ts` |
| TC-18.1.2 | Manage 페이지 스크린샷 | `manage.vrt.spec.ts` |
| TC-18.1.3 | Characters 페이지 스크린샷 | `characters.vrt.spec.ts` |
| TC-18.1.4 | Voices 페이지 스크린샷 | `voices.vrt.spec.ts` |
| TC-18.1.5 | Music 페이지 스크린샷 | `music.vrt.spec.ts` |
| TC-18.1.6 | Backgrounds 페이지 스크린샷 | `backgrounds.vrt.spec.ts` |
| TC-18.1.7 | Scripts 페이지 스크린샷 | `scripts.vrt.spec.ts` |
| TC-18.1.8 | Lab 페이지 스크린샷 | `lab.vrt.spec.ts` |

### TC-18.2 E2E (유저 플로우)

| ID | 테스트 케이스 | 파일 |
|----|-------------|------|
| TC-18.2.1 | Studio E2E (스토리보드 로드, 씬 확인) | `studio-e2e.spec.ts` |
| TC-18.2.2 | Manage E2E (그룹/시리즈 관리) | `manage-e2e.spec.ts` |
| TC-18.2.3 | Home E2E (대시보드) | `home.spec.ts` |

---

## 커버리지 갭 요약 (미구현 TC)

### 라우터 테스트 미구현 (8개)

| 우선순위 | 라우터 | 영향도 |
|---------|--------|--------|
| P2 | `youtube.py` | 업로드 기능 |
| P2 | `scripts.py` | Script Graph |
| P2 | `cleanup.py` | 스토리지 정리 |
| P2 | `backgrounds.py` (라우터) | 에셋 관리 |
| P3 | `prompt_histories.py` | 이력 관리 |
| P3 | `sd_models.py` | SD 모델 관리 |
| P3 | `creative_presets.py` | Creative Engine |
| P3 | `memory.py` | 추론 메모리 |

> P1 라우터(Projects, Groups, Voice Presets, Render Presets)는 2026-02-19 완료.

### 추천 액션

1. **P2 (다음 Phase)**: YouTube, Scripts, Cleanup, Backgrounds 라우터
2. **P3 (백로그)**: 나머지 라우터

---

## 테스트 실행 방법

```bash
# 전체
./run_tests.sh

# Backend 전체 (VRT 제외)
cd backend && uv run pytest --ignore=tests/vrt -v

# Backend VRT
cd backend && uv run pytest tests/vrt -v

# Frontend Unit
cd frontend && npx vitest run

# Frontend VRT
cd frontend && npm run test:vrt

# Frontend E2E
cd frontend && npx playwright test
```
