# Agent Spec — LangGraph 에이전트 아키텍처

**상태**: Active (v2.0)
**최종 업데이트**: 2026-02-27
**관련 문서**: `docs/01_product/FEATURES/AGENTIC_PIPELINE.md`

---

## 1. 에이전트 분류 체계

| 분류 | 조건 | 네이밍 규칙 | 예시 |
|------|------|------------|------|
| **AI Agent** | LLM(Gemini) 호출 + 자율 판단 | 역할형 (명사) | `critic`, `writer`, `cinematographer` |
| **Tool-Calling Agent** | LLM + Function Calling (도구 자율 선택) | 역할형 (명사) | `research`, `cinematographer` |
| **Hybrid** | 규칙 우선 + 조건부 LLM | 동작형 (동사) | `review`, `revise` |
| **System** | LLM 없음, 데이터 처리/체크포인트 | 동작형 (동사) | `finalize`, `learn`, `concept_gate` |

---

## 2. 에이전트 목록 (19개)

### 2-1. AI Agent (7개)

| # | 노드명 | 역할 | 입력 | 출력 | QC |
|---|--------|------|------|------|-----|
| 1 | `critic` | 3인 Architect 실시간 토론 (Phase 10-C-3). 독립 컨셉 → 상호 비평 → KPI 수렴 → Director 평가 | `topic`, `research_brief` | `critic_result`, `debate_log` | NarrativeScore 추정 + Hook 강도 + Groupthink 감지 |
| 2 | `writer` | 스크립트 작가. Full에서 Planning Step 추가 (Phase 10-A) | `topic`, `description`, `critic_result`, `revision_feedback` | `draft_scenes`, `writer_plan` | 없음 (review에 위임) |
| 3 | `director_checkpoint` | Review 통과 후 스크립트 품질 게이트. score(0.0-1.0) 기반 proceed/revise 결정. Score-based override: proceed+score<0.4→revise, revise+score≥0.85→proceed | `draft_scenes`, `review_result`, `director_plan` | `director_checkpoint_decision`, `director_checkpoint_score`, `director_checkpoint_feedback` | score 기반 자동 보정 |
| 4 | `tts_designer` | TTS 디자이너 — 씬별 음성 설계 | `cinematographer_result`, `critic_result` | `tts_designer_result` | `validate_tts_design()` + fallback |
| 5 | `sound_designer` | 사운드 디자이너 — BGM 방향성 추천 | `cinematographer_result`, `critic_result` | `sound_designer_result` | `validate_music()` + fallback |
| 6 | `copyright_reviewer` | 저작권 검토자 — IP 위험 검토 | `cinematographer_result` | `copyright_reviewer_result` | `validate_copyright()` + fallback PASS |
| 7 | `explain` | 창작 설명 — 파이프라인 결정을 한국어로 설명 (Full만) | 모든 production 결과 | `explanation_result` | 없음 (실패 시 None) |

### 2-2. Tool-Calling Agent (2개, Phase 10-B)

| # | 노드명 | 역할 | 도구 | 최대 호출 |
|---|--------|------|------|----------|
| 8 | `research` | Research Agent — Memory Store + 소재 분석 + 트렌딩 | `search_topic_history`, `search_character_history`, `fetch_url_content`, `analyze_trending` | 5회 |
| 9 | `cinematographer` | Cinematographer Agent — Danbooru 태그 검증 + 캐릭터 태그 + 호환성 체크 | `validate_danbooru_tag`, `get_character_visual_tags`, `check_tag_compatibility`, `search_similar_compositions` | 10회 |

### 2-3. Director Agent (1개, Phase 10-A ReAct + Phase 10-C-2 메시지)

| # | 노드명 | 역할 | 특수 기능 |
|---|--------|------|----------|
| 10 | `director` | Production chain 통합 검증. ReAct Loop (Observe→Think→Act) + Agent 간 메시지 기반 양방향 소통 | 최대 `LANGGRAPH_MAX_REACT_STEPS`(3) 스텝. revise 판정 시 타겟 에이전트 재실행 |

### 2-4. Hybrid (2개)

| # | 노드명 | 역할 | 전략 |
|---|--------|------|------|
| 11 | `review` | 3-tier 검증: 규칙 → Gemini 피드백 → 서사 품질(NarrativeScore). Phase 10-A: Self-Reflection | 규칙 → LLM (비용 절감) |
| 12 | `revise` | 수정. 규칙 기반 수정 → 복잡 오류는 Gemini 재생성 (Self-Reflection 활용) | 규칙 → LLM |

### 2-5. System (7개)

| # | 노드명 | 역할 | 동작 |
|---|--------|------|------|
| 13 | `director_plan` | Director 초기 목표 수립 (creative_goal, target_emotion, quality_criteria, risk_areas, style_direction). Gemini 호출. | 파이프라인 시작 시 실행 |
| 14 | `director_plan_gate` | 목표 수립에 대한 승인/반려 (Guided/Hands-on 모드) | `human_action` (승인/계획수정) |
| 15 | `inventory_resolve` | 에이전트 캐스팅 및 배경/음악 인벤토리 리졸버 | `director_plan` 확정 후 할당 |
| 16 | `concept_gate` | 컨셉 선택 게이트 (Guided/Hands-on 모드: `interrupt()`) | 선택/재생성/커스텀 컨셉 지원 |
| 17 | `human_gate` | 승인 게이트 — `interrupt()` 기반 사용자 대기 (Hands-on 전용) | 승인/수정 결정 → `human_action` |
| 18 | `finalize` | 최종화 — Production 결과 병합 | cinematographer + tts + sound + copyright → `final_scenes` |
| 19 | `learn` | 학습 — Memory Store 저장 | topic/character/user 히스토리 업데이트 |

---

## 3. Phase 10-A: True Agentic Architecture

### 3-1. Writer Planning Step

Full 모드에서 Writer가 대본 생성 전 계획 수립 (`LANGGRAPH_PLANNING_ENABLED=true`):

1. **Planning**: Gemini로 Hook 전략, 감정 곡선, 씬 배분 계획 생성 (`writer_planning.j2`)
2. **Generation**: 계획을 description에 주입하여 대본 생성

출력: `WriterPlan` (`hook_strategy`, `emotional_arc`, `scene_distribution`)

### 3-2. Director ReAct Loop

Production chain 완료 후 Director가 Observe→Think→Act 루프 수행:

```
for step in range(1, MAX_REACT_STEPS + 1):  # 최대 3 스텝
    observe: 현재 production 결과 분석
    think: 문제점/개선점 사고
    act: approve | revise_cinematographer | revise_tts | revise_sound | revise_script
```

각 스텝의 reasoning이 `director_reasoning_steps`에 기록.

### 3-3. Review Self-Reflection

Review 실패 시 Self-Reflection 수행 (`review_reflection.j2`):

```
근본 원인 → 영향 평가 → 수정 전략 → 기대 결과
```

Revise 노드가 `review_reflection`을 우선 참조하여 근본 원인 기반 수정.

---

## 4. Phase 10-B: Tool-Calling Agent

### 4-1. 인프라 (`services/agent/tools/base.py`)

Gemini Function Calling 기반 ReAct 루프:

```
LLM 호출 → tool_call 감지 → 도구 실행 → 결과 재주입 → 최종 응답까지 반복
```

- `define_tool()`: Gemini용 Tool 정의 헬퍼
- `call_with_tools()`: 비용 가드레일 내에서 LLM-도구 루프 실행
- `ToolCallLog`: 도구 호출 이력 기록 (tool_name, arguments, result, error)

### 4-2. Research Agent 도구 (`research_tools.py`)

| 도구 | 설명 | 소스 |
|------|------|------|
| `search_topic_history` | Memory Store 토픽 히스토리 검색 | Store namespace `(topic, hash)` |
| `search_character_history` | 캐릭터 생성 이력 검색 | Store namespace `(character, id)` |
| `fetch_url_content` | URL 콘텐츠 fetch (SSRF 방어 포함) | httpx + `_is_safe_url()` |
| `analyze_trending` | 트렌딩 키워드 분석 (placeholder) | 향후 외부 API 통합 예정 |

### 4-3. Cinematographer Agent 도구 (`cinematographer_tools.py`)

| 도구 | 설명 | 소스 |
|------|------|------|
| `validate_danbooru_tag` | 태그 유효성 검증 | `tags` 테이블 조회 |
| `get_character_visual_tags` | 캐릭터 비주얼 태그 조회 | `Character.tags` 관계 |
| `check_tag_compatibility` | 태그 충돌 검사 | `tag_rules` 테이블 |
| `search_similar_compositions` | 유사 구도 레퍼런스 검색 (placeholder) | 향후 `tag_effectiveness` 기반 |

---

## 5. Phase 10-C: Agent Communication

### 5-1. Message Protocol (`messages.py`)

```python
class AgentMessage(TypedDict):
    sender: str       # "director", "cinematographer" 등
    recipient: str
    content: str      # 자연어 메시지
    message_type: str # "feedback" | "request" | "suggestion" | "approval"
    metadata: dict | None
```

### 5-2. Director ↔ Agent 양방향 소통 (Phase 10-C-2)

Director가 revise 판정 시 `_agent_messaging.py`를 통해:
1. Director → Agent: `feedback` 타입 메시지 전송
2. Agent 재실행: `run_agent_with_message()` → 결과 업데이트
3. Agent → Director: `approval` 타입 응답 메시지

지원 타겟: `cinematographer`, `tts_designer`, `sound_designer`, `copyright_reviewer`

### 5-3. Critic Debate (Phase 10-C-3)

3인 Architect 실시간 토론 (`_debate_utils.py`):

1. **Round 1**: 독립 컨셉 생성 (emotional_arc, visual_hook, narrative_twist)
2. **Round 2+**: 상호 비평 + 컨셉 개선 (최대 `MAX_DEBATE_ROUNDS`)
3. **수렴 판단**: NarrativeScore ≥ 0.7 또는 Hook 강도 ≥ 0.6
4. **Groupthink 방지**: Jaccard 유사도 ≥ 0.85 감지 → 다양성 강제
5. **Hard Timeout**: `DEBATE_TIMEOUT_SEC`(60초) 초과 시 최선 선택
6. **Director 최종 평가**: 승리 컨셉 선정

### 5-4. State Condensation

`condense_messages()`: 슬라이딩 윈도우(최근 10개) + 오래된 메시지 요약.
`truncate_to_token_budget()`: 토큰 예산(2000) 내 텍스트 절단.

---

## 6. 그래프 구조

### 6-1. Interaction Mode: Express (단축 실행)

```
START → director_plan → inventory_resolve → writer → review → [revise] → finalize → learn → END
```

- Gemini 1회 호출 (~30초)
- Production chain 스킵 (`skip_stages` 활용)

### 6-2. Full 모드 (17노드, 병렬 실행)

```
START → director_plan → research → critic → concept_gate → writer → review → [revise] →
                                                ↑
                                     Creator: interrupt
                                     Full Auto: pass-through

                                        ┌→ tts_designer ────┐
director_checkpoint → cinematographer ──┤→ sound_designer ──┤→ director → [human_gate] →
                                        └→ copyright_reviewer┘

finalize → explain → learn → END
```

- Gemini 8-12회 호출 (~5-15분)
- **tts/sound/copyright 3개 노드 병렬 실행** (LangGraph fan-out/fan-in)
- Tool-Calling (Research 5회 + Cinematographer 10회)

### 6-3. 조건 분기 (라우팅)

| 분기점 | 함수 | 로직 |
|--------|------|------|
| START | `route_after_start` | quick → writer, full → director_plan |
| writer | `route_after_writer` | 에러 → finalize, 정상 → review |
| concept_gate | `route_after_concept_gate` | regenerate → critic, 기타 → writer |
| review | `route_after_review` | passed+full → director_checkpoint, passed+quick → finalize, failed → revise |
| director_checkpoint | `route_after_director_checkpoint` | proceed → cinematographer, revise → writer, max reached → cinematographer |
| cinematographer | `route_after_cinematographer` | 에러 → finalize, 정상 → 3개 병렬 fan-out |
| director | `route_after_director` | approve → human_gate/finalize, revise → 해당 노드 |
| human_gate | `route_after_human_gate` | approve → finalize, revise → revise |
| finalize | `route_after_finalize` | full → explain, quick → learn |

### 6-4. 병렬 실행 (Fan-Out/Fan-In)

cinematographer 이후 3개 노드 **동시 실행**:
- `tts_designer`, `sound_designer`, `copyright_reviewer`
- LangGraph가 3개 모두 완료될 때까지 `director` 실행을 자동 대기

### 6-5. Fallback 패턴

| 노드 | 실패 시 동작 | fallback 값 |
|------|-------------|------------|
| `cinematographer` | `error` 설정 → finalize short-circuit | (핵심 단계) |
| `tts_designer` | fallback 반환 | `{"tts_designs": []}` |
| `sound_designer` | fallback 반환 | `{"recommendation": {..., "mood": "neutral"}}` |
| `copyright_reviewer` | fallback PASS | `{"overall": "PASS", ...}` |

---

## 7. Director Agent 상세

### 7-1. ReAct Loop (Phase 10-A)

```
for step in 1..MAX_REACT_STEPS:
    observe → think → act
    ├─ approve → 즉시 종료
    └─ revise_* → 타겟 에이전트에 메시지 전송 (Phase 10-C-2)
                → 에이전트 재실행 → 응답 수집
                → 업데이트된 결과로 다음 스텝 계속
```

### 7-2. 의사결정 분기

| 판정 | 라우팅 |
|------|--------|
| `approve` + `auto_approve` | → finalize |
| `approve` + `!auto_approve` | → human_gate |
| `revise_cinematographer` | → cinematographer 재실행 |
| `revise_tts` | → tts_designer 재실행 |
| `revise_sound` | → sound_designer 재실행 |
| `revise_script` | → revise 노드 |
| revision_count >= MAX | → human_gate (강제 통과) |
| 에러 | → approve fallback |

### 7-3. 안전장치

- **최대 Director 재시도**: `LANGGRAPH_MAX_DIRECTOR_REVISIONS = 3`
- **최대 ReAct 스텝**: `LANGGRAPH_MAX_REACT_STEPS = 3`
- **에러 fallback**: Director 노드 실패 시 `approve` 반환

---

## 8. Error Short-Circuit 패턴

어떤 노드든 `error` 필드를 설정하면, 다음 분기점에서 즉시 `finalize`로 이동.

적용 위치: `route_after_writer`, `route_after_review`, `route_after_cinematographer`, `route_after_director`

---

## 9. QC 2계층

### Layer 1: 내부 QC (Production 노드별)

`run_production_step()` 내부: Gemini → JSON → QC → 재시도 (최대 `CREATIVE_PIPELINE_MAX_RETRIES`회)

| 노드 | QC 함수 | 검증 항목 |
|------|---------|----------|
| cinematographer | `validate_visuals()` | image_prompt 필수, 카메라 다양성, environment |
| tts_designer | `validate_tts_design()` | voice_design_prompt, pacing 범위 |
| sound_designer | `validate_music()` | prompt/mood/duration 필수 |
| copyright_reviewer | `validate_copyright()` | checks 상태 (FAIL 시 재시도) |

### Layer 2: 통합 QC (Director ReAct)

Production chain 완료 후 Director가 ReAct Loop로 수행:
- 시각-음성 일관성, BGM 적합도, 저작권 리스크, 전체 스토리 임팩트
- 문제 발견 시 타겟 에이전트에 메시지 전송 → 재실행

---

## 10. Observability (LangFuse)

`services/agent/observability.py`:

- **요청별 trace_id**: `contextvars.ContextVar`로 asyncio 태스크별 분리
- **trace_llm_call()**: Gemini 호출을 LangFuse GENERATION으로 추적
- **interrupt 기록**: `update_trace_on_interrupt()` — REST ingestion API 사용
- **비활성 시**: 완전 no-op (graceful degradation)

---

## 11. Persistence

### Checkpointer (`checkpointer.py`)

`AsyncPostgresSaver` 싱글턴 — LangGraph checkpoint 저장/복원.

### Memory Store (`store.py`)

`AsyncPostgresStore` 싱글턴 — 네임스페이스별 학습 데이터:
- `(topic, hash)`: 주제별 생성 이력 (최근 10건)
- `(character, id)`: 캐릭터 생성 횟수/최근 사용일
- `(user, preferences)`: 전역 통계 (총 생성/피드백 비율)

---

## 12. State 구조 (ScriptState)

```python
class ScriptState(TypedDict, total=False):
    # 입력 (StoryboardRequest 매핑)
    topic, description, duration, style, language, structure
    actor_a_gender, character_id, character_b_id, group_id
    references: list[str] | None  # 소재 URL/텍스트 목록

    # Graph 설정
    interaction_mode: str # "auto" | "guided" | "hands_on"
    skip_stages: list[str] | None
    auto_approve: bool

    # 중간 상태
    draft_scenes, draft_character_id, draft_character_b_id

    # Director Plan
    director_plan: DirectorPlan | None

    # Writer Planning (Phase 10-A)
    writer_plan: WriterPlan | None

    # Tool-Calling 로그 (Phase 10-B)
    research_tool_logs: list[dict] | None
    cinematographer_tool_logs: list[dict] | None

    # Critic 결과 + 토론 (Phase 10-C-3)
    critic_result, scene_reasoning
    debate_log: list[dict] | None

    # Concept Gate
    concept_action: str | None  # "select" | "regenerate"
    concept_regen_count: int

    # Revision 상태
    revision_count, revision_feedback

    # Human Gate
    human_action, human_feedback

    # Phase 2 Research & Learn
    research_brief, learn_result

    # Review + Self-Reflection (Phase 10-A)
    review_result: ReviewResult | None
    review_reflection: str | None

    # Production 결과 (Full)
    cinematographer_result, tts_designer_result
    sound_designer_result, copyright_reviewer_result

    # Director Checkpoint
    director_checkpoint_decision: str | None
    director_checkpoint_score: float | None
    director_checkpoint_feedback: str | None
    director_checkpoint_revision_count: int
    revision_history: list[dict] | None  # attempt, errors, reflection, score, tier

    # Director ReAct (Phase 10-A + Phase 10-C-2)
    director_decision, director_feedback, director_revision_count
    director_reasoning_steps: list[DirectorReActStep] | None

    # Agent Communication (Phase 10-C)
    agent_messages: list[dict] | None
    agent_summary: str | None

    # Explain + Final
    explanation_result, final_scenes, error
```

---

## 13. 설정 상수 (`config_pipelines.py`)

| 상수 | 기본값 | 용도 |
|------|--------|------|
| `LANGGRAPH_MAX_REVISIONS` | 3 | Review→Revise 루프 최대 |
| `LANGGRAPH_MAX_DIRECTOR_REVISIONS` | 3 | Director revision 최대 |
| `LANGGRAPH_MAX_REACT_STEPS` | 3 | Director ReAct 최대 스텝 |
| `LANGGRAPH_MAX_CONCEPT_REGEN` | 2 | Concept Gate 재생성 최대 |
| `MAX_TOOL_CALLS_PER_NODE` | 5 | 노드당 도구 호출 최대 |
| `MAX_DEBATE_ROUNDS` | 2 | Critic 토론 라운드 최대 |
| `DEBATE_TIMEOUT_SEC` | 60 | 토론 전체 타임아웃 |
| `CONVERGENCE_SCORE_THRESHOLD` | 0.7 | NarrativeScore 수렴 |
| `CONVERGENCE_HOOK_THRESHOLD` | 0.6 | Hook 강도 수렴 |
| `GROUPTHINK_SIMILARITY_THRESHOLD` | 0.85 | Groupthink 감지 |
| `LANGGRAPH_NARRATIVE_THRESHOLD` | 0.6 | 서사 품질 통과 기준 |
| `LANGGRAPH_MAX_CHECKPOINT_REVISIONS` | 3 | Director Checkpoint 재시도 최대 |
| `LANGGRAPH_CHECKPOINT_THRESHOLD` | 0.7 | Checkpoint 통과 기준 score |
| `LANGGRAPH_CHECKPOINT_LOW_THRESHOLD` | 0.4 | proceed override → revise |
| `LANGGRAPH_CHECKPOINT_HIGH_THRESHOLD` | 0.85 | revise override → proceed |
| `LANGGRAPH_PLANNING_ENABLED` | true | Writer Planning 활성화 |
| `LANGGRAPH_REFLECTION_ENABLED` | true | Self-Reflection 활성화 |

---

## 14. SSE 스트리밍 매핑

`routers/scripts.py`의 `_NODE_META`:

| 노드 | 라벨 | percent |
|------|------|---------|
| director_plan | 목표 수립 | 3 |
| research | 리서치 | 5 |
| critic | 컨셉 토론 | 15 |
| concept_gate | 컨셉 선택 | 25 |
| writer | 대본 생성 | 40 |
| review | 구조 검증 | 55 |
| revise | 수정 중 | 58 |
| director_checkpoint | 품질 게이트 | 57 |
| cinematographer | 비주얼 디자인 | 60 |
| tts_designer | 음성 디자인 | 75 |
| sound_designer | BGM 설계 | 75 |
| copyright_reviewer | 저작권 검토 | 75 |
| director | 통합 검증 | 90 |
| human_gate | 승인 대기 | 93 |
| finalize | 최종화 | 95 |
| explain | 결정 설명 | 98 |
| learn | 완료 | 100 |

---

## 15. 파일 구조

```
backend/services/agent/
├── __init__.py           # 공개 API (build_script_graph, ScriptState 등)
├── state.py              # ScriptState, ReviewResult, NarrativeScore 등 TypedDict
├── script_graph.py       # 21노드 StateGraph 구성 (병렬 fan-out)
├── routing.py            # 조건 분기 함수 (8개)
├── messages.py           # AgentMessage 프로토콜 + State Condensation
├── checkpointer.py       # AsyncPostgresSaver 싱글턴
├── store.py              # AsyncPostgresStore 싱글턴 (Memory)
├── feedback.py           # 피드백 Store 헬퍼
├── observability.py      # LangFuse 콜백 (trace_llm_call 등)
├── tools/
│   ├── __init__.py
│   ├── base.py           # Gemini Function Calling 인프라 (define_tool, call_with_tools)
│   ├── research_tools.py # Research Agent 도구 5개
│   └── cinematographer_tools.py # Cinematographer Agent 도구 4개
└── nodes/
    ├── director_plan.py      # [System] Director 초기 목표 수립 (Gemini 호출)
    ├── director_plan_gate.py # [System] 목표 생성 대기/승인
    ├── inventory_resolve.py  # [System] 인벤토리(캐릭터, 보이스 등) 에이전트 매핑
    ├── research.py           # [Tool-Calling] Memory + 소재 + 트렌딩 + DNA
    ├── critic.py             # [AI Agent] 3인 Architect 토론 (Phase 10-C-3)
    ├── concept_gate.py       # [System] 컨셉 선택 (interrupt / pass-through)
    ├── writer.py             # [AI Agent] 스크립트 작성 + Planning (Phase 10-A)
    ├── review.py             # [Hybrid] 3-tier 검증 + Self-Reflection (Phase 10-A)
    ├── revise.py             # [Hybrid] 규칙/재생성 수정
    ├── _revise_expand.py     # Revise 확장 로직
    ├── director_checkpoint.py # [AI Agent] Review 후 스크립트 품질 게이트
    ├── cinematographer.py    # [Tool-Calling] 비주얼 디자인 (Phase 10-B-3)
    ├── tts_designer.py       # [AI Agent] 음성 디자인
    ├── sound_designer.py     # [AI Agent] BGM 설계
    ├── copyright_reviewer.py # [AI Agent] 저작권 검토
    ├── director.py           # [AI Agent] ReAct Loop + 메시지 소통 (Phase 10-A/C)
    ├── human_gate.py         # [System] 승인 게이트
    ├── finalize.py           # [System] 결과 병합
    ├── explain.py            # [AI Agent] 창작 결정 설명
    ├── learn.py              # [System] Memory 저장
    ├── _production_utils.py  # 공통: Gemini + QC + 재시도
    ├── _debate_utils.py      # Critic 토론: 수렴/Groupthink 판단 (Phase 10-C-3)
    └── _agent_messaging.py   # Director ↔ Agent 메시지 라우팅 (Phase 10-C-2)
```

---

## 16. Script Generation Service

`services/script/gemini_generator.py` — Writer 노드가 호출하는 실제 대본 생성 로직:
캐릭터 컨텍스트 로드 → Multi-Character 감지 → Gemini 호출 (프리셋 템플릿 렌더, Safety Settings BLOCK_NONE) → 태그 파이프라인 (normalize → validate → filter → negative prompt) → Auto-Pin (공유 배경/환경 태그 오버랩) → Character Actions (`auto_populate_character_actions()`)
