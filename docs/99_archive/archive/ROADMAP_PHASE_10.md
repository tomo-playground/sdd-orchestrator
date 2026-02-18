# Phase 10: True Agentic Architecture — 아카이브

**완료일**: 2026-02-18
**목표**: DAG Workflow → 진정한 Agentic AI 전환. ReAct Loop, Tool-Calling, Agent Communication 도입.
**선행**: Phase 9 완료 (LangGraph 파이프라인 안정화) — **충족**.
**명세**: [TRUE_AGENTIC_ARCHITECTURE.md](../../01_product/FEATURES/TRUE_AGENTIC_ARCHITECTURE.md)

**진단**: 현재 15노드 파이프라인은 LangGraph를 사용하지만 실질은 "State Machine 기반 DAG Workflow". LLM이 자율적 의사결정, Tool Use, Planning, Self-Reflection, 에이전트 간 소통 **5대 Agentic 요건을 모두 미충족**.

**설계 완료** (2026-02-18): 기능 명세 작성, Gemini 크로스 리뷰 4대 리스크 대응 반영, A/B 벤치마크 샘플 10건 설계 완료. 구현 대기.

---

## Phase 0: Benchmark Baseline 수집

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 0 | 벤치마크 샘플 10건 + 자동화 스크립트 | `scripts/benchmark/` (run_benchmark.py, benchmark_samples.json, compare_results.py). BM-01~10 각 3회 Baseline 실행 (진행 중), LangFuse "baseline" 태그. TDD 18개 테스트, SSE 파싱 수정, Gemini safety filter 해결 완료 (2026-02-18) | [x] |

## Phase A: ReAct Loop + Self-Reflection (Level 1)

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 1 | Director ReAct Loop | Single-shot → Observe→Think→Act 루프 (최대 3 스텝). 사고 과정 기록 | [x] 2026-02-18 |
| 2 | Review Self-Reflection | 실패 시 원인 분석 + 구체적 수정 전략 수립 → revise에 전달 | [x] 2026-02-18 |
| 3 | Writer Planning Step | 즉시 생성 → 계획 수립(Hook 전략, 감정 곡선, 씬 배분) → 계획 기반 생성 | [x] 2026-02-18 |

## Phase B: Tool-Calling Agent (Level 2)

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 4 | Gemini Function Calling 인프라 | `tools/` 패키지, `define_tool()`, `call_with_tools()`, MAX_TOOL_CALLS 가드레일, ToolCallLog, LangFuse 통합 | [x] 2026-02-18 |
| 5 | Research Agent Tool-Calling | 고정 순회 → LLM이 필요한 도구 선택적 호출 (히스토리/URL/트렌딩/채널DNA). 5개 도구 (`search_topic_history`, `search_character_history`, `fetch_url_content`, `analyze_trending`, `get_group_dna`), `research_tool_logs` 상태 필드 추가 | [x] 2026-02-18 |
| 6 | Cinematographer Agent Tool-Calling | 고정 템플릿 → LLM이 태그 검증/호환성 체크/레퍼런스 검색 도구 호출. 4개 도구 (`validate_danbooru_tag`, `search_similar_compositions`, `get_character_visual_tags`, `check_tag_compatibility`), `cinematographer_tool_logs` 상태 필드 추가 | [x] 2026-02-18 |

## Phase C: Agent Communication (Level 3)

| # | 작업 | 핵심 | 상태 |
|---|------|------|------|
| 7 | Agent Message Protocol + State Condensation | AgentMessage TypedDict + 노드별 상태 압축 (컨텍스트 오염 방지). `messages.py`: format/condense/truncate 유틸리티, MAX_MESSAGE_WINDOW=10, MAX_CONTEXT_TOKENS=2000. ScriptState: `agent_messages`, `agent_summary` 필드 추가 | [x] 2026-02-18 |
| 8 | Director ↔ Production 양방향 소통 | 직접 피드백/응답 메시지 + Speculative Execution (레이턴시 대응) | [x] 2026-02-18 |
| 9 | Critic 실시간 토론 + KPI 수렴 | 3인 상호 비평 + NarrativeScore 기반 수렴 + Groupthink 방지 + Fallback | [x] 2026-02-18 |

---

## 리스크 대응 (Gemini 크로스 리뷰 반영)

- **예측 불가능성**: KPI 수렴 + Fallback
- **비용 ROI**: Phase별 A/B 테스트 필수
- **레이턴시**: Speculative Execution
- **State 비대화**: Condensation

[상세](../../01_product/FEATURES/TRUE_AGENTIC_ARCHITECTURE.md#6-리스크-대응-gemini-크로스-리뷰-반영)

---

## 5대 Agentic 요건 충족 결과

| # | 요건 | 구현 |
|---|------|------|
| 1 | 자율적 의사결정 | Director ReAct Loop, Critic 토론 |
| 2 | Tool Use | Research 5 tools, Cinematographer 4 tools |
| 3 | Planning | Writer Planning Step |
| 4 | Self-Reflection | Review Reflection |
| 5 | 에이전트 간 소통 | Message Protocol, Director↔Production 양방향, Critic 토론 |

**테스트**: 68개 전체 통과 (Phase A: 12, Phase B: 26, Phase C: 30)
