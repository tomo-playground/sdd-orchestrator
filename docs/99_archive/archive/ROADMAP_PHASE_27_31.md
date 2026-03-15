# Roadmap Archive: Phase 27~31 + Infrastructure (2026-03-15)

## Phase 27: Chat System UX & Architecture
채팅 시스템 기술 부채 14건 해소. P0(타이핑 인디케이터, Zustand persist 히스토리, a11y). P1(ChatMessage Discriminated Union 11-variant, AbortController, 에러 복구, AutoScroll). P2(chatMessageFactory 헬퍼, 취소 버튼 UI, chat_context→Writer/Cinematographer 템플릿 전달). Chat Context→Director Plan 연결(analyze-topic 이력 → skip_stages 판단 정확도 향상). 20파일+, 코드 리뷰 PASS.

## Phase 28: Pipeline Resilience
4-Phase 전체 구현. A(빈 씬 다층 방어선 — writer 재시도+routing 가드+SSE+ReviewApprovalPanel). B(에러 복구 — finalize validator+copyright WARN+글로벌 리비전 상한). C(관측성 — fallback_reason 표준화, PipelineStepCard 6노드, fallback 배지). D(데이터 무결성 — _extract_reasoning 원본 보존, checkpoint 음수 score 방어). 70개 테스트, 커밋 4건.

## Phase 29: Video Pre-validation
4-Sub-Phase(A~D) 완료. A(TTS 프리뷰 UX — 프로그레스 바, voice_design 디버그, inlineKeyframes 통합). B(TTS 프리뷰→렌더 연결 — tts_asset_id 기반 재사용, Spread Passthrough 패턴 8함수 전환). C(타임라인 시각화 — useTimeline 훅, TimelineBar, 서버 effective_duration). D(통합 사전검증 리포트 — 캐릭터/음성/이미지/스크립트/TTS/시간 7항목, 자동 실행, 렌더 연동).

## Casting 네이밍 정규화
`character_id`→`character_a_id`, `character_name`→`character_a_name` (Casting 컨텍스트 내). Backend 10파일+Frontend 11파일. Alembic JSONB 키 리네임 마이그레이션. Casting SSOT Race Condition 근본 수정(5개 누락 경로, isScriptGenerating 플래그, autoSave 완전 차단). 테스트 163개 PASS.

## Checkpointer 리팩토링
AsyncConnectionPool 기반 per-request checkpointer/store 생성. 라우터 의존성 주입 패턴. DB 풀 고갈 방지.

## Phase 30: Character Consistency V2
11개 Sub-Phase(A~N)+O+P+P-6+F-2 완료.
- A(Config 튜닝)+B+(Finalize 복장 교정 2단계 — 비DB 태그 제거+DB 태그 주입)+F(프롬프트 필드 리네이밍 5개)
- H(context_tags 구조화 — camera/cinematic/props 3필드+cross-field 검증)+I(Gemini 역할 분리+scene_negative Sync 버그)
- J(SCENE_CHARACTER_LORA_SCALE=0.45 — LoRA vs 텍스트 태그 제어)+K(캐릭터 프롬프트 5필드→2필드 통합)
- L(image_prompt 복장 오염 차단 강화)+M/N(sitting 포즈 근본 보정 — dynamic weight+camera 강제)
- O(Multi-Character Scene — BREAK 토큰 구조, per-BREAK dedup, solo 자동 제거, facing_another)
- P(배경-대본 일관성+IP-Adapter race condition refsLoadedRef 패턴)+P-6(Location Planner 독립 노드 — concept_gate 후 20노드)
- F-2(Preview→Reference 네이밍 통일). C(Dual IP-Adapter), D(LoRA 트레이닝)는 SDXL 전환 후 재검토 보류.
테스트 200개+, 코드 리뷰 다수.

## Phase 31: UX Navigation Overhaul
6개 Sub-Phase(A~F) 완료.
- A(Admin 유령 라우트 9+AdminShell 2+Lab 고아 18+기타 4 = 31파일 삭제, Settings 이동)
- B(상태 누수 3건 완전 리셋+resetTransientStores DRY 헬퍼 추출)
- C(LoRA Service/Admin split, DELETE response_model 추가, Scene URL 통일)
- D(LibraryShell+SettingsShell→SubNavShell 통합, Library LoRA 탭 읽기 전용)
- E(POST /api/v1/projects/quick-start 원자적 생성, SetupWizard 빠른시작, Dead Code 삭제)
- F(Group SoftDeleteMixin+Alembic 마이그레이션, Cascade soft delete, Trash 탭, StyleProfile/RenderPreset/VoicePreset DELETE 409)

## Forge 전환 (Stage 1)
A1111→Forge Docker 전환. forge-docker/Dockerfile(ADetailer 확장+CUDA 12.8+4-layer pip 캐싱). Forge API 호환성 — split_sampler_scheduler()/apply_sampler_to_payload() config.py SSOT, ControlNet 3슬롯 패딩, IP-Adapter 모듈명(InsightFace+CLIP-H, CLIP-ViT-H), reference_adain 정리. Hi-Res 버그 패치(hr_additional_modules None TypeError, Dockerfile sed 영구화). 파라미터 튜닝(CFG 6.5, DPM++ 2M SDE Karras). sampler SSOT — avatar/lora_calibration 통일, image_cache 캐시키 scheduler 추가.

## NoobAI-XL V-Pred 전환 (Stage 4)
SD1.5→NoobAI-XL V-Pred 1.0 전체 스택 마이그레이션. config.py(Euler/CFG 4.5/832x1216), apply_sampler_to_payload() CFG Rescale 0.2 주입, 51건 테스트 수정. is_active Boolean 필터 8곳. SD1.5 LoRA 13건 삭제+SDXL LoRA 3종(Flat Color v2, Detailer, MeMaXL). StyleProfile 정리(5→2개, Flat Color Anime+MeMaXL Flat Anime). DB 클렌징 — groups 2, storyboards 3, scenes 41, characters 5 삭제, 고아 media_assets 269건+MinIO 349파일. 하은/재민 레퍼런스 SDXL 재생성. SD_WEBUI_SETUP.md NoobAI-XL 기준 전면 재작성+Rollback 절차.

## LLM Provider 추상화 (Phase A~E)
`services/llm/` 패키지(types, provider, gemini_provider, registry) 구축. `google.genai` 직결 제거 — `get_llm_provider()` 팩토리 9개 파일 전환. trace + PROHIBITED_CONTENT fallback 중복 해소. Backend Lint 기술 부채 10건 해소(ruff CLEAN). Phase F(OllamaProvider)는 LiteLLM SDK 도입(착수 조건: 두 번째 Provider 확정 시)으로 대체 — 백로그 등록.

---

## 03-03~03-15 안정화 및 개선 작업

- **LangFuse Observability 개선** (03-15): Resume 트레이스 input/output 역전 수정, stale `interrupted: True` 수정, `update_trace_on_completion()` 신규, errored 플래그 도입, root span 기반 계층 구조, handler_trace_id 추출 공통화. Frontend DEBUG console.log 4개 제거. 테스트 22개 PASS.
- **Phase 30-P-6 Location Planner 독립 노드** (03-15): concept_gate 직후 Location Planner 독립 노드 분리(20노드). `location_planner.py` + `location_planner.j2` 신규. `_estimate_scene_range()`, `build_director_context()` 공통 헬퍼. writer fallback graceful degradation. 테스트 13개.
- **Phase 30-P 배경-대본 일관성** (03-15): Writer 템플릿 Location Continuity 4규칙, Director Checkpoint Location Map QC(5번 기준), Finalize cinematic 안정화(`_stabilize_location_cinematic`), BG 배지 hover 메타 오버레이, IP-Adapter race condition 수정. 테스트 5개.
- **Phase 30-O Multi-Character Scene** (03-14): LoRA multi 3필드 제거, 게이트 단순화, BREAK 토큰 구조, per-BREAK dedup, MULTI_BANNED_TAGS(solo), facing_another, LoRA weight 합산 상한 1.5. Finalize BLOCKER 방어 5건. 4-Agent 크로스 분석. 테스트 25개.
- **NoobAI-XL V-Pred 전환 + DB 클렌징** (03-14): 전체 스택 마이그레이션 완료.
- **Forge 전환 Stage 1** (03-14): forge-docker/Dockerfile 신규, API 호환성 7경로 통일.
- **Phase 31 A~F 완결** (03-13~14): UX Navigation Overhaul 전체 완료.
- **/dev/system 페이지 정리** (03-13): Gemini Auto Edit/Performance Analytics/Show Lab Menu/Memory 탭 제거. 16파일 -1,008줄.
- **TTS 감정 적응 + BGM aloop + VRAM 최적화** (03-13): Gemini 감정 적응 voice design 활성화, BGM aloop+apad, MusicGen on-demand GPU load/unload, Audio Server pre-flight health check.
- **MusicGen/TTS 품질 개선** (03-13): CUDA 전환, musicgen-medium(1.5B), 60초 BGM, 한국어 숫자 전처리(`text_preprocess.py`), TTS 전처리 버그 5건.
- **WSL2 환경 세팅 + LangFuse 트레이싱** (03-13): root span 계층 구조, scripts.py 분리(593줄→270+328줄), docker-compose.yml, Master Data 등록(LoRA 13, Embedding 7, SD Model 2, Group 6, Character 12).

---

## 03-01~03-02 안정화 (일부)

- **Auto Run 22건 버그 수정** (03-05): AbortSignal SSE 취소, Batch 프롬프트 불일치, TTS 캐시키, stageStatus 복구, didScenesChanged 7필드, DB 풀 고갈 3-Phase 분리 등. 15파일.
- **Gemini PROHIBITED_CONTENT 방어** (03-03): system_instruction 분리, 자동 폴백(gemini-2.0-flash), GEMINI_SAFETY_SETTINGS SSOT 5곳.
- **Finalize 파이프라인 버그 3건** (03-03): negative_prompt 빈 문자열 방어, mood fallback, EXCLUSIVE identity 태그 필터링.
- **캐릭터 스타일 일관성 + 포즈 다양성** (03-03): Cinematographer 태그 계층화, IP-Adapter weight 포즈 테이블 제거, Finalize 교정 3종. 테스트 21개.
- **QA 리그레션 테스트** (03-01): 신규 246개(Backend 108+Frontend 105+E2E 33), Frontend 커버리지 64.4%. 총 4,030개.
- **Character-Group 소유권, Service/Admin 분리, Prompt 3-Tier, Realistic 배경 품질** (03-02): 다수 리팩토링.
