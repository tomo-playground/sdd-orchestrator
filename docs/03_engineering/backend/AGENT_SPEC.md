# Agent Spec — LangGraph 에이전트 아키텍처

**상태**: Active (v1.0)
**최종 업데이트**: 2026-02-16
**관련 문서**: `docs/01_product/FEATURES/AGENTIC_PIPELINE.md` (마이그레이션 계획)

---

## 1. 에이전트 분류 체계

Agentic AI 기준으로 노드를 3종류로 분류한다.

| 분류 | 조건 | 네이밍 규칙 | 예시 |
|------|------|------------|------|
| **AI Agent** | LLM(Gemini) 호출 + 자율 판단 | 역할형 (명사) | `critic`, `writer`, `cinematographer` |
| **Hybrid** | 규칙 우선 + 조건부 LLM | 동작형 (동사) | `review`, `revise` |
| **System** | LLM 없음, 데이터 처리/체크포인트 | 동작형 (동사) | `research`, `finalize`, `learn` |

**근거**: AI Agent는 자율적 "역할"을 수행하므로 페르소나(역할형)로, System/Hybrid는 파이프라인 "동작"이므로 동작형으로 명명한다.

---

## 2. 에이전트 목록 (13개)

### 2-1. AI Agent (7개)

| # | 노드명 | 역할 | 입력 | 출력 | QC |
|---|--------|------|------|------|-----|
| 1 | `critic` | 컨셉 비평가 — 3인 Architect 병렬 → Devil's Advocate → Director 평가 | `topic`, `research_brief` | `critic_result` | 내부 (평가 점수 기반 승자 선정) |
| 2 | `writer` | 스크립트 작가 — Gemini로 초안 생성 | `topic`, `description`, `revision_feedback` | `draft_scenes`, `draft_character_id` | 없음 (review에 위임) |
| 3 | `cinematographer` | 촬영감독 — 비주얼 디자인 (Danbooru 태그, 카메라, 환경) | `draft_scenes`, 캐릭터 태그 | `cinematographer_result` | `validate_visuals()` + 재시도 |
| 4 | `tts_designer` | TTS 디자이너 — 씬별 음성 설계 (감정, 톤, 페이싱) | `cinematographer_result`, `critic_result` | `tts_designer_result` | `validate_tts_design()` + 재시도 |
| 5 | `sound_designer` | 사운드 디자이너 — BGM 방향성 추천 | `cinematographer_result`, `critic_result` | `sound_designer_result` | `validate_music()` + 재시도 |
| 6 | `copyright_reviewer` | 저작권 검토자 — IP 위험 검토 | `cinematographer_result` | `copyright_reviewer_result` | `validate_copyright()` + fallback PASS |
| 7 | `director` | 프로덕션 디렉터 — Production chain 결과 통합 검증 | 모든 production 결과 | `director_decision`, `director_feedback` | Gemini 통합 평가 |

### 2-2. Hybrid (2개)

| # | 노드명 | 역할 | 전략 |
|---|--------|------|------|
| 8 | `review` | 구조 검증 — 규칙 기반 검증 우선, 실패 시 Gemini 평가 | 규칙 → LLM (비용 절감) |
| 9 | `revise` | 수정 — 규칙 기반 수정 시도, 불가 시 Gemini 재생성 | 규칙 → LLM (단순 오류 즉시 수정) |

### 2-3. System (4개)

| # | 노드명 | 역할 | 동작 |
|---|--------|------|------|
| 10 | `research` | 리서치 — Memory Store 조회 | 캐릭터/주제/사용자 히스토리 검색 → `research_brief` |
| 11 | `human_gate` | 승인 게이트 — `interrupt()` 기반 사용자 대기 | 승인/수정 결정 → `human_action` |
| 12 | `finalize` | 최종화 — Production 결과 병합 | cinematographer + tts + sound + copyright → `final_scenes` |
| 13 | `learn` | 학습 — Memory Store 저장 | 생성 결과 + 히스토리 업데이트 |

---

## 3. Director Agent 상세

### 3-1. 역할

Production chain(cinematographer → tts → sound → copyright) 완료 후, 4개 결과를 **통합 검증**한다. 각 노드의 내부 QC가 개별 품질을 보장하지만, Director는 **전체 맥락에서의 조화**를 평가한다.

### 3-2. 입출력

**입력** (State에서 읽기):
- `cinematographer_result` — 비주얼 디자인 (씬별 태그, 카메라, 환경)
- `tts_designer_result` — 음성 디자인 (감정, 톤, 페이싱)
- `sound_designer_result` — BGM 설계 (프롬프트, 무드)
- `copyright_reviewer_result` — 저작권 검토 (PASS/FAIL)

**출력**:
- `director_decision`: `"approve"` | `"revise_cinematographer"` | `"revise_tts"` | `"revise_sound"` | `"revise_script"`
- `director_feedback`: 상세 피드백 문자열
- `director_revision_count`: 현재 횟수 + 1

### 3-3. 의사결정 분기

```
Director 평가
├─ approve → route_after_director
│  ├─ auto_approve=True  → finalize
│  └─ auto_approve=False → human_gate
├─ revise_* (revision_count < MAX) → 해당 노드로 돌아감
├─ revise_* (revision_count >= MAX) → human_gate (강제 통과)
└─ 에러 → approve fallback
```

### 3-4. 안전장치

- **최대 재시도**: `LANGGRAPH_MAX_DIRECTOR_REVISIONS = 1` (무한루프 방지)
- **에러 fallback**: Director 노드 실패 시 `approve` 반환 (파이프라인 중단 방지)

---

## 4. 그래프 구조

### 4-1. Quick 모드 (5노드)

```
START → writer → review → [revise] → finalize → learn → END
```

- Gemini 1회 호출 (~30초)
- Production chain 스킵

### 4-2. Full 모드 (13노드)

```
START → research → critic → writer → review → [revise] →
cinematographer → tts_designer → sound_designer → copyright_reviewer →
director → [human_gate] → finalize → learn → END
```

- Gemini 7-10회 호출 (~5-15분)
- Production chain + Director 통합 검증

### 4-3. 조건 분기 (라우팅)

| 분기점 | 함수 | 로직 |
|--------|------|------|
| START | `route_after_start` | quick → writer, full → research |
| writer | `route_after_writer` | 에러 → finalize, 정상 → review |
| review | `route_after_review` | passed → cinematographer/finalize, failed → revise |
| production chain | `route_production_step(next)` | 에러 → finalize, 정상 → next |
| copyright | `route_after_copyright` | 직접 → director |
| director | `route_after_director` | approve/revise/max_revision 분기 |
| human_gate | `route_after_human_gate` | approve → finalize, revise → revise |

---

## 5. Error Short-Circuit 패턴

어떤 노드든 `error` 필드를 설정하면, 다음 분기점에서 즉시 `finalize`로 이동한다.

```python
def _has_error(state: ScriptState) -> bool:
    return bool(state.get("error"))
```

**적용 위치**: `route_after_writer`, `route_after_review`, `route_production_step`, `route_after_director`

**효과**: 에러 발생 후 불필요한 Gemini API 호출 방지.

---

## 6. QC 2계층

### Layer 1: 내부 QC (Production 노드별)

`run_production_step()` 내부에서 수행:
1. Gemini 호출 → JSON 파싱
2. `validate_fn()` QC 검증
3. 실패 시 feedback 주입 → 재시도 (최대 `CREATIVE_PIPELINE_MAX_RETRIES`회)

| 노드 | QC 함수 | 검증 항목 |
|------|---------|----------|
| cinematographer | `validate_visuals()` | image_prompt 필수, 카메라 다양성, environment |
| tts_designer | `validate_tts_design()` | voice_design_prompt, pacing 범위 |
| sound_designer | `validate_music()` | prompt/mood/duration 필수 |
| copyright_reviewer | `validate_copyright()` | checks 상태 (FAIL 시 재시도) |

### Layer 2: 통합 QC (Director)

Production chain 완료 후 Director가 수행:
- 시각-음성 일관성
- BGM 적합도
- 저작권 리스크 종합
- 전체 스토리 임팩트

---

## 7. SSE 스트리밍 매핑

`routers/scripts.py`의 `_NODE_META`:

| 노드 | 라벨 | percent |
|------|------|---------|
| research | 리서치 | 5 |
| critic | 컨셉 토론 | 15 |
| writer | 대본 생성 | 40 |
| review | 구조 검증 | 55 |
| revise | 수정 중 | 58 |
| cinematographer | 비주얼 디자인 | 65 |
| tts_designer | 음성 디자인 | 75 |
| sound_designer | BGM 설계 | 82 |
| copyright_reviewer | 저작권 검토 | 88 |
| director | 통합 검증 | 92 |
| human_gate | 승인 대기 | 95 |
| finalize | 최종화 | 97 |
| learn | 완료 | 100 |

---

## 8. State 구조 (ScriptState)

```python
class ScriptState(TypedDict, total=False):
    # 입력 (StoryboardRequest 매핑)
    topic, description, duration, style, language, structure
    actor_a_gender, character_id, character_b_id, group_id

    # Graph 설정
    mode: str           # "quick" | "full"
    preset: str | None
    auto_approve: bool

    # 중간 상태
    draft_scenes: list[dict] | None
    draft_character_id: int | None
    draft_character_b_id: int | None

    # Critic 결과 (Full)
    critic_result: dict | None
    scene_reasoning: list[SceneReasoning] | None

    # Revision 상태
    revision_count: int
    revision_feedback: str | None

    # Human Gate 상태
    human_action: str | None    # "approve" | "revise"
    human_feedback: str | None

    # Phase 2
    research_brief: str | None
    learn_result: dict | None

    # Review 결과
    review_result: ReviewResult | None

    # Production 결과 (Full)
    cinematographer_result: dict | None
    tts_designer_result: dict | None
    sound_designer_result: dict | None
    copyright_reviewer_result: dict | None

    # Director 결과 (Full)
    director_decision: str | None
    director_feedback: str | None
    director_revision_count: int

    # 최종 출력
    final_scenes: list[dict] | None
    error: str | None
```

---

## 9. 파일 구조

```
backend/services/agent/
├── state.py              # ScriptState TypedDict
├── script_graph.py       # 13노드 StateGraph 구성
├── routing.py            # 조건 분기 함수
├── checkpointer.py       # AsyncPostgresSaver
├── store.py              # AsyncPostgresStore (Memory)
├── observability.py      # LangFuse 콜백
└── nodes/
    ├── research.py       # [System] Memory Store 조회
    ├── critic.py         # [AI Agent] 컨셉 비평
    ├── writer.py         # [AI Agent] 스크립트 작성
    ├── review.py         # [Hybrid] 구조 검증
    ├── revise.py         # [Hybrid] 수정
    ├── cinematographer.py # [AI Agent] 비주얼 디자인
    ├── tts_designer.py   # [AI Agent] 음성 디자인
    ├── sound_designer.py # [AI Agent] BGM 설계
    ├── copyright_reviewer.py # [AI Agent] 저작권 검토
    ├── director.py       # [AI Agent] 통합 검증
    ├── human_gate.py     # [System] 승인 게이트
    ├── finalize.py       # [System] 결과 병합
    ├── learn.py          # [System] Memory 저장
    └── _production_utils.py  # 공통: Gemini + QC + 재시도
```
