# Phase 12: Agent Enhancement & AI BGM (완료 02-20)

**목표**: 17개 에이전트 품질 강화 + Sound Designer 기반 AI BGM 자동 파이프라인 구축.
**설계 문서**: `docs/03_engineering/backend/AGENT_ENHANCEMENT.md`

## 12-A: Agent Bug Fixes (5건)

| # | 항목 | 영향 노드 | 상태 |
|---|------|----------|------|
| 1 | [x] `language` 필드 template_vars 추가 (3개 노드 동일 버그) | tts_designer, sound_designer, copyright_reviewer | 02-20 |
| 2 | [x] `_topic_key()` 중복 제거 → 공통 모듈 추출 | learn, research, research_tools | 02-20 |
| 3 | [x] Cinematographer `search_similar_compositions` await 누락 | cinematographer | 02-20 |
| 4 | [x] Copyright Reviewer `overall` 서버사이드 재계산 | copyright_reviewer | 02-20 |
| 5 | [x] Learn `character_b_id` 저장 추가 | learn | 02-20 |

## 12-B: Agent Data Flow (10건)

| # | 항목 | 상세 | 상태 |
|---|------|------|------|
| 1 | [x] Director Plan → 전체 파이프라인 주입 | Research/Critic/Writer 프롬프트에 `creative_goal`, `quality_criteria` 주입 | 02-20 |
| 2 | [x] Research → Critic 데이터 구조화 | `research_brief` JSON 형식 강제 + Critic 템플릿 연결 | 02-20 |
| 3 | [x] 예외 시 자동 통과 제거 (2개 노드) | director_checkpoint, director → `"error"` 결정 도입 | 02-20 |
| 4 | [x] Learn 저장 데이터 확충 | `quality_score`, `narrative_score`, `hook_strategy`, `revision_count` 추가 | 02-20 |
| 5 | [x] Critic 컨셉 정보 손실 방지 | `_parse_candidates`에서 arc/mood/pacing 원본 보존 | 02-20 |
| 6 | [x] Critic 수렴 임계값 재조정 | Round 1 즉시 수렴 방지 (0.7 → 0.85), 최소 2라운드 강제 | 02-20 |
| 7 | [x] Revise Tier 1 placeholder 개선 | `"1girl, solo"` → state의 style/gender 참조 동적 생성 | 02-20 |
| 8 | [x] Review `script_image_sync` 가중치 상향 | 0.05 → 0.15 (쇼츠 비주얼 동기화 핵심) | 02-20 |
| 9 | [x] Finalize 메타데이터 구조 분리 | sound/copyright → 씬 외부 별도 state 필드 | 02-20 |
| 10 | [x] Human Gate 인터럽트에 Director 판단 근거 포함 | `director_decision`, `director_feedback`, `reasoning_steps` | 02-20 |

## 12-C: AI BGM Pipeline (6건)

Sound Designer 추천 → DB 저장 → 렌더링 자동 적용. `bgm_mode` 3종: `"file"`, `"ai"`, `"auto"`.

| # | 항목 | 상세 | 상태 |
|---|------|------|------|
| 1 | [x] Storyboard `bgm_prompt` + `bgm_mood` + `bgm_audio_asset_id` | Sound Designer 결과 DB 저장 (Alembic) | 02-20 |
| 2 | [x] Backend 스키마 확장 | VideoRequest bgm_mode "auto", StoryboardSave/DetailResponse bgm 필드 | 02-20 |
| 3 | [x] Storyboard CRUD 연동 | save/update에서 bgm 저장, prompt 변경 시 캐시 무효화 | 02-20 |
| 4 | [x] `_prepare_bgm()` auto 모드 | 3-mode 디스패치, DB 캐시 체크, generate_music(), asset 캐싱 | 02-20 |
| 5 | [x] BgmSection 3-Mode UI | File/AI/Auto 탭, 인라인 편집, 미리듣기 | 02-20 |
| 6 | [x] "BGM 적용" 버튼 (ProductionSections) | Sound Designer 추천 → RenderStore auto 모드 전환 | 02-20 |

## 12-D: Gemini Model Upgrade (5건)

| # | 항목 | 상세 | 상태 |
|---|------|------|------|
| 1 | [x] config_pipelines.py 모델 변수 분리 | `DIRECTOR_MODEL`, `REVIEW_MODEL` 추가 | 02-20 |
| 2 | [x] Critic → `gemini-2.5-pro` | 3인 Architect 창의적 다양성 + 컨셉 차별화 | 02-20 |
| 3 | [x] Director → `gemini-2.5-pro` | 4개 Production 결과 교차 판단 | 02-20 |
| 4 | [x] Review (Tier 3) → `gemini-2.5-pro` | 5차원 NarrativeScore + Self-Reflection | 02-20 |
| 5 | [x] 성과 측정 메트릭 수집 | Groupthink 빈도, NarrativeScore 분포, revise 정확도 | 02-20 |

---

# Phase 13: Creative Control & Production Speed (완료 02-20)

**목표**: 이미지 자연어 편집, 실시간 진행률, Structure별 최적 템플릿, 장면별 의상 변경으로 창작 유연성과 속도 대폭 향상.

## 13-A: Performance Quick Wins (5건)

| # | 항목 | 상태 |
|---|------|------|
| 1 | [x] Research URL fetch `asyncio.gather` 병렬화 | 02-20 |
| 2 | [x] Studio 캐릭터/스타일 `Promise.allSettled` 병렬 로드 | 02-20 |
| 3 | [x] Review Gemini `asyncio.gather` 평가 최적화 | 02-20 |
| 4 | [x] Critic 씬 배치 처리 (전체 씬 한 번에 평가) | 02-20 |
| 5 | [x] SSE 렌더링 예상 시간 (`estimate_remaining()` + stage 이력 학습) | 02-20 |

## 13-B: Image Generation UX (5건)

| # | 항목 | 상태 |
|---|------|------|
| 1 | [x] 이미지 생성 Progress SSE + SD WebUI `/progress` 프리뷰 | 02-20 |
| 2 | [x] Frontend Progress UI (진행률 바 + 프리뷰 이미지) | 02-20 |
| 3 | [x] Scene 자연어 이미지 편집 API (`POST /scenes/{id}/edit-image`) | 02-20 |
| 4 | [x] SceneEditImageModal (자연어 입력 + 전/후 비교) | 02-20 |
| 5 | [x] Batch 생성 개별 취소 (`POST /scene/cancel/{task_id}`) | 02-20 |

## 13-C: Structure별 Gemini 템플릿 (6건)

| # | 항목 | 상태 |
|---|------|------|
| 1 | [x] Monologue 전용 J2 템플릿 (감정 흐름, 클로즈업 중심) | 02-20 |
| 2 | [x] Dialogue 전용 J2 템플릿 (화자 전환, 리액션 샷) | 02-20 |
| 3 | [x] Narrated Dialogue 전용 J2 템플릿 (시점 전환) | 02-20 |
| 4 | [x] Confession/Lesson 전용 J2 템플릿 (회상, 교훈) | 02-20 |
| 5 | [x] Structure → 템플릿 자동 매핑 (presets.py 디스패치) | 02-20 |
| 6 | [x] Danbooru 허용 태그 카테고리별 동적 삽입 | 02-20 |

## 13-D: Scene Clothing Override (3건)

| # | 항목 | 상태 |
|---|------|------|
| 1 | [x] Scene `clothing_tags` JSONB 필드 + Alembic 마이그레이션 | 02-20 |
| 2 | [x] 12-Layer Builder `_apply_clothing_override()` 반영 | 02-20 |
| 3 | [x] SceneClothingModal UI (태그 입력 + 프리셋 + 리셋) | 02-20 |
