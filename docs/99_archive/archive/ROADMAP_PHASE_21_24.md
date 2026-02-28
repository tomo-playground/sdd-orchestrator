# Roadmap Archive: Phase 21~24 + 안정화 작업 (2026-02-28)

## Phase 21: Persona-based Menu Reorganization
Admin을 Library/Settings/Dev 3-tier로 재편. Shell 3종 + 14개 라우트 신설, admin dead code 제거. 120파일 변경. 6/6 완료.

## Phase 22: Backend Complete Image Generation
SD 이미지 생성→저장까지 Backend 자율 완결, Frontend SPOF 제거. MinIO 저장+DB 갱신을 Backend에서 처리, Graceful Degradation fallback. 8파일 변경.

## Phase 23: Project/Group UX 개선
Zero-Config 자동 프로비저닝, 용어 통일(채널/시리즈/영상), 설정 가시성(ConfigBadges), 내비게이션 개선(리다이렉트 제거). 4/4 완료.

## Phase 24: Script 탭 → 하이브리드 채팅 AI
좌측 설정 사이드바+우측 채팅, POST /scripts/analyze-topic, load_full_inventory(), Chat UI 7종, useChatScriptEditor/useAutoScroll, SSE onNodeEvent 콜백. stale closure 수정, SSOT 언어 검증. 41파일. 코드 리뷰 7건 수정(SSE 에러 BLOCKER, topic min_length, structure 정규화, sendMessage 동시 요청 방지, character_name null, ChatMessage memo, topic_analysis 서비스 추출). 15테스트.

---

## 02-28 안정화 및 개선 작업

- **StyleProfile 5개 체제 정립 + 시리즈 정리**: Default Anime 제거→Flat Color 흡수, 5개 프로필 display_name(한국어) 부여, LoRA 소유권 SSOT 확립(style/detail→StyleProfile, character→Character), 전 캐릭터 style LoRA 제거(9건), add_detail 전 프로필 보조 적용, add_detail lora_type→detail, 시리즈 7→6개 정리(일상 공감 통합, 감성 한 스푼 신규), 시리즈명 콘텐츠 기반 리네이밍. LoRA 선택 가이드 문서 업데이트.
- **StyleProfile LoRA 레퍼런스 주입 + base_model 정규화**: _inject_loras_for_reference()에 StyleProfile LoRA 주입, quality_tags fallback 추가, REFERENCE_STYLE_LORA_SCALE 0.45 조정, _BaseModelNormMixin으로 6개 스키마 DRY 적용, 전 StyleProfile 네거티브 프롬프트/임베딩 업데이트, LoRA 선택 가이드 문서 신규 작성. 18테스트 PASS.
- **StyleProfile reference_env_tags / reference_camera_tags 추가**: StyleProfile에 JSONB 필드 2개 추가. ORM, StyleContext, V3PromptBuilder, preview.py, controlnet.py, schemas.py 수정. Alembic 마이그레이션 + 기존 5개 프로필 시딩. 테스트 4개 추가 (총 155개 통과). DB_SCHEMA.md 동기화.
- **Lab StyleProfile DB 파라미터 적용 수정**: `generate_image_with_v3()`에서 StyleProfile의 steps/cfg_scale/sampler_name/clip_skip이 무시되던 버그 수정. `override_settings`로 clip_skip 전달. preview.py 패턴 일관성 확보.
- **P0~P1 안정화**: P0-1 ActivityLog(기존 해결), P0-2 checksum 보완(`_link_media_asset`), P0-3 base_seed(기존 해결), P1-1 identity_score(정상 확인), P1-2 valence 시딩(startup 자동화). 테스트 오류 2건 수정(research tools 5→4, graph 18→19노드). 5파일.
- **characters.preview_locked 필드 제거**: 미사용 기능 전체 삭제. ORM 모델, 스키마 3곳, preview.py 가드, Frontend 타입/배지/필터, 테스트 fixtures, 문서 3종 정리. Alembic 마이그레이션 포함. 12파일.
- **GroupConfig를 Groups에 병합**: group_config 테이블 삭제, FK 3개+channel_dna를 groups 테이블에 통합. language/duration 제거. Alembic 마이그레이션+코드리뷰 완료. 25파일.
- **GroupConfig SD 생성 파라미터 4개 제거**: sd_steps, sd_cfg_scale, sd_sampler_name, sd_clip_skip 컬럼 삭제. StyleProfile이 SSOT이므로 GroupConfig의 informational 중복 제거.
- **GroupConfig structure 컬럼 제거**: 무의미한 structure 설정 제거 (Express→AI 자동, Standard→Script 탭). 13파일, Alembic 마이그레이션 포함.
- **FIX FIRST 1-1 보완: final_match_rate 기록**: Auto Edit 후 WD14 재검증으로 final_match_rate 측정·ActivityLog 저장.
- **Phase 17-3: 유저 UI 간소화**: Tooltip 시스템(10개 용어), Direct Advanced 토글, Publish Quick Render. 14파일 변경.
- **Phase 20-D: Script 탭 캐스팅 UX 잔여**: optgroup AI 추천 분리, Structure 추천 배지, inventory_resolve 매핑.
- **Phase 17-1 API prefix 오분류 수정**: service 엔드포인트 13개 ADMIN→API_BASE 전환. 9파일 수정.
- **Phase 17-2: Frontend Route Group 분리**: `(service)/` + `admin/` 2-tier 구조. ~70파일 이동.
