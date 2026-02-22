# Agentic AI Pipeline & True Agentic Architecture

**상태**: **완료/안정** (Phase 9~10 기반 + Phase 11~13 고도화 완료, 2026-02-22)
**관련**: [AGENT_SPEC.md](../../03_engineering/backend/AGENT_SPEC.md), [SCRIPT_QUALITY_UX.md](SCRIPT_QUALITY_UX.md)

---

## 1. 배경

### 1-1. 전환 전 문제점

| 문제 | 설명 |
|------|------|
| **단일 호출** | `Topic → Jinja2 → Gemini 1회 → JSON → 끝`. 반복 개선 루프 없음 |
| **이원화** | Script Generation(`/scripts/generate`)과 Creative Lab(`/lab/creative/...`)이 같은 목적, 다른 코드 |
| **메모리 부재** | 세션 간 학습 없음, 사용자 선호 미기억 |
| **DAG Workflow** | LangGraph 사용하지만 실질 패턴은 "State Machine 기반 DAG". 제어 흐름은 하드코딩 Python 로직 |

### 1-2. 전환 목표: Agentic AI 5대 요건

```
단순 LLM 호출  <  Chain/Pipeline  <  DAG Workflow  <  Router Agent  <  ReAct Agent  <  Multi-Agent
                                     [전환 전]                         [달성 (Phase 10)]
```

| # | 요건 | 전환 전 | 전환 후 |
|---|------|--------|--------|
| 1 | **자율적 의사결정** | `routing.py`의 if/else | Director ReAct Loop (Observe→Think→Act) |
| 2 | **Tool Use** | 항상 같은 함수 호출 | Gemini Function Calling (Research 5도구, Cinematographer 4도구) |
| 3 | **Planning** | 그래프 토폴로지 = 고정 계획 | Writer Planning Step (계획→생성 2-step) |
| 4 | **Self-Reflection** | Review/Director는 외부 검증만 | Review Self-Reflection (실패 원인 분석 + 수정 전략) |
| 5 | **에이전트 소통** | 공유 state dict 단방향 | Agent Message Protocol + Director↔Production 양방향 + Critic 토론 |

---

## 2. 아키텍처

### 2-1. 기술 스택

| 컴포넌트 | 선택 | 비고 |
|----------|------|------|
| **워크플로우** | LangGraph (`langgraph` + `langchain-core`) | 풀 LangChain 불필요 |
| **LLM** | Gemini — 기존 `google-genai` 유지 | 노드에서 래핑, LangChain wrapper 불필요 |
| **Checkpointer** | `AsyncPostgresSaver` (psycopg v3) | 기존 PostgreSQL, `setup()` 자동 테이블 |
| **Memory** | `AsyncPostgresStore` | 키-값 장기 메모리 |
| **Observability** | LangFuse v3 (셀프호스팅 Docker) | PostgreSQL + ClickHouse + Redis + MinIO |
| **Frontend** | SSE (`astream` → SSE) | 기존 패턴 재활용, Human Gate는 POST resume |

### 2-2. 제어 스펙트럼 (Control Spectrum)

사용자가 **AI 개입 수준을 선택**하는 유연한 파이프라인:

| Preset | `skip_stages` | 설명 |
|--------|---------------|------|
| **express** | `["research", "concept", "production", "explain"]` | Gemini 1회 생성 후 즉시 검토 (가장 빠름) |
| **standard** | `["research", "explain"]` | Concept Gate 생략, Production(이미지/음성) 자동 실행 |
| **creator** | `[]` (빈 배열) | Research부터 Explain까지 모든 디테일 제어 및 Human Gate 개입 |

> 이전의 "Quick", "Full" 모드 이원화는 폐기되었으며, 현재는 **Stage-Level Skip (`skip_stages`) 통합 아키텍처**로 단일화되었습니다.

### 2-3. 17-노드 그래프 구조

전체 그래프 경로는 `skip_stages` 값에 따라 유동적으로 단축됩니다:
```
START → director_plan → Research → Critic → concept_gate → Writer → Review → [Revise]
  → director_checkpoint(score-based) → Cinematographer | TTS | Sound | Copyright
  → Director(ReAct) → [human_gate] → Finalize → Explain → Learn → END
```

* `skip_stages`에 포함된 단계(예: `"research"`, `"concept"`, `"production"`, `"explain"`)는 Graph 내의 `_skip_guard` 노드를 통해 자동으로 통과(Pass-through)됩니다.

| 분류 | 에이전트 | Agentic 레벨 |
|------|---------|-------------|
| AI Agent | Writer, Critic, Review, Director, Research, Cinematographer, Explain, **director_checkpoint** | ReAct/Tool-Calling |
| Hybrid | Human Gate, Concept Gate | AI + Human interrupt |
| System | Finalize, Learn, TTS Designer, Sound Designer, Copyright Reviewer, **director_plan** | 규칙 기반 |

### 2-4. Director-as-Orchestrator (2026-02-19)

| 노드 | 역할 | 핵심 |
|------|------|------|
| **director_plan** | 초기 목표 수립 | creative_goal, target_emotion, quality_criteria, risk_areas, style_direction |
| **director_checkpoint** | Production 진입 전 품질 게이트 | score(0.0~1.0) 기반 proceed/revise 판정 |

**Score-Based Routing** (director_checkpoint):
- `score < 0.4` + "proceed" → **override to "revise"** (safety net)
- `score >= 0.85` + "revise" → **override to "proceed"** (불필요한 재생성 방지)
- 중간 범위: Director 판단 존중

**Revision History**: `revision_history` 필드에 attempt/errors/reflection/score/tier 누적 기록

### 2-5. NarrativeScore 서사 품질 평가

Review 노드에서 Full 모드 전용 서사 평가 (LANGGRAPH_NARRATIVE_THRESHOLD=0.6):

| 메트릭 | 가중치 | 설명 |
|--------|--------|------|
| Hook | 40% | 첫 씬 흡인력 |
| 감정 | 25% | 감정 곡선 존재 |
| 반전 | 20% | 예상 전복 요소 |
| 톤 | 10% | 일관된 어조 |
| 정합성 | 5% | 논리적 연결 |

---

## 3. 핵심 설계 결정 (ADR)

| # | 질문 | 결정 | 근거 |
|---|------|------|------|
| D1 | LangChain 범위 | LangGraph만 | `langchain-core` 자동 포함, 풀 LangChain 불필요 |
| D2 | Gemini 호출 방식 | `google-genai` 유지 | Jinja2 템플릿 6종 재활용, 노드에서 래핑 |
| D3 | 단일 생성도 Graph? | **항상 Graph** | 이원화 방지, Quick=조건 분기로 Review/Revise 스킵 |
| D4 | Review 평가 | 규칙 + Gemini 혼합 | 규칙 먼저 → 통과 시 Gemini 스킵 (비용 절감) |
| D5 | Thread ID | `storyboard_id` | 자연스러운 매핑, 별도 ID 관리 불필요 |
| D6 | Gemini 호출 제한 | 최대 4회 (Draft 1 + Revise 3) | `MAX_REVISIONS=3`, 비용 통제 |
| D7 | LangFuse DB | 별도 PostgreSQL | LangFuse 자체 마이그레이션, 비즈니스 DB와 분리 |
| D8 | Creative Lab | 폐기 (선택지 C) | Script Graph로 대체 가능, Lab UI/라우터는 7-4에서 삭제 완료 |
| D9 | Multi-draft vs Concept Gate | **Concept Gate** | 같은 템플릿 3x는 다양성 부족, 컨셉 비교가 효율적 |
| D10 | 전환 원칙 | 점진적, 선택적 Agentic | 핵심 노드(Director, Research, Cinematographer)부터 전환 |

**비용 가드레일**: MAX_TOOL_CALLS=5, MAX_THINKING_STEPS=3, MAX_DEBATE_ROUNDS=2, DEBATE_TIMEOUT_SEC=60, CHECKPOINT_LOW=0.4, CHECKPOINT_HIGH=0.85

---

## 4. 구현 완료 요약

### Phase 9: LangGraph Migration (2026-02-13~17)

| Phase | 핵심 | 상태 |
|-------|------|------|
| **0. Foundation** | LangGraph + AsyncPostgresSaver + psycopg v3, 2-노드 PoC | [x] |
| **1. 동등 전환** | Draft→Review→Finalize 3노드, `/scripts/generate` Graph 교체, SSE | [x] |
| **1.5. 기능 확장** | Full 모드 확장, Revise 루프, Human Gate, Quick/Full 토글 | [x] |
| **2. Memory + Obs** | AsyncPostgresStore, LangFuse v3 Docker, Research/Learn 노드, 피드백 UI | [x] |
| **3. Creative 재평가** | 폐기 결정, creative_utils.py 데드코드 258줄 정리 | [x] |
| **4A. E2E Pipeline** | Script→Preflight→AutoRun 자동 체인, `pendingAutoRun` 시그널 | [x] |
| **4B. Agent Spec** | 에이전트 분류 체계, Director Agent, 12→13노드 | [x] |
| **4C. 고도화** | Director feedback 주입, Production 병렬화 (fan-out), Explain Node, 13→14노드 | [x] |
| **5A. Narrative** | Hook 구조 가이드, NarrativeScore, Review 3-tier 검증 | [x] |
| **5B. Concept Gate** | Critic 3컨셉 사용자 선택, concept_gate 노드, 14→15노드 | [x] |
| **5C. Transparency** | Pipeline Stepper, Agent Reasoning 패널, NarrativeScore 차트 | [x] |
| **5D. Feedback** | 프리셋 4종, Concept Gate 재생성/직접입력, 파라미터 피드백 | [x] |
| **5E. References** | URL/텍스트 소재 분석, SSRF 방어, Gemini 분석→research_brief | [x] |
| **5F. Director-as-Orchestrator** | director_plan + director_checkpoint 노드, Score-Based Routing, 15→17노드 | [x] |
| **5G. Pipeline 고도화** | MAX_REVISIONS 2→3, revision_history 누적, Checkpoint 임계값 튜닝 | [x] |

### Phase 10~14: True Agentic & Pipeline Refinement (2026-02-18 ~ 22)

| Phase | 핵심 | 상태 |
|-------|------|------|
| **10. ReAct & Tool-Calling** | Director ReAct, Gemini Function Calling (Research/Cinematographer) | [x] |
| **11~13. Architecture Refinement** | Quick/Full 모드 이원화 폐기 → `skip_stages` Stage-Level Skip 통합 | [x] |
| **14. ControlNet & IP-Adapter** | Pipeline 내 Pose/IP-Adapter 고도화 및 Seed Anchoring 적용 | [x] |

### Phase 10: True Agentic Architecture (2026-02-18)

| Phase | 핵심 | 테스트 | 상태 |
|-------|------|--------|------|
| **0. Benchmark** | 샘플 10건 + 자동화 스크립트, TDD | 18개 | [x] |
| **A. ReAct Loop** | Director ReAct, Review Self-Reflection, Writer Planning | 27개 | [x] |
| **B. Tool-Calling** | Gemini Function Calling, Research 5도구, Cinematographer 4도구 | 36개 | [x] |
| **C. Communication** | Agent Message Protocol, Director↔Production, Critic 토론 KPI 수렴 | 31개 | [x] |

**Phase 10 총 94개 테스트 추가 + 18개 벤치마크 = 112개**

### 리스크 대응

| 리스크 | 대응 |
|--------|------|
| 예측 불가능성 | KPI 수렴, Groupthink 감지, Hard Timeout, Fallback 경로 |
| 비용 | MAX_TOOL_CALLS=5, Quick 모드 스킵, Phase별 벤치마크 |
| 레이턴시 | Progressive SSE, ETA 표시 |
| State 비대화 | Sliding Window 10건, State Condensation, 토큰 예산 2000 |

---

## 5. 참고 자료

- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Human-in-the-loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- [LangFuse Self-Hosting](https://langfuse.com/docs/deployment/self-host)
- [Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [ReAct: Synergizing Reasoning and Acting (Yao et al., 2022)](https://arxiv.org/abs/2210.03629)
- 설계 원본 아카이브: [AGENTIC_PIPELINE_DETAIL.md](../../99_archive/features/AGENTIC_PIPELINE_DETAIL.md)
- Phase 10 상세 설계: [TRUE_AGENTIC_ARCHITECTURE_DETAIL.md](../../99_archive/features/TRUE_AGENTIC_ARCHITECTURE_DETAIL.md)
- Phase 10 실행 기록: [Phase 10 아카이브](../../99_archive/archive/ROADMAP_PHASE_10.md)
