# Agent Enhancement Plan — 17개 에이전트 강화 분석

**상태**: Draft
**작성일**: 2026-02-20
**관련 문서**: `AGENT_SPEC.md`, `docs/01_product/FEATURES/AGENTIC_PIPELINE.md`

---

## 1. 현황 요약

17개 LangGraph 에이전트 전수 코드 분석 결과, **P1 28건 / P2 18건 / P3 10건**의 강화 항목을 도출했다.

### 1-1. 크로스 에이전트 구조 문제 (Top 5)

| # | 문제 | 영향 범위 | 근거 |
|---|------|----------|------|
| 1 | **Director Plan이 파이프라인에 흐르지 않음** | Research, Critic, Writer | `director_plan` state를 `director_checkpoint`만 읽음. 나머지 창작 노드에 미전달 |
| 2 | **Research → Critic 데이터 단절** | Critic 3인 Architect | `research_brief`(자유 문자열) vs `concept_architect.j2`(구조화 필드 기대). 항상 N/A 출력 |
| 3 | **`language` 필드 누락** (3개 노드 동일 버그) | tts_designer, sound_designer, copyright_reviewer | 템플릿 `{{ language }}` 사용하나 template_vars에 미전달 → 빈 문자열 |
| 4 | **예외 시 자동 통과** (품질 게이트 무력화) | director_checkpoint, director | 모든 예외 → `"proceed"` / `"approve"`. 네트워크 순단으로도 불량 통과 |
| 5 | **Learn 저장 데이터 빈약** (피드백 루프 무효) | learn → research (다음 생성 시) | 품질 점수, revision 횟수, hook 전략 미저장. Research가 품질 패턴 학습 불가 |

---

## 2. 에이전트별 강화 항목

### 2-1. Director Plan

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | Research/Critic/Writer에 plan 미전달 | 각 노드 프롬프트에 `creative_goal`, `quality_criteria` 주입 |
| P2 | `DirectorPlanOutput` 모든 필드 기본값 비어있어 검증 무의미 | `Field(min_length=...)` 추가 |
| P3 | topic과 creative_goal 연관성 미검증 | validate_fn에 topic 키워드 포함 체크 |

### 2-2. Research

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `analyze_trending` 도구가 완전한 placeholder (고정 문자열 반환) | 도구 목록에서 제거하거나 "미구현" 표시 |
| **P1** | `research_brief`가 비구조화 문자열 → Critic에서 파싱 불가 | JSON 형식 출력 강제 (`topic_summary`, `recommended_angle` 등) |
| P2 | Memory Store 결과가 `str(dict)` raw 문자열 | key-value 포매팅으로 LLM 파싱 가능하게 변환 |
| P3 | HTML 파싱이 nav/footer 포함 | `<article>`, `<main>` 태그 우선 추출 |

### 2-3. Critic

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `_parse_candidates`에서 arc/mood/pacing 전부 버림 | candidate dict에 원본 컨셉 전체 보존 |
| **P1** | `_estimate_narrative_score` → Round 1에서 즉시 수렴 가능 (임계값 0.7) | 0.7 → 0.85 상향 또는 최소 2라운드 강제 |
| P2 | Groupthink 감지 후 다양성 강제 지시 없음 | `critic_feedback`에 다양성 요구 메시지 추가 |
| P2 | Director 평가 시 `round_number=1` 고정 | 실제 라운드 번호 전달 |

### 2-4. Concept Gate

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `critic_result` None일 때 빈 interrupt 발생 | 명시적 에러 처리 또는 pass-through |
| P2 | `custom_concept` 입력 검증 없음 | `title`, `concept` 필드 존재 확인 |
| P3 | 재시도 한도 초과 시 정책 불투명 | 최고 점수 컨셉 자동 선택 |

### 2-5. Writer

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `WriterPlanOutput` 모든 필드 기본값 빈 값 → 빈 Plan 통과 | `hook_strategy: Field(min_length=10)`, `emotional_arc: min_length=2` |
| P2 | `emotional_arc`가 실제 씬 생성에 반영 안 됨 | `create_storyboard.j2`에 plan 섹션 명시적 주입 |
| P3 | `estimate_reading_duration`이 모든 씬 duration 덮어씀 | `lock_duration` 메타데이터 예외 처리 |

### 2-6. Review

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `script_image_sync` 가중치 5%로 너무 낮음 | 0.05 → 0.15 상향 (쇼츠에서 비주얼 동기화는 핵심) |
| P2 | Tier 2/Tier 3 중복 + Tier 2가 너무 단순 | Tier 3(NarrativeScore)로 일원화 |
| P2 | 동일 에러 반복 수정 시 메타 판단 없음 | `revision_history` 참조해서 반복 패턴 감지 |

### 2-7. Revise

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | Tier 1 placeholder `"1girl, solo"` 하드코딩 | state의 `style`, `actor_a_gender` 참조하여 동적 생성 |
| P2 | Tier 3 재생성 시 실패 원인이 description에 미반영 | `"[수정 N] 실패 원인: ..."` prefix 추가 |
| P2 | `revision_history` tier가 예외 시 `"pending"` 잔존 | finally 블록에서 `"error"`로 변경 |

### 2-8. Director Checkpoint

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | 예외 시 자동 `"proceed"` → 품질 게이트 무력화 | 1회 재시도 후 실패 시 `"revise"` 반환 |
| P2 | Director Plan 없을 때 평가 기준이 추상적 | fallback 기준(Hook, 감정곡선) 명시 |
| P3 | score만으로 override, MUST 조건 무시 | `quality_criteria`에서 필수 항목 추출 후 별도 체크 |

### 2-9. Cinematographer

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `search_similar_compositions`가 mood/scene_type 무시 (글로벌 top5만 반환) | DB 쿼리에 mood/scene_type 필터 추가 |
| **P1** | 동일 함수에서 `await` 누락 (AsyncSession 버그) | async/sync 분기 패턴 통일 |
| P2 | QC FAIL 결과를 그대로 통과 | FAIL 시 QC 피드백 포함 1회 재시도 |
| P3 | Tool 호출 한도 5회가 씬 수와 무관 | `min(10, len(scenes) * 2 + 3)` 동적 조정 |

### 2-10. TTS Designer

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `language` 미전달 (공통 버그) | `template_vars["language"]` 추가 |
| **P1** | fallback이 빈 배열 → TTS 생성 완전 건너뜀 | 씬 수만큼 neutral 기본값 생성 |
| P2 | speaker 정보 미활용 (화자별 목소리 특성 없음) | `character_id`, `actor_a_gender` 주입 |
| P3 | scene_id 연속성 미검증 | validate_tts_design에 씬 개수 일치 체크 |

### 2-11. Sound Designer

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `language` 미전달 (공통 버그) | `template_vars["language"]` 추가 |
| **P1** | `concept.mood_progression` 직접 접근 → Quick 모드에서 빈 값 | fallback 기본 mood 추출 로직 |
| P2 | fallback `prompt`가 빈 문자열 | 기본 프롬프트 설정 |
| P3 | 씬별 emotion → BGM 전환 정보 미제공 | `context_tags.emotion` 시간대별 힌트 추출 |

### 2-12. Copyright Reviewer

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | `language` 미전달 (공통 버그) | `template_vars["language"]` 추가 |
| **P1** | `overall` 필드를 LLM이 직접 작성 (checks와 불일치 가능) | 서버사이드에서 `checks` 기반 `overall` 재계산 |
| P2 | fallback이 `confidence: 0.0`의 PASS | `"SKIPPED"`로 변경 |
| P3 | 캐릭터 IP 검토에 실제 캐릭터 정보 없음 | `character_id` 기반 이름/원작 정보 주입 |

### 2-13. Director (ReAct)

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | 예외 시 자동 `"approve"` → 품질 게이트 무력화 | `"error"` 결정 도입 |
| **P1** | `revise_script` 선택 시 ReAct 루프 내 재실행 없음 | 루프 즉시 종료 → routing에서 writer로 전달 |
| P2 | 피드백 단순 덮어쓰기 (멀티스텝 누적 불가) | 스텝별 피드백 이력 리스트 유지 |
| P2 | `quality_criteria` 기준별 pass/fail 체크 없음 | 구조적 체크리스트 형식으로 LLM 응답 강제 |

### 2-14. Human Gate

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | interrupt 페이로드에 Director 판단 근거 미포함 | `director_decision`, `director_feedback`, `reasoning_steps` 추가 |
| P2 | action 유효성 검사 없음 | `VALID_ACTIONS = {"approve", "revise"}` 명시적 체크 |
| P3 | "전체 approve/revise" 이진 결정만 가능 | `revise_visual`, `revise_audio` 세밀한 action 추가 |

### 2-15. Finalize

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | sound/copyright가 첫 번째 씬에 `_` prefix 임시 구조 | 별도 state 필드로 분리 |
| **P1** | TTS 씬 수 불일치 시 묵시적 누락 | 불일치 감지 + WARNING 로깅 |
| P2 | `dict(s)` 얕은 복사로 원본 오염 가능 | `copy.deepcopy` 적용 |
| P3 | negative_prompt가 스타일 무관 단일 상수 | `state.get("style")` 기반 분기 |

### 2-16. Explain

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | validate_fn이 항상 통과 (필드 검증 없음) | `ExplainOutput` Pydantic 모델 추가 |
| **P1** | `director_reasoning_steps`, `writer_plan`, `director_plan` 미포함 | template_vars에 추가 |
| P2 | Frontend에서 explanation 결과 미사용 (LLM 비용만 소비) | UI 렌더링 연결 또는 노드 비활성화 |

### 2-17. Learn

| 우선순위 | 문제 | 강화 방안 |
|---------|------|----------|
| **P1** | 품질 메트릭 미저장 (score, revision_count 등) | `quality_score`, `narrative_score`, `hook_strategy` 추가 |
| **P1** | `_topic_key()` 함수 중복 정의 (learn.py + research_tools.py) | 공통 모듈로 추출 |
| **P1** | `character_b_id` 미저장 | `_update_character(store, character_b_id)` 추가 |
| P2 | scene 요약에 image_prompt 미포함 | 시각 정보 30자 truncate 포함 |

---

## 3. Gemini 모델 업그레이드 분석

### 3-1. 현재 모델 현황

모든 17개 노드가 **`gemini-2.5-flash`** 사용 중.

| 환경변수 | 기본값 | 사용 노드 |
|---------|--------|----------|
| `GEMINI_TEXT_MODEL` | `gemini-2.5-flash` | Writer, Director, Cinematographer, Research, Review, Revise 등 14개 |
| `CREATIVE_LEADER_MODEL` | `gemini-2.5-flash` | Critic (Architect 3인 + Devil's Advocate + Creative Director) |

### 3-2. 업그레이드 추천

#### Pro 업그레이드 강력 추천 (3개)

| 노드 | 이유 | 최대 호출 수 | 비용 증가 |
|------|------|------------|----------|
| **Critic** | 3관점 독립 컨셉 생성 + 상호 비평 — Flash의 창의적 다양성 부족으로 Groupthink 빈발, Round 1 즉시 수렴 | 8회 | 중 |
| **Director** | 4개 Production 결과 교차 판단 — cinematographer/tts/sound/copyright 복합 품질 문제 감지 필요 | 3회 | 소 |
| **Review (Tier 3)** | 5차원 NarrativeScore 가중 평가 + Self-Reflection 근본 원인 분석 | 2회 | 소 |

#### Pro 업그레이드 검토 권장 (3개)

| 노드 | 이유 | 조건 |
|------|------|------|
| Writer (Planning만) | Hook 전략 수립의 전략적 깊이 | 노드 내 모델 분리 인프라 필요 |
| Director Plan | `quality_criteria` 구체성, `risk_areas` 예측 | 데이터 흐름 문제(P1) 먼저 해결 후 재평가 |
| Director Checkpoint | score-decision 불일치 보정 빈도가 Flash 한계 시사 | 1회 호출이라 비용 무시 가능 |

#### Flash 유지 적합 (11개)

| 노드 | 이유 |
|------|------|
| Research | Tool 선택 판단은 Flash 충분. 문제는 코드 버그 |
| Cinematographer | 도메인 지식은 DB 도구가 제공. 모델보다 도구 품질이 핵심 |
| Revise | Review 피드백 품질이 더 중요 |
| TTS Designer | 단순 태스크. 문제는 `language` 미전달 버그 |
| Sound Designer | 단일 JSON 응답. Flash 충분 |
| Copyright Reviewer | LLM 기반 저작권 검토의 근본적 한계 (모델 업그레이드로 해결 불가) |
| Concept Gate | LLM 미사용 |
| Human Gate | LLM 미사용 |
| Finalize | LLM 미사용 |
| Explain | Frontend에서 미사용 상태 (비용 대비 효과 없음) |
| Learn | LLM 미사용 |

### 3-3. 구현 방안

**Phase 1: 환경변수 분리**

```python
# config_pipelines.py 확장
CREATIVE_LEADER_MODEL = os.getenv("CREATIVE_LEADER_MODEL", "gemini-2.5-pro")
DIRECTOR_MODEL = os.getenv("DIRECTOR_MODEL", "gemini-2.5-pro")
REVIEW_MODEL = os.getenv("REVIEW_MODEL", "gemini-2.5-pro")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
```

**Phase 2: 성과 측정 메트릭**

| 노드 | 측정 항목 |
|------|----------|
| Critic | Groupthink 빈도, 컨셉 다양성 점수, 토론 라운드 수 |
| Director | revise 판정 정확도, QC 통과율 |
| Review | NarrativeScore 분포, Self-Reflection → Revise 성공률 |

---

## 4. AI 뮤직 파이프라인 현황 분석

### 4-1. 현재 상태

Sound Designer 에이전트가 생성하는 BGM 프롬프트가 **실제 음악 생성까지 이어지지 않는** 상태.

```
Sound Designer → prompt 생성 → finalize(씬 메타데이터) → 스냅샷 저장 → 끝 ❌
                                                                    ↓
                                                          렌더링 파이프라인에서 무시
```

### 4-2. 구성 요소별 구현 상태

| 항목 | 상태 | 위치 |
|------|------|------|
| Sound Designer 프롬프트 생성 | **완성** | `nodes/sound_designer.py` |
| Stable Audio Open 연동 | **완성** | `services/audio/music_generator.py` |
| Music Preset CRUD + 미리보기 | **완성** | `routers/music_presets.py` |
| MusicPreset DB 모델 | **완성** | `models/music_preset.py` |
| 렌더링 BGM 합성 (FFmpeg) | **완성** | `services/video/effects.py` |
| Frontend BGM 선택 UI | **완성** | `components/video/BgmSection.tsx` |
| **프롬프트 → 자동 음악 생성 연결** | **미구현** | — |
| **sound_recommendation → 렌더링 연결** | **미구현** | — |

### 4-3. 단절 지점

**경로 A (현재)**: 프롬프트만 생성, 활용 안 됨

```
Sound Designer 노드
  → sound_designer_result.recommendation.prompt
  → finalize: scenes[0]["_sound_recommendation"] (메타데이터)
  → API 응답 production_snapshot에 포함 (표시용)
  → DB 저장 안 됨
  → 렌더링 파이프라인 무시
```

**경로 B (수동)**: 사용자가 직접 Music Preset 선택 시에만 작동

```
사용자: BgmSection UI에서 music_preset_id 선택
  → VideoRequest.bgm_mode="ai", music_preset_id=N
  → builder._prepare_bgm(): MusicPreset 조회 → generate_music() 실행
  → ai_bgm.wav 생성 → FFmpeg 합성
```

### 4-4. 개선 방안

### 4-4. 설계: Sound Designer 기반 BGM 전면 교체

**결정**: Sound Designer 프롬프트를 BGM의 SSOT로 삼고, 렌더링 시 자동 적용.

#### 전체 흐름 (목표 상태)

```
[대본 생성 파이프라인]
Sound Designer 노드
  → recommendation: { prompt, mood, duration }
  → Finalize 노드: 별도 state 필드로 저장 (씬 메타데이터 X)
  → Storyboard DB에 bgm_prompt, bgm_mood 저장

[렌더링 파이프라인]
VideoBuilder._prepare_bgm()
  → bgm_mode == "auto" 감지
  → Storyboard의 bgm_prompt 조회
  → SHA256 캐시 확인 (hit → 재사용)
  → cache miss → generate_music(prompt, duration) 호출
  → bgm_asset_id에 MediaAsset FK 저장
  → FFmpeg apply_bgm() → 영상에 합성

[Frontend]
PublishTab
  → bgm_mode 기본값: "auto" (Sound Designer 추천)
  → ProductionSections에 프롬프트 + 미리듣기 표시
  → 사용자가 원하면 "file" / "ai"(수동 preset)로 오버라이드
```

#### 변경 대상

| 레이어 | 파일 | 변경 내용 |
|--------|------|----------|
| **DB** | `models/storyboard.py` | `bgm_prompt: str \| None`, `bgm_mood: str \| None`, `bgm_asset_id: int \| None` (FK) |
| **DB** | Alembic 마이그레이션 | 3개 컬럼 추가 |
| **Backend** | `nodes/finalize.py` | `sound_recommendation` → 별도 state 필드 반환 (씬 외부) |
| **Backend** | `routers/scripts.py` | Storyboard 저장 시 `bgm_prompt`, `bgm_mood` 기록 |
| **Backend** | `schemas.py` | `VideoRequest.bgm_mode`에 `"auto"` 추가 |
| **Backend** | `services/video/builder.py` | `_prepare_bgm()`: auto 모드 → Storyboard bgm_prompt로 직접 생성 |
| **Frontend** | `useRenderStore.ts` | `bgmMode` 기본값 `"file"` → `"auto"` |
| **Frontend** | `PublishTab.tsx` | BGM 모드 3종 (Auto / AI Preset / File) |
| **Frontend** | `ProductionSections.tsx` | Sound Designer 프롬프트 + mood 표시, 미리듣기 버튼 |

#### 기존 시스템과의 호환

| 기존 기능 | 처리 방안 |
|----------|----------|
| `bgm_mode: "file"` | 그대로 유지 (파일 BGM) |
| `bgm_mode: "ai"` + `music_preset_id` | 그대로 유지 (수동 Preset 선택) |
| Music Preset CRUD | 유지 (수동 관리용) |
| `bgm_mode: "auto"` (신규) | Sound Designer 프롬프트 자동 적용, Storyboard에 저장된 프롬프트 사용 |

#### GPU 리소스 전략

| 시나리오 | 대응 |
|---------|------|
| SD WebUI + SAO 동시 실행 | SAO는 CPU fallback 지원 (`SAO_DEVICE=cpu`). 이미지 생성 후 BGM 생성 순서 보장 |
| 캐시 히트 | SHA256 캐시 재사용 (generate_music 내장). 동일 프롬프트 재생성 방지 |
| 첫 생성 지연 (~30초) | 렌더링 중 BGM 생성이므로 사용자 대기 시간에 포함. SSE 진행률에 "BGM 생성 중" 단계 추가 |

### 4-5. 검토 필요 사항

| 항목 | 질문 | 비고 |
|------|------|------|
| 생성 품질 | Stable Audio Open 30초 BGM 품질이 쇼츠에 적합한가? | 실제 테스트 필요 |
| 저작권 | AI 생성 음악 상업적 사용 가능 여부 | SAO 라이선스 확인 |
| 프롬프트 수정 UX | 사용자가 Sound Designer 프롬프트를 직접 편집할 수 있어야 하는가? | ProductionSections에서 인라인 편집 검토 |
| 외부 서비스 대안 | Suno/Udio API 비교 검토 필요한가? | 로컬 GPU 대비 클라우드 트레이드오프 |

---

## 5. Phase 12 실행 순서

### Phase 12-A: Agent Bug Fixes (5건)

즉시 수정 가능. 의존성 없음.

| # | 항목 | 예상 작업량 |
|---|------|-----------|
| 1 | `language` 필드 3개 노드 일괄 추가 | 3줄 × 3파일 |
| 2 | `_topic_key()` 중복 제거 | 공통 모듈 추출 |
| 3 | Cinematographer `search_similar_compositions` await 누락 | 1줄 |
| 4 | Copyright Reviewer `overall` 서버사이드 재계산 | ~10줄 |
| 5 | Learn `character_b_id` 저장 추가 | 1줄 |

### Phase 12-B: Agent Data Flow (10건)

12-A 완료 후 착수. 파이프라인 품질에 가장 큰 임팩트.

| # | 항목 | 영향 |
|---|------|------|
| 1 | Director Plan → 전체 파이프라인 주입 | 창작 방향이 실제로 흐르게 |
| 2 | Research → Critic 데이터 구조화 | Research 결과가 토론에 반영 |
| 3 | 예외 시 자동 통과 제거 (2개 노드) | 품질 게이트 무력화 방지 |
| 4 | Learn 저장 데이터 확충 | 피드백 루프 실효성 확보 |
| 5 | Critic 컨셉 정보 보존 + 수렴 재조정 | 토론 품질 향상 |
| 6 | Revise placeholder 개선 | 스타일/성별 맞는 기본 태그 |
| 7 | Review script_image_sync 가중치 상향 | 비주얼 동기화 품질 |
| 8 | Finalize 메타데이터 구조 분리 | 12-C 전제 조건 |
| 9 | Human Gate Director 판단 근거 포함 | 사용자 UX |
| 10 | Explain 검증 + 컨텍스트 추가 | LLM 비용 정당화 |

### Phase 12-C: AI BGM Pipeline — 하이브리드 (9건)

12-B의 #8(Finalize 구조 분리) 완료 후 착수. #7~9는 #1~6 완성 후 진행.

**설계**: Sound Designer 자동 + 경량 즐겨찾기. 기존 File BGM + Music Preset 제거.

| # | 항목 | 의존성 |
|---|------|--------|
| 1 | Storyboard `bgm_prompt` + `bgm_seed` + `bgm_asset_id` + Alembic | — |
| 2 | `bgm_favorites` 경량 테이블 + CRUD API (name, prompt, group_id) | — |
| 3 | Finalize → BGM 프롬프트 자동 저장 | 12-B #8, #1 |
| 4 | `_prepare_bgm()` 단순화 (모드 분기 제거, bgm_prompt 직접 생성) | #1, #3 |
| 5 | ProductionSections BGM UI (프롬프트 편집 + 미리듣기 + 즐겨찾기) | #3 |
| 6 | BGM 캐싱 + bgm_asset_id FK | #4 |
| 7 | File BGM 전체 제거 (resolve_bgm_file, /audio/list, MP3 파일) | #1~6 완성 |
| 8 | Music Preset 시스템 제거 (테이블, 라우터, /music 페이지, useMusic) | #7 |
| 9 | DB 마이그레이션 정리 (bgm_file, bgm_mode, music_preset_id 제거) | #8 |

### Phase 12-D: Gemini Model Upgrade (5건)

12-B와 독립적으로 진행 가능.

| # | 항목 | 비용 영향 |
|---|------|----------|
| 1 | config_pipelines.py 모델 변수 분리 | 없음 |
| 2 | Critic → `gemini-2.5-pro` | 8회 호출 (중) |
| 3 | Director → `gemini-2.5-pro` | 3회 호출 (소) |
| 4 | Review (Tier 3) → `gemini-2.5-pro` | 2회 호출 (소) |
| 5 | 성과 측정 메트릭 수집 | 없음 |
